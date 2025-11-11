# Orchestrator/NightCrows/System_Monitor/config/sm_config.py
"""
SM1 v3 리모델링 설정 (제너레이터 '상황반장' 아키텍처)
- '똑똑한 정책' (Smart Policy) 모델
- monitor.py(실행기)에 '지시서'를 발행하는 제너레이터 함수들을 정의
- get_state_policies: '제너레이터'를 실행할 상태 (예: LOGIN_REQUIRED)
- get_detection_policy: '단순 감지'만 할 상태 (예: NORMAL)
"""

from enum import Enum, auto
from typing import Generator, Dict, Any, Optional


# =============================================================================
# 🎯 로컬룰 1: 상태 정의 (이름/값은 v1과 동일하게 유지)
# =============================================================================

class SystemState(Enum):
    """SystemMonitor 상태 정의 (v1과 동일)"""
    NORMAL = auto()
    CONNECTION_ERROR = auto()
    CLIENT_CRASHED = auto()
    RESTARTING_APP = auto()
    LOGIN_REQUIRED = auto()
    LOGGING_IN = auto()
    RETURNING_TO_GAME = auto()


# =============================================================================
# 🎯 로컬룰 2: "상황반장" 정책 (v1 로직의 제너레이터 '번역')
# =============================================================================
#
# 각 함수는 '제너레이터'입니다.
# 'yield'를 만나면 '지시서'를 반환하고, 'monitor.py'가 처리를 완료하고
# 다음 루프에서 'next()'를 호출할 때까지 '일시 정지'합니다.
#
# 'screen' 객체(컨텍스트)는 monitor.py가 인자로 주입해줍니다.
#
# =============================================================================

def policy_connection_error(screen: dict) -> Generator[Dict[str, Any], Any, None]:
    """
    [상황반장: 연결 오류]
    v1의 'detect_and_click' (retry 3회) 로직을 번역합니다.
    """
    print(f"INFO: [{screen['screen_id']}] 상황반장: '연결 오류' 접수. 3회 확인 시도.")

    # v1의 'retry_config': max_attempts: 3, retry_delay: 2.5
    for attempt in range(1, 4):  # 1, 2, 3
        # 'click_if_present' 지시: 있으면 클릭하고 'pos' 반환, 없으면 None 반환
        pos = yield {
            'operation': 'click_if_present',
            'template_name': 'CONNECTION_CONFIRM_BUTTON'
        }

        if pos:
            print(f"INFO: [{screen['screen_id']}] 연결 오류 확인 버튼 클릭 성공.")
            return  # 성공! 제너레이터 종료 (-> 'complete' 전이)

        # 실패 시 2.5초 대기 후 다음 시도
        yield {'operation': 'wait_duration', 'duration': 2.5}

    # 3회 모두 실패하면 예외 발생 (-> 'fail' 전이)
    raise Exception("Failed to click CONNECTION_CONFIRM_BUTTON after 3 attempts")


def policy_client_crashed(screen: dict) -> Generator[Dict[str, Any], Any, None]:
    """
    [상황반장: 클라이언트 크래시]
    v1의 'detect_and_click' (retry 3회) 로직을 번역합니다.
    """
    print(f"INFO: [{screen['screen_id']}] 상황반장: '클라이언트 크래시' 접수. 3회 재시작 시도.")

    # v1의 'retry_config': max_attempts: 3, retry_delay: 3.0
    for attempt in range(1, 4):  # 1, 2, 3
        pos = yield {
            'operation': 'click_if_present',
            'template_name': 'APP_ICON'
        }
        if pos:
            print(f"INFO: [{screen['screen_id']}] 앱 아이콘 클릭 성공 (재시작).")
            return  # 성공! 제너레이터 종료

        yield {'operation': 'wait_duration', 'duration': 3.0}

    raise Exception("Failed to click APP_ICON after 3 attempts")


def policy_restarting_app(screen: dict) -> Generator[Dict[str, Any], Any, None]:
    """
    [상황반장: 앱 재시작 대기]
    v1의 'time_based_wait' (expected_duration: 30.0) 로직을 번역합니다.
    """
    print(f"INFO: [{screen['screen_id']}] 상황반장: '앱 재시작' 대기 (30초).")

    # v1의 'expected_duration': 30.0
    yield {'operation': 'wait_duration', 'duration': 30.0}

    # 30초 대기 후, 제너레이터가 정상 종료 (-> 'complete' 전이)
    print(f"INFO: [{screen['screen_id']}] 앱 재시작 시간 경과. 'LOGIN_REQUIRED'로 이동.")


