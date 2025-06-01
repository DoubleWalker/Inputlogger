# Orchestrator/NightCrows/Combat_Monitor/config/template_paths.py
import os

# 중앙 템플릿 베이스 경로
BASE_TEMPLATE_PATH = r"C:\Users\yjy16\template"

# NightCrows > CombatMonitor 템플릿 경로
NIGHTCROWS_CM_PATH = os.path.join(BASE_TEMPLATE_PATH, "NightCrows", "CombatMonitor")

# 화면별 템플릿 디렉토리 (S1~S5 각각에 대한 하위 폴더 구조 추천)
SCREEN_TEMPLATE_PATHS = {
    'S1': os.path.join(NIGHTCROWS_CM_PATH, "S1"),
    'S2': os.path.join(NIGHTCROWS_CM_PATH, "S2"),
    'S3': os.path.join(NIGHTCROWS_CM_PATH, "S3"),
    'S4': os.path.join(NIGHTCROWS_CM_PATH, "S4"),
    'S5': os.path.join(NIGHTCROWS_CM_PATH, "S5")
}

# 화면별 템플릿 정의 (화면 ID를 키로 사용하는 중첩 사전)
TEMPLATES = {
    'S1': {
        'ARENA': os.path.join(SCREEN_TEMPLATE_PATHS['S1'], "arena_indicator.png"),
        'DEAD': os.path.join(SCREEN_TEMPLATE_PATHS['S1'], "dead_indicator.png"),
        'HOSTILE': os.path.join(SCREEN_TEMPLATE_PATHS['S1'], "hostile_indicator.png"),
        'FLIGHT_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S1'], "flight_button.png"),
        'SHOP_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S1'], "shop_button.png"),
        'PURCHASE_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S1'], "purchase_button.png"),
        'WAYPOINT_1': os.path.join(SCREEN_TEMPLATE_PATHS['S1'], "wp1_reached.png"),
        'WAYPOINT_2': os.path.join(SCREEN_TEMPLATE_PATHS['S1'], "wp2_reached.png"),
        'WAYPOINT_3': os.path.join(SCREEN_TEMPLATE_PATHS['S1'], "wp3_reached.png"),
        'WAYPOINT_4': os.path.join(SCREEN_TEMPLATE_PATHS['S1'], "wp4_reached.png"),
        'WAYPOINT_5': os.path.join(SCREEN_TEMPLATE_PATHS['S1'], "wp5_reached.png"),
        'COMBAT_SPOT': os.path.join(SCREEN_TEMPLATE_PATHS['S1'], "combat_spot.png"),
        'RETURNED': os.path.join(SCREEN_TEMPLATE_PATHS['S1'], "returned_well.png"),
        'PARTY_UI': os.path.join(SCREEN_TEMPLATE_PATHS['S1'], "party_ui.png"),
        'REVIVE_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S1'], "revive_button.png"),
        'GRAVEYARD': os.path.join(SCREEN_TEMPLATE_PATHS['S1'], "graveyard.png"),
        'CONFIRM_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S1'], "confirm_button.png"),
        # 새로 추가된 템플릿 (비어있음)
        'ARENA_MENU_ICON': os.path.join(SCREEN_TEMPLATE_PATHS['S1'], "arena_menu_icon.png"),
        'ARENA_ENTRY_UI': os.path.join(SCREEN_TEMPLATE_PATHS['S1'], "arena_entry_ui.png"),
        'S2': os.path.join(SCREEN_TEMPLATE_PATHS['S1'], "s2.png"),  # 새로 추가: S1이 S2 찾을 때 사용
        'S3': os.path.join(SCREEN_TEMPLATE_PATHS['S1'], "s3.png"),  # 새로 추가: S1이 S3 찾을 때 사용
        'S4': os.path.join(SCREEN_TEMPLATE_PATHS['S1'], "s4.png"),  # 새로 추가: S1이 S4 찾을 때 사용
        'S5': os.path.join(SCREEN_TEMPLATE_PATHS['S1'], "s5.png")  # 새로 추가: S1이 S5 찾을 때 사용
    },
    'S2': {
        'ARENA': os.path.join(SCREEN_TEMPLATE_PATHS['S2'], "arena_indicator.png"),
        'DEAD': os.path.join(SCREEN_TEMPLATE_PATHS['S2'], "dead_indicator.png"),
        'HOSTILE': os.path.join(SCREEN_TEMPLATE_PATHS['S2'], "hostile_indicator.png"),
        'FLIGHT_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S2'], "flight_button.png"),
        # 나머지 템플릿은 S1과 동일한 구조로 추가 필요
        'SHOP_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S2'], "shop_button.png"),
        'PURCHASE_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S2'], "purchase_button.png"),
        'PARTY_UI': os.path.join(SCREEN_TEMPLATE_PATHS['S2'], "party_ui.png"),
        'REVIVE_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S2'], "revive_button.png"),
        'GRAVEYARD': os.path.join(SCREEN_TEMPLATE_PATHS['S2'], "graveyard.png"),
        'WAYPOINT_1': os.path.join(SCREEN_TEMPLATE_PATHS['S2'], "wp1_reached.png"),
        'WAYPOINT_2': os.path.join(SCREEN_TEMPLATE_PATHS['S2'], "wp2_reached.png"),
        'WAYPOINT_3': os.path.join(SCREEN_TEMPLATE_PATHS['S2'], "wp3_reached.png"),
        'WAYPOINT_4': os.path.join(SCREEN_TEMPLATE_PATHS['S2'], "wp4_reached.png"),
        'WAYPOINT_5': os.path.join(SCREEN_TEMPLATE_PATHS['S2'], "wp5_reached.png"),
        'COMBAT_SPOT': os.path.join(SCREEN_TEMPLATE_PATHS['S2'], "combat_spot.png"),
        'CONFIRM_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S2'], "confirm_button.png"),
        'ARENA_MENU_ICON': os.path.join(SCREEN_TEMPLATE_PATHS['S2'], "arena_menu_icon.png"),
        'ARENA_ENTRY_UI': os.path.join(SCREEN_TEMPLATE_PATHS['S2'], "arena_entry_ui.png"),
    },
    'S3': {
        'ARENA': os.path.join(SCREEN_TEMPLATE_PATHS['S3'], "arena_indicator.png"),
        'DEAD': os.path.join(SCREEN_TEMPLATE_PATHS['S3'], "dead_indicator.png"),
        'HOSTILE': os.path.join(SCREEN_TEMPLATE_PATHS['S3'], "hostile_indicator.png"),
        'FLIGHT_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S3'], "flight_button.png"),
        # 나머지 템플릿은 S1과 동일한 구조로 추가 필요
        'SHOP_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S3'], "shop_button.png"),
        'PURCHASE_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S3'], "purchase_button.png"),
        'PARTY_UI': os.path.join(SCREEN_TEMPLATE_PATHS['S3'], "party_ui.png"),
        'REVIVE_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S3'], "revive_button.png"),
        'GRAVEYARD': os.path.join(SCREEN_TEMPLATE_PATHS['S3'], "graveyard.png"),
        'WAYPOINT_1': os.path.join(SCREEN_TEMPLATE_PATHS['S3'], "wp1_reached.png"),
        'WAYPOINT_2': os.path.join(SCREEN_TEMPLATE_PATHS['S3'], "wp2_reached.png"),
        'WAYPOINT_3': os.path.join(SCREEN_TEMPLATE_PATHS['S3'], "wp3_reached.png"),
        'WAYPOINT_4': os.path.join(SCREEN_TEMPLATE_PATHS['S3'], "wp4_reached.png"),
        'WAYPOINT_5': os.path.join(SCREEN_TEMPLATE_PATHS['S3'], "wp5_reached.png"),
        'COMBAT_SPOT': os.path.join(SCREEN_TEMPLATE_PATHS['S3'], "combat_spot.png"),
        'CONFIRM_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S3'], "confirm_button.png"),
        'ARENA_MENU_ICON': os.path.join(SCREEN_TEMPLATE_PATHS['S3'], "arena_menu_icon.png"),
        'ARENA_ENTRY_UI': os.path.join(SCREEN_TEMPLATE_PATHS['S3'], "arena_entry_ui.png"),
    },
    'S4': {
        'ARENA': os.path.join(SCREEN_TEMPLATE_PATHS['S4'], "arena_indicator.png"),
        'DEAD': os.path.join(SCREEN_TEMPLATE_PATHS['S4'], "dead_indicator.png"),
        'HOSTILE': os.path.join(SCREEN_TEMPLATE_PATHS['S4'], "hostile_indicator.png"),
        'FLIGHT_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S4'], "flight_button.png"),
        # 나머지 템플릿은 S1과 동일한 구조로 추가 필요
        'SHOP_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S4'], "shop_button.png"),
        'PURCHASE_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S4'], "purchase_button.png"),
        'PARTY_UI': os.path.join(SCREEN_TEMPLATE_PATHS['S4'], "party_ui.png"),
        'REVIVE_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S4'], "revive_button.png"),
        'GRAVEYARD': os.path.join(SCREEN_TEMPLATE_PATHS['S4'], "graveyard.png"),
        'WAYPOINT_1': os.path.join(SCREEN_TEMPLATE_PATHS['S4'], "wp1_reached.png"),
        'WAYPOINT_2': os.path.join(SCREEN_TEMPLATE_PATHS['S4'], "wp2_reached.png"),
        'WAYPOINT_3': os.path.join(SCREEN_TEMPLATE_PATHS['S4'], "wp3_reached.png"),
        'WAYPOINT_4': os.path.join(SCREEN_TEMPLATE_PATHS['S4'], "wp4_reached.png"),
        'WAYPOINT_5': os.path.join(SCREEN_TEMPLATE_PATHS['S4'], "wp5_reached.png"),
        'COMBAT_SPOT': os.path.join(SCREEN_TEMPLATE_PATHS['S4'], "combat_spot.png"),
        'CONFIRM_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S4'], "confirm_button.png"),
        'ARENA_MENU_ICON': os.path.join(SCREEN_TEMPLATE_PATHS['S4'], "arena_menu_icon.png"),
        'ARENA_ENTRY_UI': os.path.join(SCREEN_TEMPLATE_PATHS['S4'], "arena_entry_ui.png"),
    },
    'S5': {
        'ARENA': os.path.join(SCREEN_TEMPLATE_PATHS['S5'], "arena_indicator.png"),
        'DEAD': os.path.join(SCREEN_TEMPLATE_PATHS['S5'], "dead_indicator.png"),
        'HOSTILE': os.path.join(SCREEN_TEMPLATE_PATHS['S5'], "hostile_indicator.png"),
        'FLIGHT_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S5'], "flight_button.png"),
        # 나머지 템플릿은 S1과 동일한 구조로 추가 필요
        'SHOP_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S5'], "shop_button.png"),
        'PURCHASE_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S5'], "purchase_button.png"),
        'PARTY_UI': os.path.join(SCREEN_TEMPLATE_PATHS['S5'], "party_ui.png"),
        'REVIVE_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S5'], "revive_button.png"),
        'GRAVEYARD': os.path.join(SCREEN_TEMPLATE_PATHS['S5'], "graveyard.png"),
        'WAYPOINT_1': os.path.join(SCREEN_TEMPLATE_PATHS['S5'], "wp1_reached.png"),
        'WAYPOINT_2': os.path.join(SCREEN_TEMPLATE_PATHS['S5'], "wp2_reached.png"),
        'WAYPOINT_3': os.path.join(SCREEN_TEMPLATE_PATHS['S5'], "wp3_reached.png"),
        'WAYPOINT_4': os.path.join(SCREEN_TEMPLATE_PATHS['S5'], "wp4_reached.png"),
        'WAYPOINT_5': os.path.join(SCREEN_TEMPLATE_PATHS['S5'], "wp5_reached.png"),
        'COMBAT_SPOT': os.path.join(SCREEN_TEMPLATE_PATHS['S5'], "combat_spot.png"),
        'CONFIRM_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S5'], "confirm_button.png"),
        'ARENA_MENU_ICON': os.path.join(SCREEN_TEMPLATE_PATHS['S5'], "arena_menu_icon.png"),
        'ARENA_ENTRY_UI': os.path.join(SCREEN_TEMPLATE_PATHS['S5'], "arena_entry_ui.png"),
    }
}

