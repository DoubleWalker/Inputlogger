# Orchestrator/NightCrows/System_Monitor/config/sm_config.py
"""
SystemMonitor 로컬룰 정의 (정책화된 버전)
- SM1의 고유한 "성격"과 "정책" 정의
- 상태별 통합 정책 (5가지 핵심 정책)
- 기존 분산된 설정들을 상태별로 통합
"""

from enum import Enum, auto


# =============================================================================
# 🎯 로컬룰 1: 상태 정의 (SM1의 고유한 생활 패턴)
# =============================================================================

class SystemState(Enum):
    """SystemMonitor 상태 정의"""
    NORMAL = auto()  # 정상 상태
    CONNECTION_ERROR = auto()  # 연결 에러 감지
    CLIENT_CRASHED = auto()  # 클라이언트 크래시
    RESTARTING_APP = auto()  # 앱 재시작 중
    LOADING = auto()  # 로딩 중
    LOGIN_REQUIRED = auto()  # 로그인 필요
    LOGGING_IN = auto()  # 로그인 진행 중
    RETURNING_TO_GAME = auto()  # 게임 복귀 중


# =============================================================================
# 🎯 로컬룰 2: 상태별 통합 정책 (5가지 핵심 정책)
# =============================================================================

SM_STATE_POLICIES = {
    SystemState.NORMAL: {
        # 1. 무엇을 감지할지
        'targets': [
            {'template': 'CONNECTION_CONFIRM_BUTTON', 'result': 'connection_error_detected'},
            {'template': 'APP_ICON', 'result': 'client_crashed_detected'}
        ],

        # 2. 어떻게 할지
        'action_type': 'detect_only',

        # 3. 어디로 갈지
        'transitions': {
            'connection_error_detected': SystemState.CONNECTION_ERROR,
            'client_crashed_detected': SystemState.CLIENT_CRASHED,
            'stay_normal': SystemState.NORMAL
        },

        # 4. 조건부 흐름제어 방식
        'conditional_flow': 'if_detected_then_branch',

        # 5. 화면 순회 방식
        'screen_policy': {
            'mode': 'first_match_wins',
            'stop_on_first': True
        },

        # 설정값: 타임아웃 (없음)
        'timeout': None
    },

    SystemState.CONNECTION_ERROR: {
        'targets': [
            {'template': 'CONNECTION_CONFIRM_BUTTON', 'result': 'confirm_clicked_success'}
        ],

        'action_type': 'detect_and_click',

        'transitions': {
            'confirm_clicked_success': SystemState.LOGIN_REQUIRED,
            'confirm_click_failed': SystemState.CONNECTION_ERROR,  # 재시도
            'max_retries_reached': SystemState.NORMAL  # 포기
        },

        'conditional_flow': 'retry_until_success',

        'screen_policy': {
            'mode': 'handle_all_matches',
            'stop_on_first': False,
            'success_condition': 'any_success'
        },

        'timeout': None,  # 재시도 로직이니까 타임아웃 없음

        # 재시도 설정
        'retry_config': {
            'max_attempts': 3,
            'failure_result': 'confirm_click_failed',
            'give_up_result': 'max_retries_reached'
        }
    },

    SystemState.CLIENT_CRASHED: {
        'targets': [
            {'template': 'APP_ICON', 'result': 'restart_initiated'}
        ],

        'action_type': 'detect_and_click',

        'transitions': {
            'restart_initiated': SystemState.RESTARTING_APP,
            'restart_failed': SystemState.CLIENT_CRASHED,  # 재시도
            'max_retries_reached': SystemState.NORMAL  # 포기
        },

        'conditional_flow': 'retry_until_success',

        'screen_policy': {
            'mode': 'handle_all_matches',  # 여러 화면 동시 크래시 대응
            'stop_on_first': False,
            'success_condition': 'any_success'
        },

        'timeout': None,

        'retry_config': {
            'max_attempts': 2,  # 앱 재시작은 2번만
            'failure_result': 'restart_failed',
            'give_up_result': 'max_retries_reached'
        }
    },

    SystemState.RESTARTING_APP: {
        'targets': [
            {'template': 'LOADING_SCREEN', 'result': 'app_started'}
        ],

        'action_type': 'detect_only',

        'transitions': {
            'app_started': SystemState.LOADING,
            'restart_timeout': SystemState.CLIENT_CRASHED,  # 다시 시도
            'restart_failed': SystemState.NORMAL
        },

        'conditional_flow': 'wait_until_condition',

        'screen_policy': {
            'mode': 'first_match_wins',
            'stop_on_first': True
        },

        'timeout': 20.0  # 앱 재시작 20초 대기
    },

    SystemState.LOADING: {
        'targets': [
            {'template': 'LOGIN_SCREEN', 'result': 'loading_complete', 'condition': 'without_loading_screen'}
        ],

        'action_type': 'detect_only',

        'transitions': {
            'loading_complete': SystemState.LOGIN_REQUIRED,
            'loading_timeout': SystemState.RESTARTING_APP,  # 다시 시작
            'loading_failed': SystemState.NORMAL
        },

        'conditional_flow': 'wait_until_condition',

        'screen_policy': {
            'mode': 'first_match_wins',
            'stop_on_first': True
        },

        'timeout': 15.0  # 로딩 15초 대기
    },

    SystemState.LOGIN_REQUIRED: {
        'targets': [
            {'template': 'LOGIN_SCREEN', 'result': 'login_started'}
        ],

        'action_type': 'detect_and_special_action',

        'transitions': {
            'login_started': SystemState.LOGGING_IN,
            'login_failed': SystemState.LOGIN_REQUIRED,  # 재시도
            'max_login_retries': SystemState.NORMAL  # 포기
        },

        'conditional_flow': 'retry_until_success',

        'screen_policy': {
            'mode': 'sequential_all',  # 순차적으로 로그인
            'stop_on_first': False,
            'delay_between_screens': 0.5
        },

        'timeout': 15.0,  # 로그인 15초 대기

        'retry_config': {
            'max_attempts': 3,
            'failure_result': 'login_failed',
            'give_up_result': 'max_login_retries'
        }
    },

    SystemState.LOGGING_IN: {
        'targets': [
            {'template': 'GAME_WORLD_LOADED', 'result': 'login_complete'}
        ],

        'action_type': 'detect_only',

        'transitions': {
            'login_complete': SystemState.RETURNING_TO_GAME,
            'login_timeout': SystemState.LOGIN_REQUIRED,  # 다시 시도
            'login_failed': SystemState.NORMAL
        },

        'conditional_flow': 'wait_until_condition',

        'screen_policy': {
            'mode': 'first_match_wins',
            'stop_on_first': True
        },

        'timeout': 15.0  # 로그인 15초 대기
    },

    SystemState.RETURNING_TO_GAME: {
        'targets': [
            {'template': 'GAME_WORLD_LOADED', 'result': 'game_ready'}
        ],

        'action_type': 'detect_only',

        'transitions': {
            'game_ready': SystemState.NORMAL,
            'return_timeout': SystemState.LOGIN_REQUIRED,  # 로그인부터 다시
            'return_failed': SystemState.NORMAL
        },

        'conditional_flow': 'wait_until_condition',

        'screen_policy': {
            'mode': 'first_match_wins',
            'stop_on_first': True
        },

        'timeout': 15.0  # 게임 복귀 15초 대기
    }
}

