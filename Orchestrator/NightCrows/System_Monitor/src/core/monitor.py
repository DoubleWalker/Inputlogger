# Orchestrator/NightCrows/System_Monitor/src/core/monitor.py
"""
System Monitor 브릿지 (v3 제너레이터 '상황반장' 아키텍처)
- '바보 실행기' (Dumb Executor) 모델
- 모든 로직은 sm_config.py의 제너레이터 함수로 위임
- monitor는 제너레이터의 '지시서'를 받아 IO 스케줄러에 요청
"""

import time
import threading
from typing import Dict, List, Optional, Any, Tuple
import pyautogui
from Orchestrator.src.core.io_scheduler import Priority
from Orchestrator.NightCrows.utils.image_utils import set_focus
from Orchestrator.NightCrows.utils.screen_info import SCREEN_REGIONS

# ❗️ [신규] SRM 상태 확인을 위해 ScreenState 임포트
from Orchestrator.NightCrows.Combat_Monitor.config.srm_config import ScreenState

# 로컬룰 import
from Orchestrator.NightCrows.System_Monitor.config.template_paths import get_template, verify_template_paths
from Orchestrator.NightCrows.System_Monitor.config.sm_config import (
    SystemState,
    SM_CONFIG,
    SM_EXCEPTION_POLICIES,
    get_state_policies,
    get_detection_policy,
    validate_config
)


