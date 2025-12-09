# C:/Orchestrator/Raven2/Combat_Monitor/src/config/srm_config_raven2.py
# (v3 - 제너레이터 "상황반장" 아키텍처)

from typing import Callable, Generator, Dict, Any, Optional
from Orchestrator.Raven2.Combat_Monitor.src.models.screen_info import ScreenState

# =============================================================================
# 🎯 1. 상태 정의 (monitor_v1의 ScreenState 계승)
# =============================================================================

# =============================================================================
# 🎯 2. "상황반장" 정책 (monitor_v1.py 로직의 "번역")
# =============================================================================
#
# 각 함수는 '제너레이터'입니다.
# 'yield'를 만나면 '지시서'를 반환하고, 'monitor_v3'가 처리를 완료하고
# 다음 루프에서 'next()'를 호출할 때까지 '일시 정지'합니다.
#
# 'screen' 객체(CombatScreenInfo)는 monitor_v3가 인자로 주입해줍니다.
#
# 참고: 함수가 'return' 하거나 '끝'까지 실행되면 'sequence_complete'로 간주됩니다.
#      만약 'yield'된 지시(예: wait_for_template)가 실패(timeout)하면
#      monitor_v3가 'sequence_failed'로 처리합니다.
#
# =============================================================================

# --- 'detect_only' 상태 (SLEEP, AWAKE) ---
# 이 상태들은 monitor_v3의 check_status()가 처리하므로
# 별도의 제너레이터 정책이 필요 없습니다.
# --- Policy: DEAD (monitor_v1.py의 process_death_recovery 번역) ---
def policy_dead(screen: Any) -> Generator[Dict[str, Any], Any, None]:
    """
    [상황반장: 사망 처리]
    v1의 process_death_recovery 로직을 수행합니다.
    ❗️ [수정] '이중 탐색' 문제를 해결한 견고한 패턴을 사용합니다.
    """
    print(f"INFO: [{screen.window_id}] 상황반장: '사망' 상태 접수. 부활을 시작합니다.")

    # 1. v1의 'return_ui_location' 로직 -> 'wait_for_template' 지시로 번역
    #    (v2에서 추가된 5초 타임아웃을 적용하여 안정성 확보)
    #    ❗️ [수정] 템플릿의 '위치'를 반장(pos)이 기억합니다.
    pos = yield {
        'operation': 'wait_for_template',
        'template_key': 'DEATH_RETURN_BUTTON',
        'timeout': 5.0
    }

    # 2. v1의 'pyautogui.click(return_pos)' 로직 -> 'click_at' 지시로 번역
    #    ❗️ [수정] 템플릿을 '다시 찾는' 비효율적인 'click' 대신,
    #           기억해 둔 'pos' 위치에 'click_at'을 지시합니다.
    #           (monitor.py의 _process_instruction이 pos를 반환해 줌)
    yield {
        'operation': 'click_at',
        'x': pos[0],
        'y': pos[1]
    }

    # 3. v1의 'time.sleep(0.5)' 로직 -> 'wait_duration' 지시로 번역
    #    (클릭 후 UI 반응 시간 대기)
    yield {
        'operation': 'wait_duration',
        'duration': 0.5
    }
    print(f"INFO: [{screen.window_id}] 상황반장: '부활' 지시 완료. 'RECOVERING' 상태로 전환합니다.")

# --- Policy: RECOVERING (monitor_v1.py의 'RECOVERING' 루프 번역) ---
def policy_recovering(screen: Any) -> Generator[Dict[str, Any], Any, None]:
    """
    [상황반장: 부활 중]
    v1의 is_recovered (TOWN_UI)를 60초 타임아웃으로 대기합니다.
    """
    print(f"INFO: [{screen.window_id}] 상황반장: '부활 중'. 마을 UI가 보일 때까지 60초간 대기합니다.")

    # 1. v1의 'is_recovered' (is_in_safe_zone -> template1)를
    #    'retry_count > 60' (60초 타임아웃)으로 대기
    yield {
        'operation': 'wait_for_template',
        'template_key': 'TOWN_UI_TEMPLATE',  # 'combat.template1'
        'timeout': 60.0
    }
    print(f"INFO: [{screen.window_id}] 상황반장: '마을 UI' 감지. 'SAFE_ZONE' 상태로 전환합니다.")


