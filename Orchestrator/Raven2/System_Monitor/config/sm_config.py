# Orchestrator/Raven2/System_Monitor/config/sm_config.py
# RAVEN2 SystemMonitor 설정 - monitor.py 브릿지 연동용

from enum import Enum, auto


# =============================================================================
# 🎯 로컬룰 1: 상태 정의 (RAVEN2 특화)
# =============================================================================

class SystemState(Enum):
    """RAVEN2 SystemMonitor 상태 정의"""
    NORMAL = auto()  # 정상 상태
    CONNECTION_ERROR = auto()  # 연결 에러 감지
    CLIENT_CRASHED = auto()  # 클라이언트 크래시
    RESTARTING_APP = auto()  # 앱 재시작 중
    LOADING = auto()  # 로딩 중
    LOGIN_REQUIRED = auto()  # 로그인 필요
    LOGGING_IN = auto()  # 로그인 진행 중
    RETURNING_TO_GAME = auto()  # 게임 복귀 중


# =============================================================================
# 🎯 로컬룰 2: 상태별 정책 정의 (monitor.py의 4대 정책 구조 적용)
# =============================================================================

SM_STATE_POLICIES = {
    SystemState.NORMAL: {
        # 1. targets: 무엇을 감지할지
        'targets': [
            {'template': 'CONNECTION_CONFIRM_BUTTON', 'result': 'connection_error_detected'},
            {'template': 'APP_ICON', 'result': 'client_crashed_detected'}
        ],
        # 2. action_type: 어떻게 처리할지
        'action_type': 'detect_only',
        # 3. transitions: 어디로 갈지
        'transitions': {
            'connection_error_detected': SystemState.CONNECTION_ERROR,
            'client_crashed_detected': SystemState.CLIENT_CRASHED
        },
        # 4. conditional_flow: 언제 전이할지
        'conditional_flow': 'trigger'
    },

    SystemState.CONNECTION_ERROR: {
        'targets': [
            {'template': 'CONNECTION_CONFIRM_BUTTON', 'result': 'confirm_clicked'}
        ],
        'action_type': 'detect_and_click',
        'transitions': {
            'confirm_clicked': SystemState.LOADING,
            'retry_failed': SystemState.CONNECTION_ERROR
        },
        'conditional_flow': 'retry',
        'retry_config': {
            'max_attempts': 3,
            'retry_delay': 2.5,
            'failure_result': 'retry_failed'
        }
    },

    SystemState.CLIENT_CRASHED: {
        'targets': [
            {'template': 'APP_ICON', 'result': 'app_started'}
        ],
        'action_type': 'detect_and_click',
        'transitions': {
            'app_started': SystemState.RESTARTING_APP,
            'restart_failed': SystemState.CLIENT_CRASHED
        },
        'conditional_flow': 'retry',
        'retry_config': {
            'max_attempts': 3,
            'retry_delay': 3.0,
            'failure_result': 'restart_failed'
        }
    },

    SystemState.RESTARTING_APP: {
        'targets': [],  # time_based_wait은 템플릿 감지 없음
        'action_type': 'time_based_wait',
        'expected_duration': 35.0,  # RAVEN2는 35초로 설정
        'timeout': 90.0,
        'transitions': {
            'duration_passed': SystemState.LOGIN_REQUIRED,
            'timeout_reached': SystemState.CLIENT_CRASHED
        },
        'conditional_flow': 'wait_for_duration'
    },

    SystemState.LOADING: {
        'targets': [],  # time_based_wait은 템플릿 감지 없음
        'action_type': 'time_based_wait',
        'expected_duration': 25.0,  # RAVEN2 로딩 시간
        'timeout': 45.0,
        'transitions': {
            'duration_passed': SystemState.LOGIN_REQUIRED,
            'timeout_reached': SystemState.LOGIN_REQUIRED
        },
        'conditional_flow': 'wait_for_duration'
    },

    SystemState.LOGIN_REQUIRED: {
        'targets': [],  # sequence 타입은 targets 비움
        'action_type': 'sequence',
        'sequence_config': {
            'max_attempts': 10,
            'actions': [
                {'template': 'CONNECT_BUTTON', 'operation': 'click', 'initial': True},
                {'template': 'AD_POPUP', 'operation': 'click'},
                {'template': 'LOGIN_BUTTON', 'operation': 'click', 'final': True}
            ]
        },
        'transitions': {
            'sequence_complete': SystemState.LOGGING_IN,
            'sequence_failed': SystemState.LOGIN_REQUIRED
        },
        'conditional_flow': 'sequence_with_retry'
    },

    SystemState.LOGGING_IN: {
        'targets': [],
        'action_type': 'time_based_wait',
        'expected_duration': 20.0,  # RAVEN2 로그인 시간
        'timeout': 60.0,
        'transitions': {
            'duration_passed': SystemState.RETURNING_TO_GAME,
            'timeout_reached': SystemState.LOGIN_REQUIRED
        },
        'conditional_flow': 'wait_for_duration'
    },

    SystemState.RETURNING_TO_GAME: {
        'targets': [],
        'action_type': 'time_based_wait',
        'expected_duration': 12.0,  # RAVEN2 복귀 시간
        'timeout': 30.0,
        'transitions': {
            'duration_passed': SystemState.NORMAL,
            'timeout_reached': SystemState.NORMAL
        },
        'conditional_flow': 'wait_for_duration'
    }
}


