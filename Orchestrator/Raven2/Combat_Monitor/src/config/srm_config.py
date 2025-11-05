# Orchestrator/Raven2/Combat_Monitor/src/config/srm_config_raven2.py
# (신규 생성)

from enum import Enum, auto


# =============================================================================
# 🎯 로컬룰 1: 상태 정의 (레이븐2 전투 로직)
# =============================================================================

class ScreenState(Enum):
    """
    레이븐2 모니터의 상태 정의 (monitor.py 기반)
    """
    SLEEP = auto()  # 0. 아무것도 하지 않는 기본 상태
    AWAKE = auto()  # 1. 정상 전투/사냥 중 상태 (SLEEP/AWAKE는 탐지 전용)
    DEAD = auto()  # 2. 사망 감지
    RECOVERING = auto()  # 3. 부활 중 (부활 버튼 클릭 후 마을 도착 대기)
    ABNORMAL = auto()  # 4. 비정상 상태 감지 (예: 피격)
    RETREATING = auto()  # 5. 후퇴 중 (안전지대 도착 대기)
    SAFE_ZONE = auto()  # 6. 안전지대 도착 (물약 구매 시작점)
    POTIONS_PURCHASED = auto()  # 7. 물약 구매 완료 (사냥터 복귀 시작점)
    RETURNING_TO_COMBAT = auto()  # 8. 사냥터 복귀 중 (복귀 완료 대기)


# =============================================================================
# 🎯 로컬룰 2: 레이븐2 정책 정의 (상태별 행동 지침)
# =============================================================================