class SystemMonitor:
    """SM 브릿지 - v3 제너레이터 모델 (NightCrows)"""

    # ❗️ [수정] shared_states 인자 추가
    def __init__(self, monitor_id: str, vd_name: str, orchestrator=None, shared_states=None):
        self.orchestrator = orchestrator
        self.io_scheduler = orchestrator.io_scheduler

        if not validate_config():
            raise ValueError(f"[{monitor_id}] sm_config.py 설정 검증 실패")
        if not verify_template_paths():
            raise FileNotFoundError(f"[{monitor_id}] 템플릿 파일 검증 실패")

        self.monitor_id = monitor_id
        self.vd_name = vd_name

        # ❗️ [신규] 공유 상태 저장소 저장
        self.shared_states = shared_states if shared_states is not None else {}

        self.local_config = SM_CONFIG
        self.exception_policies = SM_EXCEPTION_POLICIES

        self.state_policy_map = get_state_policies()
        self.detection_policy_map = get_detection_policy()

        self.screens = {}
        self._initialize_screens()

        print(f"INFO: [{self.monitor_id}] SystemMonitor Bridge initialized (Generator Model)")
        print(f"INFO: [{self.monitor_id}] Target screens: {list(self.screens.keys())}")

    def _initialize_screens(self):
        """screen_info.py 기반으로 화면 객체들 생성 (동일)"""
        target_screens = self.local_config['target_screens']['included']
        for screen_id in target_screens:
            self.add_screen(screen_id)

    def add_screen(self, screen_id: str) -> bool:
        """화면 객체 생성 (v3 제너레이터 상태 필드 추가)"""
        if screen_id not in SCREEN_REGIONS:
            print(f"WARN: [{self.monitor_id}] Unknown screen_id: {screen_id}")
            return False

        # ❗️ [신규] 공유 상태 초기값 등록 (SRM이 먼저 등록했을 수도 있음)
        if screen_id not in self.shared_states:
            self.shared_states[screen_id] = SystemState.NORMAL

        screen_region = SCREEN_REGIONS[screen_id]

        # ❗️ [수정] current_state 필드 제거 (공유 상태 사용)
        self.screens[screen_id] = {
            'screen_id': screen_id,
            # 'current_state': SystemState.NORMAL,  <-- 삭제됨
            'state_enter_time': time.time(),
            'region': screen_region,
            'current_generator': None,
            'generator_wait_start_time': 0.0,
            'generator_wait_timeout': 0.0,
            'generator_last_yielded_value': None,
        }
        print(f"INFO: [{self.monitor_id}] Added screen {screen_id}")
        return True

    # =========================================================================
    # 🔌 Orchestrator 인터페이스 (run_loop 수정됨)
    # =========================================================================

    def run_loop(self, stop_event: threading.Event):
        """Orchestrator 스레드에서 실행되는 메인 루프 (v3 모델)"""
        print(f"INFO: [{self.monitor_id}] Starting SystemMonitor bridge loop... (Generator Model)")
        check_interval = self.local_config['timing']['check_interval']

        while not stop_event.is_set():
            try:
                current_time = time.time()

                for screen_id, screen_obj in self.screens.items():
                    # ❗️ [수정] 공유 상태 읽기
                    current_state = self.shared_states.get(screen_id)

                    # ❗️ [신규] 교통 정리: 내 담당(SystemState)이 아니면?
                    if not isinstance(current_state, SystemState):
                        # SRM 상태(ScreenState)라면 게임이 정상 동작 중이거나 전투 중임.
                        # 하지만 SM은 '감시자'이므로 에러(팝업, 튕김) 감지는 계속 해야 함.

                        # NORMAL 상태의 감지 로직만 빌려와서 실행 (상태 변경 없이 감지만 수행)
                        # (감지되면 _handle_detect_only_state 내부에서 report_system_error 등을 통해 개입 시도)
                        if SystemState.NORMAL in self.detection_policy_map:
                            self._handle_detect_only_state(screen_obj, self.detection_policy_map[SystemState.NORMAL])
                        continue

                    # --- 이하 내 담당 상태(SystemState) 처리 ---

                    if current_state in self.state_policy_map:
                        policy = self.state_policy_map[current_state]
                        self._run_generator_step(screen_obj, policy, current_time)

                    elif current_state in self.detection_policy_map:
                        policy = self.detection_policy_map[current_state]
                        self._handle_detect_only_state(screen_obj, policy)
                    else:
                        pass

                if stop_event.wait(check_interval):
                    break
            except Exception as e:
                print(f"ERROR: [{self.monitor_id}] SystemMonitor loop exception: {e}")
                self._handle_exception_policy('state_machine_error')
                time.sleep(5.0)

        print(f"INFO: [{self.monitor_id}] SystemMonitor bridge loop stopped")

    def stop(self):
        print(f"INFO: [{self.monitor_id}] SystemMonitor stopping...")

    # =========================================================================
    # 🎯 v3 상태머신 실행 엔진
    # =========================================================================

    def _handle_detect_only_state(self, screen_obj: dict, policy: dict):
        """
        [v3] '감지 전용' 상태 처리기 (예: NORMAL)
        'targets'를 순회하며 템플릿을 감지하고, 발견 시 상태를 즉시 전이시킵니다.
        """
        targets = policy.get('targets', [])

        for target in targets:
            template_name = target.get('template_name')
            next_state = target.get('next_state')

            if not template_name or not next_state:
                continue

            template_path = get_template(screen_obj['screen_id'], template_name)

            pos = self._detect_template(screen_obj, template_path=template_path)

            if pos:  # 템플릿을 찾았다면
                print(f"INFO: [{screen_obj['screen_id']}] DetectOnly: '{template_name}' 발견.")

                # --- Orchestrator에게 오류 보고 및 확인 ---
                is_false_positive = False
                if self.orchestrator:
                    # 리턴 값 캡처 (True면 "거짓 양성이니 무시해라")
                    is_false_positive = self.orchestrator.report_system_error(self.monitor_id, screen_obj['screen_id'])

                if is_false_positive:
                    print(
                        f"INFO: [{screen_obj['screen_id']}] Orchestrator confirmed False Positive. SM1 will NOT transition state.")
                    return  # 상태 전이 중단

                # (is_false_positive가 False인 경우에만 전이)
                self._transition_screen_to_state(screen_obj, next_state, f"detected: {template_name}")
                return  # 감지했으므로 루프 종료

    def _run_generator_step(self, screen_obj: dict, policy: dict, current_time: float):
        """[v3] '제너레이터' 상태 처리기 (예: LOGGING_IN)"""

        # 1. 대기 확인
        if screen_obj['generator_wait_start_time'] > 0.0:
            if current_time < screen_obj['generator_wait_start_time']:
                return
            else:
                screen_obj['generator_wait_start_time'] = 0.0

        if screen_obj['generator_wait_timeout'] > 0.0:
            if current_time > screen_obj['generator_wait_timeout']:
                screen_obj['generator_wait_timeout'] = 0.0
                try:
                    screen_obj['current_generator'].throw(Exception("Template Wait Timeout"))
                except StopIteration:
                    pass
                except Exception:
                    pass
                return

        # 2. 제너레이터 생성
        if not screen_obj['current_generator']:
            gen_func = policy['generator']
            screen_obj['current_generator'] = gen_func(screen_obj)
            screen_obj['generator_last_yielded_value'] = None

        # 3. 제너레이터 실행
        try:
            # A. 실행 권한 부여
            instruction = screen_obj['current_generator'].send(
                screen_obj['generator_last_yielded_value']
            )

            # B. 지시사항 수행
            try:
                result_value = self._process_instruction(screen_obj, instruction)
                screen_obj['generator_last_yielded_value'] = result_value

            except Exception as io_error:
                print(f"WARN: [{screen_obj['screen_id']}] Instruction failed: {io_error}. Throwing to generator...")
                recovery_instruction = screen_obj['current_generator'].throw(io_error)
                result_value = self._process_instruction(screen_obj, recovery_instruction)
                screen_obj['generator_last_yielded_value'] = result_value

        except StopIteration:
            next_state = policy['transitions']['complete']
            self._transition_screen_to_state(screen_obj, next_state, "generator_complete")

        except Exception as e:
            print(f"ERROR: [{screen_obj['screen_id']}] Generator failed or unhandled error: {e}")
            next_state = policy['transitions']['fail']

            if screen_obj['current_generator']:
                screen_obj['current_generator'].close()
                screen_obj['current_generator'] = None

            self._transition_screen_to_state(screen_obj, next_state, "generator_failed")

        # =========================================================================
        # 🖱️ 입력 헬퍼 메서드 (내부용)
        # =========================================================================

    def _atomic_key(self, key: str):
        """
        [원자적 키 입력] 누름 -> 대기 -> 뗌
        - pyautogui.press()의 빠른 속도로 인한 입력 씹힘 방지
        - 게임 내 키 입력 확실한 인식 보장

        Args:
            key: 'L', 'esc', 'enter' 등 pyautogui가 인식하는 키 문자열
        """
        try:
            # 1. 누르기 (Press)
            pyautogui.keyDown(key)
            time.sleep(0.1)  # 0.1초 동안 확실히 누름 유지

            # 2. 떼기 (Release)
            pyautogui.keyUp(key)
            time.sleep(0.05)  # 뗀 상태 확실히 인식

        except Exception as e:
            print(f"WARN: Atomic Key Failed ({key}): {e}")
            # 비상시 강제 Release
            try:
                pyautogui.keyUp(key)
            except:
                pass

    def _atomic_click(self, x: int, y: int):
        """
        [원자적 클릭] 이동 -> 누름 -> 대기 -> 뗌
        - pyautogui.click()의 빠른 속도로 인한 입력 씹힘 방지
        - 드래그(Ghost Drag) 발생 원천 차단
        """
        try:
            # 1. 이동 후 안정화
            pyautogui.moveTo(x, y)

            # 2. 누르기 (Press)
            pyautogui.mouseDown()
            time.sleep(0.1)  # 0.1초 동안 확실히 누름 유지

            # 3. 떼기 (Release)
            pyautogui.mouseUp()
            time.sleep(0.05)  # 뗀 상태 확실히 인식

        except Exception as e:
            print(f"WARN: Atomic Click Failed: {e}")
            # 비상시 강제 Release
            pyautogui.mouseUp()

    # =========================================================================
    # 🎯 v3 상태머신 실행 엔진
    # =========================================================================

    def _process_instruction(self, screen_obj: dict, instruction: Dict[str, Any]) -> Any:
        """[v3] 지시 처리기 (원격 제어 및 Atomic Click 적용 완료)"""

        if not instruction:
            return None

        # ---------------------------------------------------------------------
        # ✅ [핵심] 원격 제어 컨텍스트(Context) 생성
        # 지시서에 'target_screen'이 있으면 그 화면을 실행 대상으로 설정 (S5 등)
        # 없으면 본인(screen_id)이 실행 대상이 됨
        # ---------------------------------------------------------------------
        target_id = instruction.get('target_screen', screen_obj['screen_id'])

        # 타겟의 region 정보 조회 (self.screens에 없을 수 있으므로 전역 정보 사용)
        target_region = SCREEN_REGIONS.get(target_id)
        if not target_region:
            print(f"ERROR: Unknown target screen {target_id}")
            return None

        # [중요] ctx_obj는 '실행(Action/IO)'을 담당하는 객체입니다.
        # - screen_id: 타겟 화면 ID (예: S5) -> 템플릿 경로 찾기, 락 걸기 용도
        # - region: 타겟 화면 좌표 (예: S5 영역) -> 이미지 서치, 클릭 좌표 용도
        ctx_obj = screen_obj.copy()
        ctx_obj['screen_id'] = target_id
        ctx_obj['region'] = target_region

        # screen_obj는 '생각(Logic/State)'을 담당하는 원본 객체입니다. (예: S1)
        # - generator_wait_*: 본인의 대기 상태 관리
        source_id = screen_obj['screen_id']
        op = instruction.get('operation')

        # ---------------------------------------------------------------------

        # 1. 대기 (Duration) - [Logic] 시간 흐름은 원본(screen_obj) 관리
        if op == 'wait_duration':
            duration = instruction.get('duration', 1.0)
            screen_obj['generator_wait_start_time'] = time.time() + duration
            return None

        # 2. 템플릿 대기 (Wait for Template) - [Action: ctx / Logic: screen_obj]
        elif op == 'wait_for_template':
            template_name = instruction['template_name']
            # ★ 타겟 화면(ctx)의 템플릿 경로를 가져옴
            template_path = get_template(ctx_obj['screen_id'], template_name)
            timeout = instruction.get('timeout', 5.0)

            # ★ 타겟 화면(ctx)에서 이미지 감지
            pos = self._detect_template(ctx_obj, template_path=template_path)

            if pos:
                # 찾았으면 원본의 대기 타이머 해제
                screen_obj['generator_wait_timeout'] = 0.0
                return pos
            else:
                # 못 찾았으면 원본의 타임아웃 체크
                if screen_obj['generator_wait_timeout'] == 0.0:
                    screen_obj['generator_wait_timeout'] = time.time() + timeout
                return None

        # 3. 클릭 (Click) - [Action: ctx]
        elif op == 'click':
            template_name = instruction['template_name']
            # ★ 타겟 화면(ctx)의 템플릿 경로
            template_path = get_template(ctx_obj['screen_id'], template_name)

            # ★ 타겟 화면(ctx)에서 감지
            pos = self._detect_template(ctx_obj, template_path=template_path)
            if not pos:
                # 타겟 화면에서 못 찾음
                raise Exception(f"Template not found on {ctx_obj['screen_id']} for click: {template_name}")

            # ★ 타겟 화면(ctx)으로 IO 요청 (S5에 락을 걺)
            action_lambda = lambda: self._atomic_click(pos[0], pos[1])
            self._request_io_action(ctx_obj, action_lambda)
            return pos

        # 4. 있으면 클릭 (Click if present) - [Action: ctx]
        elif op == 'click_if_present':
            template_name = instruction['template_name']
            template_path = get_template(ctx_obj['screen_id'], template_name)

            pos = self._detect_template(ctx_obj, template_path=template_path)
            if pos:
                action_lambda = lambda: self._atomic_click(pos[0], pos[1])
                self._request_io_action(ctx_obj, action_lambda)
            return pos

        # 5. 포커스 (Set Focus) - [Action: ctx]
        elif op == 'set_focus':
            # ★ 타겟 화면(ctx)의 region 사용
            region = ctx_obj['region']
            center_x = region[0] + region[2] // 2
            center_y = region[1] + region[3] // 2

            action_lambda = lambda: self._atomic_click(center_x, center_y)
            self._request_io_action(ctx_obj, action_lambda)
            return None

        # 6. 파티원 확인 (Multi-Template) - [Action: ctx]
        elif op == 'check_party_templates':
            candidate_templates = [
                'PARTY_MEMBER_1', 'PARTY_MEMBER_2', 'PARTY_MEMBER_3', 'PARTY_MEMBER_4'
            ]

            for template_key in candidate_templates:
                try:
                    # ★ 타겟 화면(ctx) 기준으로 템플릿 확인
                    template_path = get_template(ctx_obj['screen_id'], template_key)
                    pos = self._detect_template(ctx_obj, template_path=template_path)

                    if pos:
                        print(f"INFO: [{ctx_obj['screen_id']}] 파티원 감지 성공 ({template_key})")
                        return pos

                except Exception:
                    continue
            return None

        # 7. 단순 템플릿 확인 (Check Template) - [Action: ctx]
        elif op == 'check_template':
            template_name = instruction['template']
            template_path = get_template(ctx_obj['screen_id'], template_name)
            # ★ 타겟 화면(ctx)에서 감지
            pos = self._detect_template(ctx_obj, template_path=template_path)
            return pos

        # 8. 공유 상태 변경 (Set Shared State) - [Logic: screen_obj]
        # ★ 주의: 상태 변경은 로직의 주체(S1)가 변경되는 것임. 타겟(S5)의 상태를 바꾸는 게 아님.
        elif op == 'set_shared_state':
            new_state = instruction.get('state')
            if new_state:
                self.shared_states[source_id] = new_state
                print(f"INFO: [{source_id}] Shared State 전환 -> {new_state.name}")
            return True

        # 9. 드래그 동작 (Key Drag) - [Action: ctx]
        elif op == 'key_drag':
            action_config = {
                'key': instruction.get('key', 'ctrl'),
                'from': instruction.get('from'),
                'to': instruction.get('to'),
                'duration': instruction.get('duration', 0.5),
                'delay_after': instruction.get('delay_after', 0.0)
            }
            # ★ 타겟 화면 ID와 타겟 Region 전달
            self._handle_key_drag_operation(ctx_obj['screen_id'], ctx_obj['region'], action_config)
            return True

        # 10. 텍스트 입력 (Input Text) - [Action: ctx]
        elif op == 'input_text':
            text = instruction.get('text')
            if not text:
                raise Exception("Input Text operation requires a 'text' parameter.")

            action_lambda = lambda: pyautogui.write(text, interval=0.01)
            # ★ 타겟 화면(ctx)에 락을 걸고 입력 (Priority.HIGH)
            self._request_io_action(ctx_obj, action_lambda, priority=Priority.HIGH)
            print(f"INFO: [{ctx_obj['screen_id']}] 텍스트 입력 요청: {text}")
            return True
        # 11. 키 입력 (Key Press) - [Action: ctx]
        elif op == 'key_press':
            key = instruction.get('key')
            if not key:
                raise Exception("Key Press requires 'key' parameter")

            action_lambda = lambda: self._atomic_key(key)
            self._request_io_action(ctx_obj, action_lambda, priority=Priority.NORMAL)
            print(f"INFO: [{ctx_obj['screen_id']}] Atomic Key: {key}")
            return True

        else:
            print(f"WARN: [{source_id}] 알 수 없는 지시어: {op}")
            return None

    # =========================================================================
    # 🔧 유틸리티
    # =========================================================================

    def _detect_template(self, screen_obj: dict, template_path=None, template_name=None) -> Optional[Tuple[int, int]]:
        """템플릿 위치 반환 (좌표 튜플 또는 None)"""
        if template_path:
            path = template_path
        elif template_name:
            path = get_template(screen_obj['screen_id'], template_name)
        else:
            raise ValueError("template_path or template_name required")

        try:
            screenshot = self.orchestrator.capture_screen_safely(screen_obj['screen_id'])

            # NightCrows 유틸 사용
            from Orchestrator.NightCrows.utils.image_utils import return_ui_location
            return return_ui_location(
                template_path=path,
                region=screen_obj['region'],
                threshold=0.82,
                screenshot_img=screenshot
            )
        except Exception as e:
            print(f"WARN: [{self.monitor_id}] Template detection error: {e}")
            return None

    def _request_io_action(self, screen_obj, action_lambda, priority=Priority.NORMAL):
        """IO 스케줄러 요청"""
        screen_id = screen_obj['screen_id']
        self.io_scheduler.request(
            component="SM1",
            screen_id=screen_id,
            action=action_lambda,
            priority=priority
        )

    # =========================================================================
    # 🔄 상태 전이 및 예외 처리
    # =========================================================================

    def _transition_screen_to_state(self, screen_obj: dict, new_state: SystemState, reason: str):
        """화면별 상태 전이 실행 (v3: 공유 상태 사용)"""
        screen_id = screen_obj['screen_id']

        # ❗️ [수정] 공유 상태 읽기
        old_state = self.shared_states.get(screen_id)

        if old_state == new_state:
            return

        print(f"INFO: [{self.monitor_id}] {screen_id}: {old_state.name} → {new_state.name} ({reason})")

        if screen_obj['current_generator']:
            try:
                screen_obj['current_generator'].close()
            except Exception as e:
                print(f"WARN: [{screen_id}] Generator close error: {e}")

        # ❗️ [수정] 공유 상태 쓰기
        self.shared_states[screen_id] = new_state
        screen_obj['state_enter_time'] = time.time()

        screen_obj['current_generator'] = None
        screen_obj['generator_wait_start_time'] = 0.0
        screen_obj['generator_wait_timeout'] = 0.0
        screen_obj['generator_last_yielded_value'] = None

    def _handle_exception_policy(self, error_type: str):
        """예외 처리 정책"""
        if error_type in self.exception_policies:
            policy = self.exception_policies[error_type]
            action = policy.get('default_action', 'RETURN_TO_NORMAL')

            if action == 'RETURN_TO_NORMAL':
                for screen_obj in self.screens.values():
                    self._transition_screen_to_state(screen_obj, SystemState.NORMAL, f"exception policy: {error_type}")

        # 기존 _handle_action_result 메서드 내부나, yield 처리 부분에 추가 필요
        # SystemMonitor 구조상 generator가 yield한 operation을 처리하는 분기문이 있을 것입니다.

    def _handle_key_drag_operation(self, screen_id: str, region: tuple, action_config: dict):
        """
        범용: 키(Ctrl/Shift 등)를 누른 채로 드래그 수행
        (기존 _do_camera_drag_action을 범용화)
        """
        # IO 스케줄러에 요청 (람다로 감싸서)
        self.io_scheduler.request(
            component=self.monitor_id,
            screen_id=screen_id,
            action=lambda: self._execute_key_drag(region, action_config),
            priority=Priority.NORMAL
        )

    def _execute_key_drag(self, region: tuple, config: dict):
        """실제 PyAutoGUI 동작 실행"""
        import pyautogui

        key = config.get('key', 'ctrl')
        from_x, from_y = config.get('from')
        to_x, to_y = config.get('to')
        duration = config.get('duration', 0.5)

        region_x, region_y, _, _ = region
        abs_start_x = region_x + from_x
        abs_start_y = region_y + from_y
        abs_end_x = region_x + to_x
        abs_end_y = region_y + to_y

        try:
            pyautogui.keyDown(key)
            pyautogui.moveTo(abs_start_x, abs_start_y)
            pyautogui.dragTo(abs_end_x, abs_end_y, duration=duration, tween=pyautogui.easeOutQuad)
        except Exception as e:
            print(f"ERROR: Drag failed: {e}")
        finally:
            pyautogui.keyUp(key)  # 무조건 키 뗌

        if config.get('delay_after'):
            time.sleep(config.get('delay_after'))

# =============================================================================
# 🔌 Orchestrator 호출 인터페이스
# =============================================================================

# ❗️ [수정] shared_states 인자 추가
def create_system_monitor(monitor_id: str, vd_name: str, orchestrator=None, shared_states=None) -> SystemMonitor:
    """Orchestrator에서 호출하는 팩토리 함수"""
    return SystemMonitor(monitor_id, vd_name, orchestrator, shared_states)


if __name__ == "__main__":
    print("이 파일은 직접 실행할 수 없으며, Orchestrator가 로드해야 합니다.")