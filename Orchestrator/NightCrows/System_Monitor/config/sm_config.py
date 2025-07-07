# Orchestrator/NightCrows/System_Monitor/config/sm_config.py
# SM1 통합 설정 - 공통 정책 + S1~S4 독립 상태 실행

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
# 🎯 로컬룰 2: 공통 상태 정책 (4대 정책 범주)
# =============================================================================
DEFAULT_SEQUENCE_CONFIG = {
    'max_attempts': 10,
    'step_timeout': 3.0,
    'detection_interval': 0.5,
    'default_wait_after': 1.0,
    'default_max_detections': 6
}

SM_STATE_POLICIES = {
    SystemState.NORMAL: {
        # 1. targets: 무엇을 감지할지
        'targets': [
            {'template': 'CONNECTION_CONFIRM_BUTTON', 'result': 'connection_error_detected'},
            {'template': 'APP_ICON', 'result': 'client_crashed_detected'}
        ],
        # 2. action_type: 어떻게 할지
        'action_type': 'detect_only',
        # 3. transitions: 어디로 갈지
        'transitions': {
            'connection_error_detected': SystemState.CONNECTION_ERROR,
            'client_crashed_detected': SystemState.CLIENT_CRASHED,
            'stay_normal': SystemState.NORMAL
        },
        # 4. conditional_flow: 어떤   방식으로 처리할지
        'conditional_flow': 'trigger'
    },

    SystemState.CONNECTION_ERROR: {
        'targets': [
            {'template': 'CONNECTION_CONFIRM_BUTTON', 'result': 'confirm_clicked'}
        ],
        'action_type': 'detect_and_click',
        'transitions': {
            'confirm_clicked': SystemState.LOGIN_REQUIRED,
            'confirm_click_failed': SystemState.CONNECTION_ERROR
        },
        'conditional_flow': 'retry',
        'retry_config': {
            'max_attempts': 3,
            'failure_result': 'confirm_click_failed'
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
            'failure_result': 'restart_failed'
        }
    },


    SystemState.RESTARTING_APP: {
        'targets': [],  # 명시적으로 빈 리스트
        'action_type': 'time_based_wait',
        'expected_duration': 30.0,
        'timeout': 90.0,
        'transitions': {
            'duration_passed': SystemState.LOGIN_REQUIRED,
            'timeout_reached': SystemState.CLIENT_CRASHED
        },
        'conditional_flow': 'wait_for_duration'
    },

    SystemState.LOADING: {
        'targets': [],  # 템플릿 감지 없음
        'action_type': 'time_based_wait',
        'expected_duration': 30.0,  # 30초 대기 후 로그인 단계로
        'timeout': 45.0,
        'transitions': {
            'duration_passed': SystemState.LOGIN_REQUIRED,
            'timeout_reached': SystemState.LOGIN_REQUIRED
        },
        'conditional_flow': 'wait_for_duration'
    },

    SystemState.LOGIN_REQUIRED: {
        'targets': [],  # sequence 타입은 targets 비우기
        'action_type': 'sequence',
        'sequence_config': {
            **DEFAULT_SEQUENCE_CONFIG,
            'actions': [
                {'template': 'CONNECT_BUTTON', 'initial': True},
                {'template': 'AD_POPUP'},
                # LOADING_SPINNER 제거
                {'template': 'LOGIN_BUTTON', 'final': True}
            ]
        },
        'transitions': {
            'sequence_complete': SystemState.LOGGING_IN,
            'sequence_failed': SystemState.LOGIN_REQUIRED
        },
        'conditional_flow': 'retry'
    },

    SystemState.LOGGING_IN: {
        'targets': [],  # 명시적으로 빈 리스트
        'action_type': 'time_based_wait',
        'expected_duration': 25.0,
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
        'expected_duration': 15.0,
        'timeout': 30.0,
        'transitions': {
            'duration_passed': SystemState.NORMAL,
            'timeout_reached': SystemState.NORMAL
        },
        'conditional_flow': 'wait_for_duration'
    }
}

# =============================================================================
# 🎯 로컬룰 3: SM1 운영 설정
# =============================================================================