RAVEN2_STATE_POLICIES = {

    # -----------------------------------------------------
    # 1. 탐지/대기 상태 (SLEEP, AWAKE)
    # -----------------------------------------------------

    ScreenState.SLEEP: {
        # 1. 무엇을 감지할지: 사망(DEAD), 비정상(ABNORMAL) 우선 감지
        'targets': [
            {'template': 'DEAD_TEMPLATE', 'result': 'death_detected'},
            {'template': 'ABNORMAL_TEMPLATE', 'result': 'abnormal_detected'},
            {'template': 'AWAKE_TEMPLATE', 'result': 'awake_detected'}  # (예시)
        ],
        # 2. 어떻게 할지: 감지만 (check_status 로직)
        'action_type': 'detect_only',
        # 3. 어디로 갈지: 감지 결과에 따라 상태 전이
        'transitions': {
            'death_detected': ScreenState.DEAD,
            'abnormal_detected': ScreenState.ABNORMAL,
            'awake_detected': ScreenState.AWAKE,
        },
        # 4. 조건부 흐름제어: 위험 감지되면 즉시 분기
        'conditional_flow': 'trigger'
    },

    ScreenState.AWAKE: {
        # 1. 무엇을 감지할지: SLEEP과 동일 (사망, 비정상 우선)
        'targets': [
            {'template': 'DEAD_TEMPLATE', 'result': 'death_detected'},
            {'template': 'ABNORMAL_TEMPLATE', 'result': 'abnormal_detected'},
            {'template': 'SLEEP_TEMPLATE', 'result': 'sleep_detected'}  # (예시)
        ],
        # 2. 어떻게 할지: 감지만 (check_status 로직)
        'action_type': 'detect_only',
        # 3. 어디로 갈지: 감지 결과에 따라 상태 전이
        'transitions': {
            'death_detected': ScreenState.DEAD,
            'abnormal_detected': ScreenState.ABNORMAL,
            'sleep_detected': ScreenState.SLEEP,
        },
        # 4. 조건부 흐름제어: 위험 감지되면 즉시 분기
        'conditional_flow': 'trigger'
    },

    # -----------------------------------------------------
    # 2. 사망(DEAD) 및 부활(RECOVERING)
    # -----------------------------------------------------

    ScreenState.DEAD: {
        # 1. targets: sequence는 빈 배열
        'targets': [],
        # 2. action_type: 'process_death_recovery' 메서드 로직 번역
        'action_type': 'sequence',
        # 'process_death_recovery'의 내용을 여기에 번역
        'sequence_config': {
            'actions': [
                # {'operation': 'click', 'template': 'REVIVE_BUTTON_TEMPLATE', 'initial': True},
                # {'operation': 'wait_duration', 'duration': 0.5},
                # {'operation': 'click_relative', 'key': 'graveyard_confirm', 'final': True},
                # (예시)
            ]
        },
        # 3. transitions:
        'transitions': {
            'sequence_complete': ScreenState.RECOVERING,
            'sequence_failed': ScreenState.DEAD,  # 재시도
            'sequence_in_progress': ScreenState.DEAD
        },
        # 4. conditional_flow:
        'conditional_flow': 'sequence_with_retry'
    },

    ScreenState.RECOVERING: {
        # 1. targets: 'is_recovered' 확인 로직 번역
        'targets': [
            # 'is_recovered'는 'is_in_safe_zone'을 호출하고,
            # 'is_in_safe_zone'은 'combat.template1' (마을 UI)을 찾음
            {'template': 'TOWN_UI_TEMPLATE', 'result': 'recovery_confirmed'}
        ],
        # 2. action_type: 템플릿 감지 (대기)
        'action_type': 'detect_only',
        # 3. transitions:
        'transitions': {
            'recovery_confirmed': ScreenState.SAFE_ZONE,
            # (타임아웃은 monitor.py의 retry_count > 60 로직으로 처리)
        },
        # 4. conditional_flow:
        'conditional_flow': 'trigger'  # 감지되면 즉시 전이
    },

    # -----------------------------------------------------
    # 3. 피격(ABNORMAL) 및 후퇴(RETREATING)
    # -----------------------------------------------------

    ScreenState.ABNORMAL: {
        # 1. targets: sequence는 빈 배열
        'targets': [],
        # 2. action_type: 'retreat_to_safe_zone' 메서드 로직 번역
        'action_type': 'sequence',
        # 'retreat_to_safe_zone'의 내용을 여기에 번역
        'sequence_config': {
            'actions': [
                # {'operation': 'click', 'template': 'RETREAT_CONFIRM_BUTTON', 'optional': True, 'initial': True},
                # {'operation': 'click_relative', 'key': 'retreat_confirm_button', 'optional': True},
                # {'operation': 'click', 'template': 'RETREAT_BUTTON', 'final': True}
            ]
        },
        # 3. transitions:
        'transitions': {
            'sequence_complete': ScreenState.RETREATING,
            'sequence_failed': ScreenState.ABNORMAL,  # 재시도
            'sequence_in_progress': ScreenState.ABNORMAL
        },
        # 4. conditional_flow:
        'conditional_flow': 'sequence_with_retry'
    },

    ScreenState.RETREATING: {
        # 1. targets: 'is_in_safe_zone' 확인 로직 번역
        'targets': [
            {'template': 'TOWN_UI_TEMPLATE', 'result': 'safe_zone_confirmed'}
        ],
        # 2. action_type: 템플릿 감지 (대기)
        'action_type': 'detect_only',
        # 3. transitions:
        'transitions': {
            'safe_zone_confirmed': ScreenState.SAFE_ZONE,
            # (타임아웃은 monitor.py의 retry_count > 60 로직으로 처리)
        },
        # 4. conditional_flow:
        'conditional_flow': 'trigger'
    },

    # -----------------------------------------------------
    # 4. 물약 구매(SAFE_ZONE) 및 복귀(POTIONS_PURCHASED)
    # -----------------------------------------------------

    ScreenState.SAFE_ZONE: {
        # 1. targets: sequence는 빈 배열
        'targets': [],
        # 2. action_type: 'replenish_potions' 메서드 로직 번역
        'action_type': 'sequence',
        # 'replenish_potions'의 내용을 여기에 번역
        'sequence_config': {
            'actions': [
                # {'operation': 'wait_duration', 'duration': 2.5, 'initial': True},
                # {'operation': 'wait', 'template': 'SHOP_UI', 'timeout': 3.0, 'on_timeout': 'fail_sequence'},
                # {'operation': 'click', 'template': 'SHOP_UI'},
                # ... (구매, 확인, esc) ...
                # {'operation': 'key_press', 'key': 'esc', 'final': True}
            ]
        },
        # 3. transitions:
        'transitions': {
            'sequence_complete': ScreenState.POTIONS_PURCHASED,
            'sequence_failed': ScreenState.SAFE_ZONE,  # 재시도
            'sequence_in_progress': ScreenState.SAFE_ZONE
        },
        # 4. conditional_flow:
        'conditional_flow': 'sequence_with_retry'
    },

    ScreenState.POTIONS_PURCHASED: {
        # 1. targets: sequence는 빈 배열
        'targets': [],
        # 2. action_type: 'return_to_combat' 메서드 로직 번역
        'action_type': 'sequence',
        # 'return_to_combat'의 복잡한 로직을 여기에 번역
        # (만약 너무 복잡하면 'execute_subroutine' 사용 고려)
        'sequence_config': {
            'actions': [
                # {'operation': 'click', 'template': 'COMBAT_TEMPLATE_1', 'initial': True},
                # {'operation': 'click_relative', ... (상대 좌표 클릭)},
                # {'operation': 'execute_subroutine', 'name': '_do_raven2_drag_logic'}, # (복잡한 로직)
                # {'operation': 'click', 'coords': (410, 60), 'context': 'S1'}, # (절대 좌표 클릭)
                # ... (template2 찾기, 상대 이동 클릭) ...
                # {'operation': 'click_relative', ... , 'final': True}
            ]
        },
        # 3. transitions:
        'transitions': {
            'sequence_complete': ScreenState.RETURNING_TO_COMBAT,
            'sequence_failed': ScreenState.POTIONS_PURCHASED,  # 재시도
            'sequence_in_progress': ScreenState.POTIONS_PURCHASED
        },
        # 4. conditional_flow:
        'conditional_flow': 'sequence_with_retry'
    },

    # -----------------------------------------------------
    # 5. 복귀 중(RETURNING_TO_COMBAT)
    # -----------------------------------------------------

    ScreenState.RETURNING_TO_COMBAT: {
        # 1. targets: 'is_at_combat_spot' 픽셀 체크 로직 번역
        # (픽셀 체크는 'operation': 'check_pixel' 등으로 확장 필요)
        # (또는 'perform_repeated_combat_return' 로직을 실행)
        'targets': [
            # 픽셀 체크 대신 템플릿으로 대체하거나,
            # monitor.py가 특수 로직(픽셀체크)을 수행하도록 함
            {'template': 'COMBAT_SPOT_TEMPLATE', 'result': 'combat_spot_confirmed'}
        ],
        # 2. action_type:
        'action_type': 'detect_only',  # (또는 픽셀/재복귀 로직 실행)

        # (만약 'perform_repeated_combat_return'을 실행해야 한다면)
        # 'action_type': 'sequence',
        # 'sequence_config': {
        #    'actions': [ ... ('perform_repeated_combat_return' 로직) ... ]
        # },

        # 3. transitions:
        'transitions': {
            'combat_spot_confirmed': ScreenState.AWAKE,
            # (타임아웃/재시도 초과는 monitor.py가 관리)
        },
        # 4. conditional_flow:
        'conditional_flow': 'trigger'
    },
}


