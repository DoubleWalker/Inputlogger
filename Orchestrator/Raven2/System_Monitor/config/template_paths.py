# Orchestrator/Raven2/System_Monitor/config/template_paths.py
"""
SM2 템플릿 경로 정의
- SM2에서 사용하는 모든 템플릿 이미지 경로
- 화면별(S1~S4) 템플릿 조직화
- 템플릿 유효성 검사 기능 포함
"""

import os

# =============================================================================
# 📁 중앙 템플릿 베이스 경로
# =============================================================================

BASE_TEMPLATE_PATH = r"C:\Users\yjy16\template"

# Raven2 > SystemMonitor 템플릿 경로
RAVEN2_SM_PATH = os.path.join(BASE_TEMPLATE_PATH, "RAVEN2", "SystemMonitor")

# =============================================================================
# 📁 화면별 템플릿 디렉토리 (S1~S4만, S5 제외)
# =============================================================================

SCREEN_TEMPLATE_PATHS = {
    'S1': os.path.join(RAVEN2_SM_PATH, "S1"),
    'S2': os.path.join(RAVEN2_SM_PATH, "S2"),
    'S3': os.path.join(RAVEN2_SM_PATH, "S3"),
    'S4': os.path.join(RAVEN2_SM_PATH, "S4")
    # S5는 PC 네이티브이므로 SM2에서 제외
}

# =============================================================================
# 🖼️ 화면별 템플릿 정의 (화면 ID를 키로 사용하는 중첩 사전)
# =============================================================================

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


# =============================================================================
# 🔍 템플릿 접근 헬퍼 함수
# =============================================================================

def get_template(screen_id: str, template_name: str) -> str:
    """특정 화면의 템플릿 경로를 반환합니다."""
    if screen_id not in TEMPLATES:
        raise ValueError(f"지원하지 않는 화면 ID: {screen_id}")

    if template_name not in TEMPLATES[screen_id]:
        raise ValueError(f"{screen_id}에서 지원하지 않는 템플릿: {template_name}")

    return TEMPLATES[screen_id][template_name]


def get_all_templates_for_screen(screen_id: str) -> dict:
    """특정 화면의 모든 템플릿을 반환합니다."""
    if screen_id not in TEMPLATES:
        raise ValueError(f"지원하지 않는 화면 ID: {screen_id}")

    return TEMPLATES[screen_id].copy()


def get_supported_screens() -> list:
    """지원하는 모든 화면 ID 목록을 반환합니다."""
    return list(TEMPLATES.keys())


# =============================================================================
# ✅ 템플릿 유효성 검증
# =============================================================================

def verify_template_paths() -> bool:
    """모든 템플릿 파일이 존재하는지 검증합니다."""
    print("SM2 템플릿 파일 존재 여부 검증 중...")

    missing_files = []
    total_files = 0

    for screen_id, templates in TEMPLATES.items():
        print(f"  화면 {screen_id} 검증 중...")

        for template_name, template_path in templates.items():
            total_files += 1
            if not os.path.exists(template_path):
                missing_files.append(f"{screen_id}/{template_name}: {template_path}")
                print(f"    ❌ {template_name}: 파일 없음")
            else:
                print(f"    ✅ {template_name}: 존재함")

    if missing_files:
        print(f"\n❌ {len(missing_files)}개 템플릿 파일이 누락되었습니다:")
        for missing in missing_files:
            print(f"  - {missing}")
        print(f"\n📁 필요한 디렉토리 구조:")
        print(f"  {BASE_TEMPLATE_PATH}/")
        print(f"  └── RAVEN2/")
        print(f"      └── SystemMonitor/")
        print(f"          ├── S1/")
        print(f"          ├── S2/")
        print(f"          ├── S3/")
        print(f"          └── S4/")
        return False

    print(f"\n✅ 모든 템플릿 파일이 존재합니다! (총 {total_files}개)")
    return True


def create_template_directories():
    """템플릿 디렉토리 구조를 생성합니다."""
    print("SM2 템플릿 디렉토리 구조 생성 중...")

    # 베이스 디렉토리 생성
    os.makedirs(RAVEN2_SM_PATH, exist_ok=True)
    print(f"✅ 베이스 디렉토리 생성: {RAVEN2_SM_PATH}")

    # 화면별 디렉토리 생성
    for screen_id, screen_path in SCREEN_TEMPLATE_PATHS.items():
        os.makedirs(screen_path, exist_ok=True)
        print(f"✅ {screen_id} 디렉토리 생성: {screen_path}")

    print("\n📁 생성된 디렉토리 구조:")
    print(f"  {RAVEN2_SM_PATH}/")
    for screen_id in SCREEN_TEMPLATE_PATHS.keys():
        print(f"  ├── {screen_id}/")

    print("\n📝 필요한 템플릿 파일들:")
    for screen_id in get_supported_screens():
        print(f"  {screen_id}:")
        templates = get_all_templates_for_screen(screen_id)
        for template_name in templates.keys():
            print(f"    - {template_name}")


# =============================================================================
# 🧪 테스트 함수
# =============================================================================

def test_template_system():
    """템플릿 시스템 테스트"""
    print("=" * 60)
    print("SM2 템플릿 시스템 테스트")
    print("=" * 60)

    print(f"📁 베이스 경로: {BASE_TEMPLATE_PATH}")
    print(f"📁 SM2 경로: {RAVEN2_SM_PATH}")
    print(f"🖼️  지원 화면: {get_supported_screens()}")
    print()

    # 디렉토리 구조 생성
    create_template_directories()
    print()

    # 파일 존재 여부 검증
    verify_template_paths()

    print("\n" + "=" * 60)
    print("SM2 템플릿 시스템 테스트 완료")


if __name__ == "__main__":
    test_template_system()