# --- Policy: ABNORMAL (monitor_v1.py의 retreat_to_safe_zone 번역) ---
def policy_abnormal(screen: Any) -> Generator[Dict[str, Any], Any, None]:
    """
    [상황반장: 비정상]
    v1의 retreat_to_safe_zone 로직을 수행합니다.
    """
    print(f"INFO: [{screen.window_id}] 상황반장: '비정상' 상태 접수. 후퇴를 시작합니다.")

    # 1. v1의 'confirm_pos' 템플릿 클릭 (optional=True)
    yield {
        'operation': 'click',
        'template_key': 'RETREAT_CONFIRM_BUTTON',
        'optional': True
    }

    # 2. v1의 'FIXED_UI_COORDS' 고정 좌표 클릭 (optional=True)
    yield {
        'operation': 'click_fixed',
        'coord_key': 'retreat_confirm_button',
        'optional': True
    }

    # 3. v1의 'time.sleep(0.5)' (v2 config에도 존재)
    yield {
        'operation': 'wait_duration',
        'duration': 0.5
    }

    # 4. v1의 'retreat_pos' (후퇴 버튼) 대기 (v2의 5초 타임아웃 적용)
    yield {
        'operation': 'wait_for_template',
        'template_key': 'RETREAT_BUTTON',
        'timeout': 5.0
    }

    # 5. v1의 'retreat_pos' 클릭
    yield {
        'operation': 'click',
        'template_key': 'RETREAT_BUTTON'
    }
    print(f"INFO: [{screen.window_id}] 상황반장: '후퇴' 지시 완료. 'RETREATING' 상태로 전환합니다.")


# --- Policy: RETREATING (monitor_v1.py의 'RETREATING' 루프 번역) ---
def policy_retreating(screen: Any) -> Generator[Dict[str, Any], Any, None]:
    """
    [상황반장: 후퇴 중]
    v1의 is_in_safe_zone (TOWN_UI)를 60초 타임아웃으로 대기합니다.
    (policy_recovering과 로직 동일)
    """
    print(f"INFO: [{screen.window_id}] 상황반장: '후퇴 중'. 마을 UI가 보일 때까지 60초간 대기합니다.")

    # 1. v1의 'is_in_safe_zone' (template1)를
    #    'retry_count > 60' (60초 타임아웃)으로 대기
    yield {
        'operation': 'wait_for_template',
        'template_key': 'TOWN_UI_TEMPLATE',  # 'combat.template1'
        'timeout': 60.0
    }
    print(f"INFO: [{screen.window_id}] 상황반장: '마을 UI' 감지. 'SAFE_ZONE' 상태로 전환합니다.")


