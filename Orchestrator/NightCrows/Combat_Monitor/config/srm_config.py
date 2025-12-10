# srm1_config.py - SRM1 통합 설정 (운영 설정 + 4대 정책)

from enum import Enum, auto
from typing import final

from pyautogui import click


# =============================================================================
# 🎯 로컬룰 1: 상태 정의 (SRM1 전투 로직)
# =============================================================================

class ScreenState(Enum):
    """SRM1 화면별 상태 정의 (원래 SRM1 구조 유지)"""
    NORMAL = auto()  # 정상 상태
    INITIALIZING = auto()
    DEAD = auto()  # 사망 상태
    RECOVERING = auto()  # 부활 중
    HOSTILE = auto()  # 적대 상태
    S1_EMERGENCY_FLEE = auto()
    FLEEING = auto()  # 도주 중
    BUYING_POTIONS = auto()  # 물약 구매 중 (구매+복귀 포함)
    RETURNING = auto()  # 복귀 중 (웨이포인트 포함)
    RESUME_COMBAT = auto()


# =============================================================================
# 🎯 로컬룰 2: SRM1 정책 정의 (4개 핵심 정책) - SM1 패턴 적용
# =============================================================================

SRM1_STATE_POLICIES = {
    ScreenState.NORMAL: {
        # 1. 무엇을 감지할지 - 위험 요소 스캔
        'targets': [
            {'template': 'DEAD', 'result': 'death_detected'},
            {'template': 'HOSTILE', 'result': 'hostile_detected'}
        ],

        # 2. 어떻게 할지 - 감지만 (모니터링)
        'action_type': 'detect_only',  # ✅ SM1 표준 4가지 중 하나

        # 3. 어디로 갈지 - 위험 요소별 상태 전이
        'transitions': {
            'death_detected': ScreenState.DEAD,
            'hostile_detected': ScreenState.HOSTILE
        },

        # 4. 조건부 흐름제어 - 위험 감지되면 즉시 분기
        'conditional_flow': 'trigger'
    },

ScreenState.INITIALIZING: {
        'targets': [],
        'action_type': 'sequence',

        'sequence_config': {
            'actions': [
                # ❗️ 'S1'만 이 로직을 실행하는 것이 보장됩니다.
                # ❗️ 따라서 'screen_id': 'S1' 태그도 모두 제거할 수 있습니다.

                # Step 0: S1 화면에 포커스
                # Step 1: ESC 키 입력
                {'operation': 'key_press', 'key': 'esc'},
                # Step 2: 1초 대기
                {'operation': 'wait_duration', 'duration': 1.0},
                # Step 3: ARENA 템플릿 대기 (최대 5초)
                {'operation': 'wait', 'template': 'ARENA', 'timeout': 5.0,
                 'on_timeout': 'fail_sequence', 'final': True},

                # ❗️ S2-S5를 위한 'wait_for_flag' 로직은 완전히 제거됩니다.
            ]
        },

        'transitions': {
            'sequence_complete': ScreenState.NORMAL,  # S1이 ARENA 템플릿을 찾음
            'sequence_failed': ScreenState.NORMAL,    # S1이 타임아웃됨 (FIELD)
            'sequence_in_progress': ScreenState.INITIALIZING
        },
        'conditional_flow': 'sequence_with_retry'
    },

    ScreenState.DEAD: {
        # 1. 무엇을 감지할지 - sequence는 빈 배열 (하위 상태함수)
        'targets': [],  # ✅ 하위 상태함수 - 내부 step 진행 있음

        # 2. 어떻게 할지 - 부활 시퀀스 실행 (복잡한 내부 진행)
        'action_type': 'sequence',  # ✅ 하위 상태함수용 범용 프레임워크

        # 시퀀스 설정 - 부활의 내부 step들을 표준화
        'sequence_config': {
            'actions': [
                {'template': 'REVIVE_BUTTON', 'operation': 'click', 'initial': True},
                {'operation': 'wait_duration', 'duration': 2.0},  # 부활 처리 대기
                {'template': 'GRAVEYARD', 'operation': 'click'},  # 묘지 선택
                {'operation': 'wait_duration', 'duration': 1.0},  # 이동 처리 대기
                {'operation': 'key_press', 'key': 'esc', 'final': True}  # UI 닫기
            ]
        },

        # 3. 어디로 갈지 - 부활 완료 시
        'transitions': {
            'sequence_complete': ScreenState.RECOVERING,
            'sequence_failed': ScreenState.DEAD,  # 재시도
            'sequence_in_progress': ScreenState.DEAD
        },

        # 4. 조건부 흐름제어 - 성공할 때까지 재시도
        'conditional_flow': 'sequence_with_retry'
    },
    # 🌟 [신규] S1_EMERGENCY_FLEE 정책 추가
    # 이 상태는 S1이 잠든(NORMAL) 상태에서 S2-S5의 피격으로 강제 호출된 상태입니다.
    ScreenState.S1_EMERGENCY_FLEE: {
        'targets': [],
        'action_type': 'sequence',
        'sequence_config': {
            'actions': [
                # Step 0: S1 화면을 깨우기 위해 'safe_click_point' 클릭
                {
                    'operation': 'click_relative',
                    'key': 'safe_click_point',
                    'delay_after': 0.3,  # 클릭 후 활성화 대기
                    'initial': True
                },

                # Step 1: 화면이 깨어난 후, 기존 HOSTILE과 동일하게 _do_flight 실행
                {
                    'operation': 'execute_subroutine',
                    'name': '_do_flight',
                    'final': True
                }
            ]
        },
        'transitions': {
            'sequence_complete': ScreenState.FLEEING,  # 성공하면 FLEEING
            'sequence_failed': ScreenState.S1_EMERGENCY_FLEE,  # 실패 시 재시도
            'sequence_in_progress': ScreenState.S1_EMERGENCY_FLEE
        },
        'conditional_flow': 'sequence_with_retry'
    },

    ScreenState.RECOVERING: {
        # 1. targets: sequence는 빈 배열
        'targets': [],

        # 2. action_type: 'sequence'로 변경
        'action_type': 'sequence',

        # 3. sequence_config: '10초 대기' + '타임아웃이 있는 템플릿 대기'
        'sequence_config': {
            'actions': [
                # Step 0: 부활 후 최소 10초 대기
                {'operation': 'wait_duration', 'duration': 10.0, 'initial': True},

                # Step 1: 묘지 템플릿 대기 (최대 20초 추가 대기 = 총 30초)
                {'operation': 'wait', 'template': 'GRAVEYARD', 'timeout': 20.0, 'on_timeout': 'fail_sequence',
                 'final': True}
            ]
        },

        # 4. transitions:
        'transitions': {
            'sequence_complete': ScreenState.BUYING_POTIONS,  # 묘지 템플릿 감지 성공
            'sequence_failed': ScreenState.NORMAL,  # 30초 타임아웃
            'sequence_in_progress': ScreenState.RECOVERING
        },

        # 5. conditional_flow: 'sequence_with_retry'
        'conditional_flow': 'sequence_with_retry'
    },

    ScreenState.HOSTILE: {
        # 1. targets: sequence는 빈 배열
        'targets': [],

        # 2. action_type: 'sequence'로 변경
        'action_type': 'sequence',

        # 3. sequence_config: '_do_flight' 서브루틴을 직접 호출
        'sequence_config': {
            'actions': [
                # _do_flight는 IO만 수행하고 즉시 완료됩니다.
                {'operation': 'execute_subroutine', 'name': '_do_flight', 'final': True, 'initial': True}
            ]
        },

        # 4. transitions: 시퀀스 완료 시 FLEEING으로
        'transitions': {
            'sequence_complete': ScreenState.FLEEING,
            'sequence_failed': ScreenState.HOSTILE, # 실패 시 재시도
            'sequence_in_progress': ScreenState.HOSTILE
        },

        # 5. conditional_flow: 'sequence_with_retry'로 변경
        'conditional_flow': 'sequence_with_retry'
    },

    ScreenState.FLEEING: {
        # 1. 무엇을 감지할지 - 시간 기반 대기는 빈 배열
        'targets': [],  # ✅ time_based_wait는 targets 빈 배열

        # 2. 어떻게 할지 - 도주 완료 대기
        'action_type': 'time_based_wait',  # ✅ SM1 표준 타입

        # 시간 기반 설정
        'expected_duration': 12.0,  # 12초 대기

        # 3. 어디로 갈지 - 도주 완료 시 물약 구매로
        'transitions': {
            'duration_complete': ScreenState.BUYING_POTIONS,
            'timeout': ScreenState.BUYING_POTIONS  # 타임아웃도 물약으로
        },

        # 4. 조건부 흐름제어 - 지정 시간까지 대기
        'conditional_flow': 'wait_for_duration'
    },

    ScreenState.BUYING_POTIONS: {
        'targets': [],
        'action_type': 'sequence',

        'sequence_config': {
            'actions': [
                # 1. [수정] 시작 시 '안전한 좌표'를 클릭하여 포커스 확보 (set_focus 대체)
                {
                    'operation': 'click_relative',
                    'key': 'safe_click_point',
                    'initial': True,
                    'delay_after': 0.5  # 포커스 후 약간 대기
                },

                # 2. 상점 버튼 찾기 (실패 시 처음부터 재시도)
                {'template': 'SHOP_BUTTON', 'operation': 'wait', 'timeout': 30.0,
                 'on_timeout': 'fail_sequence'},
                {'template': 'SHOP_BUTTON', 'operation': 'click'},

                # 3. 상점 로딩 대기 (이 시간 동안 S3 등 다른 창이 위로 올라올 수 있음)
                {'operation': 'wait_duration', 'duration': 5.0},

                # 4. [수정] 중요! 구매 버튼 찾기 전, 다시 한번 '안전한 좌표' 클릭으로 창을 맨 앞으로!
                {
                    'operation': 'click_relative',
                    'key': 'safe_click_point',
                    'delay_after': 0.5
                },

                # 5. 구매 버튼 대기 (확실히 떴는지 확인)
                {'template': 'PURCHASE_BUTTON', 'operation': 'wait', 'timeout': 10.0,
                 'on_timeout': 'fail_sequence'},

                # 6. 구매 진행
                {'template': 'PURCHASE_BUTTON', 'operation': 'click'},
                {'operation': 'wait_duration', 'duration': 1.0},

                {'template': 'CONFIRM_BUTTON', 'operation': 'wait', 'timeout': 5.0,
                 'on_timeout': 'fail_sequence'},
                {'template': 'CONFIRM_BUTTON', 'operation': 'click'},
                {'operation': 'wait_duration', 'duration': 1.0},

                # 7. 상점 닫기 (실패해도 다음 단계 진행을 위해 optional 처리하거나 그냥 진행)
                {'operation': 'key_press', 'key': 'esc'},
                {'operation': 'wait_duration', 'duration': 0.5},
                {'operation': 'key_press', 'key': 'esc'},
                {'operation': 'wait_duration', 'duration': 1.0, 'final': True}
            ]
        },

        'transitions': {
            'sequence_complete': ScreenState.RETURNING,
            # [중요] 실패 시 다시 물약 구매 시도 (무한 루프 방지를 위해 모니터링 필요)
            'sequence_failed': ScreenState.BUYING_POTIONS,
            'sequence_in_progress': ScreenState.BUYING_POTIONS
        },

        'conditional_flow': 'sequence_with_retry'
    },

    ScreenState.RETURNING: {
        # 1. 무엇을 감지할지 - sequence는 빈 배열 (하위 상태함수)
        'targets': [],  # ✅ 하위 상태함수 - 복잡한 WP1~5 인덱스 진행 있음

        # 2. 어떻게 할지 - 웨이포인트 네비게이션의 복잡한 내부 step들
        'action_type': 'sequence',  # ✅ 하위 상태함수용 범용 프레임워크

        # 시퀀스 설정 - 기존 wp1_step, wp2_step 등을 표준화된 actions로 변환
        'sequence_config': {
        'actions': [


            # === ARENA 컨텍스트: WP1 ~ WP5 ===
            # WP1 (기존과 유사)
            {'operation': 'click_relative', 'key': 'main_menu_button', 'context': 'ARENA', 'initial': True},
            {'operation': 'click', 'template': 'ARENA_MENU_ICON', 'context': 'ARENA'},
            {'operation': 'key_press', 'key': 'y', 'context': 'ARENA'},
            {'operation': 'wait_duration', 'duration': 10.0, 'context': 'ARENA'},
            {'template': 'ARENA_ENTRY_UI', 'operation': 'wait', 'timeout': 30.0, 'initial': True},
            {'template': 'ARENA_ENTRY_UI', 'operation': 'click'},
            {'operation': 'wait_duration', 'duration': 25.0, 'context': 'ARENA'},
            # 말타기 끝, WP2 시작 (기존과 유사)
            {'operation': 'key_press', 'key': 'm', 'context': 'ARENA'},
            {'operation': 'click_relative', 'key': 'tower_click_1','context': 'ARENA'},
            {'operation': 'wait_duration', 'duration': 2.0, 'context': 'ARENA'},
            {'operation': 'click_relative', 'key': 'tower_click_2','context': 'ARENA'},
            {'operation': 'click_relative', 'key': 'tower_click_2','context': 'ARENA'},
            {'operation': 'wait_duration', 'duration': 1.0, 'context': 'ARENA'},
            {'operation': 'key_press', 'key': 'y', 'context': 'ARENA'},
            {'operation': 'wait_duration', 'duration': 5.0, 'context': 'ARENA'}, # 맵 이동 대기
            # WP2 도착 확인
            # 1. 지도 열기
            {'operation': 'key_press', 'key': 'm', 'context': 'ARENA'},
            {'operation': 'wait_duration', 'duration': 1.0, 'context': 'ARENA'},
            {'operation': 'execute_subroutine', 'name': '_do_wp3_movement', 'context': 'ARENA','final':True}
        ]
    },
        'transitions': {
        'sequence_complete': ScreenState.NORMAL,
        'sequence_failed': ScreenState.NORMAL,  # 실패해도 일단 사냥 시도
        'sequence_in_progress': ScreenState.RETURNING
    },
    'conditional_flow': 'sequence_with_retry'
    },

# SRM1_STATE_POLICIES 딕셔너리에 추가

    ScreenState.RESUME_COMBAT: {
        'targets': [],
        'action_type': 'sequence',
        'sequence_config': {
            'actions': [
                # 1. 화면 포커스 (safe_click_point 클릭)
                {
                    'operation': 'click_relative',
                    'key': 'safe_click_point',
                    'delay_after': 0.3,
                    'initial': True
                },
                # 2. Q 키 눌러서 자동사냥 시작
                {
                    'operation': 'key_press',
                    'key': 'q',
                    'final': True
                }
            ]
        },
        'transitions': {
            'sequence_complete': ScreenState.NORMAL,
            'sequence_failed': ScreenState.NORMAL
        },
        'conditional_flow': 'sequence_with_retry'
    }
}
# =============================================================================
# 🎯 로컬룰 3: SRM1 운영 설정 (전투 특화 파라미터)
# =============================================================================