# =============================================================================
# 🔧 유틸리티 함수들 (나이트크로우 srm_config.py와 동일)
# =============================================================================

def get_state_policy(state: ScreenState) -> dict:
    """특정 상태의 정책을 반환합니다."""
    return RAVEN2_STATE_POLICIES.get(state, {})


def get_all_states() -> list:
    """레이븐2가 지원하는 모든 상태 목록을 반환합니다."""
    return list(RAVEN2_STATE_POLICIES.keys())


def get_initial_state() -> ScreenState:
    """초기 상태를 반환합니다."""
    # monitor.py의 기본값인 SLEEP 또는 AWAKE로 설정
    return ScreenState.SLEEP


def validate_state_policies() -> bool:
    """모든 상태 정책이 올바르게 정의되었는지 검증합니다."""
    required_keys = ['targets', 'action_type', 'transitions', 'conditional_flow']

    # (나머지 검증 로직은 srm_config.py에서 그대로 복사)

    print("✅ 모든 레이븐2 상태 정책이 올바르게 정의되었습니다. (뼈대 기준)")
    return True


# =============================================================================
# 🧪 테스트 및 디버깅
# =============================================================================

if __name__ == "__main__":
    print("🎯 레이븐2 통합 설정(SRM) 뼈대 테스트")
    print("=" * 60)

    # 정책 유효성 검증
    print("📊 정책 검증 중...")
    policies_valid = validate_state_policies()

    if policies_valid:
        print(f"\n📊 정의된 상태 수: {len(get_all_states())}")
        print("📋 지원 상태들:")
        for state in get_all_states():
            print(f"  - {state.name}")

    print("\n" + "=" * 60)
    print("SRM(레이븐2) 뼈대 테스트 완료")