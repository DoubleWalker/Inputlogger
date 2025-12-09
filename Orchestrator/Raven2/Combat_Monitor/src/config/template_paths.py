# Orchestrator/Raven2/Combat_Monitor/src/config/template_paths.py
import os

# =============================================================================
# 📁 경로 설정
# =============================================================================

BASE_TEMPLATE_PATH = r"C:\Users\yjy16\template"
RAVEN2_CM_PATH = os.path.join(BASE_TEMPLATE_PATH, "RAVEN2", "Combat_Monitor")

# 화면별 디렉토리
SCREEN_PATHS = {
    'S1': os.path.join(RAVEN2_CM_PATH, "S1"),
    'S2': os.path.join(RAVEN2_CM_PATH, "S2"),
    'S3': os.path.join(RAVEN2_CM_PATH, "S3"),
    'S4': os.path.join(RAVEN2_CM_PATH, "S4"),
    'S5': os.path.join(RAVEN2_CM_PATH, "S5"),
}

# =============================================================================
# 🖼️ 템플릿 정의 (NightCrows 스타일: Screen ID -> Key -> Path)
# =============================================================================

# 팁: 파일명이 _S1.png 등으로 끝나도 상관없습니다. 경로만 맞으면 됩니다.
TEMPLATE_PATHS = {
    'S1': {
        # [Status]
        'AWAKE_TEMPLATE': os.path.join(SCREEN_PATHS['S1'], "awake_S1.png"),
        'ABNORMAL_TEMPLATE': os.path.join(SCREEN_PATHS['S1'], "abnormal_S1.png"),
        'DEAD_TEMPLATE': os.path.join(SCREEN_PATHS['S1'], "dead_S1.png"),

        # [Death]
        'DEATH_RETURN_BUTTON': os.path.join(SCREEN_PATHS['S1'], "return_button_S1.png"),  # death 폴더에 있던 것 이동

        # [Potion]
        'SHOP_UI_TEMPLATE': os.path.join(SCREEN_PATHS['S1'], "shop_ui_S1.png"),
        'BUY_BUTTON_TEMPLATE': os.path.join(SCREEN_PATHS['S1'], "buy_button_S1.png"),
        'CONFIRM_TEMPLATE': os.path.join(SCREEN_PATHS['S1'], "confirm_S1.png"),

        # [Retreat]
        'RETREAT_BUTTON': os.path.join(SCREEN_PATHS['S1'], "retreat_button_S1.png"),
        'RETREAT_CONFIRM_BUTTON': os.path.join(SCREEN_PATHS['S1'], "confirm_button_S1.png"),  # retreat 폴더에 있던 것 이동

        # [Combat]
        'TOWN_UI_TEMPLATE': os.path.join(SCREEN_PATHS['S1'], "template1_S1.png"),  # template1 -> TOWN_UI로 명확화
        'COMBAT_TEMPLATE_2': os.path.join(SCREEN_PATHS['S1'], "template2_S1.png"),
        'COMBAT_SUCCESS': os.path.join(SCREEN_PATHS['S1'], "success_S1.png"),
    },

    'S2': {
        'AWAKE_TEMPLATE': os.path.join(SCREEN_PATHS['S2'], "awake_S2.png"),
        'ABNORMAL_TEMPLATE': os.path.join(SCREEN_PATHS['S2'], "abnormal_S2.png"),
        'DEAD_TEMPLATE': os.path.join(SCREEN_PATHS['S2'], "dead_S2.png"),
        'DEATH_RETURN_BUTTON': os.path.join(SCREEN_PATHS['S2'], "return_button_S2.png"),
        'SHOP_UI_TEMPLATE': os.path.join(SCREEN_PATHS['S2'], "shop_ui_S2.png"),
        'BUY_BUTTON_TEMPLATE': os.path.join(SCREEN_PATHS['S2'], "buy_button_S2.png"),
        'CONFIRM_TEMPLATE': os.path.join(SCREEN_PATHS['S2'], "confirm_S2.png"),
        'RETREAT_BUTTON': os.path.join(SCREEN_PATHS['S2'], "retreat_button_S2.png"),
        'RETREAT_CONFIRM_BUTTON': os.path.join(SCREEN_PATHS['S2'], "confirm_button_S2.png"),
        'TOWN_UI_TEMPLATE': os.path.join(SCREEN_PATHS['S2'], "template1_S2.png"),
        'COMBAT_TEMPLATE_2': os.path.join(SCREEN_PATHS['S2'], "template2_S2.png"),
        'COMBAT_SUCCESS': os.path.join(SCREEN_PATHS['S2'], "success_S2.png"),
    },

    # S3, S4, S5도 동일한 패턴으로 작성...
    # (일단 S1, S2만 예시로 작성했습니다. 나머지도 복사해서 숫자만 바꾸시면 됩니다)
}

# S3~S5 자동 생성 (코드 줄이기 꼼수)
for screen_id in ['S3', 'S4', 'S5']:
    TEMPLATE_PATHS[screen_id] = {
        'AWAKE_TEMPLATE': os.path.join(SCREEN_PATHS[screen_id], f"awake_{screen_id}.png"),
        'ABNORMAL_TEMPLATE': os.path.join(SCREEN_PATHS[screen_id], f"abnormal_{screen_id}.png"),
        'DEAD_TEMPLATE': os.path.join(SCREEN_PATHS[screen_id], f"dead_{screen_id}.png"),
        'DEATH_RETURN_BUTTON': os.path.join(SCREEN_PATHS[screen_id], f"return_button_{screen_id}.png"),
        'SHOP_UI_TEMPLATE': os.path.join(SCREEN_PATHS[screen_id], f"shop_ui_{screen_id}.png"),
        'BUY_BUTTON_TEMPLATE': os.path.join(SCREEN_PATHS[screen_id], f"buy_button_{screen_id}.png"),
        'CONFIRM_TEMPLATE': os.path.join(SCREEN_PATHS[screen_id], f"confirm_{screen_id}.png"),
        'RETREAT_BUTTON': os.path.join(SCREEN_PATHS[screen_id], f"retreat_button_{screen_id}.png"),
        'RETREAT_CONFIRM_BUTTON': os.path.join(SCREEN_PATHS[screen_id], f"confirm_button_{screen_id}.png"),
        'TOWN_UI_TEMPLATE': os.path.join(SCREEN_PATHS[screen_id], f"template1_{screen_id}.png"),
        'COMBAT_TEMPLATE_2': os.path.join(SCREEN_PATHS[screen_id], f"template2_{screen_id}.png"),
        'COMBAT_SUCCESS': os.path.join(SCREEN_PATHS[screen_id], f"success_{screen_id}.png"),
    }


# =============================================================================
# 🔧 헬퍼 함수 (monitor.py에서 사용)
# =============================================================================

def get_template(screen_id: str, template_key: str) -> str:
    """화면 ID와 키로 템플릿 경로 반환"""
    return TEMPLATE_PATHS.get(screen_id, {}).get(template_key)


def verify_template_paths() -> bool:
    """파일 존재 여부 검증"""
    print("SRM2 템플릿 경로 검증 중...")
    all_valid = True
    for screen_id, templates in TEMPLATE_PATHS.items():
        for key, path in templates.items():
            if not os.path.exists(path):
                print(f"❌ [Missing] {screen_id} {key}: {path}")
                all_valid = False
    return all_valid


if __name__ == "__main__":
    verify_template_paths()