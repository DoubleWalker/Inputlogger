# Orchestrator/NightCrows/System_Monitor/config/sm_config.py
"""
SystemMonitor 로컬룰 정의
- SM1의 고유한 "성격"과 "정책" 정의
- 상태머신 정의와 전이규칙
- 타이밍, 우선순위, 복구 전략 등 개성적 설정
- SM1 전용 감지 및 액션 함수들
"""

import time
from enum import Enum, auto


# =============================================================================
# 🎯 로컬룰 1: 상태 정의 (SM1의 고유한 생활 패턴)
# =============================================================================

class SystemState(Enum):
    """SystemMonitor 상태 정의 - 수정된 상태머신"""
    NORMAL = auto()  # 정상 상태
    CONNECTION_ERROR = auto()  # 연결 에러 감지
    CLIENT_CRASHED = auto()  # 클라이언트 크래시
    RESTARTING_APP = auto()  # 앱 재시작 중
    LOADING = auto()  # 로딩 중
    LOGIN_REQUIRED = auto()  # 로그인 필요
    LOGGING_IN = auto()  # 로그인 진행 중
    RETURNING_TO_GAME = auto()  # 게임 복귀 중


# =============================================================================
# 🎯 로컬룰 2: 상태전이 규칙 (SM1의 의사결정 패턴)
# =============================================================================

SM_TRANSITIONS = {
    SystemState.NORMAL: {
        'connection_error_detected': SystemState.CONNECTION_ERROR,
        'client_crashed_detected': SystemState.CLIENT_CRASHED,
        'stay_normal': SystemState.NORMAL
    },

    SystemState.CONNECTION_ERROR: {
        'confirm_clicked_success': SystemState.LOGIN_REQUIRED,  # 바로 로그인으로
        'confirm_click_failed': SystemState.CONNECTION_ERROR,
        'max_retries_reached': SystemState.NORMAL  # 포기하고 정상으로
    },

    SystemState.CLIENT_CRASHED: {
        'restart_initiated': SystemState.RESTARTING_APP,
        'restart_failed': SystemState.CLIENT_CRASHED,
        'max_retries_reached': SystemState.NORMAL
    },

    SystemState.RESTARTING_APP: {
        'app_started': SystemState.LOADING,
        'restart_timeout': SystemState.CLIENT_CRASHED,  # 다시 시도
        'restart_failed': SystemState.NORMAL
    },

    SystemState.LOADING: {
        'loading_complete': SystemState.LOGIN_REQUIRED,
        'loading_timeout': SystemState.RESTARTING_APP,  # 다시 시작
        'loading_failed': SystemState.NORMAL
    },

    SystemState.LOGIN_REQUIRED: {
        'login_started': SystemState.LOGGING_IN,
        'login_failed': SystemState.LOGIN_REQUIRED,
        'max_login_retries': SystemState.NORMAL
    },

    SystemState.LOGGING_IN: {
        'login_complete': SystemState.RETURNING_TO_GAME,
        'login_timeout': SystemState.LOGIN_REQUIRED,  # 다시 시도
        'login_failed': SystemState.NORMAL
    },

    SystemState.RETURNING_TO_GAME: {
        'game_ready': SystemState.NORMAL,
        'return_timeout': SystemState.LOGIN_REQUIRED,  # 로그인부터 다시
        'return_failed': SystemState.NORMAL
    }
}

# =============================================================================
# 🎯 로컬룰 3: 개성적 설정 (SM1만의 고유한 특성)
# =============================================================================

SM_CONFIG = {
    # 타이밍 설정 - "SM1은 5초마다 적당히 체크하는 성격"
    'timing': {
        'check_interval': 5.0,  # 5초 간격 (SRM의 0.5초보다는 느긋함)
        'max_retries': 3,  # 최대 3회 재시도
        'app_restart_timeout': 20.0,  # 앱 재시작 20초 대기
        'loading_timeout': 15.0,  # 로딩 15초 대기
        'login_timeout': 15.0,  # 로그인 15초 대기
        'game_return_timeout': 15.0  # 게임 복귀 15초 대기
    },

    # 대상 화면 설정 - "SM1은 스마트폰 화면만 관리하는 정책"
    'target_screens': {
        'included': ['S1', 'S2', 'S3', 'S4'],  # 스마트폰 화면만
        'excluded': ['S5'],  # PC 네이티브 제외
        'check_order': ['S1', 'S2', 'S3', 'S4']  # 체크 순서
    },

    # 복구 전략 설정 - "SM1만의 복구 방식"
    'recovery_strategy': {
        'connection_error': {
            'method': 'CLICK_CONFIRM_BUTTON',
            'retry_delay': 5.0,
            'max_attempts': 3
        },
        'client_crash': {
            'method': 'RESTART_APP_ICON',
            'retry_delay': 10.0,
            'max_attempts': 2
        },
        'login_process': {
            'method': 'SIMPLE_LOGIN',  # 단순화된 로그인
            'center_click_count': 2,  # 가운데 2번 클릭
            'click_delay': 2.0
        }
    },

    # 감지 임계값 - "SM1의 감지 민감도"
    'detection': {
        'confidence_threshold': 0.85,  # 85% 신뢰도
        'template_matching_method': 'TM_CCOEFF_NORMED',
        'state_change_delay': 2.0  # 상태 변경 전 2초 대기
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

    # 템플릿 매칭 실패 시
    'template_not_found': {
        'action': 'CONTINUE_MONITORING',
        'log_level': 'WARNING',
        'retry_with_lower_confidence': True,
        'fallback_confidence': 0.7
    }
}