# =============================================================================
# 🎯 로컬룰 3: SM 운영 설정 (monitor.py와 완전 호환)
# =============================================================================

SM_CONFIG = {
    # 타이밍 설정
    'timing': {
        'check_interval': 5.0,  # monitor.py의 run_loop에서 사용
        'default_timeout': 60.0
    },

    # 대상 화면 설정 - monitor.py의 _initialize_screens()에서 사용
    'target_screens': {
        'included': ['S1', 'S2', 'S3', 'S4'],  # 스마트폰 화면만
        'excluded': ['S5']  # PC 네이티브 제외
    },

    # IO 정책 - monitor.py의 _detect_template_in_region()에서 사용
    'io_policy': {
        'lock_timeout': 5.0,
        'click_delay': 0.2,
        'threshold': 0.85  # 템플릿 매칭 임계값
    },

    # 재시도 정책
    'retry_policy': {
        'max_attempts': 3,
        'retry_delay': 2.0
    },

    # 게임 설정 - RAVEN2 특화
    'game_settings': {
        'game_type': 'raven2',
        'vd_name': 'VD2'
    }
}


# =============================================================================
# 🎯 로컬룰 4: 예외 처리 정책 (monitor.py의 _handle_exception_policy()에서 사용)
# =============================================================================

SM_EXCEPTION_POLICIES = {
    # 연속 실패 시 정책
    'continuous_failure': {
        'max_continuous_errors': 5,
        'default_action': 'RETURN_TO_NORMAL',
        'sleep_duration': 300.0
    },

    # 알 수 없는 상태 감지 시
    'unknown_state': {
        'default_action': 'RETURN_TO_NORMAL',
        'investigation_attempts': 3,
        'fallback_delay': 30.0
    },

    # 상태머신 에러 시 - monitor.py에서 직접 호출
    'state_machine_error': {
        'default_action': 'RETURN_TO_NORMAL',
        'log_level': 'ERROR',
        'recovery_delay': 30.0
    }
}


# =============================================================================
# 🔧 monitor.py 연동 함수들 (브릿지에서 직접 호출)
# =============================================================================

def get_state_policy(state: SystemState) -> dict:
    """monitor.py의 _execute_screen_state_machine()에서 호출"""
    return SM_STATE_POLICIES.get(state, {})


def get_all_states() -> list:
    """지원하는 모든 상태 목록 반환"""
    return list(SM_STATE_POLICIES.keys())


def get_target_screens() -> list:
    """monitor.py의 _initialize_screens()에서 호출"""
    return SM_CONFIG['target_screens']['included']


def validate_state_policies() -> bool:
    """monitor.py의 __init__()에서 호출 - 정책 유효성 검증"""
    required_keys = ['action_type', 'transitions', 'conditional_flow']
    valid_action_types = ['detect_only', 'detect_and_click', 'sequence', 'time_based_wait']
    valid_flows = ['trigger', 'retry', 'hold', 'wait_for_duration', 'sequence_with_retry']

    for state, policy in SM_STATE_POLICIES.items():
        # action_type 검증
        action_type = policy.get('action_type', '')
        if action_type not in valid_action_types:
            print(f"ERROR: {state.name}의 action_type '{action_type}'이 유효하지 않습니다.")
            return False

        # conditional_flow 검증
        flow_type = policy.get('conditional_flow', '')
        if flow_type not in valid_flows:
            print(f"ERROR: {state.name}의 conditional_flow '{flow_type}'이 유효하지 않습니다.")
            return False

        # time_based_wait와 sequence는 targets가 비어야 함
        if action_type in ['time_based_wait', 'sequence']:
            targets = policy.get('targets', [])
            if targets:
                print(f"WARN: {state.name} 상태({action_type})에 불필요한 targets가 있습니다.")

        # 필수 키 검증
        for key in required_keys:
            if key not in policy:
                print(f"ERROR: {state.name} 상태에 '{key}' 정책이 없습니다.")
                return False

        # transitions 유효성 검증
        transitions = policy.get('transitions', {})
        for result, next_state in transitions.items():
            if not isinstance(next_state, SystemState):
                print(f"ERROR: {state.name}의 전이 결과 '{result}'가 유효하지 않은 상태입니다.")
                return False

    print("INFO: SystemMonitor 상태 정책 검증 완료")
    return True


