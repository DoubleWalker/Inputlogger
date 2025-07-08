# Orchestrator/NightCrows/System_Monitor/config/sm_config.py
"""
SM1 리모델링 설정 - 4대 정책 범주 + 화면별 개별 객체성 적용
- targets, action_type, transitions, conditional_flow 중심
- 간소화된 구조로 브릿지 복잡성 최소화
- 화면별 독립 상태머신 지원
"""

from enum import Enum, auto


# =============================================================================
# 🎯 로컬룰 1: 상태 정의 (SM1의 생활 패턴)
# =============================================================================

class SystemState(Enum):
    """SystemMonitor 상태 정의 - 간소화된 구조"""
    NORMAL = auto()  # 정상 상태 (기본)
    CONNECTION_ERROR = auto()  # 연결 에러 감지
    CLIENT_CRASHED = auto()  # 클라이언트 크래시
    RESTARTING_APP = auto()  # 앱 재시작 대기
    LOGIN_REQUIRED = auto()  # 로그인 필요
    LOGGING_IN = auto()  # 로그인 진행 중
    RETURNING_TO_GAME = auto()  # 게임 복귀 중


# =============================================================================
# 🎯 로컬룰 2: 4대 정책 범주 기반 상태 정책
# =============================================================================

SM_STATE_POLICIES = {
    # =========================================================================
    # 🔍 감지 전용 상태들
    # =========================================================================

    SystemState.NORMAL: {
        # 1. targets: 문제 상황 감지용 템플릿들
        'targets': [
            {'template': 'CONNECTION_CONFIRM_BUTTON', 'result': 'connection_error_detected'},
            {'template': 'APP_ICON', 'result': 'client_crashed_detected'}
        ],
        # 2. action_type: 감지만 (클릭 안함)
        'action_type': 'detect_only',
        # 3. transitions: 문제 발견 시 해당 복구 상태로
        'transitions': {
            'connection_error_detected': SystemState.CONNECTION_ERROR,
            'client_crashed_detected': SystemState.CLIENT_CRASHED
        },
        # 4. conditional_flow: 즉시 전이
        'conditional_flow': 'trigger'
    },

    # =========================================================================
    # 🔧 즉시 처리 상태들 (감지+클릭)
    # =========================================================================

    SystemState.CONNECTION_ERROR: {
        'targets': [
            {'template': 'CONNECTION_CONFIRM_BUTTON', 'result': 'confirm_clicked'}
        ],
        'action_type': 'detect_and_click',
        'transitions': {
            'confirm_clicked': SystemState.LOGIN_REQUIRED,
            'retry_failed': SystemState.CONNECTION_ERROR  # 재시도 실패 시 현재 상태 유지
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
            'retry_failed': SystemState.CLIENT_CRASHED
        },
        'conditional_flow': 'retry',
        'retry_config': {
            'max_attempts': 3,
            'retry_delay': 3.0,
            'failure_result': 'retry_failed'
        }
    },

    # =========================================================================
    # ⏰ 시간 기반 대기 상태들
    # =========================================================================

    SystemState.RESTARTING_APP: {
        'targets': [],  # 시간 기반 처리 - 템플릿 감지 없음
        'action_type': 'time_based_wait',
        'expected_duration': 30.0,  # 앱 재시작 예상 시간
        'timeout': 90.0,  # 최대 대기 시간
        'transitions': {
            'duration_passed': SystemState.LOGIN_REQUIRED,
            'timeout_reached': SystemState.CLIENT_CRASHED  # 재시작 실패로 간주
        },
        'conditional_flow': 'wait_for_duration'
    },

    SystemState.LOGGING_IN: {
        'targets': [],
        'action_type': 'time_based_wait',
        'expected_duration': 25.0,  # 로그인 완료 예상 시간
        'timeout': 60.0,
        'transitions': {
            'duration_passed': SystemState.RETURNING_TO_GAME,
            'timeout_reached': SystemState.LOGIN_REQUIRED  # 로그인 실패
        },
        'conditional_flow': 'wait_for_duration'
    },

    SystemState.RETURNING_TO_GAME: {
        'targets': [],
        'action_type': 'time_based_wait',
        'expected_duration': 15.0,  # 게임 복귀 예상 시간
        'timeout': 30.0,
        'transitions': {
            'duration_passed': SystemState.NORMAL,
            'timeout_reached': SystemState.NORMAL  # 타임아웃도 정상으로 간주
        },
        'conditional_flow': 'wait_for_duration'
    },

    # =========================================================================
    # 🔄 시퀀스 실행 상태
    # =========================================================================

    SystemState.LOGIN_REQUIRED: {
        'targets': [],  # sequence는 targets 비움
        'action_type': 'sequence',
        'sequence_config': {
            'max_attempts': 10,  # 시퀀스 전체 재시도 횟수
            'actions': [
                # 1단계: 연결 버튼 클릭 (최초 1회만)
                {'template': 'CONNECT_BUTTON', 'operation': 'click', 'initial': True},

                # 2단계: 광고 팝업 처리 (나타나면 클릭)
                {'template': 'AD_POPUP', 'operation': 'click'},

                # 3단계: 로그인 버튼 클릭 (최종 단계)
                {'template': 'LOGIN_BUTTON', 'operation': 'click', 'final': True}
            ]
        },
        'transitions': {
            'sequence_complete': SystemState.LOGGING_IN,
            'sequence_failed': SystemState.LOGIN_REQUIRED  # 실패 시 재시도
        },
        'conditional_flow': 'sequence_with_retry'
    }
}