SRM1_CONFIG = {
    # 타이밍 설정 - SRM1 고유 특성 (빠른 반응 필요)
    'timing': {
        'check_interval': 0.5,  # 0.5초 간격 (빠른 감지)
        'recovery_wait_min': 10.0,  # 최소 부활 대기 시간
        'recovery_timeout': 30.0,  # 부활 타임아웃
        'flee_wait_min': 12.0,  # 최소 도주 대기 시간
        'potion_step_timeout': 30.0  # 물약 구매 단계별 타임아웃
    },

    # 전투 우선순위 - SRM1 고유 정책
    'combat_priorities': {
        'threat_detection_order': ['DEAD', 'HOSTILE'],  # 위험 감지 순서 (사망 우선)
        'hostile_sampling': {  # 적대 감지 샘플링
            'max_samples': 3,
            'sample_interval': 0.1,
            'confidence_threshold': 0.8
        }
    },

    # 화면 설정 - SRM1 멀티스크린 지원
    'screen_management': {
        'target_screens': ['S1', 'S2', 'S3', 'S4', 'S5'],  # 모든 화면 지원
        'priority_screens': ['S1', 'S2'],  # 우선순위 화면
        'hostile_emergency_logic': True,  # HOSTILE 시 S1 긴급 처리
        's1_party_gathering_config': {
            'max_retries': 5,
            'retry_interval': 2.0,
            'total_timeout': 40.0
        },
        'other_screens_config': {
            'max_retries': 10,
            'retry_interval': 2.0,
            'total_timeout': 30.0
        }
    },

    # 위치별 처리 - SRM1 고유 컨텍스트
    'location_contexts': {
        'FIELD': {
            'return_strategy': 'field_schedule_return',
            's1_role': 'party_leader',
            'other_role': 'party_follower'
        },
        'ARENA': {
            'return_strategy': 'waypoint_navigation',
            'wp_sequence': [1, 2, 3, 4, 5],
            'wp1_config': {
                'arena_menu_wait': 35.0,
                'entry_confirm_wait': 15.0
            }
        }
    },

    # 게임 설정
    'game_settings': {
        'game_type': 'nightcrows',  # 글로벌 설정 키
        'confidence_threshold': 0.75,  # 템플릿 매칭 임계값
        'vd_name': 'VD1'  # 가상 데스크톱
    }
}


