# Orchestrator/NightCrows/System_Monitor/src/core/monitor.py (브릿지 메인 클래스)
"""
System Monitor 브릿지 - Orchestrator 스레드로 실행되는 실행 엔진
- 로컬룰(sm_config.py) + 글로벌룰(screen_utils.py) 조합 실행
- Orchestrator와의 스레드 통신 담당
- SM 상태머신 실행 엔진
"""

import time
import threading
from typing import Dict, List
from ...config.template_paths import get_template
from ...config.sm_config import SystemState, SM_TRANSITIONS, SM_CONFIG, SM_EXCEPTION_POLICIES
from Orchestrator.NightCrows.utils.screen_utils import detect_designated_template_image, click_designated_template_image
from Orchestrator.NightCrows.utils import image_utils
from Orchestrator.NightCrows.utils.screen_info import SCREEN_REGIONS


class SystemMonitor:
    """SM 브릿지 - Orchestrator 스레드로 실행되는 시스템 모니터

    역할:
    1. Orchestrator와 스레드 통신 (run_loop, stop)
    2. 로컬룰 정책에 따른 상태머신 실행
    3. 글로벌룰 메커니즘 조합하여 실제 액션 수행
    """

    def __init__(self, monitor_id: str, config: Dict, vd_name: str):
        """브릿지 초기화

        Args:
            monitor_id: SM1, SM2 등 모니터 식별자
            config: Orchestrator에서 전달받은 설정 (사용 안함 - 로컬룰 우선)
            vd_name: VD1, VD2 등 가상 데스크톱 이름
        """
        # Orchestrator 인터페이스
        self.monitor_id = monitor_id
        self.vd_name = vd_name
        self.io_lock = threading.Lock()

        # 로컬룰 설정 로드
        self.local_config = SM_CONFIG
        self.transitions = SM_TRANSITIONS
        self.exception_policies = SM_EXCEPTION_POLICIES

        # 브릿지 상태
        self.current_state = SystemState.NORMAL
        self.target_screens = self.local_config['target_screens']['included']
        self.screen_regions = {sid: SCREEN_REGIONS[sid] for sid in self.target_screens}

        # 실행 상태
        self.retry_counts = {screen_id: 0 for screen_id in self.target_screens}
        self.last_check_time = time.time()

        print(f"INFO: [{self.monitor_id}] SystemMonitor Bridge initialized for {vd_name}")
        print(f"INFO: [{self.monitor_id}] Target screens: {self.target_screens}")

    # =========================================================================
    # 🔌 Orchestrator 인터페이스 (스레드 통신)
    # =========================================================================

    def run_loop(self, stop_event: threading.Event):
        """Orchestrator 스레드에서 실행되는 메인 루프

        Args:
            stop_event: Orchestrator에서 전달하는 종료 신호
        """
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
                # 로컬룰 정책: 예외 발생 시 30초 대기
                if stop_event.wait(30.0):
                    break

        print(f"INFO: [{self.monitor_id}] SystemMonitor bridge loop stopped")

    def stop(self):
        """Orchestrator가 모니터 종료 시 호출"""
        print(f"INFO: [{self.monitor_id}] SystemMonitor bridge stopping...")
        # 리소스 정리 등 필요시 구현

    # =========================================================================
    # 🧠 상태머신 실행 엔진 (브릿지 핵심 로직)
    # =========================================================================

    def _execute_state_machine(self):
        """상태머신 실행 - 로컬룰 전이규칙에 따라 글로벌룰 메커니즘 조합"""
        try:
            # 범용 상태 핸들러 실행
            result = self._handle_current_state()

            # 로컬룰 전이규칙에 따른 상태 전이
            if result and result in self.transitions.get(self.current_state, {}):
                new_state = self.transitions[self.current_state][result]
                self._transition_to_state(new_state, result)

        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] State machine execution failed: {e}")
            self._handle_exception_policy('state_machine_error')

    def _transition_to_state(self, new_state: SystemState, reason: str = ""):
        """상태 전이 실행 - 로컬룰 전이규칙 검증"""
        if new_state != self.current_state:
            old_state = self.current_state
            self.current_state = new_state
            print(f"INFO: [{self.monitor_id}] State transition: {old_state.name} → {new_state.name} ({reason})")

    # =========================================================================
    # 🎯 범용 상태 핸들러 (통합된 감지/액션 패턴)
    # =========================================================================

    def _handle_current_state(self) -> str:
        """현재 상태에 맞는 감지/액션 수행 - 통합된 범용 핸들러"""

        # 상태별 처리 설정 (로컬룰 매핑)
        state_configs = {
            SystemState.NORMAL: {
                'type': 'detect_only',
                'conditions': {
                    'connection_error_detected': 'CONNECTION_CONFIRM_BUTTON',
                    'client_crashed_detected': 'APP_ICON'
                },
                'default': 'stay_normal'
            },

            SystemState.CONNECTION_ERROR: {
                'type': 'detect_and_click',
                'detect_template': 'CONNECTION_CONFIRM_BUTTON',
                'action_template': 'CONNECTION_CONFIRM_BUTTON',
                'success_key': 'confirm_clicked_success',
                'fail_key': 'confirm_click_failed',
                'not_found_key': 'max_retries_reached'
            },

            SystemState.CLIENT_CRASHED: {
                'type': 'detect_and_click',
                'detect_template': 'APP_ICON',
                'action_template': 'APP_ICON',
                'success_key': 'restart_initiated',
                'fail_key': 'restart_failed',
                'not_found_key': 'max_retries_reached'
            },

            SystemState.RESTARTING_APP: {
                'type': 'detect_only',
                'conditions': {
                    'app_started': 'LOADING_SCREEN'
                },
                'default': 'restart_timeout'
            },

            SystemState.LOADING: {
                'type': 'detect_only',
                'conditions': {
                    'loading_complete': ['LOGIN_SCREEN', '!LOADING_SCREEN']  # 복수 조건
                },
                'default': 'loading_timeout'
            },

            SystemState.LOGIN_REQUIRED: {
                'type': 'detect_and_special_action',
                'detect_template': 'LOGIN_SCREEN',
                'special_action': 'simple_login',
                'success_key': 'login_started',
                'fail_key': 'login_failed',
                'not_found_key': 'max_login_retries'  # 게임 이미 준비됨
            },

            SystemState.LOGGING_IN: {
                'type': 'detect_only',
                'conditions': {
                    'login_complete': 'GAME_WORLD_LOADED'
                },
                'default': 'login_timeout'
            },

            SystemState.RETURNING_TO_GAME: {
                'type': 'detect_only',
                'conditions': {
                    'game_ready': 'GAME_WORLD_LOADED'
                },
                'default': 'return_timeout'
            }
        }

        config = state_configs.get(self.current_state)
        if not config:
            return 'unknown_state'

        # 설정에 따른 범용 처리
        if config['type'] == 'detect_only':
            return self._handle_detect_only(config)
        elif config['type'] == 'detect_and_click':
            return self._handle_detect_and_click(config)
        elif config['type'] == 'detect_and_special_action':
            return self._handle_detect_and_special_action(config)
        else:
            return 'unknown_type'

    def _handle_detect_only(self, config: dict) -> str:
        """감지만 하는 범용 핸들러"""
        conditions = config['conditions']
        default = config['default']

        for screen_id in self.target_screens:
            region = self.screen_regions[screen_id]

            for condition_key, template_spec in conditions.items():
                if isinstance(template_spec, list):
                    # 복수 조건 처리 (예: ['LOGIN_SCREEN', '!LOADING_SCREEN'])
                    if self._check_multiple_templates(screen_id, region, template_spec):
                        return condition_key
                else:
                    # 단일 템플릿 처리
                    if self._detect_template(screen_id, region, template_spec):
                        return condition_key

        return default

    def _handle_detect_and_click(self, config: dict) -> str:
        """감지 + 클릭 범용 핸들러"""
        detect_template = config['detect_template']
        action_template = config['action_template']
        success_key = config['success_key']
        fail_key = config['fail_key']
        not_found_key = config['not_found_key']

        for screen_id in self.target_screens:
            region = self.screen_regions[screen_id]

            if self._detect_template(screen_id, region, detect_template):
                if self._click_template(screen_id, region, action_template):
                    print(f"INFO: [{self.monitor_id}] Action succeeded on {screen_id}")
                    return success_key
                else:
                    print(f"ERROR: [{self.monitor_id}] Action failed on {screen_id}")
                    return fail_key

        # 감지되지 않음 - 보통 max_retries_reached (NORMAL로)
        return not_found_key

    def _handle_detect_and_special_action(self, config: dict) -> str:
        """감지 + 특수 액션 범용 핸들러"""
        detect_template = config['detect_template']
        special_action = config['special_action']
        success_key = config['success_key']
        fail_key = config['fail_key']
        not_found_key = config['not_found_key']

        for screen_id in self.target_screens:
            region = self.screen_regions[screen_id]

            if self._detect_template(screen_id, region, detect_template):
                # 특수 액션 실행
                if special_action == 'simple_login':
                    if self._perform_simple_login(screen_id):
                        return success_key
                    else:
                        return fail_key
                # 다른 특수 액션들 추가 가능

        # 감지되지 않음 - 게임이 이미 준비되었을 수 있음
        if self._check_any_game_ready():
            return not_found_key

        return fail_key

    def _check_any_game_ready(self) -> bool:
        """모든 화면에서 게임 준비 상태 확인"""
        for screen_id in self.target_screens:
            region = self.screen_regions[screen_id]
            if self._detect_template(screen_id, region, 'GAME_WORLD_LOADED'):
                return True
        return False

    def _check_multiple_templates(self, screen_id: str, region: tuple, template_specs: list) -> bool:
        """복수 템플릿 조건 체크 (!로 부정 조건 지원)"""
        for template_spec in template_specs:
            if template_spec.startswith('!'):
                # 부정 조건 (예: !LOADING_SCREEN)
                template_key = template_spec[1:]
                if self._detect_template(screen_id, region, template_key):
                    return False  # 있으면 안되는데 있음
            else:
                # 긍정 조건
                if not self._detect_template(screen_id, region, template_spec):
                    return False  # 있어야 하는데 없음

        return True  # 모든 조건 만족

    # =========================================================================
    # 🔧 브릿지 헬퍼 메서드들 (범용 브릿지 - 중복 제거)
    # =========================================================================

    def _detect_template(self, screen_id: str, screen_region: tuple, template_key: str) -> bool:
        """범용 템플릿 감지 - 브릿지 헬퍼"""
        template_path = get_template(screen_id, template_key)  # 로컬룰
        return detect_designated_template_image(screen_id, screen_region, template_path)  # 글로벌룰

    def _click_template(self, screen_id: str, screen_region: tuple, template_key: str) -> bool:
        """범용 템플릿 클릭 - 브릿지 헬퍼"""
        template_path = get_template(screen_id, template_key)  # 로컬룰
        return click_designated_template_image(screen_id, screen_region, template_path)  # 글로벌룰

    def _perform_simple_login(self, screen_id: str) -> bool:
        """단순 로그인 수행 - SM 전용 브릿지 함수"""
        try:
            # 로컬룰 정책: SM_CONFIG의 로그인 방식
            login_config = self.local_config['recovery_strategy']['login_process']
            click_count = login_config['center_click_count']
            click_delay = login_config['click_delay']

            # 글로벌룰 메커니즘: set_focus 조합
            with self.io_lock:  # Orchestrator IO 동기화
                for i in range(click_count):
                    if not image_utils.set_focus(screen_id, delay_after=0.2):
                        return False
                    if i < click_count - 1:
                        time.sleep(click_delay)

            return True

        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Simple login failed for {screen_id}: {e}")
            return False

    def _check_game_ready_any_screen(self) -> bool:
        """호환성을 위한 래퍼 메서드"""
        return self._check_any_game_ready()

    def _handle_exception_policy(self, error_type: str):
        """예외 처리 정책 적용"""
        if error_type in self.exception_policies:
            policy = self.exception_policies[error_type]
            action = policy.get('default_action', 'RETURN_TO_NORMAL')

            if action == 'RETURN_TO_NORMAL':
                self._transition_to_state(SystemState.NORMAL, f"exception policy: {error_type}")


# =============================================================================
# 🔌 Orchestrator 호출 인터페이스 (선택적)
# =============================================================================

def create_system_monitor(monitor_id: str, config: Dict, vd_name: str) -> SystemMonitor:
    """Orchestrator에서 호출하는 팩토리 함수"""
    return SystemMonitor(monitor_id, config, vd_name)