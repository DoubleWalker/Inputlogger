# Orchestrator/NightCrows/System_Monitor/src/core/monitor.py
"""
System Monitor 브릿지 (정책화된 버전)
- 5가지 핵심 정책 기반의 상태머신 실행
- 조건부 흐름제어 헬퍼함수들
- 스크린 정책 적용된 화면 순회
"""

import threading
from typing import Dict, List
from ...config.template_paths import get_template
from ...config.sm_config import SystemState, SM_STATE_POLICIES, SM_CONFIG, SM_EXCEPTION_POLICIES
from Orchestrator.NightCrows.utils.screen_utils import detect_designated_template_image, click_designated_template_image
from Orchestrator.NightCrows.utils import image_utils
from Orchestrator.NightCrows.utils.screen_info import SCREEN_REGIONS


class SystemMonitor:
    """SM 브릿지 - 정책 기반 시스템 모니터"""

    def __init__(self, monitor_id: str, config: Dict, vd_name: str):
        """브릿지 초기화"""
        # Orchestrator 인터페이스
        self.monitor_id = monitor_id
        self.vd_name = vd_name
        self.io_lock = threading.Lock()

        # 로컬룰 설정 로드
        self.local_config = SM_CONFIG
        self.exception_policies = SM_EXCEPTION_POLICIES

        # 브릿지 상태
        self.current_state = SystemState.NORMAL
        self.state_enter_time = time.time()  # 상태 진입 시간 (타임아웃용)
        self.target_screens = self.local_config['target_screens']['included']
        self.screen_regions = {sid: SCREEN_REGIONS[sid] for sid in self.target_screens}

        # 재시도 카운트 (상태별)
        self.retry_counts = {state: 0 for state in SystemState}

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
                print(f"ERROR: [{self.monitor_id}] Exception in main loop: {e}")
                # 예외 발생 시 30초 대기
                if stop_event.wait(30.0):
                    break

        print(f"INFO: [{self.monitor_id}] SystemMonitor bridge loop stopped")

    def stop(self):
        """Orchestrator가 모니터 종료 시 호출"""
        print(f"INFO: [{self.monitor_id}] SystemMonitor bridge stopping...")

    # =========================================================================
    # 🧠 상태머신 실행 엔진 (정책 기반)
    # =========================================================================

    def _execute_state_machine(self):
        """정책 기반 상태머신 실행"""
        try:
            # 현재 상태 정책 가져오기
            policy = SM_STATE_POLICIES.get(self.current_state, {})

            # 타임아웃 체크 (있는 상태만)
            timeout = policy.get('timeout')
            if timeout and self._is_timeout_exceeded(timeout):
                print(f"INFO: [{self.monitor_id}] Timeout ({timeout}s) exceeded in {self.current_state.name}")
                result = f'{self.current_state.name.lower()}_timeout'
            else:
                # 정책 기반 상태 핸들러 실행
                result = self._handle_universal()

            # 재시도 로직 처리
            result = self._handle_retry_logic(result, policy)

            # 상태 전이 실행
            if result and result in policy.get('transitions', {}):
                new_state = policy['transitions'][result]
                self._transition_to_state(new_state, result)

        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] State machine execution failed: {e}")
            self._handle_exception_policy('state_machine_error')

    def _handle_retry_logic(self, result: str, policy: dict) -> str:
        """재시도 로직 처리"""
        retry_config = policy.get('retry_config')
        if not retry_config:
            # 재시도 설정이 없으면 결과 그대로 반환
            return result

        failure_result = retry_config.get('failure_result')
        if result == failure_result:
            # 실패한 경우 재시도 카운트 증가
            self.retry_counts[self.current_state] += 1
            max_attempts = retry_config.get('max_attempts', 3)

            if self.retry_counts[self.current_state] >= max_attempts:
                # 최대 재시도 횟수 도달 → 포기
                give_up_result = retry_config.get('give_up_result', 'max_retries_reached')
                self.retry_counts[self.current_state] = 0
                print(f"INFO: [{self.monitor_id}] Max retries reached for {self.current_state.name}")
                return give_up_result
            else:
                # 재시도 (상태 유지)
                print(f"INFO: [{self.monitor_id}] Retrying {self.current_state.name} "
                      f"(Attempt {self.retry_counts[self.current_state]}/{max_attempts})")
                return None  # 상태 전이 없음
        else:
            # 성공한 경우 재시도 카운트 초기화
            self.retry_counts[self.current_state] = 0
            return result

    def _transition_to_state(self, new_state: SystemState, reason: str = ""):
        """상태 전이 실행"""
        if new_state != self.current_state:
            old_state = self.current_state
            self.current_state = new_state
            self.state_enter_time = time.time()  # 새 상태 진입 시간 기록
            print(f"INFO: [{self.monitor_id}] State transition: {old_state.name} → {new_state.name} ({reason})")

    def _is_timeout_exceeded(self, timeout: float) -> bool:
        """현재 상태 진입 후 타임아웃 초과 여부"""
        elapsed = time.time() - self.state_enter_time
        return elapsed > timeout

    # =========================================================================
    # 🎯 정책 기반 범용 핸들러
    # =========================================================================

    def _handle_universal(self) -> str:
        """5가지 정책 기반 범용 핸들러"""
        policy = SM_STATE_POLICIES.get(self.current_state, {})
        if not policy:
            return self._get_default_result()

        # 조건부 흐름제어 방식에 따라 분기
        conditional_flow = policy.get('conditional_flow')

        if conditional_flow == 'if_detected_then_branch':
            return self._handle_branch_flow(policy)
        elif conditional_flow == 'retry_until_success':
            return self._handle_retry_flow(policy)
        elif conditional_flow == 'wait_until_condition':
            return self._handle_wait_flow(policy)
        else:
            print(f"WARNING: [{self.monitor_id}] Unknown conditional_flow: {conditional_flow}")
            return self._get_default_result()

    # =========================================================================
    # 🔧 조건부 흐름제어 헬퍼함수들
    # =========================================================================

    def _handle_branch_flow(self, policy: dict) -> str:
        """if_detected_then_branch: 감지되면 분기"""
        targets = policy.get('targets', [])
        action_type = policy.get('action_type', 'detect_only')
        screen_policy = policy.get('screen_policy', {})

        # 스크린 정책 적용
        results = self._execute_screen_policy(targets, action_type, screen_policy)

        # 첫 번째 성공 결과 반환
        for result in results:
            if result:
                return result

        # 아무것도 감지되지 않음
        return 'stay_normal'

    def _handle_retry_flow(self, policy: dict) -> str:
        """retry_until_success: 성공할 때까지 재시도"""
        targets = policy.get('targets', [])
        action_type = policy.get('action_type', 'detect_only')
        screen_policy = policy.get('screen_policy', {})
        retry_config = policy.get('retry_config', {})

        # 스크린 정책 적용
        results = self._execute_screen_policy(targets, action_type, screen_policy)

        # 성공 조건 확인
        success_condition = screen_policy.get('success_condition', 'any_success')

        if success_condition == 'any_success':
            # 하나라도 성공하면 성공
            for result in results:
                if result and result != retry_config.get('failure_result'):
                    return result

        # 모든 시도 실패
        return retry_config.get('failure_result', 'action_failed')

    def _handle_wait_flow(self, policy: dict) -> str:
        """wait_until_condition: 조건 만족할 때까지 대기"""
        targets = policy.get('targets', [])
        action_type = policy.get('action_type', 'detect_only')
        screen_policy = policy.get('screen_policy', {})

        # 특수 조건 처리 (LOADING 상태의 복합 조건 등)
        for target in targets:
            condition = target.get('condition')
            if condition == 'without_loading_screen':
                # LOGIN_SCREEN 있고 LOADING_SCREEN 없어야 함
                if self._check_loading_completion():
                    return target['result']
            else:
                # 일반 감지
                results = self._execute_screen_policy([target], action_type, screen_policy)
                for result in results:
                    if result:
                        return result

        # 조건 만족하지 않음 (계속 대기)
        return None

    # =========================================================================
    # 🖥️ 스크린 정책 실행
    # =========================================================================

    def _execute_screen_policy(self, targets: list, action_type: str, screen_policy: dict) -> list:
        """스크린 정책에 따른 화면 순회 및 액션 실행"""
        mode = screen_policy.get('mode', 'first_match_wins')
        stop_on_first = screen_policy.get('stop_on_first', True)

        results = []

        if mode == 'first_match_wins':
            # 첫 번째 매치에서 즉시 종료
            for screen_id in self.target_screens:
                region = self.screen_regions[screen_id]
                for target in targets:
                    success = self._execute_action_by_type(action_type, screen_id, region, target['template'])
                    if success:
                        return [target['result']]  # 즉시 반환
            return [None]

        elif mode == 'handle_all_matches':
            # 모든 화면에서 매치 처리
            for screen_id in self.target_screens:
                region = self.screen_regions[screen_id]
                for target in targets:
                    success = self._execute_action_by_type(action_type, screen_id, region, target['template'])
                    if success:
                        results.append(target['result'])
                        print(f"INFO: [{self.monitor_id}] Handled {target['template']} on {screen_id}")
            return results

        elif mode == 'sequential_all':
            # 순차적으로 모든 화면 처리
            delay = screen_policy.get('delay_between_screens', 0.5)
            for screen_id in self.target_screens:
                region = self.screen_regions[screen_id]
                for target in targets:
                    success = self._execute_action_by_type(action_type, screen_id, region, target['template'])
                    if success:
                        results.append(target['result'])
                        print(f"INFO: [{self.monitor_id}] Sequential action on {screen_id}")
                if delay > 0:
                    time.sleep(delay)
            return results

        return [None]

    # =========================================================================
    # 🔧 브릿지 헬퍼 메서드들
    # =========================================================================

    def _execute_action_by_type(self, action_type: str, screen_id: str, region: tuple, template_key: str) -> bool:
        """액션타입에 따라 적절한 글로벌룰 메커니즘 매핑"""

        if action_type == 'detect_only':
            # 글로벌룰: 감지만
            return self._detect_template(screen_id, region, template_key)

        elif action_type == 'detect_and_click':
            # 글로벌룰: 감지 + 클릭
            return self._click_template(screen_id, region, template_key)

        elif action_type == 'detect_and_special_action':
            # 글로벌룰: 감지 후 특수액션 (로그인)
            if self._detect_template(screen_id, region, template_key):
                return self._perform_simple_login(screen_id)
            return False

        else:
            print(f"WARNING: [{self.monitor_id}] Unknown action type: {action_type}")
            return False

    def _detect_template(self, screen_id: str, screen_region: tuple, template_key: str) -> bool:
        """범용 템플릿 감지 - 브릿지 헬퍼"""
        template_path = get_template(screen_id, template_key)
        if not template_path:
            return False
        return detect_designated_template_image(screen_id, screen_region, template_path)

    def _click_template(self, screen_id: str, screen_region: tuple, template_key: str) -> bool:
        """범용 템플릿 클릭 - 브릿지 헬퍼"""
        template_path = get_template(screen_id, template_key)
        if not template_path:
            return False
        return click_designated_template_image(screen_id, screen_region, template_path)

    def _perform_simple_login(self, screen_id: str) -> bool:
        """단순 로그인 수행 - SM 전용 브릿지 함수"""
        try:
            # 로컬룰 정책: 단순 로그인 방식 (가운데 2번 클릭)
            with self.io_lock:
                for i in range(2):
                    if not image_utils.set_focus(screen_id, delay_after=0.2):
                        return False
                    if i < 1:  # 마지막이 아니면
                        time.sleep(2.0)
            return True
        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Simple login failed for {screen_id}: {e}")
            return False

    def _check_loading_completion(self) -> bool:
        """LOADING 상태의 복합 조건 (LOGIN_SCREEN 감지 & LOADING_SCREEN 미감지)"""
        for screen_id in self.target_screens:
            region = self.screen_regions[screen_id]
            login_detected = self._detect_template(screen_id, region, 'LOGIN_SCREEN')
            loading_detected = self._detect_template(screen_id, region, 'LOADING_SCREEN')
            if login_detected and not loading_detected:
                return True
        return False

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
    import time

    print("🌉 SystemMonitor Policy-Based Bridge Test Starting...")

    # 테스트용 SystemMonitor 생성
    sm = SystemMonitor("SM_TEST", {}, "VD1")
    stop_event = threading.Event()

    try:
        print(f"INFO: Starting test with target screens: {sm.target_screens}")
        print(f"INFO: Current state: {sm.current_state}")
        print("INFO: Press Ctrl+C to stop...")

        # 메인 루프 실행 (별도 스레드)
        monitor_thread = threading.Thread(target=sm.run_loop, args=(stop_event,))
        monitor_thread.daemon = True
        monitor_thread.start()

        # 메인 스레드는 키보드 입력 대기
        while not stop_event.is_set():
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        stop_event.set()

    except Exception as e:
        print(f"❌ Test error: {e}")
        stop_event.set()

    finally:
        print("🏁 SystemMonitor Policy-Based Bridge Test Completed")
        time.sleep(1)