# =============================================================================
# 🔧 유틸리티 함수들
# =============================================================================

def get_state_policy(state: ScreenState, screen_id: str = None) -> dict:
    """
    특정 상태의 정책을 반환합니다.
    (v4.0 수정: WP 시퀀스를 여기서 풀지 않고, Monitor가 통째로 실행하도록 위임함)
    """
    return SRM1_STATE_POLICIES.get(state, {})

def get_all_states() -> list:
    """SRM1이 지원하는 모든 상태 목록을 반환합니다."""
    return list(SRM1_STATE_POLICIES.keys())


def get_initial_state() -> ScreenState:
    """초기 상태를 반환합니다."""
    return ScreenState.NORMAL


def validate_state_policies() -> bool:
    """모든 상태 정책이 올바르게 정의되었는지 검증합니다."""
    required_keys = ['targets', 'action_type', 'transitions', 'conditional_flow']
    valid_action_types = ['detect_only', 'detect_and_click', 'sequence', 'time_based_wait']  # ✅ SM1 표준
    valid_flows = ['trigger', 'retry', 'wait_for_duration', 'sequence_with_retry']  # ✅ SM1 표준

    for state, policy in SRM1_STATE_POLICIES.items():
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

        # ✅ SM1 패턴: targets 일관성 검증
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
        for result, next_state in transitions.items():
            if not isinstance(next_state, ScreenState):
                print(f"오류: {state.name}의 전이 결과 '{result}'가 유효하지 않은 상태입니다.")
                return False

    print("✅ 모든 SRM1 상태 정책이 올바르게 정의되었습니다.")
    return True


