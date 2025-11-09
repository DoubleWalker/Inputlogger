# Orchestrator/NightCrows/Combat_Monitor/monitor.py
# add_screen 방식을 사용하고, config/template_paths.py 에서 템플릿 경로를 읽도록 수정된 버전

import pyautogui
import traceback
import cv2
import time
import threading
import os
import keyboard
import win32api
import win32con
import sys # if __name__ == "__main__" 에서 경로 설정 위해 추가
import numpy as np
from dataclasses import dataclass
from typing import Tuple, List, Dict, Optional
from Orchestrator.NightCrows.utils import image_utils
from Orchestrator.NightCrows.utils.screen_info import FIXED_UI_COORDS
from Orchestrator.src.core.io_scheduler import IOScheduler, Priority  # ← 추가!
from .config import srm_config, template_paths
from .config.srm_config import ScreenState
from enum import Enum, auto

class Location(Enum):
    """캐릭터의 주요 위치"""
    ARENA = auto()          # 아레나 (또는 특정 던전 내부)
    FIELD = auto()          # 필드 (또는 마을 등 안전 지역)
    UNKNOWN = auto()        # 알 수 없음

# (Placeholder - BaseMonitor 클래스는 Orchestrator에서 제공될 것으로 가정)
class BaseMonitor:
    """오케스트레이터와 호환되는 모니터의 기본 클래스"""

    def __init__(self, monitor_id: str, config: Optional[Dict], vd_name: str, orchestrator=None):
        self.orchestrator = orchestrator
        self.monitor_id = monitor_id
        self.config = config if isinstance(config, dict) else {}
        self.vd_name = vd_name

    def run_loop(self, stop_event: threading.Event):
        """Orchestrator가 스레드에서 실행할 메인 루프. stop_event로 종료 제어."""
        raise NotImplementedError("Subclasses should implement this method.")

    def stop(self):
        """Orchestrator가 모니터 종료 시 호출할 메서드. 리소스 정리 등."""
        print(f"INFO: Stopping BaseMonitor for {self.monitor_id}")

# --- Enum 정의 ---
class CharacterState(Enum):
    """캐릭터의 주요 상태"""
    NORMAL = auto()         # 정상
    HOSTILE_ENGAGE = auto() # 적대적 교전
    DEAD = auto()           # 사망

# --- 화면 정보 데이터 클래스 ---
@dataclass

class ScreenMonitorInfo:
    """모니터링할 개별 화면의 정보"""
    screen_id: str
    region: Tuple[int, int, int, int]
    current_state: ScreenState = ScreenState.NORMAL
    retry_count: int = 0
    last_state_change_time: float = 0.0
    s1_completed: bool = False  # ← 새로 추가!
    # 💥 (신규) 범용 실행기를 위한 변수
    policy_step: int = 0
    policy_step_start_time: float = 0.0


