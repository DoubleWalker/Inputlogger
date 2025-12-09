# C:/Orchestrator/Raven2/Combat_Monitor/monitor.py
# (v3 - "CCTV 감시요원" / 제너레이터 실행기 아키텍처)

import time
import os
import traceback
import pyautogui
import keyboard
import win32api
import win32con
import numpy as np
import cv2
from threading import Event
from typing import List, Tuple, Optional, Dict, Any
from Orchestrator.Raven2.System_Monitor.config.sm_config import SystemState

# ❗️ 1. [참조] NightCrows의 BaseMonitor를 상속받아 호환성 확보
from Orchestrator.NightCrows.Combat_Monitor.monitor import BaseMonitor

# ❗️ 2. [필수] v3 "상황반장" 설정 파일 임포트
from .config import srm_config_raven2 as srm_config

# ❗️ 3. [공통] Raven2의 의존성들 (v1과 동일)
from Orchestrator.src.core.io_scheduler import IOScheduler, Priority
from Orchestrator.Raven2.Combat_Monitor.src.models.screen_info import CombatScreenInfo, ScreenState
from Orchestrator.Raven2.utils.screen_info import SCREEN_REGIONS, FIXED_UI_COORDS
from Orchestrator.Raven2.utils.image_utils import return_ui_location, compare_images
from Orchestrator.Raven2.Combat_Monitor.src.config.template_paths import get_template