# 편의를 위한 전역 변수 (호환성 유지용)
# 기존 코드에서 이 변수들을 사용하고 있다면 S1의 템플릿을 기본값으로 할 수 있음
ARENA_TEMPLATE = TEMPLATES['S1']['ARENA']
DEAD_TEMPLATE = TEMPLATES['S1']['DEAD']
HOSTILE_TEMPLATE = TEMPLATES['S1']['HOSTILE']


def verify_template_paths():
    """모든 화면의 템플릿 경로가 유효한지 확인하고 경고를 출력합니다."""
    missing_templates = []
    # TEMPLATES 딕셔너리만 검사하면 됨
    for screen_id, templates in TEMPLATES.items():
        for template_name, path in templates.items():
            if not os.path.exists(path):
                missing_templates.append(f"{screen_id}.{template_name}: {path}")

    if missing_templates:
        print("경고: 다음 템플릿 파일이 존재하지 않습니다:")
        for template in missing_templates:
            print(f"  - {template}")
        print("템플릿 이미지 파일을 해당 경로에 생성하거나 경로를 수정하세요.")
        return False
    print("모든 템플릿 경로가 유효합니다.")
    return True


# 특정 화면의 템플릿 경로를 반환하는 헬퍼 함수
def get_template(screen_id, template_name):
    """
    특정 화면 ID와 템플릿 이름에 해당하는 템플릿 경로를 반환합니다.
    :param screen_id: 화면 ID ('S1', 'S2', ...)
    :param template_name: 템플릿 이름 ('ARENA', 'DEAD', 'PARTY_UI', ...)
    :return: 템플릿 경로 또는 없으면 None
    """
    # TEMPLATES 딕셔너리에서 직접 찾음
    if screen_id in TEMPLATES and template_name in TEMPLATES[screen_id]:
        return TEMPLATES[screen_id][template_name]
    print(f"경고: 템플릿을 찾을 수 없음 - Screen ID: {screen_id}, Template Name: {template_name}")
    return None


if __name__ == "__main__":
    # 템플릿 경로 유효성 검사 실행 (직접 실행할 때만)
    verify_template_paths()