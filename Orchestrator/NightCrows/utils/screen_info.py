from typing import Dict, Tuple

# 기존 화면 영역 정보
SCREEN_REGIONS: Dict[str, Tuple[int, int, int, int]] = {
    'S1': (0, 0, 766, 346),
    'S2': (770, 0, 840, 378),
    'S3': (0, 350, 767, 343),
    'S4': (0, 697, 767, 343),
    'S5': (770, 394, 1140, 642)
}

# 추가: 이벤트 UI 관련 영역 정보
EVENT_UI_REGIONS: Dict[str, Dict[str, Tuple[int, int, int, int]]] = {
    'S1': {
        'left_menu': (129, 47, 111, 258),    # 왼쪽 20% 정도
        'right_content': (245, 59, 392, 243)  # 나머지 80%
    },
    'S2': {
        'left_menu': (909, 50, 120, 282),
        'right_content': (1040, 64, 426, 266)
    },
    'S3': {
        'left_menu': (127, 393, 107, 261),
        'right_content': (245, 409, 389, 243)
    },
    'S4': {
        'left_menu': (127, 739, 112, 262),
        'right_content': (245, 753, 392, 247)
    },
    'S5': {
        'left_menu': (962, 526, 161, 391),
        'right_content': (1137, 550, 583, 366)
    }
}

# 각 화면별 고정 UI 요소의 상대 좌표 (화면 영역의 좌상단 기준)
FIXED_UI_COORDS = {
    'S1': {
        # 예시: S1 화면 내에서 '三' 버튼의 상대적 (x, y) 좌표
        'main_menu_button': (748, 15)
    },
    'S2': {
        # 예시: S2 화면 내에서 '三' 버튼의 상대적 (x, y) 좌표
        'main_menu_button': (820, 18) # S1과 같거나 다를 수 있음
    },
    'S3': {
        'main_menu_button': (713, 15) # 정확한 좌표 측정 필요
    },
    'S4': {
        'main_menu_button': (748, 15) # 정확한 좌표 측정 필요
    },
    'S5': {
        'main_menu_button': (1117, 28) # 정확한 좌표 측정 필요
    },
}
