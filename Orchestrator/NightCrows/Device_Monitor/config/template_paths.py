# Orchestrator/NightCrows/System_Monitor/config/template_paths.py

import os

# 중앙 템플릿 베이스 경로
BASE_TEMPLATE_PATH = r"C:\Users\yjy16\template"

# NightCrows > SystemMonitor 템플릿 경로
NIGHTCROWS_SM_PATH = os.path.join(BASE_TEMPLATE_PATH, "NightCrows", "SystemMonitor")

# 화면별 템플릿 디렉토리 (S1~S4만, S5 제외)
SCREEN_TEMPLATE_PATHS = {
    'S1': os.path.join(NIGHTCROWS_SM_PATH, "S1"),
    'S2': os.path.join(NIGHTCROWS_SM_PATH, "S2"),
    'S3': os.path.join(NIGHTCROWS_SM_PATH, "S3"),
    'S4': os.path.join(NIGHTCROWS_SM_PATH, "S4")
    # S5는 PC 네이티브이므로 제외
}

# 화면별 템플릿 정의 (화면 ID를 키로 사용하는 중첩 사전)
TEMPLATES = {
    'S1': {
        # 연결 에러 관련
        'CONNECTION_CONFIRM_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S1'], "connection_confirm.png"),

        # 클라이언트 크래시 관련
        'APP_ICON': os.path.join(SCREEN_TEMPLATE_PATHS['S1'], "app_icon.png"),
        'APP_LOADING_SCREEN': os.path.join(SCREEN_TEMPLATE_PATHS['S1'], "loading_screen.png"),

        # 로그인 관련
        'LOGIN_SCREEN': os.path.join(SCREEN_TEMPLATE_PATHS['S1'], "login_screen.png"),
        'CONNECT_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S1'], "connect_button.png"),

        # 복귀 확인
        'GAME_WORLD_LOADED': os.path.join(SCREEN_TEMPLATE_PATHS['S1'], "world_loaded.png"),
    },

    'S2': {
        # 연결 에러 관련
        'CONNECTION_CONFIRM_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S2'], "connection_confirm.png"),

        # 클라이언트 크래시 관련
        'APP_ICON': os.path.join(SCREEN_TEMPLATE_PATHS['S2'], "app_icon.png"),
        'APP_LOADING_SCREEN': os.path.join(SCREEN_TEMPLATE_PATHS['S2'], "loading_screen.png"),

        # 로그인 관련
        'LOGIN_SCREEN': os.path.join(SCREEN_TEMPLATE_PATHS['S2'], "login_screen.png"),
        'CONNECT_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S2'], "connect_button.png"),

        # 복귀 확인
        'GAME_WORLD_LOADED': os.path.join(SCREEN_TEMPLATE_PATHS['S2'], "world_loaded.png"),
    },

    'S3': {
        # 연결 에러 관련
        'CONNECTION_CONFIRM_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S3'], "connection_confirm.png"),

        # 클라이언트 크래시 관련
        'APP_ICON': os.path.join(SCREEN_TEMPLATE_PATHS['S3'], "app_icon.png"),
        'APP_LOADING_SCREEN': os.path.join(SCREEN_TEMPLATE_PATHS['S3'], "loading_screen.png"),

        # 로그인 관련
        'LOGIN_SCREEN': os.path.join(SCREEN_TEMPLATE_PATHS['S3'], "login_screen.png"),
        'CONNECT_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S3'], "connect_button.png"),

        # 복귀 확인
        'GAME_WORLD_LOADED': os.path.join(SCREEN_TEMPLATE_PATHS['S3'], "world_loaded.png"),
    },

    'S4': {
        # 연결 에러 관련
        'CONNECTION_CONFIRM_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S4'], "connection_confirm.png"),

        # 클라이언트 크래시 관련
        'APP_ICON': os.path.join(SCREEN_TEMPLATE_PATHS['S4'], "app_icon.png"),
        'APP_LOADING_SCREEN': os.path.join(SCREEN_TEMPLATE_PATHS['S4'], "loading_screen.png"),

        # 로그인 관련
        'LOGIN_SCREEN': os.path.join(SCREEN_TEMPLATE_PATHS['S4'], "login_screen.png"),
        'CONNECT_BUTTON': os.path.join(SCREEN_TEMPLATE_PATHS['S4'], "connect_button.png"),

        # 복귀 확인
        'GAME_WORLD_LOADED': os.path.join(SCREEN_TEMPLATE_PATHS['S4'], "world_loaded.png"),
    }
}


def verify_template_paths():
    """모든 화면의 템플릿 경로가 유효한지 확인하고 경고를 출력합니다."""
    missing_templates = []

    for screen_id, templates in TEMPLATES.items():
        for template_name, path in templates.items():
            if not os.path.exists(path):
                missing_templates.append(f"{screen_id}.{template_name}: {path}")

    if missing_templates:
        print("경고: 다음 SM1 템플릿 파일이 존재하지 않습니다:")
        for template in missing_templates:
            print(f"  - {template}")
        print("템플릿 이미지 파일을 해당 경로에 생성하거나 경로를 수정하세요.")
        return False

    print("모든 SM1 템플릿 경로가 유효합니다.")
    return True


def get_template(screen_id: str, template_name: str) -> str:
    """
    특정 화면 ID와 템플릿 이름에 해당하는 템플릿 경로를 반환합니다.

    Args:
        screen_id: 화면 ID ('S1', 'S2', 'S3', 'S4')
        template_name: 템플릿 이름 ('CONNECTION_CONFIRM_BUTTON', 'APP_ICON', ...)

    Returns:
        템플릿 경로 또는 없으면 None
    """
    if screen_id in TEMPLATES and template_name in TEMPLATES[screen_id]:
        return TEMPLATES[screen_id][template_name]

    print(f"경고: SM1 템플릿을 찾을 수 없음 - Screen ID: {screen_id}, Template Name: {template_name}")
    return None


if __name__ == "__main__":
    # 템플릿 경로 유효성 검사 실행 (직접 실행할 때만)
    verify_template_paths()