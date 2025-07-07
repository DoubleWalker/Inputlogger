# Orchestrator/NightCrows/System_Monitor/src/core/monitor.py
"""
System Monitor 브릿지 (정책화된 버전) - 4대 정책 범주 기준 리팩토링
- targets, action_type, transitions, conditional_flow 4대 정책만 사용
- screen_policy 제거하고 모든 화면 대상으로 단순화
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

# 글로벌룰 import
from Orchestrator.NightCrows.utils.screen_utils import (
    detect_designated_template_image,
    click_designated_template_image
)
from Orchestrator.NightCrows.utils.screen_info import SCREEN_REGIONS


class SystemMonitor:
    """SM 브릿지 - 4대 정책 범주 기반 시스템 모니터"""

    def __init__(self, monitor_id: str, config: Dict, vd_name: str, orchestrator=None):
        self.orchestrator = orchestrator
        """브릿지 초기화"""
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

        # 브릿지 상태
        self.current_state = SystemState.NORMAL
        self.state_enter_time = time.time()
        self.target_screens = self.local_config['target_screens']['included']
        self.screen_regions = {sid: SCREEN_REGIONS[sid] for sid in self.target_screens}
        self.retry_count = {}  # 상태별 재시도 카운트 관리
        self.last_retry_time = {}  # 마지막 재시도 시간
        self.sequence_attempts = {}
        self.initial_done = {}

        print(f"INFO: [{self.monitor_id}] SystemMonitor Bridge initialized for {vd_name}")
        print(f"INFO: [{self.monitor_id}] Target screens: {self.target_screens}")

    # =========================================================================
    # 🔌 Orchestrator 인터페이스 (스레드 통신)
    # =========================================================================

    def run_loop(self, stop_event: threading.Event):
        """Orchestrator 스레드에서 실행되는 메인 루프"""
        print(f"INFO: [{self.monitor_id}] Starting SystemMonitor bridge loop...")

        while not stop_event.is_set():
            try:
                # 로컬룰 정책: 체크 간격
                check_interval = self.local_config['timing']['check_interval']

                # 상태머신 실행 (브릿지 핵심 역할)
                self._execute_state_machine()

                # 대기 (중지 신호 확인하면서)
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
        pass

    # =========================================================================
    # 🎯 상태머신 실행 엔진 (4대 정책 범주 기반)
    # =========================================================================

    def _execute_state_machine(self):
        """현재 상태의 4대 정책을 실행하는 브릿지 엔진"""
        # 현재 상태 정책 가져오기
        policy = get_state_policy(self.current_state)
        if not policy:
            print(f"WARN: [{self.monitor_id}] No policy found for {self.current_state.name}")
            return

        # 4대 정책 범주 처리
        result = self._process_four_policies(policy)

        # 3. transitions: 어디로 갈지
        self._handle_state_transition(policy, result)

    def _process_four_policies(self, policy: dict) -> str:
        """4대 정책 범주를 순서대로 처리"""

        # 2. action_type: 어떻게 할지
        action_results = self._execute_action_type(policy)

        # 4. conditional_flow: 어떤 방식으로 처리할지
        result = self._handle_conditional_flow(policy, action_results)

        return result or self._get_default_result()

    def _handle_sequence_action(self, policy: dict) -> dict:
        """범용 시퀀스 액션 처리 - 간단한 BT 방식"""
        sequence_config = policy.get('sequence_config', {})
        state_key = self.current_state.name

        # 시퀀스 상태 초기화
        if state_key not in self.sequence_attempts:
            self.sequence_attempts[state_key] = 0
            self.initial_done[state_key] = False

        # 무한루프 방지
        self.sequence_attempts[state_key] += 1
        max_attempts = sequence_config.get('max_attempts', 15)

        if self.sequence_attempts[state_key] > max_attempts:
            self.sequence_attempts[state_key] = 0
            self.initial_done[state_key] = False
            return {'sequence_failed': True}

        # 모든 액션들을 하나로 처리 (initial/final 플래그로 구분)
        all_actions = sequence_config.get('actions', [])

        for action in all_actions:
            template_name = action['template']
            is_initial = action.get('initial', False)
            is_final = action.get('final', False)

            # Initial 액션: 한 번만 실행
            if is_initial:
                if self.initial_done.get(state_key, False):
                    continue  # 이미 실행됨, 스킵

            # 템플릿 체크 및 액션 실행
            for screen_id in self.target_screens:
                region = self.screen_regions[screen_id]
                template_path = get_template(screen_id, template_name)

                if template_path and self._detect_template(screen_id, region, template_path):
                    # Initial 액션: 배경 설정용, 실행만 하면 OK
                    if is_initial:
                        self.initial_done[state_key] = True
                        template_name = action.get('template', '')
                        self._execute_click_action(screen_id, region, template_path, f"sequence:{template_name}")
                        return {'sequence_in_progress': True}

                    # Final 액션: 완료 신호만 보내면 OK
                    if is_final:
                        self.sequence_attempts[state_key] = 0
                        self.initial_done[state_key] = False
                        return {'sequence_complete': True}

                    # 일반 액션 실행
                    template_name = action.get('template', '')
                    self._execute_click_action(screen_id, region, template_path, f"sequence:{template_name}")
                    return {'sequence_in_progress': True}

        return {'sequence_in_progress': True}

    def _execute_action_type(self, policy: dict) -> dict:
        """action_type에 따른 실행"""
        action_type = policy.get('action_type', 'detect_only')

        if action_type in ['detect_only', 'detect_and_click']:
            # targets가 있을 때만 감지 액션 실행
            targets = policy.get('targets', [])
            if not targets:
                print(f"INFO: [{self.monitor_id}] No targets for detection action in {self.current_state.name}")
                return {}
            return self._handle_detection_action(policy)

        elif action_type == 'time_based_wait':
            return self._handle_time_based_action(policy)
        elif action_type == 'sequence':  # ← 새로 추가
            result = self._handle_sequence_action(policy)
            # sequence 결과를 표준 형태로 변환
            if result.get('sequence_complete'):
                return {'sequence_complete': True}
            elif result.get('sequence_failed'):
                return {'sequence_failed': True}
            else:
                return {}  # 진행 중
        else:
            print(f"WARN: [{self.monitor_id}] Unknown action_type: {action_type}")
            return {}

    def _handle_detection_action(self, policy: dict) -> dict:
        """템플릿 감지 기반 액션 처리"""
        targets = policy.get('targets', [])
        action_type = policy.get('action_type', 'detect_only')

        # 빈 targets 방어 로직 추가
        if not targets:
            print(f"INFO: [{self.monitor_id}] No targets defined for {self.current_state.name}, skipping detection")
            return {}

        # 기존 감지 로직...

        results = {}

        for target in targets:
            template_name = target.get('template', '')
            result_key = target.get('result', 'detected')

            # 모든 대상 화면에서 템플릿 감지
            detected = False
            for screen_id in self.target_screens:
                region = self.screen_regions[screen_id]
                template_path = get_template(screen_id, template_name)

                if template_path and self._detect_template(screen_id, region, template_path):
                    detected = True

                    # detect_and_click인 경우 클릭 실행
                    if action_type == 'detect_and_click':
                        self._execute_click_action(screen_id, region, template_path, result_key)

                    break

            results[result_key] = detected

        return results

    def _handle_time_based_action(self, policy: dict) -> dict:
        """시간 기반 액션 처리"""
        current_time = time.time()
        elapsed = current_time - self.state_enter_time
        expected_duration = policy.get('expected_duration', 30.0)
        timeout = policy.get('timeout', 60.0)

        results = {
            'elapsed_time': elapsed,
            'duration_passed': elapsed >= expected_duration,
            'timeout_reached': elapsed >= timeout
        }

        return results

    def _handle_conditional_flow(self, policy: dict, action_results: dict) -> Optional[str]:
        """conditional_flow에 따른 흐름 제어 - 이름 통일"""
        flow_type = policy.get('conditional_flow', 'trigger')

        if flow_type == 'trigger':  # trigger (기존)
            return self._handle_trigger_flow(action_results)
        elif flow_type == 'retry':  # retry (이름 변경)
            return self._handle_retry_flow(action_results, policy)
        elif flow_type == 'hold':  # hold (이름 변경)
            return self._handle_hold_flow(action_results)
        elif flow_type == 'wait_for_duration':  # wait_for_duration (기존)
            return self._handle_wait_for_duration_flow(action_results)
        else:
            print(f"WARN: [{self.monitor_id}] Unknown conditional_flow: {flow_type}")
            return None

    def _handle_trigger_flow(self, action_results: dict) -> Optional[str]:
        """trigger 흐름: 감지 즉시 전이"""
        # 빈 결과 처리 추가
        if not action_results:
            return None

        for result_key, detected in action_results.items():
            if detected and result_key not in ['elapsed_time']:
                return result_key
        return None

    def _handle_retry_flow(self, action_results: dict, policy: dict) -> Optional[str]:
        """retry 흐름: 실패 시 시간 텀 두고 재시도"""
        retry_config = policy.get('retry_config', {})
        max_attempts = retry_config.get('max_attempts', 3)
        retry_delay = retry_config.get('retry_delay', 2.0)  # 재시도 간격
        failure_result = retry_config.get('failure_result', 'retry_failed')

        current_time = time.time()
        state_key = self.current_state.name

        # 성공한 결과가 있으면 카운트 리셋하고 반환
        for result_key, detected in action_results.items():
            if detected and result_key not in ['elapsed_time']:
                self.retry_count[state_key] = 0  # 성공 시 리셋
                return result_key

        # 실패 처리
        if state_key not in self.retry_count:
            self.retry_count[state_key] = 0

        # 재시도 딜레이 체크
        last_time = self.last_retry_time.get(state_key, 0)
        if current_time - last_time < retry_delay:
            return None  # 아직 딜레이 시간 안됨, 계속 대기

        # 재시도 횟수 증가
        self.retry_count[state_key] += 1
        self.last_retry_time[state_key] = current_time

        # 최대 재시도 횟수 초과 시
        if self.retry_count[state_key] >= max_attempts:
            self.retry_count[state_key] = 0  # 리셋
            return failure_result

        return None  # 재시도 계속

    def _handle_hold_flow(self, action_results: dict) -> Optional[str]:
        """hold 흐름: 조건 만족까지 대기"""
        # 빈 결과 처리 추가
        if not action_results:
            return None  # 계속 대기

        for result_key, detected in action_results.items():
            if detected and result_key not in ['elapsed_time']:
                return result_key
        return None  # 계속 대기

    def _handle_wait_for_duration_flow(self, action_results: dict) -> Optional[str]:
        """wait_for_duration 흐름: 시간 기반 전이"""
        if action_results.get('duration_passed', False):
            return 'duration_passed'
        elif action_results.get('timeout_reached', False):
            return 'timeout_reached'
        return None  # 계속 대기

    def _detect_template(self, screen_id: str, region: tuple, template_path: str) -> bool:
        """실제 템플릿 감지 (글로벌룰 활용)"""
        try:
            with self.io_lock:
                return detect_designated_template_image(
                    screen_id=screen_id,
                    screen_region=region,
                    template_path=template_path
                )
        except Exception as e:
            print(f"WARN: [{self.monitor_id}] Template detection error: {e}")
            return False

    def _execute_click_action(self, screen_id: str, region: tuple, template_path: str, result_key: str):
        """클릭 액션 실행 (글로벌룰 활용)"""
        print(f"INFO: [{self.monitor_id}] Executing click action for {result_key} on {screen_id}")

        try:
            with self.io_lock:
                success = click_designated_template_image(
                    screen_id=screen_id,
                    screen_region=region,
                    template_path=template_path
                )
                if success:
                    print(f"INFO: [{self.monitor_id}] Successfully clicked {result_key} on {screen_id}")
                else:
                    print(f"WARN: [{self.monitor_id}] Failed to click {result_key} on {screen_id}")
        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Click action error: {e}")

    def _handle_state_transition(self, policy: dict, result: str):
        """상태 전이 처리"""
        transitions = policy.get('transitions', {})
        next_state = transitions.get(result, self.current_state)

        if next_state != self.current_state:
            self._transition_to_state(next_state, f"result: {result}")

    def _transition_to_state(self, new_state: SystemState, reason: str):
        """상태 전이 실행"""
        old_state = self.current_state
        self.current_state = new_state
        self.state_enter_time = time.time()

        print(f"INFO: [{self.monitor_id}] {old_state.name} → {new_state.name} ({reason})")

    def _get_default_result(self) -> str:
        """상태별 기본 결과값 반환"""
        defaults = {
            SystemState.NORMAL: 'stay_normal',
            SystemState.CONNECTION_ERROR: 'confirm_click_failed',
            SystemState.CLIENT_CRASHED: 'restart_failed',
            SystemState.RESTARTING_APP: 'restart_timeout',
            SystemState.LOADING: 'loading_timeout',
            SystemState.LOGIN_REQUIRED: 'login_failed',
            SystemState.LOGGING_IN: 'login_timeout',
            SystemState.RETURNING_TO_GAME: 'return_timeout'
        }
        return defaults.get(self.current_state, 'unknown_state')

    def _handle_exception_policy(self, error_type: str):
        """예외 처리 정책 적용"""
        if error_type in self.exception_policies:
            policy = self.exception_policies[error_type]
            action = policy.get('default_action', 'RETURN_TO_NORMAL')

            if action == 'RETURN_TO_NORMAL':
                self._transition_to_state(SystemState.NORMAL, f"exception policy: {error_type}")


# =============================================================================
# 🔌 Orchestrator 호출 인터페이스
# =============================================================================

def create_system_monitor(monitor_id: str, config: Dict, vd_name: str) -> SystemMonitor:
    """Orchestrator에서 호출하는 팩토리 함수"""
    return SystemMonitor(monitor_id, config, vd_name)


# =============================================================================
# 🧪 테스트 실행 블록
# =============================================================================

if __name__ == "__main__":
    import threading

    print("🌉 SystemMonitor 4-Policy Bridge Test Starting...")

    # 테스트용 SystemMonitor 생성
    sm = SystemMonitor("SM_TEST", {}, "VD1")

    # 5초간 테스트 실행
    stop_event = threading.Event()
    test_thread = threading.Thread(target=sm.run_loop, args=(stop_event,))
    test_thread.start()

    time.sleep(5)
    stop_event.set()
    test_thread.join()

    print("✅ SystemMonitor test completed")