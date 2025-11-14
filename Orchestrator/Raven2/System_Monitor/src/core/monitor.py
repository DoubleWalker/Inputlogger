# Orchestrator/Raven2/System_Monitor/src/core/monitor.py (수정됨)
"""
System Monitor 브릿지 (v3. SM1 아키텍처 적용)
- IO 스케줄러 연동
- 비차단(non-blocking) 시퀀스 실행
"""

import time
import threading
from typing import Dict, List, Optional

# ❗️ [수정] 로컬룰 import 경로 변경
from Orchestrator.Raven2.System_Monitor.config.template_paths import get_template, verify_template_paths
from Orchestrator.Raven2.System_Monitor.config.sm_config import (
    SystemState,
    SM_CONFIG,
    SM_EXCEPTION_POLICIES,
    get_state_policy,
    validate_state_policies
)

# ❗️ [수정] 글로벌룰 import 경로 변경 (Raven2 유틸 사용)
from Orchestrator.Raven2.utils import image_utils
from Orchestrator.Raven2.utils.image_utils import set_focus
from Orchestrator.Raven2.utils.screen_info import SCREEN_REGIONS
from Orchestrator.src.core.io_scheduler import Priority


class SystemMonitor:
    """SM 브릿지 - 화면별 개별 객체성 관리 (RAVEN2)"""

    def __init__(self, monitor_id: str, vd_name: str, orchestrator=None):
        self.orchestrator = orchestrator
        # ❗️ [수정] IO 스케줄러 주입
        self.io_scheduler = orchestrator.io_scheduler

        # 설정 검증 (Raven2 config 사용)
        if not validate_state_policies():
            raise ValueError(f"[{monitor_id}] 상태 정책 검증 실패")
        if not verify_template_paths():
            raise FileNotFoundError(f"[{monitor_id}] 템플릿 파일 검증 실패")

        self.monitor_id = monitor_id
        self.vd_name = vd_name

        self.local_config = SM_CONFIG
        self.exception_policies = SM_EXCEPTION_POLICIES
        self.screens = {}
        self._initialize_screens()

        print(f"INFO: [{self.monitor_id}] SystemMonitor Bridge initialized for {vd_name} (RAVEN2)")
        print(f"INFO: [{self.monitor_id}] Target screens: {list(self.screens.keys())}")

    def _initialize_screens(self):
        """(변경 없음)"""
        target_screens = self.local_config['target_screens']['included']
        for screen_id in target_screens:
            self.add_screen(screen_id)

    def add_screen(self, screen_id: str) -> bool:
        """(v3: policy_step, step_timer_end 추가)"""
        if screen_id not in SCREEN_REGIONS:
            print(f"WARN: [{self.monitor_id}] Unknown screen_id: {screen_id}")
            return False

        screen_region = SCREEN_REGIONS[screen_id]

        self.screens[screen_id] = {
            'screen_id': screen_id,
            'current_state': SystemState.NORMAL,
            'state_enter_time': time.time(),
            'region': screen_region,

            # ❗️ [수정] v3 실행기 상태 변수 추가
            'policy_step': 0,
            'step_timer_end': 0.0,

            'retry_count': 0,
            'last_retry_time': 0.0,
            'sequence_attempts': 0,
            'initial_done': False,
        }
        # ❗️ [수정] 'fixed_coords'는 SM2 monitor.py 원본에 있었으나,
        #    SM1 아키텍처(config) 기반에서는 사용되지 않으므로 제거 (필요시 복구)
        # 'fixed_coords': FIXED_UI_COORDS.get(screen_id, {})

        print(f"INFO: [{self.monitor_id}] Added screen {screen_id} with region {screen_region}")
        return True

    # =========================================================================
    # 🔌 Orchestrator 인터페이스 (변경 없음)
    # =========================================================================

    def run_loop(self, stop_event: threading.Event):
        """(변경 없음)"""
        print(f"INFO: [{self.monitor_id}] Starting SystemMonitor bridge loop... (RAVEN2)")

        while not stop_event.is_set():
            try:
                check_interval = self.local_config['timing']['check_interval']
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
        """(변경 없음)"""
        print(f"INFO: [{self.monitor_id}] SystemMonitor stopping...")

    # =========================================================================
    # 🎯 화면별 상태머신 실행 엔진 (변경 없음)
    # =========================================================================

    def _execute_screen_state_machine(self, screen_obj: dict):
        """(변경 없음)"""
        policy = get_state_policy(screen_obj['current_state'])
        if not policy:
            print(
                f"WARN: [{self.monitor_id}] No policy found for {screen_obj['current_state'].name} on {screen_obj['screen_id']}")
            return
        action_results = self._execute_action_type(policy, screen_obj)
        result_key = self._execute_conditional_flow(policy, action_results, screen_obj)
        self._handle_state_transition(policy, result_key, screen_obj)

    def _execute_action_type(self, policy: dict, screen_obj: dict) -> dict:
        """(변경 없음)"""
        action_type = policy.get('action_type', 'detect_only')
        if action_type == 'detect_only':
            return self._handle_detection_targets(policy, screen_obj)
        elif action_type == 'detect_and_click':
            return self._handle_detection_targets(policy, screen_obj, should_click=True)
        elif action_type == 'sequence':
            # ❗️ [수정] _handle_sequence_execution으로 교체
            return self._handle_sequence_execution(policy, screen_obj)
        elif action_type == 'time_based_wait':
            return self._handle_time_based_check(policy, screen_obj)
        else:
            print(f"WARN: [{self.monitor_id}] Unknown action_type: {action_type}")
            return {}

    def _execute_conditional_flow(self, policy: dict, action_results: dict, screen_obj: dict) -> Optional[str]:
        """(변경 없음)"""
        flow_type = policy.get('conditional_flow', 'trigger')
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
    # 🎯 action_type 핸들러들 - (❗️핵심 수정)
    # =========================================================================

    def _handle_detection_targets(self, policy: dict, screen_obj: dict, should_click: bool = False) -> dict:
        """(❗️ [수정] 감지 시 Orchestrator에 오류 보고 추가)"""
        targets = policy.get('targets', [])
        if not targets:
            return {}

        screen_id = screen_obj['screen_id']
        region = screen_obj['region']

        for target in targets:
            template_name = target.get('template')
            result_key = target.get('result', 'detected')
            template_path = get_template(screen_id, template_name)
            if not template_path:
                continue

            # (Sensor) 감지
            if self._detect_template(screen_obj, template_path=template_path):
                # --- 🌟 [추가] Orchestrator에게 화면별 오류 보고 ---
                if self.orchestrator:
                    # SRM2가 이 화면(screen_id)에서만 손 떼도록 요청
                    self.orchestrator.report_system_error(self.monitor_id, screen_id)
                # --- 🌟 추가 완료 ---

                if should_click:
                    action_lambda = lambda p=template_path, r=region: image_utils.click_image(
                        template_path=p,
                        region=r,
                        threshold=0.85,
                        screenshot_img=None
                    )
                    self._request_io_action(screen_obj, action_lambda)

                return {result_key: True}
        return {}

    def _handle_time_based_check(self, policy: dict, screen_obj: dict) -> dict:
        """(변경 없음)"""
        current_time = time.time()
        elapsed = current_time - screen_obj['state_enter_time']
        expected_duration = policy.get('expected_duration', 30.0)
        timeout = policy.get('timeout', 60.0)
        return {
            'elapsed_time': elapsed,
            'duration_passed': elapsed >= expected_duration,
            'timeout_reached': elapsed >= timeout
        }

    # ❗️ [수정] SM1의 비차단 시퀀스 핸들러로 교체
    def _handle_sequence_execution(self, policy: dict, screen_obj: dict) -> dict:
        """
        [v3 SM1 아키텍처] policy_step 기반 비차단 시퀀스 핸들러
        - 'wait_duration'은 내부 타이머로 처리
        - 'click_if_present' (선택적 클릭) 지원
        """
        sequence_config = policy.get('sequence_config', {})
        actions = sequence_config.get('actions', [])
        step_index = screen_obj.get('policy_step', 0)

        screen_id = screen_obj['screen_id']
        region = screen_obj['region']

        # 1. 시퀀스 완료 확인
        if step_index >= len(actions):
            screen_obj['policy_step'] = 0
            return {'sequence_complete': True}

        # 2. 진행 중인 '스텝별 타이머' 확인 (wait_duration 처리)
        if screen_obj['step_timer_end'] > 0:
            if time.time() < screen_obj['step_timer_end']:
                return {'sequence_in_progress': True}  # 아직 대기 중
            else:
                screen_obj['step_timer_end'] = 0.0
                screen_obj['policy_step'] += 1
                step_index += 1
                if step_index >= len(actions):
                    screen_obj['policy_step'] = 0
                    return {'sequence_complete': True}

        # 3. 현재 스텝의 액션 가져오기
        action = actions[step_index]
        operation = action.get('operation')
        template_name = action.get('template')

        # 4. [Sensor] 비동기 대기 (wait)
        if operation == 'wait':
            template_path = get_template(screen_id, template_name)
            if self._detect_template(screen_obj, template_path=template_path):
                screen_obj['policy_step'] += 1
            return {'sequence_in_progress': True}

        # 5. [Sensor + Execution] 조건부 클릭 (click)
        if operation == 'click':
            template_path = get_template(screen_id, template_name)
            if self._detect_template(screen_obj, template_path=template_path):
                action_lambda = lambda p=template_path, r=region: image_utils.click_image(
                    template_path=p, region=r, threshold=0.85, screenshot_img=None
                )
                self._request_io_action(screen_obj, action_lambda)
                screen_obj['policy_step'] += 1
            return {'sequence_in_progress': True}

        # 6. [Sensor + Execution] 선택적 클릭 (click_if_present)
        if operation == 'click_if_present':
            template_path = get_template(screen_id, template_name)
            if self._detect_template(screen_obj, template_path=template_path):
                action_lambda = lambda p=template_path, r=region: image_utils.click_image(
                    template_path=p, region=r, threshold=0.85, screenshot_img=None
                )
                self._request_io_action(screen_obj, action_lambda)
            # ❗️ 'click'과 달리, 템플릿이 없어도 무조건 다음 스텝으로
            screen_obj['policy_step'] += 1
            return {'sequence_in_progress': True}

        # 7. [Execution] 즉시 실행 (set_focus)
        action_lambda = None
        if operation == 'set_focus':
            action_lambda = lambda sid=screen_id: set_focus(sid)

        if action_lambda:
            self._request_io_action(screen_obj, action_lambda)
            screen_obj['policy_step'] += 1
            return {'sequence_in_progress': True}

        # 8. [Non-Blocking Timer] wait_duration
        if operation == 'wait_duration':
            duration = action.get('duration', 1.0)
            screen_obj['step_timer_end'] = time.time() + duration
            # ❗️ policy_step은 증가시키지 않음!
            return {'sequence_in_progress': True}

        # 9. 알 수 없는 operation
        print(f"WARN: [{self.monitor_id}] 알 수 없는 시퀀스 operation: {operation}")
        screen_obj['policy_step'] += 1
        return {'sequence_in_progress': True}

    # =========================================================================
    # 🔄 conditional_flow 핸들러들
    # =========================================================================

    def _handle_immediate_trigger(self, action_results: dict) -> Optional[str]:
        """(변경 없음)"""
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
        """(변경 없음 - 'hold' flow type용)"""
        for result_key, detected in action_results.items():
            if detected and result_key not in ['elapsed_time']:
                return result_key
        return None

    def _handle_duration_based_flow(self, action_results: dict) -> Optional[str]:
        """(변경 없음)"""
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
    # 🔧 글로벌룰 호출 함수들 (❗️ [수정])
    # =========================================================================

    def _detect_template(self, screen_obj: dict, template_path=None, template_name=None) -> bool:
        """(❗️ [수정] IO Lock 제거, Orchestrator 캡처 사용)"""
        if template_path:
            path = template_path
        elif template_name:
            path = get_template(screen_obj['screen_id'], template_name)
        else:
            raise ValueError("template_path or template_name required")

        try:
            # ❗️ [수정] with self.io_lock: 제거
            screenshot = self.orchestrator.capture_screen_safely(screen_obj['screen_id'])

            # ❗️ [수정] Raven2 유틸 사용
            return image_utils.is_image_present(
                template_path=path,
                region=screen_obj['region'],
                threshold=0.85,
                screenshot_img=screenshot
            )
        except Exception as e:
            print(f"WARN: [{self.monitor_id}] Template detection error: {e}")
            return False

    # ❗️ [추가] IO 스케줄러 요청 헬퍼
    def _request_io_action(self, screen_obj, action_lambda, priority=Priority.NORMAL):
        """IO 스케줄러에 작업을 요청하는 중앙 헬퍼"""
        screen_id = screen_obj['screen_id']
        self.io_scheduler.request(
            component="SM2",
            screen_id=screen_id,
            action=action_lambda,
            priority=priority
        )

    # ❗️ [삭제] _click_template, _set_screen_focus 함수 삭제
    # (IO 스케줄러로 통합됨)

    # =========================================================================
    # 🔄 상태 전이 및 예외 처리 (❗️ [수정] v3 상태 변수 리셋 추가)
    # =========================================================================

    def _handle_state_transition(self, policy: dict, result_key: str, screen_obj: dict):
        """(변경 없음)"""
        if not result_key:
            return
        transitions = policy.get('transitions', {})
        next_state = transitions.get(result_key, screen_obj['current_state'])
        if next_state != screen_obj['current_state']:
            self._transition_screen_to_state(screen_obj, next_state, f"result: {result_key}")

    def _transition_screen_to_state(self, screen_obj: dict, new_state: SystemState, reason: str):
        """(❗️ [수정] v3 상태 변수 리셋 추가)"""
        old_state = screen_obj['current_state']
        screen_obj['current_state'] = new_state
        screen_obj['state_enter_time'] = time.time()

        # ❗️ [수정] v3 시퀀스 상태 정리
        screen_obj['policy_step'] = 0
        screen_obj['step_timer_end'] = 0.0

        screen_obj['retry_count'] = 0
        screen_obj['last_retry_time'] = 0.0
        screen_obj['sequence_attempts'] = 0
        screen_obj['initial_done'] = False

        print(f"INFO: [{self.monitor_id}] {screen_obj['screen_id']}: {old_state.name} → {new_state.name} ({reason})")

    def _handle_exception_policy(self, error_type: str):
        """(변경 없음)"""
        if error_type in self.exception_policies:
            policy = self.exception_policies[error_type]
            action = policy.get('default_action', 'RETURN_TO_NORMAL')
            if action == 'RETURN_TO_NORMAL':
                for screen_obj in self.screens.values():
                    self._transition_screen_to_state(screen_obj, SystemState.NORMAL, f"exception policy: {error_type}")


# =============================================================================
# 🔌 Orchestrator 호출 인터페이스
# =============================================================================

def create_system_monitor(monitor_id: str, vd_name: str, orchestrator=None) -> SystemMonitor:
    """Orchestrator에서 호출하는 팩토리 함수"""
    return SystemMonitor(monitor_id, vd_name, orchestrator)

if __name__ == "__main__":
    print("SM2 Monitor (v3 아키텍처) 테스트는 Orchestrator를 통해 실행해야 합니다.")