# --- Policy: SAFE_ZONE (monitor_v1.py의 replenish_potions 번역) ---
def policy_safe_zone(screen: Any) -> Generator[Dict[str, Any], Any, None]:
    """
    [상황반장: 물약 구매]
    v1의 replenish_potions (단순 시퀀스)를 완벽하게 번역합니다.
    """
    print(f"INFO: [{screen.window_id}] 상황반장: '안전 지대' 도착. 물약 구매를 시작합니다.")

    # 1. time.sleep(2.5)
    yield {'operation': 'wait_duration', 'duration': 2.5}
    # 2. wait_for_ui(shop_ui, 3.0s)
    yield {'operation': 'wait_for_template', 'template_key': 'SHOP_UI_TEMPLATE', 'timeout': 3.0}
    # 3. click(shop_pos)
    yield {'operation': 'click', 'template_key': 'SHOP_UI_TEMPLATE'}
    # 4. time.sleep(1.5)
    yield {'operation': 'wait_duration', 'duration': 1.5}
    # 5. wait_for_ui(buy_button) -> 시간을 5.0초에서 30.0초로 늘리거나, 아예 없앰(무한대기)
    # SRM1은 기본적으로 30초 이상 기다리거나 무한 대기합니다.
    yield {
        'operation': 'wait_for_template',
        'template_key': 'BUY_BUTTON_TEMPLATE',
        'timeout': 30.0  # [수정] 5.0 -> 30.0 (렉 걸려도 충분히 기다림)
    }
    # 6. click(buy_pos)
    yield {'operation': 'click', 'template_key': 'BUY_BUTTON_TEMPLATE'}
    # 7. time.sleep(0.8)
    yield {'operation': 'wait_duration', 'duration': 0.8}
    # 8. wait_for_ui(confirm, 3.0s)
    yield {'operation': 'wait_for_template', 'template_key': 'CONFIRM_TEMPLATE', 'timeout': 3.0}
    # 9. click(confirm_pos)
    yield {'operation': 'click', 'template_key': 'CONFIRM_TEMPLATE'}
    # 10. time.sleep(0.8)
    yield {'operation': 'wait_duration', 'duration': 0.8}
    # 11. keyboard.press_and_release('esc')
    yield {'operation': 'key_press', 'key': 'esc'}
    # 12. time.sleep(1.0)
    yield {'operation': 'wait_duration', 'duration': 1.0}

    print(f"INFO: [{screen.window_id}] 상황반장: '물약 구매' 완료. 'POTIONS_PURCHASED' 상태로 전환합니다.")