def policy_logging_in(screen: dict) -> Generator[Dict[str, Any], Any, None]:
    """
    [상황반장: 로그인 진행 중]
    v1의 'time_based_wait' (expected_duration: 25.0) 로직을 번역합니다.
    """
    print(f"INFO: [{screen['screen_id']}] 상황반장: '로그인' 대기 (25초).")

    # v1의 'expected_duration': 25.0
    yield {'operation': 'wait_duration', 'duration': 25.0}

    print(f"INFO: [{screen['screen_id']}] 로그인 시간 경과. 'RETURNING_TO_GAME'으로 이동.")


def policy_returning_to_game(screen: dict) -> Generator[Dict[str, Any], Any, None]:
    """
    [상황반장: 게임 복귀 중]
    v1의 'time_based_wait' (expected_duration: 15.0) 로직을 번역합니다.
    """
    print(f"INFO: [{screen['screen_id']}] 상황반장: '게임 복귀' 대기 (15초).")

    # v1의 'expected_duration': 15.0
    yield {'operation': 'wait_duration', 'duration': 15.0}

    print(f"INFO: [{screen['screen_id']}] 게임 복귀 시간 경과. 'NORMAL'로 이동.")


def policy_login_required(screen: dict) -> Generator[Dict[str, Any], Any, None]:
    """
    [상황반장: 로그인 필요 (시퀀스)]
    v1의 'action_type: sequence' (max_attempts: 10) 로직을 번역합니다.
    """
    print(f"INFO: [{screen['screen_id']}] 상황반장: '로그인 시퀀스' 접수 (최대 10회).")

    # v1의 'sequence_config': max_attempts: 10
    for attempt in range(1, 11):  # 1부터 10까지
        print(f"INFO: [{screen['screen_id']}] 로그인 시도 ({attempt}/10)")

        try:
            # 1. 'set_focus' 지시 (v1 시퀀스 1단계)
            yield {'operation': 'set_focus'}

            # 2. 'click_if_present(AD_POPUP)' 지시 (v1 시퀀스 2단계)
            yield {
                'operation': 'click_if_present',
                'template_name': 'AD_POPUP'
            }

            # 3. 'click(LOGIN_BUTTON)' 지시 (v1 시퀀스 3단계)
            # 'click' 지시는 monitor.py에 의해 '못찾으면 예외 발생'으로 처리됨
            pos = yield {
                'operation': 'click',
                'template_name': 'LOGIN_BUTTON'
            }

            # 'click'이 성공하면 (예외가 발생 안하면) 로그인 성공
            print(f"INFO: [{screen['screen_id']}] 로그인 버튼 클릭 성공.")
            return  # 성공! 제너레이터 종료 (-> 'complete' 전이)

        except Exception as e:
            # 'click'이 실패(예외)하면 catch
            print(f"WARN: [{screen['screen_id']}] 로그인 시도 {attempt} 실패: {e}")
            yield {'operation': 'wait_duration', 'duration': 3.0}  # 3초 후 재시도

    # 10회 루프를 모두 돌았는데 return하지 못하면 예외 발생 (-> 'fail' 전이)
    raise Exception("Failed to login after 10 attempts")


# =============================================================================
# 🎯 로컬룰 3: 정책 라우터 (Monitor가 "상황반장"을 찾는 함수)
# =============================================================================

# [v3] 1. '감지 전용' 상태 맵 (예: NORMAL)
# : '바보 실행기(monitor.py)'가 이 맵을 순회하며 '단순 감지'만 수행합니다.
DETECTION_POLICY_MAP = {
    SystemState.NORMAL: {
        'targets': [
            # v1의 'transitions'를 번역: '감지 템플릿' -> '전이될 상태'
            {'template_name': 'CONNECTION_CONFIRM_BUTTON', 'next_state': SystemState.CONNECTION_ERROR},
            {'template_name': 'APP_ICON', 'next_state': SystemState.CLIENT_CRASHED}
        ]
    }
}