# ----------------------------------------------------------------------------
# Combat Monitor 클래스 구현
# ----------------------------------------------------------------------------
class CombatMonitor(BaseMonitor):
    """
    여러 NightCrows 화면의 캐릭터 상태를 모니터링합니다 (add_screen으로 추가).
    도주, 부활, 물약 구매, 웨이포인트 네비게이션을 처리합니다.
    Orchestrator에 의해 run_loop 및 stop_event로 제어됩니다.
    템플릿 경로는 config/template_paths.py에서 읽어옵니다.
    """

    def __init__(self, monitor_id="SRM1", config=None, vd_name="VD1", orchestrator=None,
                 io_scheduler=None):  # ← io_scheduler 추가!
        """CombatMonitor 초기화."""
        super().__init__(monitor_id, config, vd_name, orchestrator)

        # ⭐ IOScheduler 주입
        if io_scheduler is None:
            raise ValueError(f"[{self.monitor_id}] io_scheduler must be provided!")
        self.io_scheduler = io_scheduler

        self.location_flag: Location = Location.UNKNOWN
        self.death_count: int = 0
        self.current_wp: int = 0
        self.max_wp: int = 0
        self.stop_event = None

        self.screens: List[ScreenMonitorInfo] = []
        self.confidence = self.config.get('confidence', 0.75)

        # 필수 템플릿 경로 로드
        self.arena_template_path = getattr(template_paths, 'ARENA_TEMPLATE', None)
        self.dead_template_path = getattr(template_paths, 'DEAD_TEMPLATE', None)
        self.hostile_template_path = getattr(template_paths, 'HOSTILE_TEMPLATE', None)

        if not all([self.arena_template_path, self.dead_template_path, self.hostile_template_path]):
            print(f"WARNING: [{self.monitor_id}] Essential template attributes (ARENA, DEAD, HOSTILE) "
                  f"not found in template_paths module or config. State detection might fail.")

    def add_screen(self, screen_id: str, region: Tuple[int, int, int, int]):
        """모니터링할 화면 영역과 ID를 등록합니다."""
        if not isinstance(screen_id, str) or not screen_id:
             print(f"ERROR: [{self.monitor_id}] Invalid screen_id '{screen_id}' received. Skipping.")
             return
        if not isinstance(region, tuple) or len(region) != 4:
             print(f"ERROR: [{self.monitor_id}] Invalid region '{region}' for screen '{screen_id}'. Skipping.")
             return
        if any(s.screen_id == screen_id for s in self.screens):
            print(f"WARNING: [{self.monitor_id}] Screen ID '{screen_id}' already added. Skipping.")
            return

        screen = ScreenMonitorInfo(screen_id=screen_id, region=region)
        self.screens.append(screen)
        print(f"INFO: [{self.monitor_id}] Screen added: ID={screen_id}, Region={region}")

    def _load_template(self, template_path: Optional[str]) -> Optional[cv2.typing.MatLike]:
        """템플릿 이미지를 로드하고 유효성을 검사합니다."""
        if not template_path or not isinstance(template_path, str):
             return None
        if not os.path.exists(template_path):
             print(f"ERROR: [{self.monitor_id}] Template file not found: {template_path}")
             return None
        try:
            template = cv2.imread(template_path)
            if template is None:
                print(f"ERROR: [{self.monitor_id}] Failed to load template (imread returned None): {template_path}")
            return template
        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Exception loading template {template_path}: {e}")
            return None

    def _get_character_state_on_screen(self, screen: ScreenMonitorInfo) -> CharacterState:
        """지정된 화면 영역의 캐릭터 상태를 화면별 템플릿을 사용하여 확인합니다."""
        if not screen or not screen.region:
            print(f"ERROR: [{self.monitor_id}] Invalid screen object for state check.")
            return CharacterState.NORMAL

        try:
            screenshot = self.orchestrator.capture_screen_safely(screen.screen_id)
            if screenshot is None:
                print(f"ERROR: [{self.monitor_id}] Failed screenshot (Screen: {screen.screen_id}).")
                return CharacterState.NORMAL
        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Failed screenshot (Screen: {screen.screen_id}): {e}")
            return CharacterState.NORMAL

        try:
            # 템플릿 경로들을 한 번만 가져오기
            dead_template_path = template_paths.get_template(screen.screen_id, 'DEAD') or self.dead_template_path
            hostile_template_path = template_paths.get_template(screen.screen_id,
                                                                'HOSTILE') or self.hostile_template_path

            # DEAD 상태 확인
            dead_template = self._load_template(dead_template_path)
            if dead_template is not None and image_utils.compare_images(screenshot, dead_template,
                                                                        threshold=self.confidence):
                return CharacterState.DEAD

            # HOSTILE 상태 확인 (재선언 제거)
            if hostile_template_path is not None:
                hostile_template = self._load_template(hostile_template_path)
                # ... 나머지 로직
                if hostile_template is not None:
                    # 연속 샘플링 (최대 3회, 각 0.1초 간격)
                    max_samples = 3
                    sample_interval = 0.1

                    for sample_idx in range(max_samples):
                        # 새 스크린샷 캡처
                        try:
                            current_screenshot = self.orchestrator.capture_screen_safely(screen.screen_id)
                            if current_screenshot is None:
                                continue

                            # 템플릿 매칭 시도
                            if image_utils.compare_images(current_screenshot, hostile_template,
                                                          threshold=self.confidence):
                                # 로그 추가 (어떤 샘플에서 감지되었는지)
                                print(
                                    f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: HOSTILE detected on sample {sample_idx + 1}/{max_samples}")
                                return CharacterState.HOSTILE_ENGAGE
                        except Exception as e:
                            print(f"ERROR: [{self.monitor_id}] Error during HOSTILE sampling {sample_idx + 1}: {e}")

                        # 중지 신호 확인 (필요시)
                        if sample_idx < max_samples - 1:  # 마지막 샘플이 아니면 대기
                            time.sleep(sample_interval)

            # HOSTILE 감지 실패 시 NORMAL 반환 (기존과 동일)
            return CharacterState.NORMAL

        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] State check error (Screen: {screen.screen_id}): {e}")
            traceback.print_exc()
            return CharacterState.NORMAL

    def _notify_s1_completion(self):
        """S1 완료시 대기 중인 다른 화면들에게 알림"""
        print(f"INFO: [{self.monitor_id}] S1 party gathering completed! Notifying waiting screens...")

        for screen in self.screens:
            if screen.screen_id != 'S1' and screen.current_state == ScreenState.RETURNING:
                # 대기 중인 화면에 완료 플래그 설정
                screen.s1_completed = True
                print(f"INFO: [{self.monitor_id}] Notified {screen.screen_id} that S1 gathering is completed")

    def _is_character_in_arena(self, screen: ScreenMonitorInfo) -> bool:
        """지정된 화면을 사용하여 캐릭터가 아레나에 있는지 확인합니다."""
        if not screen or not screen.region:
            print(f"ERROR: [{self.monitor_id}] Invalid screen object for arena check.")
            return False

        arena_template_path = template_paths.get_template(screen.screen_id, 'ARENA') or self.arena_template_path
        arena_template = self._load_template(arena_template_path)
        if arena_template is None:
            return False # 템플릿 없으면 필드로 간주

        try:
            screen_capture = self.orchestrator.capture_screen_safely(screen.screen_id)
            if screen_capture is None:
                print(f"ERROR: [{self.monitor_id}] Failed screenshot for arena check (Screen: {screen.screen_id}).")
                return False
            return image_utils.compare_images(screen_capture, arena_template, threshold=self.confidence)
        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Exception during arena check (Screen: {screen.screen_id}): {e}")
            return False

    def _do_s1_emergency_return(self, screen: ScreenMonitorInfo):
        """S1의 긴급 귀환 IO 시퀀스 (스케줄러가 호출)"""
        try:
            print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Executing emergency return IO...")
            image_utils.set_focus(screen.screen_id, delay_after=0.2)
            keyboard.press_and_release('esc')
            time.sleep(0.3)
            # _click_relative는 내부에 time.sleep을 포함하므로 IO 스케줄러에서 실행하기 적합
            self._click_relative(screen, 'flight_button', delay_after=1.0)
        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: Exception in _do_s1_emergency_return: {e}")
            traceback.print_exc()

    def _change_state(self, screen: ScreenMonitorInfo, new_state: ScreenState):
        """화면 상태 변경 및 관련 정보 업데이트"""
        old_state = screen.current_state
        screen.current_state = new_state
        screen.last_state_change_time = time.time()

        # 특정 상태에서는 retry_count 초기화
        if new_state != old_state:
            screen.retry_count = 0

        # ★ 새로 추가: 누군가 HOSTILE되면 S1을 BUYING_POTIONS로 강제 변경
        if (new_state == ScreenState.HOSTILE and
                screen.screen_id != 'S1' and
                self.location_flag == Location.FIELD):  # ← 이 조건 추가!

            s1_screen = next((s for s in self.screens if s.screen_id == 'S1'), None)
            if s1_screen and s1_screen.current_state == ScreenState.NORMAL:
                 print(
                    f"INFO: [{self.monitor_id}] S1 emergency town return due to {screen.screen_id} attack (FIELD context)")

                 # 🚨 [수정] 직접 IO 실행 대신, 스케줄러에 요청
                 self.io_scheduler.request(
                     component=self.monitor_id,
                     screen_id=s1_screen.screen_id,
                     action=lambda: self._do_s1_emergency_return(s1_screen),
                     priority=Priority.HIGH  # 다른 캐릭터가 공격받는 상황이므로 HIGH
                 )

                 s1_screen.current_state = ScreenState.BUYING_POTIONS
                 s1_screen.last_state_change_time = time.time()
                 s1_screen.retry_count = 0

            print(
                f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: State changed: {old_state.name} -> {new_state.name}")

    def _check_template_present(self, screen: ScreenMonitorInfo, template_key: str) -> bool:
        """범용 실행기가 'wait' operation을 위해 사용하는 템플릿 검사기"""
        template_path = template_paths.get_template(screen.screen_id, template_key)
        if not template_path:
            # config에 템플릿 키가 없으면, 키 자체가 템플릿 명이라고 가정 (예: 'DEAD_TEMPLATE')
            template_path = getattr(template_paths, template_key, None)

        if not template_path or not os.path.exists(template_path):
            print(f"WARN: [{self.monitor_id}] _check_template_present: Template not found for key '{template_key}'")
            return False

        screenshot = self.orchestrator.capture_screen_safely(screen.screen_id)
        if screenshot is None:
            return False

        return image_utils.is_image_present(template_path, screen.region, self.confidence, screenshot)

    def _do_policy_action(self, screen: ScreenMonitorInfo, action: dict):
        """
        범용 실행기가 요청한 'operation'을 IO 스케줄러가 실제로 실행하는 함수.
        (예: 클릭, 키 입력 등)
        """
        try:
            operation = action.get('operation')
            print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Executing policy action: {operation}")

            if operation == 'click':
                # ... (기존 click 로직) ...
                template_key = action.get('template')
                if not template_key:
                    print(f"ERROR: [{self.monitor_id}] 'click' operation missing 'template' key")
                    return

                # 템플릿 경로 찾기
                template_path = template_paths.get_template(screen.screen_id, template_key)
                if not template_path:
                    template_path = getattr(template_paths, template_key, None)

                if not template_path or not os.path.exists(template_path):
                    print(f"ERROR: [{self.monitor_id}] Template not found for key '{template_key}'")
                    return

                # 스크린샷 및 위치 찾기
                screenshot = self.orchestrator.capture_screen_safely(screen.screen_id)
                location = image_utils.return_ui_location(template_path, screen.region, self.confidence, screenshot)

                if location:
                    pyautogui.click(location)
                else:
                    print(f"WARN: [{self.monitor_id}] Failed to find template '{template_key}' for click")

            elif operation == 'key_press':
                # ... (기존 key_press 로직) ...
                key = action.get('key')
                if key:
                    keyboard.press_and_release(key)
                else:
                    print(f"ERROR: [{self.monitor_id}] 'key_press' operation missing 'key'")

            # --- 🚀 [추가된 부분] 'execute_subroutine' operation 지원 ---
            elif operation == 'execute_subroutine':
                subroutine_name = action.get('name')
                if subroutine_name == '_do_flight':
                    # _do_flight 함수는 IO 로직(클릭)을 포함하므로
                    # io_scheduler가 실행하는 이 곳에 있는 것이 맞습니다.
                    self._do_flight(screen)
                # (추후 다른 서브루틴 추가 가능)
                # elif subroutine_name == '_another_complex_task':
                #     self._another_complex_task(screen)
                else:
                    print(f"ERROR: [{self.monitor_id}] Unknown subroutine name '{subroutine_name}'")
            # --- 'execute_subroutine' 지원 종료 ---

            elif operation == 'set_focus':
                if not image_utils.set_focus(screen.screen_id, delay_after=0.5):
                    print(f"ERROR: [{self.monitor_id}] Failed to set focus on screen {screen.screen_id}")

            # --- 🚀 [기존] 'click_relative' operation 지원 (들여쓰기 수정됨) ---
            elif operation == 'click_relative':
                key = action.get('key')
                if key:
                    # _click_relative 내부의 delay_after는 0으로 설정합니다.
                    # 실제 delay는 이 함수 마지막의 'delay_after' 로직이 처리합니다.
                    self._click_relative(screen, key, delay_after=0.0)
                else:
                    print(f"ERROR: [{self.monitor_id}] 'click_relative' operation missing 'key'")
            # --- 'click_relative' 지원 종료 ---

            # (추후 'drag', 'scroll' 등 다른 _do_... 원자적 동작 추가 가능)

            # YAML에 정의된 delay가 있다면 IO 실행 후 대기
            delay = action.get('delay_after', 0)
            if delay > 0:
                time.sleep(delay)

        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Exception in _do_policy_action: {e}")
            traceback.print_exc()

    def _execute_policy_step(self, screen: ScreenMonitorInfo):
        """
        [범용 실행기]
        현재 상태의 정책을 srm_config에서 읽어, 'policy_step'에 맞는 행동을 실행/검사합니다.
        (🚀 _determine_initial_location 로직이 통합된 버전)
        """

        # 1. 현재 상태의 "매뉴얼"을 가져옴
        policy = srm_config.get_state_policy(screen.current_state)

        # 2. 매뉴얼이 'sequence' 타입이 아니면 실행기 대상이 아님
        if policy.get('action_type') != 'sequence':
            print(f"WARN: [{self.monitor_id}] {screen.current_state.name} is not a sequence state.")
            return

        # 🚀 [신규] INITIALIZING 상태 특별 처리 (S2-S5 대기 로직)
        # S1 (리더)을 제외한 모든 화면은 S1이 위치를 확정할 때까지 여기서 대기합니다.
        if screen.current_state == ScreenState.INITIALIZING and screen.screen_id != 'S1':
            if self.location_flag == Location.UNKNOWN:
                # S1이 아직 작업 중이므로, 이 화면은 대기
                print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Waiting for S1 to determine location...")
                return  # ★★★ 함수 즉시 종료 (아무것도 안 함)
            else:
                # S1이 작업을 마쳤음 (location_flag가 ARENA 또는 FIELD로 설정됨)
                print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: S1 finished. Moving to NORMAL state.")
                self._change_state(screen, ScreenState.NORMAL)
                screen.policy_step = 0  # 리셋
                return  # ★★★ 상태 변경 후 즉시 종료
        # (S1이거나, INITIALIZING 상태가 아닌 경우에만 아래 로직으로 진행)

        # 3. 현재 "스텝 번호"와 "지시서 목록"을 가져옴
        step_index = screen.policy_step
        actions = policy.get('sequence_config', {}).get('actions', [])

        # 4. 스텝이 완료되었는지 확인
        if step_index >= len(actions):
            print(
                f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Sequence '{screen.current_state.name}' completed.")

            # 🚀 [신규] S1이 INITIALIZING을 '성공'하면 ARENA로 설정
            if screen.current_state == ScreenState.INITIALIZING and screen.screen_id == 'S1':
                self.location_flag = Location.ARENA
                print(f"INFO: [{self.monitor_id}] Initial Location (S1 Success): {self.location_flag.name}")

            # 'sequence_complete'에 정의된 다음 상태로 전이
            next_state_key = policy.get('transitions', {}).get('sequence_complete', 'NORMAL')
            next_state = next_state_key if isinstance(next_state_key, ScreenState) else ScreenState.NORMAL

            self._change_state(screen, next_state)
            screen.policy_step = 0  # 스텝 리셋
            screen.policy_step_start_time = 0.0
            return

        # 5. "매뉴얼"에서 현재 스텝의 "지시서"를 가져옴
        current_action = actions[step_index]
        operation = current_action.get('operation')

        # --- 🚀 [기존] 컨텍스트(Context) 키 검사 ---
        # (S1이 INITIALIZING 상태일 때는 location_flag가 UNKNOWN이므로 이 검사는 통과됨)
        required_context_str = current_action.get('context')
        if required_context_str:
            # 'FIELD' 또는 'ARENA' 문자열을 Location Enum으로 변환
            required_context = getattr(Location, required_context_str, Location.UNKNOWN)

            if self.location_flag != required_context:
                print(
                    f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Step {step_index} ({operation}) skipped (Context mismatch: {self.location_flag.name} != {required_context_str})")
                # 컨텍스트가 맞지 않으면 이 액션을 건너뛰고 바로 다음 스텝으로
                screen.policy_step += 1
                screen.policy_step_start_time = time.time()
                return  # ★★★ 현재 함수 실행 종료 ★★★
        # --- 컨텍스트 검사 종료 ---

        # 6. "지시서"를 해석하고 실행

        # --- A. IO 요청 (click, key_press 등) ---
        # 🚀 'set_focus' operation 추가
        if operation in ['click', 'key_press', 'set_focus', 'click_relative', 'execute_subroutine']:
            # IO는 요청만 하고 즉시 다음 스텝으로 넘어감
            self.io_scheduler.request(
                component=self.monitor_id,
                screen_id=screen.screen_id,
                action=lambda: self._do_policy_action(screen, current_action),
                priority=Priority.NORMAL
            )
            print(
                f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Step {step_index} ({operation}) requested.")
            screen.policy_step += 1
            screen.policy_step_start_time = time.time()  # 다음 스텝(대기)을 위한 시간 기록

        # --- B. 대기 (wait_duration) ---
        elif operation == 'wait_duration':
            if screen.policy_step_start_time == 0.0 and current_action.get('initial') == True:
                screen.policy_step_start_time = time.time()

            elapsed = time.time() - screen.policy_step_start_time
            duration = current_action.get('duration', 5.0)  # 기본 5초

            if elapsed >= duration:
                print(
                    f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Step {step_index} ({operation} {duration}s) complete.")
                screen.policy_step += 1  # 💥 다음 스텝으로
                screen.policy_step_start_time = time.time()
            else:
                pass  # 아직 대기 중

        # --- C. 시각적 확인 (wait) [🚀 업그레이드] ---
        elif operation == 'wait':
            template_key = current_action.get('template')

            # 1. 템플릿 검사
            if self._check_template_present(screen, template_key):
                print(
                    f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Step {step_index} ({operation} '{template_key}') complete.")
                screen.policy_step += 1  # 💥 다음 스텝으로
                screen.policy_step_start_time = time.time()

            # 2. 템플릿이 없다면, 타임아웃 검사
            else:
                step_timeout = current_action.get('timeout')
                if step_timeout:
                    # 이 스텝이 시작된 시간 (이전 스텝이 완료된 시간)
                    elapsed_on_step = time.time() - screen.policy_step_start_time

                    if elapsed_on_step > step_timeout:
                        print(
                            f"WARN: [{self.monitor_id}] Step {step_index} ('wait {template_key}') timed out after {elapsed_on_step:.1f}s")

                        on_timeout_action = current_action.get('on_timeout')

                        if on_timeout_action == 'fail_sequence':
                            # 🚀 [신규] S1이 INITIALIZING에서 '타임아웃(실패)'되면 FIELD로 설정
                            if screen.current_state == ScreenState.INITIALIZING and screen.screen_id == 'S1':
                                self.location_flag = Location.FIELD
                                print(
                                    f"INFO: [{self.monitor_id}] Initial Location (S1 Timeout): {self.location_flag.name}")

                            # 🚀 [버그 수정]
                            # 기존: policy_step을 맨 뒤로 보내 'sequence_complete'가 호출되도록 함 (오류)
                            # 수정: 'sequence_failed' 트랜지션을 즉시 찾아 상태를 변경함

                            next_state_key = policy.get('transitions', {}).get('sequence_failed', 'NORMAL')
                            next_state = next_state_key if isinstance(next_state_key,
                                                                      ScreenState) else ScreenState.NORMAL

                            self._change_state(screen, next_state)
                            screen.policy_step = 0
                            screen.policy_step_start_time = 0.0
                            return  # ★★★ 상태 변경 후 즉시 종료

                        # (참고: on_timeout이 없으면 템플릿을 찾을 때까지 영원히 대기)
                        pass

                # (그 외): 아직 타임아웃 안됐고, 템플릿도 못찾음 -> "아무것도 안 함"
                pass

        # --- D. (기타 operation 추가...) ---

        # 'final': True 속성이 있으면 스텝 완료 후 즉시 종료
        if current_action.get('final') == True and screen.policy_step > step_index:
            # (위의 'step_index >= len(actions)' 로직이 다음 루프에서 처리해 줄 것임)
            pass

    def _handle_screen_state(self, screen: ScreenMonitorInfo, stop_event: threading.Event):
        """현재 화면 상태에 따라 처리"""
        state = screen.current_state

        # 1. NORMAL 상태 - 이상 상태 감지 (변경 없음)
        if state == ScreenState.NORMAL:
            character_state = self._get_character_state_on_screen(screen)
            if character_state == CharacterState.DEAD:
                # 사망 상태로 전환
                self._change_state(screen, ScreenState.DEAD)
            elif character_state == CharacterState.HOSTILE_ENGAGE:
                # 적대 상태로 전환
                self._change_state(screen, ScreenState.HOSTILE)

        # 🚀 [수정] INITIALIZING을 DEAD와 함께 묶어서 처리
        # 2. DEAD, INITIALIZING 상태 - 패턴 B (요청-플래그-확인)
        elif state in [ScreenState.DEAD, ScreenState.INITIALIZING]:
            self._execute_policy_step(screen)

        # 3. RECOVERING 상태 - 부활 완료 체크 (변경 없음)
        elif state == ScreenState.RECOVERING:
            # srm_config.py의 'sequence_config' (10초 대기 + 20초 템플릿 대기)를 실행
            self._execute_policy_step(screen)

        elif state == ScreenState.HOSTILE:
            # srm_config.py의 'execute_subroutine' 정책을 실행합니다.
            self._execute_policy_step(screen)

        # 5. FLEEING 상태 - 도주 완료 체크 (변경 없음)
        elif state == ScreenState.FLEEING:
            # srm_config.py의 'time_based_wait' 정책을 실행합니다.
            self._execute_policy_step(screen)

        # 6. BUYING_POTIONS 상태 - 물약 구매 및 귀환 시작 (기존 step 방식 유지)
        elif state == ScreenState.BUYING_POTIONS:
            # 🚨 기존 _buy_potion_and_initiate_return 함수 호출을 대체
            self._execute_policy_step(screen)

            # 7. RETURNING 상태 (하이브리드 적용)
        elif state == ScreenState.RETURNING:

            # ==================================================================
            # 7-1. FIELD 컨텍스트: [로직 유지]
            # "3회 체크", "재시도" 등 복잡한 카운팅/루프 로직은
            # srm_config.py로 표현하기 까다로우므로 monitor.py에 그대로 둡니다.
            # ==================================================================
            if self.location_flag == Location.FIELD:
                elapsed = time.time() - screen.last_state_change_time

                # ----------------------------------------------------
                # [S1] 파티 리더 (S2~S5를 찾음)
                # ----------------------------------------------------
                if screen.screen_id == 'S1':

                    # [신규] 파티원 확인 카운트 초기화
                    if not hasattr(screen, 'party_check_count'):
                        screen.party_check_count = 0

                    # 1. 파티원 확인 (이제 이 함수는 즉시 반환됨)
                    if self._check_returned_well_s1(screen):
                        screen.party_check_count += 1  # 찾으면 카운트 증가

                    # 2. 카운트 누적 확인 (3회 누적되면 성공)
                    if screen.party_check_count >= 3:
                        print(f"INFO: [{self.monitor_id}] S1: Party gathering completed (member found).")
                        del screen.party_check_count  # 카운터 정리
                        self._change_state(screen, ScreenState.NORMAL)
                        self._notify_s1_completion()

                    # 3. 타임아웃 및 재시도 로직
                    elif screen.retry_count >= 5:  # 재시도 5회 초과
                        print(f"WARN: [{self.monitor_id}] S1: Max retry attempts (5) reached. Giving up gathering.")
                        if hasattr(screen, 'party_check_count'): del screen.party_check_count
                        self._change_state(screen, ScreenState.NORMAL)
                        self._notify_s1_completion()
                    elif elapsed > 40.0:  # 40초 초과
                        print(f"WARN: [{self.monitor_id}] S1: Total timeout (40s). Giving up gathering.")
                        if hasattr(screen, 'party_check_count'): del screen.party_check_count
                        self._change_state(screen, ScreenState.NORMAL)
                        self._notify_s1_completion()

                    # 4. 재시도 IO 요청 (기존과 동일)
                    else:
                        if elapsed >= (screen.retry_count * 2.0):  # 재시도 간격
                            screen.retry_count += 1
                            print(f"INFO: [{self.monitor_id}] S1: Retrying party gathering ({screen.retry_count}/5)...")
                            self.io_scheduler.request(
                                component=self.monitor_id,
                                screen_id=screen.screen_id,
                                action=lambda: self._retry_field_return(screen,
                                                                        is_first_attempt=(screen.retry_count == 1)),
                                priority=Priority.NORMAL
                            )

                # ----------------------------------------------------
                # [S2~S5] 파티원 (S1을 찾음)
                # ----------------------------------------------------
                else:
                    # [신규] S1 확인 카운트 초기화
                    if not hasattr(screen, 'party_check_count'):
                        screen.party_check_count = 0

                    if not screen.s1_completed:
                        print(
                            f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Waiting for S1 completion notification...")
                        return
                    else:
                        # 1. S1 확인 (즉시 반환됨)
                        if self._check_returned_well_others(screen):
                            screen.party_check_count += 1  # 찾으면 카운트 증가

                        # 2. 카운트 누적 확인 (3회 누적되면 성공)
                        if screen.party_check_count >= 3:
                            print(
                                f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Successfully returned to party (found S1).")
                            del screen.party_check_count  # 카운터 정리
                            self._change_state(screen, ScreenState.NORMAL)

                        # 3. 타임아웃 및 재시도 로직
                        elif screen.retry_count >= 10:
                            print(
                                f"WARN: [{self.monitor_id}] Screen {screen.screen_id}: Max retry attempts (10) reached. Forcing NORMAL.")
                            if hasattr(screen, 'party_check_count'): del screen.party_check_count
                            self._change_state(screen, ScreenState.NORMAL)
                        elif elapsed > 30.0:
                            print(
                                f"WARN: [{self.monitor_id}] Screen {screen.screen_id}: Total timeout (30s). Forcing NORMAL.")
                            if hasattr(screen, 'party_check_count'): del screen.party_check_count
                            self._change_state(screen, ScreenState.NORMAL)

                        # 4. 재시도 IO 요청 (기존과 동일)
                        else:
                            if elapsed >= (screen.retry_count * 2.0):
                                screen.retry_count += 1
                                print(
                                    f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Retrying field return ({screen.retry_count}/10)...")
                                self.io_scheduler.request(
                                    component=self.monitor_id,
                                    screen_id=screen.screen_id,
                                    action=lambda: self._retry_field_return(screen,
                                                                            is_first_attempt=(screen.retry_count == 0)),
                                    # 첫 시도는 Y키 포함
                                    priority=Priority.NORMAL
                                )

            # ==================================================================
            # 7-2. ARENA 컨텍스트: [로직 변경]
            # 단순 순차 실행(WP1->WP2...)이 가능한 ARENA 로직은
            # srm_config.py의 정책을 따르도록 합니다.
            # ==================================================================
            elif self.location_flag == Location.ARENA:
                self._execute_policy_step(screen)


    # === IO 실행 함수들 (스케줄러가 호출) ===

    def _do_flight(self, screen: ScreenMonitorInfo):
        """도주 버튼 클릭 실행 (IO만 담당, Lock 없음)"""
        try:
            flight_template_path = template_paths.get_template(screen.screen_id, 'FLIGHT_BUTTON')
            if not flight_template_path:
                print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: Flight template path not configured.")
                # 템플릿 실패 시 고정 좌표 시도
                if self._click_relative(screen, 'flight_button', delay_after=0.2):
                    print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Flight via fixed coordinates.")
                return

            if not os.path.exists(flight_template_path):
                print(
                    f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: Flight template file not found: {flight_template_path}")
                # 템플릿 실패 시 고정 좌표 시도
                if self._click_relative(screen, 'flight_button', delay_after=0.2):
                    print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Flight via fixed coordinates.")
                return

            # 스크린샷 캡처
            screenshot = self.orchestrator.capture_screen_safely(screen.screen_id)
            if screenshot is None:
                print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: Failed to capture screen for flight.")
                return

            # 1. 템플릿 매칭 시도
            center_coords = image_utils.return_ui_location(
                template_path=flight_template_path,
                region=screen.region,
                threshold=self.confidence,
                screenshot_img=screenshot
            )

            if center_coords:
                pyautogui.click(center_coords)
                print(
                    f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Flight via template matching at {center_coords}.")
            else:
                # 2. 템플릿 매칭 실패 시 고정 좌표 사용
                print(
                    f"WARN: [{self.monitor_id}] Screen {screen.screen_id}: Template matching failed, trying fixed coordinates...")
                if self._click_relative(screen, 'flight_button', delay_after=0.2):
                    print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Flight via fixed coordinates.")
                else:
                    print(
                        f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: Both template and fixed coords failed.")

        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: Exception in _do_flight: {e}")
            traceback.print_exc()

    def win32_click(self,x, y):
        win32api.SetCursorPos((x, y))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)

    def _check_single_party_template(self, screen: ScreenMonitorInfo, template_path: str,
                                     threshold: float = 0.15) -> bool:
        """
        [수정됨] 단일 파티 템플릿으로 파티 UI를 '한 번' 체크 (Non-Blocking)
        """
        if not template_path or not os.path.exists(template_path):
            return False

        try:
            template = cv2.imread(template_path)
            if template is None:
                print(f"ERROR: [{self.monitor_id}] Failed to load PARTY_UI template: {template_path}")
                return False

            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

            # 🚨 루프와 sleep 제거: 단 한 번의 스크린샷으로 검사
            try:
                screen_img = self.orchestrator.capture_screen_safely(screen.screen_id)
                if screen_img is None:
                    return False  # 스크린샷 실패

                screen_gray = cv2.cvtColor(np.array(screen_img), cv2.COLOR_RGB2GRAY)

                match_result = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_SQDIFF_NORMED)
                min_val, _, _, _ = cv2.minMaxLoc(match_result)

                if min_val < threshold:
                    print(
                        f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Party UI found (template: {os.path.basename(template_path)}, match: {min_val:.4f})")
                    return True

            except Exception as e:
                print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id} sampling error: {e}")

            return False  # 템플릿 못 찾음

        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Exception in _check_single_party_template: {e}")
            return False

    def _check_returned_well_s1(self, screen: ScreenMonitorInfo) -> bool:
        """S1용: S2~S5 중 하나라도 매칭되면 True"""
        print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: S1 searching for any party member (S2~S5)...")

        for member_id in ['S2', 'S3', 'S4', 'S5']:
            template_path = template_paths.get_template('S1', member_id)  # 'S1', 'S2' 이런 식으로
            if template_path and self._check_single_party_template(screen, template_path):
                print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Found party member {member_id}")
                return True

        print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: No party members found (S2~S5)")
        return False

    def _check_returned_well_others(self, screen: ScreenMonitorInfo) -> bool:
        """
        S2~S5용: S1 파티 템플릿만 체크
        """
        print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Searching for S1...")

        s1_template_path = template_paths.get_template('S1', 'PARTY_UI')
        if s1_template_path and self._check_single_party_template(screen, s1_template_path):
            print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Found S1")
            return True

        print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: S1 not found")
        return False


    def _check_returned_well(self, screen: ScreenMonitorInfo, samples: int = 7, threshold: float = 0.15,
                             sample_interval: float = 0.5) -> bool:
        """
        기존 호환성을 위한 함수 (자신의 화면 ID에 맞는 PARTY_UI 템플릿 사용)
        """
        template_path = template_paths.get_template(screen.screen_id, 'PARTY_UI')
        return self._check_single_party_template(screen, template_path, threshold, samples, sample_interval)

    def _click_relative(self, screen: ScreenMonitorInfo, coord_key: str, delay_after: float = 0.5, random_offset: int = 2) -> bool:
        """
        지정된 화면 영역 내에서 FIXED_UI_COORDS에 정의된 키를 사용하여
        상대 좌표에 클릭을 수행합니다.

        Args:
            screen: 클릭을 수행할 ScreenMonitorInfo 객체.
            coord_key: utils.screen_info.FIXED_UI_COORDS 내 해당 screen_id 딕셔너리의 키.
            delay_after: 클릭 후 대기 시간 (초).
            random_offset: 클릭 좌표에 적용할 랜덤 오프셋 범위 (± 값).

        Returns:
            클릭 성공 시 True, 실패 시 False.
        """
        if not screen or not screen.region:
            print(f"ERROR:[{self.monitor_id}] Invalid screen for relative click.")
            return False
        if not hasattr(screen, 'screen_id'):
             print(f"ERROR:[{self.monitor_id}] screen_info object missing 'screen_id' for relative click.")
             return False

        # screen_info 모듈의 FIXED_UI_COORDS 에서 상대 좌표 가져오기
        screen_coords = FIXED_UI_COORDS.get(screen.screen_id)
        if not screen_coords:
            print(f"ERROR:[{self.monitor_id}] Relative coordinates not found for screen '{screen.screen_id}' in FIXED_UI_COORDS.")
            return False

        relative_coord = screen_coords.get(coord_key)
        if relative_coord is None:
            print(f"ERROR:[{self.monitor_id}] Relative coordinate key '{coord_key}' not found for screen '{screen.screen_id}'.")
            return False
        if not isinstance(relative_coord, tuple) or len(relative_coord) != 2:
            print(f"ERROR:[{self.monitor_id}] Invalid coordinate format for '{coord_key}' on screen '{screen.screen_id}': {relative_coord}")
            return False

        # 절대 좌표 계산
        region_x, region_y, _, _ = screen.region
        try:
            # 정수 좌표 보장 및 랜덤 오프셋 적용
            click_x = int(region_x + relative_coord[0] + np.random.randint(-random_offset, random_offset + 1))
            click_y = int(region_y + relative_coord[1] + np.random.randint(-random_offset, random_offset + 1))
        except ValueError: # relative_coord가 숫자가 아닐 경우 대비
             print(f"ERROR:[{self.monitor_id}] Invalid coordinate values for '{coord_key}' on screen '{screen.screen_id}': {relative_coord}")
             return False

        try:
            print(f"INFO:[{self.monitor_id}] Clicking relative '{coord_key}' at ({click_x}, {click_y}) on screen {screen.screen_id}...")
            pyautogui.click(click_x, click_y)
            if delay_after > 0:
                print(f"INFO:[{self.monitor_id}] Waiting {delay_after}s after clicking '{coord_key}'.")
                time.sleep(delay_after)
            return True
        except Exception as e:
            print(f"ERROR:[{self.monitor_id}] Failed to click relative coordinate '{coord_key}' on screen {screen.screen_id}: {e}")
            return False


    def _check_reached_wp(self, screen: ScreenMonitorInfo, wp_index: int) -> bool:
        """웨이포인트 도착 여부를 확인합니다"""
        print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Checking if reached Waypoint #{wp_index}")

        try:
            if wp_index == 1:
                # WP1: 아레나 내부에 있는지 확인
                if self._is_character_in_arena(screen):
                    print(f"INFO: [{self.monitor_id}] WP1 reached - Character is in arena")
                    return True
                else:
                    print(f"INFO: [{self.monitor_id}] WP1 not reached - Character not in arena")
                    return False

            elif wp_index == 2:
                # WP2: 타워 근처 도착 확인 (템플릿 또는 위치 기반)
                tower_template_path = template_paths.get_template(screen.screen_id, 'WAYPOINT_2')
                if tower_template_path and os.path.exists(tower_template_path):
                    screenshot = self.orchestrator.capture_screen_safely(screen.screen_id)
                    if image_utils.is_image_present(tower_template_path, screen.region, threshold=0.8,
                                                    screenshot_img=screenshot):
                        print(f"INFO: [{self.monitor_id}] WP2 reached - Tower location confirmed")
                        return True

                # 템플릿 없으면 이동 완료로 간주 (기존 로직 유지)
                print(f"INFO: [{self.monitor_id}] WP2 considered reached (no template check available)")
                return True

            elif wp_index == 3:
                # WP3: 이동 시퀀스 완료로 도착 간주
                print(f"INFO: [{self.monitor_id}] WP3 considered reached (movement sequence completed)")
                return True

            elif wp_index == 4:
                # WP4: 글라이더 시퀀스 완료 확인 (시퀀스 실행 성공 여부로 판단)
                print(f"INFO: [{self.monitor_id}] WP4 considered reached after glider sequence")
                return True

            elif wp_index == 5:
                # WP5: 최종 전투 지점 확인
                return self._is_at_combat_spot(screen)

            else:
                print(f"ERROR: [{self.monitor_id}] Unknown waypoint index: {wp_index}")
                return False

        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Exception during check waypoint {wp_index}: {e}")
            return False

    def _is_at_combat_spot(self, screen: ScreenMonitorInfo) -> bool:
        """최종 전투 지점 도착 여부를 최대 3번 확인합니다."""
        print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Checking if at combat spot")

        # 전투 지점 확인 템플릿 경로 가져오기
        template_path = template_paths.get_template(screen.screen_id, 'COMBAT_SPOT')

        if not template_path or not os.path.exists(template_path):
            print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: COMBAT_SPOT template not found")
            return False

        # 최대 3번 시도
        max_attempts = 3
        for attempt in range(max_attempts):
            screenshot = self.orchestrator.capture_screen_safely(screen.screen_id)
            if image_utils.is_image_present(
                    template_path=template_path,
                    region=screen.region,
                    threshold=self.confidence,
                    screenshot_img=screenshot
            ):
                print(f"INFO: [{self.monitor_id}] Combat spot reached confirmed on attempt {attempt + 1}")
                return True

            print(f"INFO: [{self.monitor_id}] Combat spot not detected on attempt {attempt + 1}/{max_attempts}")
            time.sleep(1.0)  # 1초 간격으로 재시도

        print(f"INFO: [{self.monitor_id}] Combat spot not confirmed after {max_attempts} attempts")
        return False


    def _retry_field_return(self, screen: ScreenMonitorInfo, is_first_attempt: bool = False) -> bool:
        """필드 복귀 재시도: 단일 버튼 클릭 (첫 시도시에만 Y키 입력)"""
        try:
            print(
                f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Retrying field return (first attempt: {is_first_attempt})...")

            # 1. 단일 버튼 클릭
            if not self._click_relative(screen, 'field_return_button', delay_after=0.5):
                print(f"WARN: [{self.monitor_id}] Screen {screen.screen_id}: Failed to click field return button.")
                return False

            # 2. Y키 입력 (첫 시도일 때만)
            if is_first_attempt:
                time.sleep(0.3)  # 클릭 후 잠시 대기
                keyboard.press_and_release('y')
                print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Pressed Y key (first attempt).")

            return True

        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: Field return retry failed: {e}")
            return False

    def _get_max_wp_num(self) -> int:
        """전체 웨이포인트 개수를 반환합니다."""
        print(f"INFO: [{self.monitor_id}] Getting Max Waypoint Number...")
        return 5  # 현재 고정값, 추후 설정 또는 동적 계산 가능

    # === 메인 모니터링 루프 ===
    def run_loop(self, stop_event: threading.Event):
        """Orchestrator가 제어하는 메인 모니터링 루프."""
        print(f"INFO: Starting CombatMonitor {self.monitor_id} on {self.vd_name}...")
        if not self.screens:
            print(f"ERROR: [{self.monitor_id}] No screens added. Stopping monitor.")
            return

        # stop_event 저장
        self.stop_event = stop_event

        # 초기화
        self.death_count = 0
        try:
            self.max_wp = self._get_max_wp_num()
        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Error getting max waypoint number: {e}. Setting to 0.")
            self.max_wp = 0

        # 시작 위치 결정
        self.location_flag = Location.UNKNOWN
        print(f"INFO: [{self.monitor_id}] Initial monitoring context: UNKNOWN (pending detection)")

        # 각 화면의 상태를 NORMAL로 초기화
        for screen in self.screens:
            screen.current_state = ScreenState.INITIALIZING
            screen.last_state_change_time = time.time()
            screen.retry_count = 0
            screen.policy_step = 0  # 👈 policy_step 초기화 추가
            screen.policy_step_start_time = 0.
        # 메인 루프 시작
        while not stop_event.is_set():
            try:
                # 1. HOSTILE 상태 화면들 먼저 처리 (최우선)
                hostile_screens = [s for s in self.screens if s.current_state == ScreenState.HOSTILE]
                for screen in hostile_screens:
                    if stop_event.is_set(): break
                    self._handle_screen_state(screen, stop_event)

                # 2. 나머지 화면들 처리
                other_screens = [s for s in self.screens if s.current_state != ScreenState.HOSTILE]
                for screen in other_screens:
                    if stop_event.is_set(): break
                    self._handle_screen_state(screen, stop_event)

                # 루프 주기 조절
                if stop_event.wait(1.0): break  # 1초 대기하며 종료 신호 확인

            except Exception as e:
                # 메인 루프 내 예상치 못한 오류 처리
                print(f"ERROR: [{self.monitor_id}] Unhandled exception in main loop: {e}")
                traceback.print_exc()
                if stop_event.wait(5.0):  # 오류 발생 시 5초 대기하며 종료 신호 확인
                    break  # 종료 신호 받으면 루프 탈출

        # 루프 종료 시 stop 메서드 호출
        self.stop()

    def stop(self):
        """모니터를 중지하고 필요한 정리 작업을 수행합니다."""
        print(f"INFO: CombatMonitor {self.monitor_id} received stop signal. Cleaning up...")
        super().stop() # BaseMonitor의 stop 호출 (필요시)
        # 필요한 경우 추가적인 리소스 해제 로직

# === 독립 실행 테스트용 코드 ===
if __name__ == "__main__":
    print("INFO: Running CombatMonitor in standalone test mode...")
    print("INFO: 시작 대기중... 10초 후에 모니터링이 시작됩니다.")

    # 가상 데스크톱 전환을 위한 시작 전 딜레이 추가
    start_delay = 10  # 10초 딜레이
    for i in range(start_delay, 0, -1):
        print(f"INFO: {i}초 후 시작...")
        time.sleep(1)

    print("INFO: 모니터링을 시작합니다!")
    stop_event = threading.Event()

    # 1. 모니터 인스턴스 생성
    monitor_config = {'confidence': 0.85}
    monitor = CombatMonitor(monitor_id="SRM1_Test", config=monitor_config, vd_name="TestVD")

    # 2. 화면 정보 로드 및 추가 (Orchestrator 역할 시뮬레이션)
    try:
        # utils.screen_info 모듈 임포트를 위한 경로 설정 (환경에 따라 조정 필요)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        utils_dir = os.path.join(os.path.dirname(os.path.dirname(current_dir)), 'NightCrows', 'utils')
        if utils_dir not in sys.path:
             sys.path.insert(0, utils_dir)

        from screen_info import SCREEN_REGIONS # NightCrows/utils/screen_info.py

        if SCREEN_REGIONS and isinstance(SCREEN_REGIONS, dict):
            for screen_id in ['S1', 'S2', 'S3', 'S4', 'S5']:
                 if screen_id in SCREEN_REGIONS:
                     monitor.add_screen(screen_id=screen_id, region=SCREEN_REGIONS[screen_id])
                 else:
                     print(f"WARN: Screen ID '{screen_id}' not found in SCREEN_REGIONS.")
        else:
            print("ERROR: Could not load or invalid SCREEN_REGIONS from screen_info.py")
            sys.exit(1)
    except ImportError:
        print("ERROR: Could not import SCREEN_REGIONS from NightCrows/utils/screen_info.py.")
        print(f"Current sys.path: {sys.path}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Error loading screen info: {e}")
        sys.exit(1)

    if not monitor.screens:
         print("ERROR: No screens were added to the monitor. Exiting test.")
         sys.exit(1)

    # 3. 모니터 스레드 시작
    print(f"INFO: Starting monitor thread for {len(monitor.screens)} screens...")
    monitor_thread = threading.Thread(target=monitor.run_loop, args=(stop_event,), daemon=True)
    monitor_thread.start()

    # 4. 테스트 실행 및 종료 처리
    try:
        test_duration = 240 # 테스트 실행 시간 (초)
        print(f"INFO: Monitor running for {test_duration} seconds... Press Ctrl+C to stop early.")
        start_time = time.time()
        # 메인 스레드는 모니터 스레드가 끝나거나 시간이 다 되거나 Ctrl+C 입력 전까지 대기
        while monitor_thread.is_alive() and time.time() - start_time < test_duration:
            # KeyboardInterrupt 를 잡기 위해 짧게 sleep
            time.sleep(0.5)

        if monitor_thread.is_alive():
             print(f"\nINFO: Standalone test duration ({test_duration}s) elapsed.")
        else:
             print("\nINFO: Monitor thread finished early.")

    except KeyboardInterrupt:
        print("\nINFO: Ctrl+C detected. Stopping monitor...")
    finally:
        # 모니터 스레드 종료 신호 및 대기
        if monitor_thread.is_alive():
            print("INFO: Signaling monitor thread to stop...")
            stop_event.set()
            monitor_thread.join(timeout=10) # 최대 10초 대기
            if monitor_thread.is_alive():
                print("WARN: Monitor thread did not stop gracefully.")
        print("INFO: Standalone test finished.")


# **주요 TODO 사항:**
# - 웨이포인트 관련 함수들 구현 필요 (_move_to_wp, _check_reached_wp 등)
# - screen_info.py의 FIXED_UI_COORDS 실제 좌표값 측정 필요
# - S2-S5 템플릿 경로 추가 필요 (template_paths.py)