# --- Policy: POTIONS_PURCHASED (monitor_v1.py의 return_to_combat 번역) ---
def policy_potions_purchased(screen: Any) -> Generator[Dict[str, Any], Any, None]:
    """
    [상황반장: 사냥터 복귀 1단계]
    v1의 return_to_combat (복잡한 로직)을 번역합니다.
    제너레이터는 'if'문, '계산' 등 모든 파이썬 코드를 실행할 수 있습니다.
    """
    print(f"INFO: [{screen.window_id}] 상황반장: '복귀 시작'. v1의 return_to_combat 로직을 실행합니다.")

    # 1. Template 1 (마을 UI) 클릭
    yield {'operation': 'wait_for_template', 'template_key': 'TOWN_UI_TEMPLATE', 'timeout': 5.0}
    # ❗️ 'click_and_get_pos' 지시: 클릭 후, 해당 좌표를 '반환'받아 pos1에 저장
    pos1 = yield {'operation': 'click_and_get_pos', 'template_key': 'TOWN_UI_TEMPLATE'}

    # 2. 상대 좌표 클릭
    if pos1:  # 'click_and_get_pos'가 성공했을 때만 실행
        relative_click_x = pos1[0] - int(100 * screen.ratio)
        relative_click_y = pos1[1] + int(20 * screen.ratio)
        yield {'operation': 'click_at', 'x': relative_click_x, 'y': relative_click_y}

    # 3. time.sleep(0.8)
    yield {'operation': 'wait_duration', 'duration': 0.8}

    # =========================================================================
    # 4. [수정됨] 드래그 로직 (직접 좌표 지정 방식)
    # =========================================================================

    # 화면별 드래그 좌표 설정 (상대 좌표: 게임화면 좌상단이 0,0 기준)
    # 형식: '화면ID': ((시작X, 시작Y), (끝X, 끝Y))
    drag_config = {
        # 예시값입니다. 본인이 계산한 좌표로 수정해주세요.
        "S1": ((480, 100), (480, 278)),
        "S2": ((507, 70), (507, 274)),
        "S3": ((485, 90), (485, 290)),  # S3만 좌표가 다르면 이렇게 수정
        "S4": ((480, 84), (480, 250)),
        "S5": ((863, 152), (863, 552))
    }

    drag_coords = drag_config.get(screen.window_id)

    if drag_coords:
        # 화면의 현재 위치(좌상단)를 가져옵니다.
        screen_x, screen_y, _, _ = screen.region

        # 상대 좌표를 절대 좌표로 변환 (창이 이동해도 작동하도록)
        start_rel, end_rel = drag_coords

        abs_start_x = screen_x + start_rel[0]
        abs_start_y = screen_y + start_rel[1]
        abs_end_x = screen_x + end_rel[0]
        abs_end_y = screen_y + end_rel[1]

        print(f"INFO: [{screen.window_id}] 드래그 수행: ({abs_start_x}, {abs_start_y}) -> ({abs_end_x}, {abs_end_y})")

        # 드래그 수행
        yield {
            'operation': 'drag',
            'start_x': abs_start_x,
            'start_y': abs_start_y,
            'end_x': abs_end_x,
            'end_y': abs_end_y,
            'duration': 0.5  # 요청하신대로 0.5초 고정
        }
    else:
        print(f"WARN: [{screen.window_id}] 드래그 설정이 없습니다. 스킵합니다.")

    # 5. time.sleep(1.0)
    yield {'operation': 'wait_duration', 'duration': 1.0}

    # 6. 드래그 후 UI 클릭 (v1의 하드코딩된 절대 좌표)
    after_drag_positions = {
        "S1": (606, 109), "S2": (1342, 132), "S3": (607, 480),
        "S4": (604, 797), "S5": (1744, 673)
    }
    target_pos = after_drag_positions.get(screen.window_id)
    if not target_pos:
        print(f"[{screen.window_id}] 드래그 후 UI 절대 좌표 정보를 찾을 수 없음")
        # 실패 처리: 제너레이터를 종료시켜 'sequence_failed' 유도
        raise Exception("after_drag_positions not found")

    yield {'operation': 'click_at', 'x': target_pos[0], 'y': target_pos[1]}

    # 7. time.sleep(0.5)
    yield {'operation': 'wait_duration', 'duration': 0.5}

    # 8. Template 2 찾아서 클릭
    yield {'operation': 'wait_for_template', 'template_key': 'COMBAT_TEMPLATE_2', 'timeout': 3.0}
    pos2 = yield {'operation': 'click_and_get_pos', 'template_key': 'COMBAT_TEMPLATE_2'}

    # 9. time.sleep(0.2)
    yield {'operation': 'wait_duration', 'duration': 0.2}

    # 10. 마지막 상대 이동 후 클릭
    if pos2:
        move_pixels_x = int(265 * screen.ratio)
        move_pixels_y = int(64 * screen.ratio)
        final_x = pos2[0] - move_pixels_x
        final_y = pos2[1] - move_pixels_y
        yield {'operation': 'click_at', 'x': final_x, 'y': final_y}

    # 11. time.sleep(0.2)
    yield {'operation': 'wait_duration', 'duration': 0.2}

    print(f"INFO: [{screen.window_id}] 상황반장: '복귀 1단계' 완료. 'RETURNING_TO_COMBAT' 상태로 전환합니다.")