# =============================================================================
# 🎯 로컬룰 3: 운영 설정
# =============================================================================

SM_CONFIG = {
    # 타이밍 설정
    'timing': {
        'check_interval': 5.0,  # 메인 루프 체크 간격
        'default_timeout': 60.0  # 기본 타임아웃
    },

    # 대상 화면 설정 - screen_info.py의 SCREEN_REGIONS 키와 일치해야 함
    'target_screens': {
        'included': ['S1', 'S2', 'S3', 'S4'],  # 스마트폰 화면들
        'excluded': ['S5']  # PC 네이티브는 제외
    },

    # IO 정책
    'io_policy': {
        'lock_timeout': 5.0,  # IO Lock 타임아웃
        'click_delay': 0.2  # 클릭 후 대기 시간
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
    'state_machine_error': {
        'default_action': 'RETURN_TO_NORMAL',
        'recovery_delay': 30.0
    },

    'continuous_failure': {
        'max_continuous_errors': 5,
        'action': 'SLEEP_AND_RESET',
        'sleep_duration': 300.0
    },

    'unknown_state': {
        'default_action': 'RETURN_TO_NORMAL',
        'fallback_delay': 30.0
    }
}


# =============================================================================
# 🔧 유틸리티 함수들
# =============================================================================

def get_state_policy(state: SystemState) -> dict:
    """상태별 정책 반환 (모든 화면 공통 사용)"""
    return SM_STATE_POLICIES.get(state, {})


def get_all_states() -> list:
    """지원하는 모든 상태 목록"""
    return list(SM_STATE_POLICIES.keys())


def get_target_screens() -> list:
    """관리 대상 화면 목록"""
    return SM_CONFIG['target_screens']['included']


def validate_state_policies() -> bool:
    """상태 정책 유효성 검증"""
    required_keys = ['action_type', 'transitions', 'conditional_flow']
    valid_action_types = ['detect_only', 'detect_and_click', 'sequence', 'time_based_wait']
    valid_flows = ['trigger', 'retry', 'wait_for_duration', 'sequence_with_retry']

    for state, policy in SM_STATE_POLICIES.items():
        # 필수 키 검증
        for key in required_keys:
            if key not in policy:
                print(f"오류: {state.name} 상태에 '{key}' 정책이 없습니다.")
                return False

        # action_type 유효성 검증
        action_type = policy.get('action_type')
        if action_type not in valid_action_types:
            print(f"오류: {state.name}의 action_type '{action_type}'이 유효하지 않습니다.")
            return False

        # conditional_flow 유효성 검증
        flow_type = policy.get('conditional_flow')
        if flow_type not in valid_flows:
            print(f"오류: {state.name}의 conditional_flow '{flow_type}'이 유효하지 않습니다.")
            return False

        # targets 일관성 검증
        if action_type in ['time_based_wait', 'sequence']:
            targets = policy.get('targets', [])
            if targets:
                print(f"경고: {state.name} 상태({action_type})에 불필요한 targets가 있습니다.")
        else:
            if 'targets' not in policy or not policy['targets']:
                print(f"오류: {state.name} 상태에 targets가 필요합니다.")
                return False

        # transitions 유효성 검증
        transitions = policy.get('transitions', {})
        for result_key, next_state in transitions.items():
            if not isinstance(next_state, SystemState):
                print(f"오류: {state.name}의 전이 '{result_key}'가 유효하지 않은 상태입니다.")
                return False

    print("✅ 모든 상태 정책이 올바르게 정의되었습니다.")
    return True


def validate_config() -> bool:
    """설정 유효성 검증"""
    try:
        # 필수 섹션 확인
        required_sections = ['timing', 'target_screens', 'io_policy', 'game_settings']
        for section in required_sections:
            if section not in SM_CONFIG:
                print(f"오류: 필수 설정 섹션 '{section}'이 없습니다.")
                return False

        # 타이밍 값 검증
        timing = SM_CONFIG['timing']
        if timing['check_interval'] <= 0:
            print("오류: check_interval은 0보다 커야 합니다.")
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
    print("🎯 SM1 리모델링 설정 테스트")
    print("=" * 60)

    # 정책 유효성 검증
    print("📊 4대 정책 범주 검증 중...")
    policies_valid = validate_state_policies()

    print("\n📊 설정 검증 중...")
    config_valid = validate_config()

    if policies_valid and config_valid:
        print(f"\n📊 정의된 상태 수: {len(SM_STATE_POLICIES)}")
        print(f"📋 상태별 정책 요약:")

        for i, state in enumerate(get_all_states(), 1):
            policy = get_state_policy(state)
            action_type = policy.get('action_type', 'N/A')
            flow_type = policy.get('conditional_flow', 'N/A')
            transitions = policy.get('transitions', {})

            print(f"  {i}. {state.name}")
            print(f"     • 액션: {action_type}")
            print(f"     • 흐름: {flow_type}")
            print(f"     • 전이: {len(transitions)}개")

            # 특수 설정 표시
            if 'expected_duration' in policy:
                print(f"     • 예상 시간: {policy['expected_duration']}초")
            if 'retry_config' in policy:
                retry_config = policy['retry_config']
                print(f"     • 재시도: 최대 {retry_config.get('max_attempts', 'N/A')}회")
            if 'sequence_config' in policy:
                sequence_config = policy['sequence_config']
                actions = sequence_config.get('actions', [])
                print(f"     • 시퀀스: {len(actions)}개 액션")
            print()

        print(f"📊 관리 대상 화면: {get_target_screens()}")

        print(f"\n🎯 4대 정책 범주 적용 현황:")
        print("  • targets: 감지할 템플릿 정의")
        print("  • action_type: 실행 방식 (detect_only, detect_and_click, sequence, time_based_wait)")
        print("  • transitions: 상태 전이 매핑")
        print("  • conditional_flow: 전이 타이밍 전략 (trigger, retry, wait_for_duration, sequence_with_retry)")

        print(f"\n🌉 브릿지 호환성:")
        print("  • 화면별 개별 객체성 지원")
        print("  • screen_info.py의 SCREEN_REGIONS 연동")
        print("  • template_paths.py 템플릿 시스템 연동")
        print("  • 글로벌룰(screen_utils) 호출 구조")

    else:
        print("❌ 정책 또는 설정 검증 실패!")

    print("\n" + "=" * 60)
    print("SM1 리모델링 설정 테스트 완료")