# [v3] 2. '제너레이터 실행' 상태 맵 (예: LOGGING_IN)
# : '바보 실행기(monitor.py)'가 이 맵을 보고 '상황반장(generator)'을 호출합니다.
STATE_POLICY_MAP = {
    SystemState.CONNECTION_ERROR: {
        'generator': policy_connection_error,
        'transitions': {
            'complete': SystemState.LOGIN_REQUIRED,  # v1의 'confirm_clicked'
            'fail': SystemState.CONNECTION_ERROR  # v1의 'retry_failed'
        }
    },
    SystemState.CLIENT_CRASHED: {
        'generator': policy_client_crashed,
        'transitions': {
            'complete': SystemState.RESTARTING_APP,  # v1의 'app_started'
            'fail': SystemState.CLIENT_CRASHED  # v1의 'retry_failed'
        }
    },
    SystemState.RESTARTING_APP: {
        'generator': policy_restarting_app,
        'transitions': {
            'complete': SystemState.LOGIN_REQUIRED,  # v1의 'duration_passed'
            'fail': SystemState.CLIENT_CRASHED  # v1의 'timeout_reached'
        }
    },
    SystemState.LOGGING_IN: {
        'generator': policy_logging_in,
        'transitions': {
            'complete': SystemState.RETURNING_TO_GAME,  # v1의 'duration_passed'
            'fail': SystemState.LOGIN_REQUIRED  # v1의 'timeout_reached'
        }
    },
    SystemState.RETURNING_TO_GAME: {
        'generator': policy_returning_to_game,
        'transitions': {
            'complete': SystemState.NORMAL,  # v1의 'duration_passed'
            'fail': SystemState.NORMAL  # v1의 'timeout_reached'
        }
    },
    SystemState.LOGIN_REQUIRED: {
        'generator': policy_login_required,
        'transitions': {
            'complete': SystemState.LOGGING_IN,  # v1의 'sequence_complete'
            'fail': SystemState.LOGIN_REQUIRED  # v1의 'sequence_failed'
        }
    },
}

# =============================================================================
# 🎯 로컬룰 4: 운영 설정 (v1과 동일하게 유지)
# =============================================================================
# (monitor.py가 여전히 이 설정들을 참조합니다)

SM_CONFIG = {
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
        'click_delay': 0.2
    },
    'game_settings': {
        'game_type': 'nightcrows',
        'vd_name': 'VD1'
    }
}

# =============================================================================
# 🎯 로컬룰 5: 예외 처리 정책 (v1과 동일하게 유지)
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
# 🔧 유틸리티 함수들 (Monitor가 호출하는 핵심 함수)
# =============================================================================

def get_state_policies() -> dict:
    """
    [v3] '제너레이터 실행'이 필요한 상태들의 정책 맵을 반환합니다.
    (monitor.py가 참조 'get_state_policies'을(를) 찾을 수 없습니다 -> 해결)
    """
    return STATE_POLICY_MAP


def get_detection_policy() -> dict:
    """
    [v3] '단순 감지'만 필요한 상태들의 정책 맵을 반환합니다.
    (monitor.py가 참조 'get_detection_policy'을(를) 찾을 수 없습니다 -> 해결)
    """
    return DETECTION_POLICY_MAP


def validate_config() -> bool:
    """v1의 설정 유효성 검증 (v3에서도 유효함)"""
    try:
        required_sections = ['timing', 'target_screens', 'io_policy', 'game_settings']
        for section in required_sections:
            if section not in SM_CONFIG:
                print(f"오류: 필수 설정 섹션 '{section}'이 없습니다.")
                return False
        if SM_CONFIG['timing']['check_interval'] <= 0:
            print("오류: check_interval은 0보다 커야 합니다.")
            return False
        if not SM_CONFIG['target_screens']['included']:
            print("오류: 대상 화면이 비어있습니다.")
            return False

        print("✅ SM_CONFIG 유효성 검증 완료")

        # [v3] 제너레이터 맵 검증
        if not STATE_POLICY_MAP or not DETECTION_POLICY_MAP:
            print("오류: v3 정책 맵(STATE_POLICY_MAP, DETECTION_POLICY_MAP)이 비어있습니다.")
            return False

        print("✅ v3 제너레이터 정책 맵 로드됨")
        return True

    except Exception as e:
        print(f"오류: 설정 검증 중 예외 발생 - {e}")
        return False


# =============================================================================
# 🧪 테스트 및 디버깅
# =============================================================================

if __name__ == "__main__":
    print("🎯 SM1 v3 '상황반장' 설정 테스트")
    print("=" * 60)

    config_valid = validate_config()

    if config_valid:
        # ❌ 잘못된 부분 (들여쓰기 한 칸 많음)
        #   print("\n[v3 감지 전용 상태 (DetectOnly)]:
        #         ")

        # ✅ 수정된 부분 (들여쓰기 수정)
        print("\n[v3 감지 전용 상태 (DetectOnly)]:")
        for state, policy in get_detection_policy().items():
            print(f"  - {state.name} (감지 템플릿: {len(policy.get('targets', []))}개)")

        # ❌ 잘못된 부분 (들여쓰기 한 칸 많음)
        #   print("\n[v3 상황반장 상태 (Generator)]:
        #         ")

        # ✅ 수정된 부분 (들여쓰기 수정)
        print("\n[v3 상황반장 상태 (Generator)]:")
        for state, policy in get_state_policies().items():
            gen_name = policy.get('generator', lambda: None).__name__
            print(f"  - {state.name} -> {gen_name}")

    else:
        print("❌ 설정 검증 실패!")

    print("\n" + "=" * 60)
    print("sm_config.py (v3) 테스트 완료")