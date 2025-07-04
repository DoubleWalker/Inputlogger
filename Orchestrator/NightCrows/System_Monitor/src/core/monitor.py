# Orchestrator/NightCrows/System_Monitor/src/core/monitor.py
"""
System Monitor 브릿지 (정책화된 버전)
- 4가지 핵심 정책 기반의 상태머신 실행
- 조건부 흐름제어 헬퍼함수들
- 스크린 정책 적용된 화면 관리
"""

import time
import threading
from typing import Dict, List, Optional

# 로컬룰 import (상대경로 수정)
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
    """SM 브릿지 - 정책 기반 시스템 모니터"""

    def __init__(self, monitor_id: str, config: Dict, vd_name: str, orchestrator=None):
        self.orchestrator = orchestrator  # ← 이 줄 추가
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
                print(f"ERROR: [{self.monitor_id}] SystemMonitor loop exception: {e}")
                self._handle_exception_policy('state_machine_error')
                time.sleep(5.0)  # 에러 발생 시 5초 대기

        print(f"INFO: [{self.monitor_id}] SystemMonitor bridge loop stopped")

    def stop(self):
        """Orchestrator에서 호출하는 정리 메서드"""
        print(f"INFO: [{self.monitor_id}] SystemMonitor stopping...")
        # 필요한 정리 작업들
        pass

    # =========================================================================
    # 🎯 상태머신 실행 엔진 (브릿지 핵심)
    # =========================================================================

    def _execute_state_machine(self):
        """현재 상태의 정책을 실행하는 브릿지 엔진"""
        # 현재 상태 정책 가져오기
        policy = get_state_policy(self.current_state)
        if not policy:
            print(f"WARN: [{self.monitor_id}] No policy found for {self.current_state.name}")
            return

        # 4가지 핵심 정책 처리
        result = self._process_state_policy(policy)

        # 전이 처리
        self._handle_state_transition(policy, result)

    def _process_state_policy(self, policy: dict) -> str:
        """4가지 핵심 정책을 처리하여 결과 반환"""
        # 1. targets: 무엇을 감지할지
        targets = policy.get('targets', [])

        # 2. action_type: 어떻게 할지
        action_type = policy.get('action_type', 'detect_only')

        # 3. conditional_flow: 어떤 방식으로 처리할지
        flow_type = policy.get('conditional_flow', 'if_detected_then_branch')

        # 4. screen_policy: 어느 화면에서 처리할지
        screen_policy = policy.get('screen_policy', 'all_screens')

        # 화면 정책에 따른 대상 화면 결정
        target_screens = self._get_target_screens(screen_policy)

        # 타겟 감지 실행
        detection_results = self._detect_targets(targets, target_screens)

        # 흐름 제어에 따른 처리
        return self._handle_conditional_flow(flow_type, detection_results, action_type)

    def _detect_targets(self, targets: list, target_screens: list) -> dict:
        """타겟들을 감지하여 결과 반환"""
        results = {}

        for target in targets:
            template_name = target.get('template', '')
            result_key = target.get('result', 'detected')

            # 모든 대상 화면에서 템플릿 감지
            for screen_id in target_screens:
                region = self.screen_regions[screen_id]
                template_path = get_template(screen_id, template_name)

                if template_path and self._detect_template(screen_id, region, template_path):
                    results[result_key] = True
                    break
            else:
                results[result_key] = False

        return results

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

    def _get_target_screens(self, screen_policy: str) -> list:
        """스크린 정책에 따른 대상 화면 반환"""
        if screen_policy == 'all_screens':
            return self.target_screens
        elif screen_policy == 'any_screen':
            return self.target_screens
        elif screen_policy == 'priority_screen':
            return [self.target_screens[0]] if self.target_screens else []
        else:
            return self.target_screens

    def _handle_conditional_flow(self, flow_type: str, detection_results: dict, action_type: str) -> str:
        """조건부 흐름 제어 처리"""
        if flow_type == 'trigger':
            # 감지된 것이 있으면 해당 결과 반환
            for result_key, detected in detection_results.items():
                if detected:
                    if action_type == 'detect_and_click':
                        # 클릭 액션 실행 (글로벌룰 활용)
                        self._execute_click_action(result_key)
                    return result_key

            # 아무것도 감지되지 않음
            return self._get_default_result()

        elif flow_type == 'retry':
            # retry_until_success 로직
            return self._handle_retry(detection_results, action_type)

        elif flow_type == 'hold':
            # wait_until_condition 로직
            return self._handle_hold(detection_results, action_type)

        else:
            return self._get_default_result()

    def _handle_retry(self, detection_results: dict, action_type: str) -> str:
        """retry 전략 처리 - 성공할 때까지 재시도"""
        for result_key, detected in detection_results.items():
            if detected:
                # 성공 시 즉시 액션 실행 후 결과 반환
                if action_type == 'detect_and_click':
                    self._execute_click_action(result_key)
                return result_key

        # 실패 시 재시도를 위해 실패 결과 반환
        return self._get_default_result()

    def _handle_hold(self, detection_results: dict, action_type: str) -> str:
        """hold 전략 처리 - 조건 만족까지 대기"""
        for result_key, detected in detection_results.items():
            if detected:
                # 조건 만족 시 액션 실행 후 결과 반환
                if action_type == 'detect_and_click':
                    self._execute_click_action(result_key)
                return result_key

        # 조건 미만족 시 None 반환 (계속 대기)
        return None

    def _execute_click_action(self, result_key: str):
        """클릭 액션 실행 (글로벌룰 활용)"""
        print(f"INFO: [{self.monitor_id}] Executing click action for {result_key}")

        # 예시: CONNECTION_CONFIRM_BUTTON 클릭
        if 'connection' in result_key.lower():
            for screen_id in self.target_screens:
                region = self.screen_regions[screen_id]
                template_path = get_template(screen_id, 'CONNECTION_CONFIRM_BUTTON')
                if template_path:
                    success = click_designated_template_image(
                        screen_id=screen_id,
                        screen_region=region,
                        template_path=template_path
                    )
                    if success:
                        print(f"INFO: [{self.monitor_id}] Successfully clicked connection confirm on {screen_id}")
                        break

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

    print("🌉 SystemMonitor Policy-Based Bridge Test Starting...")

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