def get_initial_screen_states() -> dict:
    """모든 화면의 초기 상태를 NORMAL로 설정"""
    initial_states = {}
    for screen_id in get_target_screens():
        initial_states[screen_id] = SystemState.NORMAL
    return initial_states


# =============================================================================
# 🧪 설정 검증 및 테스트
# =============================================================================

def validate_config() -> bool:
    """SM_CONFIG 유효성 검증"""
    try:
        # 필수 섹션 존재 확인
        required_sections = ['timing', 'target_screens', 'io_policy', 'retry_policy', 'game_settings']

        for section in required_sections:
            if section not in SM_CONFIG:
                print(f"ERROR: 필수 설정 섹션 '{section}'이 없습니다.")
                return False

        # 타이밍 값 검증
        timing = SM_CONFIG['timing']
        if timing['check_interval'] <= 0:
            print("ERROR: check_interval은 0보다 커야 합니다.")
            return False

        # 대상 화면 검증
        target_screens = SM_CONFIG['target_screens']['included']
        if not target_screens:
            print("ERROR: 대상 화면이 비어있습니다.")
            return False

        print("INFO: SM_CONFIG 유효성 검증 완료")
        return True

    except Exception as e:
        print(f"ERROR: 설정 검증 중 예외 발생 - {e}")
        return False


# =============================================================================
# 🧪 테스트 실행 (파일 직접 실행 시)
# =============================================================================

if __name__ == "__main__":
    print("🎯 RAVEN2 SystemMonitor 설정 테스트")
    print("=" * 60)

    # 정책 유효성 검증
    print("📊 정책 검증 중...")
    policies_valid = validate_state_policies()

    print("\n📊 설정 검증 중...")
    config_valid = validate_config()

    if policies_valid and config_valid:
        print(f"\n📊 정의된 상태 수: {len(SM_STATE_POLICIES)}")
        print(f"📋 지원 상태들:")

        for i, state in enumerate(get_all_states(), 1):
            policy = get_state_policy(state)
            transitions = policy.get('transitions', {})

            print(f"  {i}. {state.name}")
            print(f"     • 액션: {policy.get('action_type', 'N/A')}")
            print(f"     • 흐름: {policy.get('conditional_flow', 'N/A')}")
            print(f"     • 전이: {len(transitions)}개 가능")

            # 시간 기반 정보
            if 'timeout' in policy:
                print(f"     • 타임아웃: {policy['timeout']}초")
            if 'expected_duration' in policy:
                print(f"     • 예상 시간: {policy['expected_duration']}초")
            print()

        print(f"📊 관리 대상 화면: {get_target_screens()}")

        print(f"\n📊 초기 화면 상태들:")
        initial_states = get_initial_screen_states()
        for screen_id, state in initial_states.items():
            print(f"  • {screen_id}: {state.name}")

        print("\n🎯 monitor.py 브릿지 연동 요약:")
        print(f"  • check_interval: {SM_CONFIG['timing']['check_interval']}초")
        print(f"  • 템플릿 매칭 임계값: {SM_CONFIG['io_policy']['threshold']}")
        print(f"  • 게임 타입: {SM_CONFIG['game_settings']['game_type']}")
        print(f"  • 가상 데스크톱: {SM_CONFIG['game_settings']['vd_name']}")

        print("\n🎮 RAVEN2 특화 설정:")
        print("  • 앱 재시작 대기: 35초")
        print("  • 로딩 대기: 25초")
        print("  • 로그인 대기: 20초")
        print("  • 게임 복귀 대기: 12초")

    else:
        print("❌ 정책 또는 설정 검증 실패!")

    print("\n" + "=" * 60)
    print("RAVEN2 SystemMonitor 설정 테스트 완료")