SM_CONFIG = {
    # 타이밍 설정
    'timing': {
        'check_interval': 5.0,  # 5초 간격
        'default_timeout': 60.0,
    },

    # 대상 화면 설정 - S1~S4 독립 상태 관리
    'target_screens': {
        'included': ['S1', 'S2', 'S3', 'S4'],  # 스마트폰 화면만
        'excluded': ['S5']  # PC 네이티브 제외
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

    # 게임 설정
    'game_settings': {
        'game_type': 'nightcrows',
        'vd_name': 'VD1'
    }
}

# =============================================================================
# 🎯 로컬룰 4: 예외 처리 정책
# =============================================================================

SM_EXCEPTION_POLICIES = {
    # 연속 실패 시 정책
    'continuous_failure': {
        'max_continuous_errors': 5,
        'action': 'SLEEP_AND_RESET',
        'sleep_duration': 300.0
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
    """특정 상태의 정책을 반환 (모든 화면 공통)"""
    return SM_STATE_POLICIES.get(state, {})


def get_all_states() -> list:
    """SM1이 지원하는 모든 상태 목록을 반환"""
    return list(SM_STATE_POLICIES.keys())


def get_target_screens() -> list:
    """SM1이 관리하는 화면 목록을 반환"""
    return SM_CONFIG['target_screens']['included']


def get_initial_screen_states() -> dict:
    """모든 화면의 초기 상태를 반환"""
    initial_states = {}
    for screen_id in get_target_screens():
        initial_states[screen_id] = SystemState.NORMAL
    return initial_states


def validate_state_policies() -> bool:
    """모든 상태 정책이 올바르게 정의되었는지 검증"""
    required_keys = ['action_type', 'transitions', 'conditional_flow']
    valid_flows = ['trigger', 'retry', 'hold', 'wait_for_duration']

    for state, policy in SM_STATE_POLICIES.items():
        action_type = policy.get('action_type', '')
        flow_type = policy.get('conditional_flow', '')

        # conditional_flow 유효성 검증
        if flow_type not in valid_flows:
            print(f"오류: {state.name}의 conditional_flow '{flow_type}'이 유효하지 않습니다.")
            print(f"유효한 값: {valid_flows}")
            return False

        # time_based_wait와 sequence는 targets가 없어도 OK
        if action_type in ['time_based_wait', 'sequence']:
            targets = policy.get('targets', [])
            if targets:  # 빈 배열이 아니면 경고
                print(f"경고: {state.name} 상태({action_type})에 불필요한 targets가 있습니다.")
        else:
            # 일반 액션은 targets 필수
            if 'targets' not in policy or not policy['targets']:
                print(f"오류: {state.name} 상태에 targets가 필요합니다.")
                return False

        # 공통 필수 키 검증
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

    print("✅ 모든 상태 정책이 올바르게 정의되었습니다.")
    return True


def validate_config() -> bool:
    """설정 유효성 검증"""
    try:
        # 필수 섹션 존재 확인
        required_sections = ['timing', 'target_screens', 'io_policy', 'retry_policy', 'game_settings']

        for section in required_sections:
            if section not in SM_CONFIG:
                print(f"오류: 필수 설정 섹션 '{section}'이 없습니다.")
                return False

        # 타이밍 값 검증
        timing = SM_CONFIG['timing']
        if timing['check_interval'] <= 0:
            print("오류: check_interval은 0보다 커야 합니다.")
            return False

        if timing['default_timeout'] <= timing['check_interval']:
            print("오류: default_timeout은 check_interval보다 커야 합니다.")
            return False

        # 대상 화면 검증
        target_screens = SM_CONFIG['target_screens']['included']
        if not target_screens:
            print("오류: 대상 화면이 비어있습니다.")
            return False

        print("✅ SM_CONFIG 유효성 검증 완료")
        return True

    except Exception as e:
        print(f"오류: 설정 검증 중 예외 발생 - {e}")
        return False


# =============================================================================
# 🧪 테스트 및 디버깅
# =============================================================================

if __name__ == "__main__":
    print("🎯 SM1 공통 정책 + 독립 화면 상태 설정 테스트")
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

            # 타임아웃 정보
            if 'timeout' in policy:
                print(f"     • 타임아웃: {policy['timeout']}초")

            # 시간 기반 정보
            if 'expected_duration' in policy:
                print(f"     • 예상 시간: {policy['expected_duration']}초")
            print()

        print(f"📊 관리 대상 화면: {get_target_screens()}")

        print(f"\n📊 초기 화면 상태들:")
        initial_states = get_initial_screen_states()
        for screen_id, state in initial_states.items():
            print(f"  • {screen_id}: {state.name}")

        print("\n🎯 핵심 설계 원칙:")
        print("  • 공통 정책 사용 (로직은 모든 화면 동일)")
        print("  • S1~S4 각각 독립적인 상태 실행")
        print("  • 템플릿 파일은 화면별로 다름 (해상도 차이)")
        print("  • 스크린 정의는 screen_info.py의 좌표만 사용")
        print("  • 4대 정책 범주만 사용 (targets, action_type, transitions, conditional_flow)")
        print("  • 시간 기반 처리로 안정성 향상")

    else:
        print("❌ 정책 또는 설정 검증 실패!")

    print("\n" + "=" * 60)
    print("SM1 설정 테스트 완료")