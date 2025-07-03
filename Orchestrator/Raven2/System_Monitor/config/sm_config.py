# Orchestrator/Raven2/System_Monitor/config/sm_config.py
# SM2 통합 설정 (config + policies)

from enum import Enum, auto


# =============================================================================
# 🎯 로컬룰 1: 상태 정의 (SM2의 고유한 생활 패턴)
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
# 🎯 로컬룰 2: 상태별 통합 정책 (4가지 핵심 정책)
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

        # 4. 어떤 방식으로 처리할지
        'conditional_flow': 'trigger',

        # 5. 화면별 처리 방식
        'screen_policy': 'independent_per_screen'
    },

    SystemState.CONNECTION_ERROR: {
        'targets': [
            {'template': 'CONNECTION_CONFIRM_BUTTON', 'result': 'confirm_button_found'}
        ],

        'action_type': 'click_and_wait',

        'transitions': {
            'confirm_clicked': SystemState.LOADING,
            'confirm_failed': SystemState.CONNECTION_ERROR,
            'no_confirm_button': SystemState.NORMAL
        },

        'conditional_flow': 'retry',
        'screen_policy': 'independent_per_screen',
        'timeout': 30.0
    },

    SystemState.CLIENT_CRASHED: {
        'targets': [
            {'template': 'APP_ICON', 'result': 'app_icon_found'}
        ],

        'action_type': 'restart_app',

        'transitions': {
            'app_clicked': SystemState.RESTARTING_APP,
            'app_click_failed': SystemState.CLIENT_CRASHED,
            'no_app_icon': SystemState.NORMAL
        },

        'conditional_flow': 'retry',
        'screen_policy': 'independent_per_screen',
        'timeout': 60.0
    },

    SystemState.RESTARTING_APP: {
        'targets': [
            {'template': 'APP_LOADING_SCREEN', 'result': 'loading_detected'},
            {'template': 'LOGIN_SCREEN', 'result': 'login_required'}
        ],

        'action_type': 'wait_for_loading',

        'transitions': {
            'loading_detected': SystemState.LOADING,
            'login_required': SystemState.LOGIN_REQUIRED,
            'loading_timeout': SystemState.NORMAL,
            'still_restarting': SystemState.RESTARTING_APP
        },

        'conditional_flow': 'hold',
        'screen_policy': 'independent_per_screen',
        'timeout': 90.0
    },

    SystemState.LOADING: {
        'targets': [
            {'template': 'GAME_WORLD_LOADED', 'result': 'game_loaded'},
            {'template': 'LOGIN_SCREEN', 'result': 'login_required'}
        ],

        'action_type': 'wait_for_completion',

        'transitions': {
            'game_loaded': SystemState.RETURNING_TO_GAME,
            'login_required': SystemState.LOGIN_REQUIRED,
            'loading_timeout': SystemState.NORMAL,
            'still_loading': SystemState.LOADING
        },

        'conditional_flow': 'hold',
        'screen_policy': 'independent_per_screen',
        'timeout': 120.0
    },

    SystemState.LOGIN_REQUIRED: {
        'targets': [
            {'template': 'CONNECT_BUTTON', 'result': 'connect_button_found'}
        ],

        'action_type': 'login_sequence',

        'transitions': {
            'login_initiated': SystemState.LOGGING_IN,
            'login_failed': SystemState.LOGIN_REQUIRED,
            'no_login_ui': SystemState.NORMAL
        },

        'conditional_flow': 'retry',
        'screen_policy': 'independent_per_screen',
        'timeout': 60.0
    },

    SystemState.LOGGING_IN: {
        'targets': [
            {'template': 'GAME_WORLD_LOADED', 'result': 'login_successful'},
            {'template': 'LOGIN_SCREEN', 'result': 'login_failed'}
        ],

        'action_type': 'wait_for_login_result',

        'transitions': {
            'login_successful': SystemState.RETURNING_TO_GAME,
            'login_failed': SystemState.LOGIN_REQUIRED,
            'login_timeout': SystemState.NORMAL,
            'still_logging_in': SystemState.LOGGING_IN
        },

        'conditional_flow': 'hold',
        'screen_policy': 'independent_per_screen',
        'timeout': 90.0
    },

    SystemState.RETURNING_TO_GAME: {
        'targets': [
            {'template': 'GAME_WORLD_LOADED', 'result': 'game_ready'}
        ],

        'action_type': 'finalize_return',

        'transitions': {
            'return_completed': SystemState.NORMAL,
            'return_timeout': SystemState.NORMAL,
            'still_returning': SystemState.RETURNING_TO_GAME
        },

        'conditional_flow': 'hold',
        'screen_policy': 'independent_per_screen',
        'timeout': 60.0
    }
}