class CombatMonitor(BaseMonitor):
    """
    [v3] 제너레이터(Generator) 기반 전투 모니터 ("CCTV 감시요원").
    srm_config_raven2.py (v3)에 정의된 "상황반장" 제너레이터 함수를 실행합니다.
    모든 I/O는 IOScheduler를 통해 비동기적으로 요청됩니다.
    """

    def __init__(self, monitor_id="SRM1", config=None, vd_name="VD1",
                 orchestrator=None, io_scheduler=None, shared_states=None):

        # [수정] 부모에게 shared_states 전달
        super().__init__(monitor_id, config, vd_name, orchestrator, io_scheduler, shared_states)

        if io_scheduler is None:
            raise ValueError(f"[{self.monitor_id}] io_scheduler must be provided!")
        self.io_scheduler = io_scheduler

        # [신규] 공유 상태 저장소 저장
        self.shared_states = shared_states if shared_states is not None else {}

        # 3. v1의 변수들 (config에서 로드)
        self.check_interval = self.config.get('check_interval', 0.5)
        self.confidence = self.config.get('confidence', 0.85)

        # 4. 모니터링 화면 리스트
        self.screens: List[CombatScreenInfo] = []
        self.stop_event: Optional[Event] = None

        # 5. v3 정책 맵 로드
        self.policy_map = srm_config.get_state_policies()

    def add_screen(self, window_id: str, region: Tuple[int, int, int, int], ratio: float = 1.0):
        """모니터링할 화면을 등록합니다."""

        # [신규] 공유 상태에 초기값 등록 (이미 있으면 건드리지 않음 - SM이 먼저 등록했을 수도 있음)
        if window_id not in self.shared_states:
            self.shared_states[window_id] = ScreenState.SLEEP

        # [수정] CombatScreenInfo 생성 시 _shared_state_ref 전달
        screen = CombatScreenInfo(
            window_id=window_id,
            region=region,
            ratio=ratio,
            _shared_state_ref=self.shared_states  # 참조 전달
        )

        # ❗️ v3: 제너레이터 실행을 위한 상태 변수들
        screen.active_generator = None  # "상황반장" 저장
        screen.yielded_instruction = None  # "다음 지시" 저장
        screen.last_result = None  # "지시 결과" 저장
        screen.wait_start_time = 0.0  # 'wait' 지시용 타이머

        self.screens.append(screen)
        print(f"[{self.monitor_id}] Screen registered - ID: {window_id}, State: {screen.current_state.name}")

    def force_reset_screen(self, screen_id: str):
        """
        [신규] Orchestrator에 의해 호출됨.
        지정된 화면의 모든 시퀀스를 강제로 중지하고 NORMAL 상태로 리셋합니다.
        """
        screen = next((s for s in self.screens if s.window_id == screen_id), None)

        if screen:
            print(f"INFO: [{self.monitor_id}] Screen {screen_id} is being forcibly reset by Orchestrator.")

            # 1. 진행 중인 모든 시퀀스 변수 초기화
            screen.policy_step = 0
            screen.policy_step_start_time = 0.0
            screen.retry_count = 0
            screen.s1_completed = False  # 파티 복귀 플래그 초기화
            if hasattr(screen, 'party_check_count'):
                del screen.party_check_count  # 파티 체크 카운터 삭제

            # 2. 상태를 NORMAL로 변경 (이로 인해 다음 틱부터는 _get_character_state_on_screen만 실행됨)
            self._change_state(screen, ScreenState.SLEEP)
        else:
            print(f"WARN: [{self.monitor_id}] force_reset_screen: Screen {screen_id} not found.")

    # =========================================================================
    # 🎯 1. [v3] 메인 루프 (v1의 거대 if/elif 제거)
    # =========================================================================

    def run_loop(self, stop_event: Event):
        """[v3] Orchestrator의 메인 루프. "감시요원"의 텅 빈 루프."""
        print(f"[{self.monitor_id}] v3 Generator Executor (CCTV 감시요원) run_loop started.")
        self.stop_event = stop_event

        while not stop_event.is_set():
            try:
                for screen in self.screens:
                    if stop_event.is_set():
                        break

                    # ❗️ 모든 로직을 '감시요원의 두뇌'(_handle_screen_state)에 위임
                    self._handle_screen_state(screen)

                # 루프 지연 (v1과 동일)
                if stop_event.wait(timeout=self.check_interval):
                    break

            except Exception as e:
                print(f"!!! [{self.monitor_id}] Unhandled exception in run_loop: {e} !!!")
                traceback.print_exc()
                if stop_event.wait(timeout=5.0):
                    break

        print(f"[{self.monitor_id}] v3 Generator Executor stopped.")

    # =========================================================================
    # 🎯 2. [v3] "감시요원의 두뇌" (핵심 실행기)
    # =========================================================================

    def get_current_state(self, screen_id: str) -> Optional[ScreenState]:
        """화면의 현재 상태 조회 (Orchestrator용)"""
        screen = next((s for s in self.screens if s.window_id == screen_id), None)
        if not screen:
            print(f"WARN: [{self.monitor_id}] get_current_state: Screen {screen_id} not found.")
            return None
        return screen.current_state

    def _handle_screen_state(self, screen: CombatScreenInfo):
        """[v3] "감시요원"이 화면 상태를 보고 '상황반장'을 부르거나 '지시'를 처리합니다."""

        state = screen.current_state

        # 2. [교통 정리] 내 담당 상태(ScreenState)가 아니면 무시
        if not isinstance(state, ScreenState):
            # SM이 작업 중인 상태 (SystemState) -> SRM은 건드리지 않음
            # print(f"[{screen.window_id}] SM 작업 중({state}). SRM 대기.") # 디버깅용
            return

            # 3. [정상 로직] 내 담당 상태면 하던 일 계속
        if state in [ScreenState.SLEEP, ScreenState.AWAKE]:
            visual_status = self.check_status(screen)
            if visual_status != state:
                # 상태 변경 시에도 프로퍼티를 통해 공유 딕셔너리가 업데이트됨
                self._change_state(screen, visual_status)
            return

        # --- 2. '정책 실행' 상태 (DEAD, ABNORMAL, ...) ---

        # 2a. 현재 '상황반장'이 없으면 새로 할당
        if screen.active_generator is None:
            policy = self.policy_map.get(state)
            if policy and 'generator' in policy:
                generator_func = policy['generator']
                # ❗️ "상황반장"(generator_func)을 호출하여 "지시"를 받을 준비
                screen.active_generator = generator_func(screen)
                screen.yielded_instruction = None
                screen.last_result = None
                print(f"[{screen.window_id}] '상황반장' {generator_func.__name__} 배정됨.")
            else:
                # 정책이 없으면 'SLEEP'로 리셋
                print(f"WARN: [{screen.window_id}] {state.name} 상태의 '상황반장'을 찾을 수 없음. SLEEP로 리셋.")
                self._change_state(screen, ScreenState.SLEEP)
                return

        # 2b. "상황반장"에게 다음 지시를 받을 차례인가?
        if screen.yielded_instruction is None:
            try:
                # ❗️ "반장님, 이전 결과(last_result)입니다. 다음 지시(yield) 내려주세요."
                #
                instruction = screen.active_generator.send(screen.last_result)
                screen.last_result = None  # 이전 결과 비우기
                screen.yielded_instruction = instruction

            except StopIteration:
                # "상황반장"이 전화를 끊음 (임무 완수)
                print(f"INFO: [{screen.window_id}] '상황반장' 임무 완료 (StopIteration).")
                self._on_sequence_complete(screen)  # -> 'RECOVERING' 등으로 상태 전이
                return

            except Exception as e:
                # "상황반장"이 로직 수행 중 오류 발생
                print(f"ERROR: [{screen.window_id}] '상황반장' 임무 실패: {e}")
                traceback.print_exc()
                self._on_sequence_failed(screen, e)  # -> 'SLEEP' 등으로 상태 전이
                return

                # 2c. "상황반장"의 지시(instruction)를 처리할 차례인가?
        if screen.yielded_instruction:
                    try:
                        # ❗️ "지시를 처리하고, 완료 여부(is_done)와 결과(result)를 받아옵니다."
                        is_done, result = self._process_instruction(screen, screen.yielded_instruction)

                        if is_done:
                            # 지시가 '완료'되었으면
                            screen.yielded_instruction = None  # 다음 지시를 받을 수 있도록 비움
                            screen.last_result = result  # 다음 'send'를 위해 결과 저장

                    except Exception as e:
                        # 🚨 [수정됨] 지시 수행 중 에러(타임아웃 등) 발생 시 처리
                        print(f"WARN: [{screen.window_id}] 지시 수행 실패 ({e}). 시퀀스를 실패 처리합니다.")

                        # 지시서 비우기 (중요: 안 비우면 다음 루프에서 또 실행함)
                        screen.yielded_instruction = None

                        # 시퀀스 실패 로직 호출 (상태 전이 발생 -> 예: SLEEP으로 리셋)
                        self._on_sequence_failed(screen, e)

    # =========================================================================
    # 🎯 3. [v3] "지시 처리기" (Dispatcher)
    # =========================================================================

    def _process_instruction(self, screen: CombatScreenInfo, instruction: Dict[str, Any]) -> Tuple[bool, Any]:
        """
        [v3] "상황반장"이 'yield'한 '지시'를 해석하고 처리합니다.
        '지시'가 완료되면 (True, result)를,
        '대기' 중이면 (False, None)을 반환합니다.
        (이 함수는 '비동기'입니다. 절대로 'sleep'하면 안 됩니다.)
        """
        op = instruction.get('operation')

        # --- 1. [I/O 지시] (Fire-and-Forget, 즉시 완료) ---
        if op in ['click', 'click_at', 'click_fixed', 'key_press', 'drag']:
            # ❗️ "경찰(IOScheduler)에게 요청만 하고, 지시 자체는 '완료'로 간주"
            #    (v3 config는 I/O 후에 항상 'wait_duration'을 yield하도록 설계됨)
            #
            self.io_scheduler.request(
                component=self.monitor_id,
                screen_id=screen.window_id,
                action=lambda s=screen, i=instruction: self._do_io_action(s, i),
                priority=Priority.NORMAL
            )
            return True, None  # (완료, 결과 없음)

        # --- 2. [대기 지시] (Stateful Wait, 비동기) ---
        elif op == 'wait_duration':
            if screen.wait_start_time == 0.0:
                screen.wait_start_time = time.time()  # 타이머 시작

            elapsed = time.time() - screen.wait_start_time
            if elapsed >= instruction['duration']:
                screen.wait_start_time = 0.0  # 타이머 리셋
                return True, None  # (완료, 결과 없음)
            else:
                return False, None  # (아직 대기 중)

        # --- 3. [템플릿 대기 지시] (Stateful Check, 비동기) ---
        elif op == 'wait_for_template':
            pos = self._helper_find_template_once(screen, instruction['template_key'])
            if pos:
                screen.wait_start_time = 0.0  # 타이머 리셋
                return True, pos  # (완료, 찾은 좌표 반환)

            # 타이머 시작
            if screen.wait_start_time == 0.0:
                screen.wait_start_time = time.time()

            # 타임아웃 체크 로직 개선
            timeout = instruction.get('timeout')  # timeout 키가 없거나 None이면 무한 대기

            if timeout is not None and timeout > 0:
                elapsed = time.time() - screen.wait_start_time
                if elapsed >= timeout:
                    screen.wait_start_time = 0.0  # 타이머 리셋

                    # [신규] optional=True이면 예외 없이 넘어감 (못 찾았지만 진행)
                    if instruction.get('optional', False):
                        print(
                            f"WARN: [{screen.window_id}] Optional template '{instruction['template_key']}' not found. Proceeding.")
                        return True, None

                        # 필수 요소라면 예외 발생
                    raise Exception(f"Template '{instruction['template_key']}' timed out after {timeout}s")

            # 타임아웃이 없거나(무한대기), 시간 안 지났으면 계속 대기
            return False, None

        # --- 4. [v3 config 전용 지시] (복합 지시) ---
        elif op == 'click_and_get_pos':
            pos = self._helper_find_template_once(screen, instruction['template_key'])
            if pos:
                # ❗️ I/O 요청을 즉시 보냄
                self._do_io_action(screen, {'operation': 'click_at', 'x': pos[0], 'y': pos[1]})
                return True, pos  # (완료, 클릭한 좌표 반환)

            # (타임아웃 로직은 'wait_for_template'과 동일하게)
            if screen.wait_start_time == 0.0: screen.wait_start_time = time.time()
            if time.time() - screen.wait_start_time > 5.0:  # (하드코딩된 5초 타임아웃)
                screen.wait_start_time = 0.0
                raise Exception(f"click_and_get_pos '{instruction['template_key']}' timed out")
            return False, None  # (아직 대기 중)

        elif op == 'check_pixel_loop':
            # ❗️ v1의 'is_at_combat_spot'을 '비동기'로 실행
            if screen.wait_start_time == 0.0: screen.wait_start_time = time.time()

            is_match = self._helper_check_pixel_once(screen, instruction)
            if is_match:
                screen.wait_start_time = 0.0
                return True, True  # (완료, 찾음)

            if time.time() - screen.wait_start_time > instruction['duration']:
                screen.wait_start_time = 0.0
                return True, False  # (완료, 못 찾음)

            return False, None  # (아직 대기 중)

        # --- 5. 알 수 없는 지시 ---
        else:
            raise Exception(f"알 수 없는 지시(operation)입니다: {op}")

    # =========================================================================
    # 🎯 4. [v3] "경찰" (IOScheduler가 호출할 실제 I/O)
    # =========================================================================

    def _do_io_action(self, screen: CombatScreenInfo, instruction: Dict[str, Any]):
        """
        [v3] "경찰"의 실제 행동. IOScheduler가 호출합니다.
        (v1의 pyautogui/keyboard 로직)
        """
        op = instruction.get('operation')

        try:
            if op == 'click':
                pos = self._helper_find_template_once(screen, instruction['template_key'])
                if pos:
                    pyautogui.click(pos[0], pos[1])
                elif not instruction.get('optional', False):
                    print(f"ERROR: [{screen.window_id}] 'click' 지시 실패 (템플릿 없음): {instruction['template_key']}")

            elif op == 'click_at':
                pyautogui.click(instruction['x'], instruction['y'])

            elif op == 'click_fixed':
                coords = self._helper_get_coords(screen, instruction['coord_key'])
                if coords:
                    pyautogui.click(coords[0], coords[1])
                elif not instruction.get('optional', False):
                    print(f"ERROR: [{screen.window_id}] 'click_fixed' 지시 실패 (좌표 없음): {instruction['coord_key']}")


            elif op == 'key_press':

                # 🌟 [1단계] 포커스 확보

                safe_coords = self._helper_get_coords(screen, 'safe_click_point')

                if safe_coords:

                    pyautogui.click(safe_coords[0], safe_coords[1])

                    time.sleep(0.1)  # 포커스 안착 대기

                else:

                    print(f"ERROR: [{screen.window_id}] safe_click_point not found! key_press may fail.")

                    return  # 포커스 실패 시 키 입력 중단

                # 🌟 [2단계] 실제 키 입력 (포커스 확보된 상태에서)

                keyboard.press_and_release(instruction['key'])

            elif op == 'drag':
                # v1의 드래그 로직 (win32api 사용)
                pyautogui.moveTo(instruction['start_x'], instruction['start_y'])
                time.sleep(0.3)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
                time.sleep(0.1)
                pyautogui.moveTo(instruction['end_x'], instruction['end_y'], duration=instruction['duration'])
                time.sleep(0.1)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)

        except Exception as e:
            print(f"ERROR: [{screen.window_id}] _do_io_action ({op}) 실패: {e}")
            if op == 'drag':  # 드래그 실패 시 마우스 강제 업
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)

    # =========================================================================
    # 🎯 5. [v3] 상태 전이 (Transitions)
    # =========================================================================

    def _change_state(self, screen: CombatScreenInfo, new_state: ScreenState):
        """[v3] 화면 상태를 변경하고 "상황반장"을 해임합니다."""
        if screen.current_state == new_state:
            return

        print(f"INFO: [{screen.window_id}] State Transition: {screen.current_state.name} -> {new_state.name}")
        screen.current_state = new_state

        # ❗️ [중요] 상태가 바뀌면, 기존 "상황반장"은 즉시 해임
        screen.active_generator = None
        screen.yielded_instruction = None
        screen.last_result = None
        screen.wait_start_time = 0.0

    def _on_sequence_complete(self, screen: CombatScreenInfo):
        """'상황반장'이 임무를 완수했을 때 다음 상태로 전이합니다."""
        policy = self.policy_map.get(screen.current_state)
        next_state = ScreenState.SLEEP  # 기본값

        if policy and 'transitions' in policy:
            next_state = policy['transitions'].get('complete', ScreenState.SLEEP)

        self._change_state(screen, next_state)

    def _on_sequence_failed(self, screen: CombatScreenInfo, error: Exception):
        """'상황반장'이 임무에 실패(Exception)했을 때 다음 상태로 전이합니다."""
        policy = self.policy_map.get(screen.current_state)
        next_state = ScreenState.SLEEP  # 기본값

        if policy and 'transitions' in policy:
            next_state = policy['transitions'].get('fail', ScreenState.SLEEP)

        self._change_state(screen, next_state)

    # =========================================================================
    # 🎯 6. [v1 계승] 헬퍼 함수들 (내부 도구)
    # =========================================================================
        # ❗️❗️ [필수 수정] v2의 '템플릿 키 -> 경로' 변환 헬퍼가 누락되었습니다.
    def _get_template_path_from_key(self, template_key: str, window_id: str) -> Optional[str]:
            """
            [v2에서 복원] 'DEATH_RETURN_BUTTON' 같은 '키'를 실제 파일 경로로 변환합니다.
            (srm_config_raven2.py의 모든 키를 여기서 매핑해야 합니다)
            """
            return get_template(window_id, template_key)

    def check_status(self, screen_info: CombatScreenInfo) -> ScreenState:
        """[v1 계승] 'SLEEP'/'AWAKE' 상태에서 사용되는 기본 상태 검사기"""
        try:
            screen_img = self.orchestrator.capture_screen_safely(screen_info.window_id)
            if screen_img is None:
                return screen_info.current_state

            # (v1의 템플릿 검사 로직)
            if self._helper_find_template_once(screen_info, 'DEAD_TEMPLATE', screen_img):
                return ScreenState.DEAD
            if self._helper_find_template_once(screen_info, 'ABNORMAL_TEMPLATE', screen_img):
                return ScreenState.ABNORMAL
            if self._helper_find_template_once(screen_info, 'AWAKE_TEMPLATE', screen_img):
                return ScreenState.AWAKE

            return ScreenState.SLEEP

        except Exception as e:
            print(f"[{screen_info.window_id}] Error in check_status: {e}")
            return screen_info.current_state

    def _helper_find_template_once(self, screen: CombatScreenInfo, template_key: str,
                                   screen_img: Optional[np.ndarray] = None) -> Optional[Tuple[int, int]]:
        """[v3] 템플릿을 '한 번'만 찾아보는 비동기 헬퍼"""
        template_path = self._get_template_path_from_key(template_key, screen.window_id)  # (가상)
        if not template_path or not os.path.exists(template_path):
            return None

        if screen_img is None:
            screen_img = self.orchestrator.capture_screen_safely(screen.window_id)
        if screen_img is None:
            return None

        return return_ui_location(template_path, screen.region, self.confidence, screen_img)

    def _helper_check_pixel_once(self, screen: CombatScreenInfo, instruction: Dict[str, Any]) -> bool:
        """[v3] 픽셀을 '한 번'만 체크하는 비동기 헬퍼 (v1 is_at_combat_spot 기반)"""
        coords = self._helper_get_coords(screen, instruction['coord_key'])
        if not coords:
            return False

        try:
            return pyautogui.pixelMatchesColor(coords[0], coords[1], instruction['color'],
                                               tolerance=instruction['tolerance'])
        except OSError:
            return False  # (pyautogui의 일반적인 예외)
        except Exception as e:
            print(f"ERROR: [{screen.window_id}] _helper_check_pixel_once 실패: {e}")
            return False

    def _helper_get_coords(self, screen: CombatScreenInfo, coord_key: str) -> Optional[Tuple[int, int]]:
        """[v3] FIXED_UI_COORDS에서 절대 좌표를 계산하는 헬퍼"""
        if screen.window_id in FIXED_UI_COORDS and coord_key in FIXED_UI_COORDS[screen.window_id]:
            relative_coords = FIXED_UI_COORDS[screen.window_id][coord_key]
            screen_x, screen_y = screen.region[0], screen.region[1]
            return (screen_x + relative_coords[0], screen_y + relative_coords[1])
        return None

    def stop(self):
        """[v1 계승] Orchestrator의 종료 호출"""
        print(f"[{self.monitor_id}] CombatMonitor stop() method called.")
        # (BaseMonitor의 stop이 있다면 호출)
        # super().stop()


# =============================================================================
# 🧪 (v1의 __main__ 테스트 스텁은 v3에서도 동일하게 작동해야 함)
# =============================================================================
if __name__ == "__main__":
    print("CombatMonitor 모듈 직접 실행 테스트 (v3 제너레이터 모델)")

    # ❗️ [가상] srm_config_raven2.py (v3)가 v2와 동일한 정책 맵을 제공한다고 가정
    # (실제로는 srm_config.py에 get_state_policies()가 구현되어 있어야 함)
    try:
        if not hasattr(srm_config, 'get_state_policies'):
            print("ERROR: srm_config_raven2.py에 get_state_policies()가 없습니다.")
            print("       v3 config 파일이 올바르게 구현되었는지 확인하세요.")
            exit()
    except Exception as e:
        print(f"ERROR: srm_config_raven2.py 임포트 중 오류: {e}")
        exit()

    monitor = CombatMonitor()  # (v1 테스트 스텁은 io_scheduler 없이 호출함 - 실제론 실패)
    print("테스트 스텁 실행... (실제 실행을 위해서는 Orchestrator가 필요합니다)")