# =============================================================================
# 🎯 로컬룰 3: 개성적 설정 (SM1만의 고유한 특성)
# =============================================================================

SM_CONFIG = {
    # 타이밍 설정 - "SM1은 5초마다 적당히 체크하는 성격"
    'timing': {
        'check_interval': 5.0,  # 5초 간격 (SRM의 0.5초보다는 느긋함)
    },

    # 대상 화면 설정 - "SM1은 스마트폰 화면만 관리하는 정책"
    'target_screens': {
        'included': ['S1', 'S2', 'S3', 'S4'],  # 스마트폰 화면만
        'excluded': ['S5'],  # PC 네이티브 제외
        'check_order': ['S1', 'S2', 'S3', 'S4']  # 체크 순서
    },

    # 게임 설정
    'game_settings': {
        'game_type': 'nightcrows',  # 글로벌 설정 키
        'vd_name': 'VD1'  # 가상 데스크톱
    }
}

# =============================================================================
# 🎯 로컬룰 4: 예외 처리 정책 (SM1만의 예외 대응 방식)
# =============================================================================

SM_EXCEPTION_POLICIES = {
    # 연속 실패 시 정책
    'continuous_failure': {
        'max_continuous_errors': 5,  # 연속 5회 에러 시
        'action': 'SLEEP_AND_RESET',  # 잠시 쉬고 리셋
        'sleep_duration': 300.0  # 5분 휴식
    },

    # 알 수 없는 상태 감지 시
    'unknown_state': {
        'default_action': 'RETURN_TO_NORMAL',
        'investigation_attempts': 3,
        'fallback_delay': 30.0
    },

    # 상태머신 에러 시
    'state_machine_error': {
        'default_action': 'RETURN_TO_NORMAL',
        'log_level': 'ERROR',
        'recovery_delay': 30.0
    }
}


# =============================================================================
# 🔧 유틸리티 함수들
# =============================================================================

def get_state_policy(state: SystemState) -> dict:
    """특정 상태의 정책을 반환합니다."""
    return SM_STATE_POLICIES.get(state, {})


def get_all_states() -> list:
    """SM1이 지원하는 모든 상태 목록을 반환합니다."""
    return list(SM_STATE_POLICIES.keys())


def validate_policies() -> bool:
    """모든 상태 정책이 올바르게 정의되었는지 검증합니다."""
    required_keys = ['targets', 'action_type', 'transitions', 'conditional_flow', 'screen_policy']

    for state, policy in SM_STATE_POLICIES.items():
        for key in required_keys:
            if key not in policy:
                print(f"경고: {state.name} 상태에 '{key}' 정책이 없습니다.")
                return False

    print("모든 SM1 상태 정책이 올바르게 정의되었습니다.")
    return True


if __name__ == "__main__":
    print("🎯 SystemMonitor 정책 검증 중...")
    validate_policies()
    print(f"📊 정의된 상태 수: {len(SM_STATE_POLICIES)}")
    print(f"📋 지원 상태들: {[state.name for state in get_all_states()]}")