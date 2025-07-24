# Orchestrator/NightCrows/System_Monitor/src/core/monitor.py
"""
System Monitor 브릿지 (화면별 개별 객체성 적용)
- 각 화면별 독립적인 상태머신 관리
- 정책은 공유, 상태와 실행은 개별 관리
- SRM1 패턴의 add_screen() 적용
"""

import time
import threading
from typing import Dict, List, Optional

# 로컬룰 import
from Orchestrator.NightCrows.System_Monitor.config.template_paths import get_template, verify_template_paths
from Orchestrator.NightCrows.System_Monitor.config.sm_config import (
    SystemState,
    SM_CONFIG,
    SM_EXCEPTION_POLICIES,
    get_state_policy,
    validate_state_policies
)

# 글로벌룰 import (NightCrows)
from Orchestrator.NightCrows.utils.screen_utils import (
    detect_designated_template_image,
    click_designated_template_image
)
from Orchestrator.NightCrows.utils.image_utils import set_focus
from Orchestrator.NightCrows.utils.screen_info import SCREEN_REGIONS


class SystemMonitor:
    """SM 브릿지 - 화면별 개별 객체성 관리 (NightCrows)"""

    def __init__(self, monitor_id: str, config: Dict, vd_name: str, orchestrator=None):
        self.orchestrator = orchestrator

        # 설정 검증
        if not validate_state_policies():
            raise ValueError(f"[{monitor_id}] 상태 정책 검증 실패")
        if not verify_template_paths():
            raise FileNotFoundError(f"[{monitor_id}] 템플릿 파일 검증 실패")

        # Orchestrator 인터페이스
        self.monitor_id = monitor_id
        self.vd_name = vd_name
        self.io_lock = threading.Lock()

        # 로컬룰 설정 로드
        self.local_config = SM_CONFIG
        self.exception_policies = SM_EXCEPTION_POLICIES

        # 화면별 개별 객체 관리
        self.screens = {}

        # 화면 객체들 초기화
        self._initialize_screens()

        print(f"INFO: [{self.monitor_id}] SystemMonitor Bridge initialized for {vd_name} (NightCrows)")
        print(f"INFO: [{self.monitor_id}] Target screens: {list(self.screens.keys())}")

    def _initialize_screens(self):
        """screen_info.py 기반으로 화면 객체들 생성"""
        target_screens = self.local_config['target_screens']['included']

        for screen_id in target_screens:
            self.add_screen(screen_id)

    def add_screen(self, screen_id: str) -> bool:
        """글로벌룰 screen_info.py에서 정보 가져와서 화면 객체 생성 (SRM1 패턴)"""
        if screen_id not in SCREEN_REGIONS:
            print(f"WARN: [{self.monitor_id}] Unknown screen_id: {screen_id}")
            return False

        # 글로벌룰에서 화면 정보 가져오기
        screen_region = SCREEN_REGIONS[screen_id]

        self.screens[screen_id] = {
            'screen_id': screen_id,
            'current_state': SystemState.NORMAL,  # 모든 화면 NORMAL로 시작
            'state_enter_time': time.time(),
            'region': screen_region,

            # conditional_flow 상태 관리 (개별)
            'retry_count': 0,
            'last_retry_time': 0.0,
            'sequence_attempts': 0,
            'initial_done': False,
        }

        print(f"INFO: [{self.monitor_id}] Added screen {screen_id} with region {screen_region}")
        return True

    # =========================================================================
    # 🔌 Orchestrator 인터페이스
    # =========================================================================

    def run_loop(self, stop_event: threading.Event):
        """Orchestrator 스레드에서 실행되는 메인 루프"""
        print(f"INFO: [{self.monitor_id}] Starting SystemMonitor bridge loop... (NightCrows)")

        while not stop_event.is_set():
            try:
                check_interval = self.local_config['timing']['check_interval']

                # 각 화면별 독립적 상태머신 실행
                for screen_id, screen_obj in self.screens.items():
                    self._execute_screen_state_machine(screen_obj)

                if stop_event.wait(check_interval):
                    break

            except Exception as e:
                print(f"ERROR: [{self.monitor_id}] SystemMonitor loop exception: {e}")
                self._handle_exception_policy('state_machine_error')
                time.sleep(5.0)

        print(f"INFO: [{self.monitor_id}] SystemMonitor bridge loop stopped")

    def stop(self):
        """Orchestrator에서 호출하는 정리 메서드"""
        print(f"INFO: [{self.monitor_id}] SystemMonitor stopping...")

    # =========================================================================
    # 🎯 화면별 상태머신 실행 엔진
    # =========================================================================

    def _execute_screen_state_machine(self, screen_obj: dict):
        """개별 화면의 상태머신 실행"""
        # 공통 정책 가져오기 (정책은 공유)
        policy = get_state_policy(screen_obj['current_state'])
        if not policy:
            print(f"WARN: [{self.monitor_id}] No policy found for {screen_obj['current_state'].name} on {screen_obj['screen_id']}")
            return

        # 화면별 개별 실행
        action_results = self._execute_action_type(policy, screen_obj)
        result_key = self._execute_conditional_flow(policy, action_results, screen_obj)
        self._handle_state_transition(policy, result_key, screen_obj)

    def _execute_action_type(self, policy: dict, screen_obj: dict) -> dict:
        """action_type 정책 실행 - 화면별 개별 처리"""
        action_type = policy.get('action_type', 'detect_only')

        if action_type == 'detect_only':
            return self._handle_detection_targets(policy, screen_obj)
        elif action_type == 'detect_and_click':
            return self._handle_detection_targets(policy, screen_obj, should_click=True)
        elif action_type == 'sequence':
            return self._handle_sequence_execution(policy, screen_obj)
        elif action_type == 'time_based_wait':
            return self._handle_time_based_check(policy, screen_obj)
        else:
            print(f"WARN: [{self.monitor_id}] Unknown action_type: {action_type}")
            return {}

    def _execute_conditional_flow(self, policy: dict, action_results: dict, screen_obj: dict) -> Optional[str]:
        """conditional_flow 정책 실행 - 화면별 상태 관리"""
        flow_type = policy.get('conditional_flow', 'trigger')
        screen_id = screen_obj['screen_id']

        if flow_type == 'trigger':
            return self._handle_immediate_trigger(action_results)
        elif flow_type == 'retry':
            return self._handle_retry_strategy(policy, action_results, screen_obj)
        elif flow_type == 'hold':
            return self._handle_wait_until_condition(action_results)
        elif flow_type == 'wait_for_duration':
            return self._handle_duration_based_flow(action_results)
        elif flow_type == 'sequence_with_retry':
            return self._handle_sequence_retry_strategy(policy, action_results, screen_obj)
        else:
            print(f"WARN: [{self.monitor_id}] Unknown conditional_flow: {flow_type}")
            return None

    # =========================================================================
    # 🎯 action_type 핸들러들 - 화면별 개별 처리
    # =========================================================================

    def _handle_detection_targets(self, policy: dict, screen_obj: dict, should_click: bool = False) -> dict:
        """템플릿 감지 (및 클릭) 처리 - 특정 화면에서만 처리"""
        targets = policy.get('targets', [])

        if not targets:
            return {}

        screen_id = screen_obj['screen_id']
        region = screen_obj['region']

        # 해당 화면에서만 템플릿 검색 (for 루프 제거!)
        for target in targets:
            template_name = target.get('template')
            result_key = target.get('result', 'detected')

            template_path = get_template(screen_id, template_name)
            if not template_path:
                continue

            # 글로벌룰 호출: 감지
            if self._detect_template(screen_obj, template_path=template_path):
                # 클릭이 필요한 경우 실행
                if should_click:
                    self._click_template(screen_obj, template_path=template_path)
                return {result_key: True}

        return {}

    def _handle_sequence_execution(self, policy: dict, screen_obj: dict) -> dict:
        """시퀀스 액션 실행 - 화면별 상태 관리"""
        sequence_config = policy.get('sequence_config', {})
        actions = sequence_config.get('actions', [])
        screen_id = screen_obj['screen_id']

        # 각 액션 실행
        for action in actions:
            # initial 액션: 한 번만 실행
            if action.get('initial', False):
                if screen_obj.get('initial_done', False):
                    continue
                screen_obj['initial_done'] = True

            # 액션 실행 조건 확인
            if not self._should_execute_sequence_action(action, screen_obj):
                continue

            # 개별 액션 실행
            success = self._execute_sequence_action(action, screen_obj)

            # final 액션이면 시퀀스 완료
            if action.get('final', False) and success:
                screen_obj['initial_done'] = False  # 상태 리셋
                return {'sequence_complete': True}

        return {'sequence_in_progress': True}

    def _handle_time_based_check(self, policy: dict, screen_obj: dict) -> dict:
        """시간 기반 체크 - 화면별 타이밍"""
        current_time = time.time()
        elapsed = current_time - screen_obj['state_enter_time']
        expected_duration = policy.get('expected_duration', 30.0)
        timeout = policy.get('timeout', 60.0)

        return {
            'elapsed_time': elapsed,
            'duration_passed': elapsed >= expected_duration,
            'timeout_reached': elapsed >= timeout
        }

    # =========================================================================
    # 🔄 conditional_flow 핸들러들 - 화면별 상태 관리
    # =========================================================================

    def _handle_immediate_trigger(self, action_results: dict) -> Optional[str]:
        """즉시 전이 전략"""
        for result_key, detected in action_results.items():
            if detected and result_key not in ['elapsed_time']:
                return result_key
        return None

    def _handle_retry_strategy(self, policy: dict, action_results: dict, screen_obj: dict) -> Optional[str]:
        """재시도 전략 - 화면별 재시도 카운트 관리"""
        retry_config = policy.get('retry_config', {})
        max_attempts = retry_config.get('max_attempts', 3)
        retry_delay = retry_config.get('retry_delay', 2.5)
        failure_result = retry_config.get('failure_result', 'retry_failed')

        # 성공 조건 확인
        for result_key, detected in action_results.items():
            if detected and result_key not in ['elapsed_time']:
                screen_obj['retry_count'] = 0  # 성공 시 리셋
                return result_key

        # 재시도 타이밍 및 횟수 관리
        current_time = time.time()
        if current_time - screen_obj['last_retry_time'] < retry_delay:
            return None  # 딜레이 미달

        screen_obj['retry_count'] += 1
        screen_obj['last_retry_time'] = current_time

        if screen_obj['retry_count'] >= max_attempts:
            screen_obj['retry_count'] = 0  # 리셋
            return failure_result

        return None

    def _handle_wait_until_condition(self, action_results: dict) -> Optional[str]:
        """조건 만족까지 대기 전략"""
        for result_key, detected in action_results.items():
            if detected and result_key not in ['elapsed_time']:
                return result_key
        return None

    def _handle_duration_based_flow(self, action_results: dict) -> Optional[str]:
        """시간 기반 전이 전략"""
        if action_results.get('duration_passed', False):
            return 'duration_passed'
        elif action_results.get('timeout_reached', False):
            return 'timeout_reached'
        return None

    def _handle_sequence_retry_strategy(self, policy: dict, action_results: dict, screen_obj: dict) -> Optional[str]:
        """시퀀스 전용 재시도 전략 - 화면별 시퀀스 카운트 관리"""
        sequence_config = policy.get('sequence_config', {})
        max_attempts = sequence_config.get('max_attempts', 12)

        # 성공 확인
        if action_results.get('sequence_complete', False):
            screen_obj['sequence_attempts'] = 0  # 상태 정리
            return 'sequence_complete'

        # 실패 카운트 관리
        screen_obj['sequence_attempts'] += 1
        if screen_obj['sequence_attempts'] > max_attempts:
            screen_obj['sequence_attempts'] = 0  # 상태 정리
            return 'sequence_failed'

        return None

    # =========================================================================
    # 🔧 시퀀스 지원 함수들
    # =========================================================================

    def _should_execute_sequence_action(self, action: dict, screen_obj: dict) -> bool:
        """시퀀스 액션 실행 조건 확인 - 해당 화면에서만"""
        # 템플릿이 있는 액션: 템플릿 감지 시에만 실행
        if 'template' in action:
            template_name = action['template']
            return self._detect_template(screen_obj, template_name=template_name)

        # operation만 있는 액션: 항상 실행 가능
        return True

    def _execute_sequence_action(self, action: dict, screen_obj: dict) -> bool:
        operation = action.get('operation', 'click')

        if operation == 'click':
            template_name = action.get('template')
            return self._click_template(screen_obj, template_name=template_name)

        elif operation == 'wait':
            template_name = action.get('template')
            return self._detect_template(screen_obj, template_name=template_name)

        elif operation == 'wait_duration':
            duration = action.get('duration', 1.0)
            time.sleep(duration)
            return True
        elif operation == 'set_focus':
            # ➕ 새로 추가 필요!
            screen_id = screen_obj['screen_id']
            return self._set_screen_focus(screen_id)

        else:
            print(f"WARN: [{self.monitor_id}] Unknown operation: {operation}")
            return False

    # =========================================================================
    # 🔧 글로벌룰 호출 함수들 - 명시적 파라미터로 통합
    # =========================================================================

    def _detect_template(self, screen_obj: dict, template_path=None, template_name=None) -> bool:
        """템플릿 감지 - 중앙집중식 캡처 사용"""
        if template_path:
            path = template_path
        elif template_name:
            path = get_template(screen_obj['screen_id'], template_name)
        else:
            raise ValueError("template_path or template_name required")

        try:
            with self.io_lock:
                # ✅ 중앙집중식 캡처 사용 (SRM1 패턴 적용)
                screenshot = self.orchestrator.capture_screen_safely(screen_obj['screen_id'])
                from Orchestrator.NightCrows.utils.image_utils import is_image_present
                return is_image_present(
                    template_path=path,
                    region=screen_obj['region'],
                    threshold=0.85,
                    screenshot_img=screenshot  # ← 핵심: screenshot_img 전달
                )
        except Exception as e:
            print(f"WARN: [{self.monitor_id}] Template detection error: {e}")
            return False

    def _click_template(self, screen_obj: dict, template_path=None, template_name=None) -> bool:
        """템플릿 클릭 - 중앙집중식 캡처 사용"""
        if template_path:
            path = template_path
        elif template_name:
            path = get_template(screen_obj['screen_id'], template_name)
        else:
            raise ValueError("template_path or template_name required")

        try:
            with self.io_lock:
                # ✅ 중앙집중식 캡처 사용 (SRM1 패턴 적용)
                screenshot = self.orchestrator.capture_screen_safely(screen_obj['screen_id'])
                from Orchestrator.NightCrows.utils.image_utils import click_image
                return click_image(
                    template_path=path,
                    region=screen_obj['region'],
                    threshold=0.85,
                    screenshot_img=screenshot  # ← 핵심: screenshot_img 전달
                )
        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Template click error: {e}")
            return False

    def _set_screen_focus(self, screen_id: str) -> bool:
        """화면 포커스 설정"""
        try:
            with self.io_lock:
                return set_focus(screen_id)
        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Focus error: {e}")
            return False

    # =========================================================================
    # 🔄 상태 전이 및 예외 처리
    # =========================================================================

    def _handle_state_transition(self, policy: dict, result_key: str, screen_obj: dict):
        """상태 전이 처리 - 화면별 개별 관리"""
        if not result_key:
            return

        transitions = policy.get('transitions', {})
        next_state = transitions.get(result_key, screen_obj['current_state'])

        if next_state != screen_obj['current_state']:
            self._transition_screen_to_state(screen_obj, next_state, f"result: {result_key}")

    def _transition_screen_to_state(self, screen_obj: dict, new_state: SystemState, reason: str):
        """화면별 상태 전이 실행"""
        old_state = screen_obj['current_state']
        screen_obj['current_state'] = new_state
        screen_obj['state_enter_time'] = time.time()

        # 상태 변경 시 관련 흐름 상태 정리
        screen_obj['retry_count'] = 0
        screen_obj['last_retry_time'] = 0.0
        screen_obj['sequence_attempts'] = 0
        screen_obj['initial_done'] = False

        print(f"INFO: [{self.monitor_id}] {screen_obj['screen_id']}: {old_state.name} → {new_state.name} ({reason})")

    def _handle_exception_policy(self, error_type: str):
        """예외 처리 정책 적용 - 모든 화면 NORMAL로 리셋"""
        if error_type in self.exception_policies:
            policy = self.exception_policies[error_type]
            action = policy.get('default_action', 'RETURN_TO_NORMAL')

            if action == 'RETURN_TO_NORMAL':
                for screen_obj in self.screens.values():
                    self._transition_screen_to_state(screen_obj, SystemState.NORMAL, f"exception policy: {error_type}")


# =============================================================================
# 🔌 Orchestrator 호출 인터페이스
# =============================================================================

def create_system_monitor(monitor_id: str, config: Dict, vd_name: str, orchestrator=None) -> SystemMonitor:
    """Orchestrator에서 호출하는 팩토리 함수"""
    return SystemMonitor(monitor_id, config, vd_name, orchestrator)


if __name__ == "__main__":
    import threading

    print("🌉 SystemMonitor 화면별 개별 객체성 적용 테스트 시작... (NightCrows)")

    sm = SystemMonitor("SM_TEST", {}, "VD1")
    stop_event = threading.Event()
    test_thread = threading.Thread(target=sm.run_loop, args=(stop_event,))
    test_thread.start()

    time.sleep(5)
    stop_event.set()
    test_thread.join()

    print("✅ SystemMonitor 화면별 객체성 테스트 완료 (NightCrows)")