# =============================================================================
# 🎯 로컬룰 3: SM2 기본 운영 설정 (SM2만의 고유한 특성)
# =============================================================================

SM_CONFIG = {
    # 타이밍 설정 - "SM2는 5초마다 적당히 체크하는 성격"
    'timing': {
        'check_interval': 5.0,  # 5초 간격 (SRM의 0.5초보다는 느긋함)
        'default_timeout': 60.0,  # 기본 타임아웃
    },

    # 대상 화면 설정 - "SM2는 스마트폰 화면만 관리하는 정책"
    'target_screens': {
        'included': ['S1', 'S2', 'S3', 'S4'],  # 스마트폰 화면만
        'excluded': ['S5'],  # PC 네이티브 제외
        'check_order': ['S1', 'S2', 'S3', 'S4']  # 체크 순서
    },

    # IO 정책
    'io_policy': {
        'lock_timeout': 5.0,
        'click_delay': 0.2
    },

    # 재시도 정책
    'retry_policy': {
        'max_attempts': 3,
        'retry_delay': 2.0
    },

    # 독립성 설정
    'independence': {
        'isolated_execution': True,
        'shared_resources': []
    },

    # 게임 설정
    'game_settings': {
        'game_type': 'raven2',  # SM1과 다른 부분 1: nightcrows → raven2
        'vd_name': 'VD2'  # SM1과 다른 부분 2: VD1 → VD2
    }
}

# =============================================================================
# 🎯 로컬룰 4: 예외 처리 정책 (SM2만의 예외 대응 방식)
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
    """SM2가 지원하는 모든 상태 목록을 반환합니다."""
    return list(SM_STATE_POLICIES.keys())


def validate_state_policies() -> bool:
    """모든 상태 정책이 올바르게 정의되었는지 검증합니다."""
    required_keys = ['targets', 'action_type', 'transitions', 'conditional_flow', 'screen_policy']

    for state, policy in SM_STATE_POLICIES.items():
        for key in required_keys:
            if key not in policy:
                print(f"경고: {state.name} 상태에 '{key}' 정책이 없습니다.")
                return False

        # transitions 유효성 검증
        transitions = policy.get('transitions', {})
        for result, next_state in transitions.items():
            if not isinstance(next_state, SystemState):
                print(f"오류: {state.name}의 전이 결과 '{result}'가 유효하지 않은 상태입니다.")
                return False

    print("✅ 모든 SM 상태 정책이 올바르게 정의되었습니다.")
    return True


# =============================================================================
# 🧪 설정 테스트 함수
# =============================================================================

def test_config():
    """SM2 설정 및 정책 검증 테스트"""
    print("=" * 60)
    print("SM2 (Raven2 SystemMonitor) 통합 설정 테스트")
    print("=" * 60)

    if validate_state_policies() and SM_CONFIG:
        print("\n🎯 상태머신 정책 요약:")
        for state, policy in SM_STATE_POLICIES.items():
            transitions = policy.get('transitions', {})
            print(f"  • {state.name}")
            print(f"     • 액션: {policy.get('action_type', 'N/A')}")
            print(f"     • 흐름: {policy.get('conditional_flow', 'N/A')}")
            print(f"     • 전이: {len(transitions)}개 가능")

            # 타임아웃 정보
            if 'timeout' in policy:
                print(f"     • 타임아웃: {policy['timeout']}초")
            print()

        print("📊 주요 운영 설정:")
        print(f"  • 체크 간격: {SM_CONFIG['timing']['check_interval']}초")
        print(f"  • 대상 화면: {SM_CONFIG['target_screens']['included']}")
        print(f"  • 제외 화면: {SM_CONFIG['target_screens']['excluded']}")
        print(f"  • 최대 재시도: {SM_CONFIG['retry_policy']['max_attempts']}회")
        print(f"  • 게임 타입: {SM_CONFIG['game_settings']['game_type']}")
        print(f"  • 가상 데스크톱: {SM_CONFIG['game_settings']['vd_name']}")

        print("\n🎯 상태머신 설계 원칙:")
        print("  • 게임 외부환경 문제 전용 (연결, 크래시, 로그인 등)")
        print("  • 각 스크린 객체가 독립적으로 상태 전이")
        print("  • 모든 문제는 결국 NORMAL 상태로 복귀")
        print("  • trigger/retry/hold 전략으로 흐름 제어")
        print("  • 4가지 핵심 정책으로 모든 상황 처리")

    else:
        print("❌ 상태 정책 또는 설정 검증 실패!")

    print("\n" + "=" * 60)
    print("SM2 통합 설정 테스트 완료")


if __name__ == "__main__":
    test_config()