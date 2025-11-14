# Orchestrator/NightCrows/System_Monitor/src/core/monitor.py
"""
System Monitor 브릿지 (v3 제너레이터 '상황반장' 아키텍처)
- '바보 실행기' (Dumb Executor) 모델
- 모든 로직은 sm_config.py의 제너레이터 함수로 위임
- monitor는 제너레이터의 '지시서'를 받아 IO 스케줄러에 요청
"""

import time
import threading
# ✅ [수정 1] 'Generator'는 이 파일에서 사용되지 않으므로 제거. 'Tuple'은 반환 타입 힌트를 위해 추가.
from typing import Dict, List, Optional, Any, Tuple
import pyautogui
from Orchestrator.src.core.io_scheduler import Priority
from Orchestrator.NightCrows.utils.image_utils import set_focus
from Orchestrator.NightCrows.utils.screen_info import SCREEN_REGIONS

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

    # ✅ [수정 3] 사용되지 않는 'config' 매개변수 제거
    def __init__(self, monitor_id: str, vd_name: str, orchestrator=None):
        self.orchestrator = orchestrator
        self.io_scheduler = orchestrator.io_scheduler

        if not validate_config():
            raise ValueError(f"[{monitor_id}] sm_config.py 설정 검증 실패")
        if not verify_template_paths():
            raise FileNotFoundError(f"[{monitor_id}] 템플릿 파일 검증 실패")

        self.monitor_id = monitor_id
        self.vd_name = vd_name
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

        screen_region = SCREEN_REGIONS[screen_id]

        self.screens[screen_id] = {
            'screen_id': screen_id,
            'current_state': SystemState.NORMAL,
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
                    current_state = screen_obj['current_state']

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
            # ℹ️ [설명] '너무 광범위한 예외 절' :
            #    이 'except Exception'은 run_loop의 메인 스레드가
            #    예기치 않은 오류로 '죽는' 것을 방지하는 '안전망'입니다.
            #    의도된 설계이므로 유지하는 것이 좋습니다.
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

            # ✅ [수정 4] _detect_template이 (x, y) 또는 None을 반환하므로,
            #    'if self._detect_template(...):'는 템플릿을 찾았을 때(truthy) 동작합니다.
            pos = self._detect_template(screen_obj, template_path=template_path)

            if pos:  # 템플릿을 찾았다면
                print(f"INFO: [{screen_obj['screen_id']}] DetectOnly: '{template_name}' 발견.")

                # --- 🌟 [수정] Orchestrator에게 즉시 오류 보고 및 리턴 값 확인 ---
                is_false_positive = False  # 기본값
                if self.orchestrator:
                    # ❗️ *** 수정 1: 리턴 값 캡처 ***
                    is_false_positive = self.orchestrator.report_system_error(self.monitor_id, screen_obj['screen_id'])

                # ❗️ *** 수정 2: 리턴 값 확인 ***
                if is_false_positive:
                    print(
                        f"INFO: [{screen_obj['screen_id']}] Orchestrator confirmed False Positive. SM1 will NOT transition state.")
                    return  # <-- *** 상태 전이 중단 ***
                # --- 🌟 수정 완료 ---

                # (is_false_positive가 False인 경우에만 아래 로직 실행)
                # 이제 SM1이 이 화면의 제어권을 가짐
                self._transition_screen_to_state(screen_obj, next_state, f"detected: {template_name}")
                return  # 중요: 감지했으므로 루프 즉시 종료

    def _run_generator_step(self, screen_obj: dict, policy: dict, current_time: float):
        """[v3] '제너레이터' 상태 처리기 (예: LOGGING_IN)"""

        # 1. 'wait_duration' 또는 'wait_for_template' 대기 중인지 확인
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

        # 2. 제너레이터가 없으면 새로 생성
        if not screen_obj['current_generator']:
            gen_func = policy['generator']
            screen_obj['current_generator'] = gen_func(screen_obj)
            screen_obj['generator_last_yielded_value'] = None

        # 3. 제너레이터 실행 (next() 또는 send())
        try:
            instruction = screen_obj['current_generator'].send(
                screen_obj['generator_last_yielded_value']
            )
            result_value = self._process_instruction(screen_obj, instruction)
            screen_obj['generator_last_yielded_value'] = result_value

        except StopIteration:
            next_state = policy['transitions']['complete']
            self._transition_screen_to_state(screen_obj, next_state, "generator_complete")

        # ℹ️ [설명] '너무 광범위한 예외 절' :
        #    이 'except Exception'은 sm_config.py의 '상황반장'이
        #    'raise Exception(...)'을 통해 의도적으로 '실패'를 알릴 때
        #    반드시 필요합니다. 이것은 '버그'가 아닌 '필수 로직'입니다.
        except Exception as e:
            print(f"ERROR: [{screen_obj['screen_id']}] Generator failed: {e}")
            next_state = policy['transitions']['fail']
            self._transition_screen_to_state(screen_obj, next_state, "generator_failed")

    def _process_instruction(self, screen_obj: dict, instruction: Dict[str, Any]) -> Any:
        """[v3] 제너레이터의 '지시서'를 처리하는 '바보 실행기'의 핵심"""

        if not instruction:
            return None

        op = instruction.get('operation')
        screen_id = screen_obj['screen_id']
        # ❌ [수정 5] 사용되지 않는 'region' 변수 제거
        # region = screen_obj['region']

        if op == 'wait_duration':
            duration = instruction.get('duration', 1.0)
            screen_obj['generator_wait_start_time'] = time.time() + duration
            return None

        elif op == 'wait_for_template':
            template_name = instruction['template_name']
            template_path = get_template(screen_id, template_name)
            timeout = instruction.get('timeout', 5.0)

            pos = self._detect_template(screen_obj, template_path=template_path)
            if pos:
                screen_obj['generator_wait_timeout'] = 0.0
                return pos
            else:
                if screen_obj['generator_wait_timeout'] == 0.0:
                    screen_obj['generator_wait_timeout'] = time.time() + timeout
                return None

        elif op == 'click':
            template_name = instruction['template_name']
            template_path = get_template(screen_id, template_name)

            pos = self._detect_template(screen_obj, template_path=template_path)
            if not pos:
                raise Exception(f"Template not found for click: {template_name}")

            # ✅ [수정 4] pos가 (x, y) 튜플이므로 pos[0], pos[1] 사용 가능
            action_lambda = lambda: pyautogui.click(pos[0], pos[1])
            self._request_io_action(screen_obj, action_lambda)
            return pos

        elif op == 'click_if_present':
            template_name = instruction['template_name']
            template_path = get_template(screen_id, template_name)

            pos = self._detect_template(screen_obj, template_path=template_path)
            if pos:
                # ✅ [수정 4] pos가 (x, y) 튜플이므로 pos[0], pos[1] 사용 가능
                action_lambda = lambda: pyautogui.click(pos[0], pos[1])
                self._request_io_action(screen_obj, action_lambda)
            return pos

        elif op == 'set_focus':
            action_lambda = lambda: set_focus(screen_id)
            self._request_io_action(screen_obj, action_lambda)
            return None

        else:
            print(f"WARN: [{screen_id}] 알 수 없는 지시어: {op}")
            return None

    # =========================================================================
    # 🔧 글로벌룰 호출 / 유틸리티 (v3에서도 동일하게 필요)
    # =========================================================================

    # ✅ [수정 4] 'bool'이(가) '__getitem__' 사용 불가 -> 반환 타입을 bool에서 좌표 튜플로 변경
    def _detect_template(self, screen_obj: dict, template_path=None, template_name=None) -> Optional[Tuple[int, int]]:
        """
        템플릿 '감지'가 아닌 '위치 반환' (좌표 튜플 또는 None)으로 수정
        - 중앙집중식 캡처 사용 (유지)
        """
        if template_path:
            path = template_path
        elif template_name:
            path = get_template(screen_obj['screen_id'], template_name)
        else:
            raise ValueError("template_path or template_name required")

        try:
            screenshot = self.orchestrator.capture_screen_safely(screen_obj['screen_id'])

            # 'is_image_present'(bool) 대신 'return_ui_location'(pos or None) 사용
            from Orchestrator.NightCrows.utils.image_utils import return_ui_location
            return return_ui_location(
                template_path=path,
                region=screen_obj['region'],
                threshold=0.82,
                screenshot_img=screenshot
            )
        # ℹ️ [설명] '너무 광범위한 예외 절' :
        #    템플릿 감지/스크린샷 과정의 (cv2, pillow, os) 오류를
        #    모두 처리하기 위한 안전망입니다.
        except Exception as e:
            print(f"WARN: [{self.monitor_id}] Template detection error: {e}")
            return None  # 실패 시 None 반환

    def _request_io_action(self, screen_obj, action_lambda, priority=Priority.NORMAL):
        """IO 스케줄러에 작업을 요청하는 중앙 헬퍼 (유지)"""
        screen_id = screen_obj['screen_id']
        self.io_scheduler.request(
            component="SM1",
            screen_id=screen_id,
            action=action_lambda,
            priority=priority
        )

    # =========================================================================
    # 🔄 상태 전이 및 예외 처리 (v3에 맞게 수정됨)
    # =========================================================================

    def _transition_screen_to_state(self, screen_obj: dict, new_state: SystemState, reason: str):
        """화면별 상태 전이 실행 (v3: 제너레이터 정리 로직 추가)"""
        old_state = screen_obj['current_state']

        if old_state == new_state:
            return

        print(f"INFO: [{self.monitor_id}] {screen_obj['screen_id']}: {old_state.name} → {new_state.name} ({reason})")

        if screen_obj['current_generator']:
            try:
                screen_obj['current_generator'].close()
            except Exception as e:
                print(f"WARN: [{screen_obj['screen_id']}] Generator close error: {e}")

        screen_obj['current_state'] = new_state
        screen_obj['state_enter_time'] = time.time()
        screen_obj['current_generator'] = None
        screen_obj['generator_wait_start_time'] = 0.0
        screen_obj['generator_wait_timeout'] = 0.0
        screen_obj['generator_last_yielded_value'] = None

    def _handle_exception_policy(self, error_type: str):
        """예외 처리 정책 적용 - 모든 화면 NORMAL로 리셋 (유지)"""
        if error_type in self.exception_policies:
            policy = self.exception_policies[error_type]
            action = policy.get('default_action', 'RETURN_TO_NORMAL')

            if action == 'RETURN_TO_NORMAL':
                for screen_obj in self.screens.values():
                    self._transition_screen_to_state(screen_obj, SystemState.NORMAL, f"exception policy: {error_type}")


# =============================================================================
# 🔌 Orchestrator 호출 인터페이스 (동일)
# =============================================================================

# ✅ [수정 3] 사용되지 않는 'config' 매개변수 제거
def create_system_monitor(monitor_id: str, vd_name: str, orchestrator=None) -> SystemMonitor:
    """Orchestrator에서 호출하는 팩토리 함수"""
    return SystemMonitor(monitor_id, vd_name, orchestrator)


if __name__ == "__main__":
    print("이 파일은 직접 실행할 수 없으며, Orchestrator가 로드해야 합니다.")
    print("sm_config.py 역시 제너레이터 모델에 맞게 수정되어야 합니다.")