# =============================================================================
# 🚀 미래 글로벌룰화 후보 함수들
# =============================================================================

#다른 컴포넌트들(SRM, MSC 등)이 정책화된 후, 공통 패턴이 발견되면
#아래 함수들을 글로벌룰로 승격시킬 수 있습니다:

#📦 global_rules.flow_controls 모듈 후보:
#- conditional_branch_flow(targets, action_type, screen_policy)     # _handle_branch_flow 글로벌화
#- retry_until_success_flow(targets, action_type, retry_config)     # _handle_retry_flow 글로벌화
#- polling_wait_flow(targets, action_type, timeout_config)          # _handle_wait_flow 글로벌화

#📦 global_rules.screen_policies 모듈 후보:
#- execute_first_match_policy(targets, action_type, screens)        # first_match_wins 글로벌화
#- execute_all_matches_policy(targets, action_type, screens)        # handle_all_matches 글로벌화
#- execute_sequential_policy(targets, action_type, screens, delay)  # sequential_all 글로벌화

#📦 global_rules.state_machine 모듈 후보:
#- policy_based_state_executor(current_state, policies)            # _execute_state_machine 글로벌화
##- retry_logic_handler(result, retry_config, retry_counts)         # _handle_retry_logic 글로벌화
#- timeout_checker(state_enter_time, timeout_config)               # _is_timeout_exceeded 글로벌화

#📦 global_rules.template_actions 모듈 후보:
##- universal_action_executor(action_type, screen_id, region, template)  # _execute_action_by_type 글로벌화
# complex_condition_checker(condition_type, screen_regions)            # _check_loading_completion 글로벌화

#🎯 글로벌화 시점 판단 기준:
#1. SRM, MSC 등 최소 2개 이상 컴포넌트에서 동일 패턴 발견
#2. 함수 시그니처가 안정화되고 더 이상 변경되지 않음
#3. 범용성이 입증되어 모든 상태머신에서 재사용 가능
#4. 성능상 이점이 있거나 중복 코드 제거 효과가 명확함

#💡 글로벌화 예시:
#현재: self._handle_branch_flow(policy)
#미래: flows.conditional_branch_flow(policy['targets'], policy['action_type'], self.screen_regions)