# --- Policy: RETURNING_TO_COMBAT (monitor_v1.py의 'RETURNING_TO_COMBAT' 루프 번역) ---
def policy_returning_to_combat(screen: Any) -> Generator[Dict[str, Any], Any, None]:
    """
    [상황반장: 사냥터 복귀 2단계]
    v1의 'RETURNING_TO_COMBAT' 루프 (픽셀 체크, 10회 재시도, perform_repeated_combat_return)를
    완벽하게 번역합니다.
    """
    print(f"INFO: [{screen.window_id}] 상황반장: '복귀 2단계' 시작. 10회 내 사냥터 도착을 시도합니다.")

    # 1. v1의 'wait_time = 3.3'
    yield {'operation': 'wait_duration', 'duration': 3.3}

    # 2. v1의 'retry_count > 10' 루프
    for attempt in range(1, 11):  # 1부터 10까지
        print(f"INFO: [{screen.window_id}] 사냥터 도착 확인 시도 ({attempt}/10)")

        # 3. v1의 'is_at_combat_spot' (픽셀 체크 3초 루프)
        # ❗️ 'check_pixel_loop' 지시: 3초간 픽셀 일치 여부 확인 후 bool 반환
        is_at_spot = yield {
            'operation': 'check_pixel_loop',
            'coord_key': 'leader_hp_pixel',
            'color': (108, 69, 71),
            'tolerance': 15,
            'duration': 3.0  # v1의 check_duration
        }

        # 4. 성공 시 제너레이터 종료 (sequence_complete)
        if is_at_spot:
            print(f"INFO: [{screen.window_id}] 상황반장: '사냥터 도착' 확인. 임무 완료.")
            return  # 제너레이터 종료

        # 5. S5는 재시도 안 함
        if screen.window_id == "S5":
            continue

        # 6. v1의 'perform_repeated_combat_return' 로직 (S1-S4)
        print(f"INFO: [{screen.window_id}] 사냥터 미도착. '반복 복귀' 액션 1회 수행.")
        map_ui_activate = {
            "S1": (92, 77), "S2": (791, 86), "S3": (114, 435), "S4": (79, 783)
        }
        target_pos = map_ui_activate.get(screen.window_id)

        if not target_pos:
            print(f"WARN: [{screen.window_id}] Map UI 활성화 좌표 없음.")
            continue

        # 6-1. Map UI 클릭 (하드코딩)
        yield {'operation': 'click_at', 'x': target_pos[0], 'y': target_pos[1]}
        # 6-2. time.sleep(0.6)
        yield {'operation': 'wait_duration', 'duration': 0.6}
        # 6-3. Template 2 대기 및 클릭
        yield {'operation': 'wait_for_template', 'template_key': 'COMBAT_TEMPLATE_2', 'timeout': 4.0}
        pos2 = yield {'operation': 'click_and_get_pos', 'template_key': 'COMBAT_TEMPLATE_2'}
        # 6-4. time.sleep(0.2)
        yield {'operation': 'wait_duration', 'duration': 0.2}

        # 6-5. 상대 이동 후 클릭
        if pos2:
            move_pixels_x = int(277 * screen.ratio)
            move_pixels_y = int(64 * screen.ratio)
            final_x = pos2[0] - move_pixels_x
            final_y = pos2[1] - move_pixels_y
            yield {'operation': 'click_at', 'x': final_x, 'y': final_y}

        # 6-6. time.sleep(0.2)
        yield {'operation': 'wait_duration', 'duration': 0.2}

        # 7. v1의 루프 마지막 'stop_event.wait(timeout=0.5)'
        yield {'operation': 'wait_duration', 'duration': 0.5}

    # 10회 루프를 모두 돌았는데 return하지 못하면 'sequence_failed'
    print(f"WARN: [{screen.window_id}] 상황반장: 10회 시도 후에도 사냥터 도착 실패.")


# =============================================================================
# 🎯 3. 정책 라우터 (Monitor가 "상황반장"을 찾는 함수)
# =============================================================================

# 각 상태와 '상황반장' 함수를 매핑
POLICY_GENERATOR_MAP: Dict[ScreenState, Callable[..., Generator[Dict, Any, None]]] = {
    ScreenState.DEAD: policy_dead,
    ScreenState.RECOVERING: policy_recovering,
    ScreenState.ABNORMAL: policy_abnormal,
    ScreenState.RETREATING: policy_retreating,
    ScreenState.SAFE_ZONE: policy_safe_zone,
    ScreenState.POTIONS_PURCHASED: policy_potions_purchased,
    ScreenState.RETURNING_TO_COMBAT: policy_returning_to_combat,
}


def get_policy_generator(state: ScreenState) -> Optional[Callable[..., Generator[Dict, Any, None]]]:
    """
    CCTV 감시요원(monitor_v3)이 현재 상태에 맞는 '상황반장' 함수를 찾아옵니다.
    """
    return POLICY_GENERATOR_MAP.get(state)