def validate_config() -> bool:
    """SRM1 설정 유효성 검증"""
    try:
        # 필수 키 존재 확인
        required_sections = ['timing', 'combat_priorities', 'screen_management', 'location_contexts', 'game_settings']
        for section in required_sections:
            if section not in SRM1_CONFIG:
                print(f"오류: 필수 설정 섹션 '{section}'이 없습니다.")
                return False

        # 타이밍 값 검증
        timing = SRM1_CONFIG['timing']
        if timing['check_interval'] <= 0:
            print("오류: check_interval은 0보다 커야 합니다.")
            return False

        # 화면 설정 검증
        screens = SRM1_CONFIG['screen_management']
        if not screens['target_screens']:
            print("오류: target_screens가 비어있습니다.")
            return False

        print("✅ SRM1_CONFIG 유효성 검증 완료")
        return True

    except Exception as e:
        print(f"오류: 설정 검증 중 예외 발생 - {e}")
        return False


# =============================================================================
# 🧪 테스트 및 디버깅
# =============================================================================

if __name__ == "__main__":
    print("🎯 SRM1 통합 설정 테스트 (SM1 패턴 적용)")
    print("=" * 60)

    # 정책 유효성 검증
    print("📊 정책 검증 중...")
    policies_valid = validate_state_policies()

    print("\n📊 설정 검증 중...")
    config_valid = validate_config()

    if policies_valid and config_valid:
        print(f"\n📊 정의된 상태 수: {len(SRM1_STATE_POLICIES)}")
        print(f"📋 지원 상태들:")

        for i, state in enumerate(get_all_states(), 1):
            policy = get_state_policy(state)
            action_type = policy.get('action_type', 'N/A')
            flow_type = policy.get('conditional_flow', 'N/A')
            transitions = policy.get('transitions', {})

            print(f"  {i}. {state.name}")
            print(f"     • 액션: {action_type}")
            print(f"     • 흐름: {flow_type}")
            print(f"     • 전이: {len(transitions)}개 가능")

            # sequence나 time_based_wait 특수 설정 표시
            if action_type == 'sequence' and 'sequence_config' in policy:
                actions = policy['sequence_config'].get('actions', [])
                print(f"     • 시퀀스: {len(actions)}개 액션")
            if action_type == 'time_based_wait' and 'expected_duration' in policy:
                duration = policy['expected_duration']
                print(f"     • 대기 시간: {duration}초")
            print()

        print("📊 주요 운영 설정:")
        print(f"  • 체크 간격: {SRM1_CONFIG['timing']['check_interval']}초")
        print(f"  • 부활 타임아웃: {SRM1_CONFIG['timing']['recovery_timeout']}초")
        print(f"  • 도주 대기 시간: {SRM1_CONFIG['timing']['flee_wait_min']}초")
        print(f"  • 위험 감지 순서: {SRM1_CONFIG['combat_priorities']['threat_detection_order']}")
        print(f"  • 대상 화면: {SRM1_CONFIG['screen_management']['target_screens']}")
        print(f"  • 우선순위 화면: {SRM1_CONFIG['screen_management']['priority_screens']}")

        print("\n🎯 SM1 패턴 적용 결과:")
        print("  • action_type 4가지로 통일: detect_only, detect_and_click, sequence, time_based_wait")
        print("  • sequence/time_based_wait는 targets=[] (빈 배열)")
        print("  • 실제 동작은 sequence_config, expected_duration에서 정의")
        print("  • SM1과 완전 호환되는 4대 정책 범주 구조")
        print("  • 브릿지에서 빈 targets 방어 로직 처리")

    else:
        print("❌ 설정 또는 정책 검증 실패!")

    print("\n" + "=" * 60)
    print("SRM1 통합 설정 테스트 완료")