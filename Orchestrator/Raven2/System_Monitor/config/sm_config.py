# Orchestrator/Raven2/System_Monitor/config/sm_config.py (수정됨)
# RAVEN2 SystemMonitor 설정 - monitor.py 브릿지 연동용

from enum import Enum, auto


# =============================================================================
# 🎯 로컬룰 1: 상태 정의 (RECOVERING_SESSION 추가)
# =============================================================================

class SystemState(Enum):
    """RAVEN2 SystemMonitor 상태 정의"""
    NORMAL = auto()
    CONNECTION_ERROR = auto()
    CLIENT_CRASHED = auto()

    # --- 5개 상태가 하나로 통합됨 ---
    # RESTARTING_APP = auto()
    # LOADING = auto()
    # LOGIN_REQUIRED = auto()
    # LOGGING_IN = auto()
    # RETURNING_TO_GAME = auto()
    RECOVERING_SESSION = auto()  # 👈 [신규] 통합된 세션 복구 상태


# =============================================================================
# 🎯 로컬룰 2: 상태별 정책 정의 (통합 시퀀스 적용)
# =============================================================================

SM_STATE_POLICIES = {
    SystemState.NORMAL: {
        # (기존과 동일)
        'targets': [
            {'template': 'CONNECTION_CONFIRM_BUTTON', 'result': 'connection_error_detected'},
            {'template': 'APP_ICON', 'result': 'client_crashed_detected'}
        ],
        'action_type': 'detect_only',
        'transitions': {
            'connection_error_detected': SystemState.CONNECTION_ERROR,
            'client_crashed_detected': SystemState.CLIENT_CRASHED
        },
        'conditional_flow': 'trigger'
    },

    SystemState.CONNECTION_ERROR: {
        # (기존과 동일)
        'targets': [
            {'template': 'CONNECTION_CONFIRM_BUTTON', 'result': 'confirm_clicked'}
        ],
        'action_type': 'detect_and_click',
        'transitions': {
            # ❗️ [수정] LOADING 대신 RECOVERING_SESSION으로
            'confirm_clicked': SystemState.RECOVERING_SESSION,
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
        # (기존과 동일)
        'targets': [
            {'template': 'APP_ICON', 'result': 'app_started'}
        ],
        'action_type': 'detect_and_click',
        'transitions': {
            # ❗️ [수정] RESTARTING_APP 대신 RECOVERING_SESSION으로
            'app_started': SystemState.RECOVERING_SESSION,
            'restart_failed': SystemState.CLIENT_CRASHED
        },
        'conditional_flow': 'retry',
        'retry_config': {
            'max_attempts': 3,
            'retry_delay': 3.0,
            'failure_result': 'restart_failed'
        }
    },

    # --- ❗️ [신규] 통합된 세션 복구 시퀀스 ---
    # RESTARTING_APP, LOADING, LOGIN_REQUIRED, LOGGING_IN, RETURNING_TO_GAME을 대체
    SystemState.RECOVERING_SESSION: {
        'targets': [],
        'action_type': 'sequence',
        'sequence_config': {
            'max_attempts': 3,  # 시퀀스 전체를 3회 재시도
            'actions': [
                # 1. (구 RESTARTING_APP) - 35초 대기
                {'operation': 'wait_duration', 'duration': 35.0, 'initial': True},

                # 2. (구 LOADING) - 25초 대기
                {'operation': 'wait_duration', 'duration': 25.0},

                # 3. (구 LOGIN_REQUIRED) - 포커스 및 클릭
                {'operation': 'set_focus'},
                # (참고: Raven2는 AD_POPUP이 없으므로 click_if_present 불필요)
                {'template': 'LOGIN_BUTTON', 'operation': 'click'},

                # 4. (구 LOGGING_IN) - 20초 대기
                {'operation': 'wait_duration', 'duration': 20.0},

                # 5. (구 RETURNING_TO_GAME) - 12초 대기
                {'operation': 'wait_duration', 'duration': 12.0, 'final': True}
            ]
        },
        'transitions': {
            'sequence_complete': SystemState.NORMAL,
            'sequence_failed': SystemState.CLIENT_CRASHED  # 실패 시 앱 아이콘 클릭부터 다시
        },
        'conditional_flow': 'sequence_with_retry'
    }

    # --- ❗️ [삭제] ---
    # SystemState.RESTARTING_APP: { ... }
    # SystemState.LOADING: { ... }
    # SystemState.LOGIN_REQUIRED: { ... }
    # SystemState.LOGGING_IN: { ... }
    # SystemState.RETURNING_TO_GAME: { ... }
}

# =============================================================================
# 🎯 로컬룰 3: SM 운영 설정 (변경 없음)
# =============================================================================

SM_CONFIG = {
    # (기존과 동일)
    'timing': {
        'check_interval': 5.0,
        'default_timeout': 60.0
    },
    'target_screens': {
        'included': ['S1', 'S2', 'S3', 'S4'],
        'excluded': ['S5']
    },
    'io_policy': {
        'lock_timeout': 5.0,
        'click_delay': 0.2,
        'threshold': 0.85
    },
    'retry_policy': {
        'max_attempts': 3,
        'retry_delay': 2.0
    },
    'game_settings': {
        'game_type': 'raven2',
        'vd_name': 'VD2'
    }
}

# =============================================================================
# 🎯 로컬룰 4: 예외 처리 정책 (변경 없음)
# =============================================================================

SM_EXCEPTION_POLICIES = {
    # (기존과 동일)
    'continuous_failure': {
        'max_continuous_errors': 5,
        'default_action': 'RETURN_TO_NORMAL',
        'sleep_duration': 300.0
    },
    'unknown_state': {
        'default_action': 'RETURN_TO_NORMAL',
        'investigation_attempts': 3,
        'fallback_delay': 30.0
    },
    'state_machine_error': {
        'default_action': 'RETURN_TO_NORMAL',
        'log_level': 'ERROR',
        'recovery_delay': 30.0
    }
}


# =============================================================================
# 🔧 monitor.py 연동 함수들 (변경 없음)
# =============================================================================

def get_state_policy(state: SystemState) -> dict:
    return SM_STATE_POLICIES.get(state, {})


def get_all_states() -> list:
    return list(SM_STATE_POLICIES.keys())


def get_target_screens() -> list:
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

    print("INFO: SystemMonitor(Raven2) 상태 정책 검증 완료")
    return True


def get_initial_screen_states() -> dict:
    """모든 화면의 초기 상태를 NORMAL로 설정"""
    initial_states = {}
    for screen_id in get_target_screens():
        initial_states[screen_id] = SystemState.NORMAL
    return initial_states


# =============================================================================
# 🧪 설정 검증 및 테스트 (변경 없음)
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

        print("INFO: SM_CONFIG(Raven2) 유효성 검증 완료")
        return True

    except Exception as e:
        print(f"ERROR: 설정 검증 중 예외 발생 - {e}")
        return False


if __name__ == "__main__":
    print("🎯 RAVEN2 SystemMonitor 설정 테스트 (v3 통합 시퀀스 적용)")
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

        print("\n🎮 RAVEN2 v3 통합 시퀀스 설정:")
        print("  • RECOVERING_SESSION 통합 시퀀스:")
        print("    - 앱 재시작 대기: 35초")
        print("    - 로딩 대기: 25초")
        print("    - 로그인 처리")
        print("    - 로그인 대기: 20초")
        print("    - 게임 복귀 대기: 12초")
        print("    - 총 예상 시간: 약 92초")

    else:
        print("❌ 정책 또는 설정 검증 실패!")

    print("\n" + "=" * 60)