def get_state_policies() -> Dict[ScreenState, Dict[str, Any]]:
    """
    [v3] monitor.py가 요구하는 정책 맵 구조를 반환합니다.

    Returns:
        각 상태별로 다음 구조를 가진 dict:
        {
            'generator': 제너레이터 함수,
            'transitions': {
                'complete': 성공 시 전환될 상태,
                'fail': 실패 시 전환될 상태
            }
        }
    """
    return {
        # DEAD 상태 -> 부활 완료 후 RECOVERING으로
        ScreenState.DEAD: {
            'generator': policy_dead,
            'transitions': {
                'complete': ScreenState.RECOVERING,
                'fail': ScreenState.SLEEP
            }
        },

        # RECOVERING 상태 -> 마을 도착 후 SAFE_ZONE으로
        ScreenState.RECOVERING: {
            'generator': policy_recovering,
            'transitions': {
                'complete': ScreenState.SAFE_ZONE,
                'fail': ScreenState.SLEEP
            }
        },

        # ABNORMAL 상태 -> 후퇴 지시 후 RETREATING으로
        ScreenState.ABNORMAL: {
            'generator': policy_abnormal,
            'transitions': {
                'complete': ScreenState.RETREATING,
                'fail': ScreenState.SLEEP
            }
        },

        # RETREATING 상태 -> 마을 도착 후 SAFE_ZONE으로
        ScreenState.RETREATING: {
            'generator': policy_retreating,
            'transitions': {
                'complete': ScreenState.SAFE_ZONE,
                'fail': ScreenState.SLEEP
            }
        },

        # SAFE_ZONE 상태 -> 물약 구매 후 POTIONS_PURCHASED로
        ScreenState.SAFE_ZONE: {
            'generator': policy_safe_zone,
            'transitions': {
                'complete': ScreenState.POTIONS_PURCHASED,
                # [수정] 실패 시 SLEEP으로 가지 않고, 다시 물약 구매 시도 (또는 ABNORMAL)
                'fail': ScreenState.SAFE_ZONE
            }
        },

        # POTIONS_PURCHASED 상태 -> 복귀 1단계 완료 후 RETURNING_TO_COMBAT으로
        ScreenState.POTIONS_PURCHASED: {
            'generator': policy_potions_purchased,
            'transitions': {
                'complete': ScreenState.RETURNING_TO_COMBAT,
                'fail': ScreenState.SLEEP
            }
        },

        # RETURNING_TO_COMBAT 상태 -> 사냥터 도착 후 AWAKE로
        ScreenState.RETURNING_TO_COMBAT: {
            'generator': policy_returning_to_combat,
            'transitions': {
                'complete': ScreenState.AWAKE,
                'fail': ScreenState.SLEEP
            }
        },
    }


# =============================================================================
# 🔧 유틸리티 함수들
# =============================================================================

def get_initial_state() -> ScreenState:
    """초기 상태를 반환합니다."""
    return ScreenState.SLEEP


# =============================================================================
# 🧪 테스트 및 디버깅
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🎯 Raven2 SRM Config (v3 - 제너레이터 '상황반장' 모델)")
    print("=" * 60)
    print("이 파일은 monitor_v3.py에 의해 'import'되어 사용됩니다.")
    print("monitor_v1.py의 모든 하드코딩된 로직이 '정책 함수'로 번역되었습니다.")
    print("\n[v3 정책 '상황반장' 목록]:")
    for state, func in POLICY_GENERATOR_MAP.items():
        print(f"  - {state.name: <20} -> {func.__name__}")

    print("\n[v3에서 'detect_only'로 처리되는 상태]:")
    print(f"  - {ScreenState.SLEEP.name}")
    print(f"  - {ScreenState.AWAKE.name}")

    print("\n테스트 완료. monitor_v3.py를 실행하여 이 로직을 사용하세요.")