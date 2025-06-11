from typing import Dict, Tuple

# 기존 화면 영역 정보
SCREEN_REGIONS: Dict[str, Tuple[int, int, int, int]] = {
    'S1': (0, 0, 706, 332),
    'S2': (706, 0, 740, 342),
    'S3': (0, 353, 704, 324),
    'S4': (0, 700, 705, 338),
    'S5': (706, 362, 1210, 660)
}

# 추가: 이벤트 UI 관련 영역 정보
EVENT_UI_REGIONS: Dict[str, Dict[str, Tuple[int, int, int, int]]] = {
    'S1': {
        'left_menu': (70, 30, 128, 258),    # 왼쪽 20% 정도
        'right_content': (210, 72, 409, 211)  # 나머지 80%
    },
    'S2': {
        'left_menu': (779, 35, 132, 265),
        'right_content': (924, 75, 434, 220)
    },
    'S3': {
        'left_menu': (70, 376, 125, 253),
        'right_content': (210, 416, 409, 214)
    },
    'S4': {
        'left_menu': (70, 732, 125, 251),
        'right_content': (210, 767, 411, 213)
    },
    'S5': {
        'left_menu': (852, 466, 208, 408),
        'right_content': (1078, 535, 669, 341)
    }
}

# 각 화면별 고정 UI 요소의 상대 좌표 (화면 영역의 좌상단 기준)
FIXED_UI_COORDS = {
    'S1': {
        'main_menu_button': (657, 24),
        'retreat_confirm_button': (350, 283),
        'leader_hp_pixel': (132, 124),
        'unlock_button':(1,1)# S1 리더 HP 바 확인 픽셀 상대 좌표
    },
    'S2': {
        'main_menu_button': (720, 28),
        'retreat_confirm_button': (375, 298),
        'leader_hp_pixel': (125, 130),
        'unlock_button':(1,1) # S2 리더 HP 바 확인 픽셀 상대 좌표
    },
    'S3': {
        'main_menu_button': (680, 20),
        'retreat_confirm_button': (350, 285),
        'leader_hp_pixel': (117, 126),
        'unlock_button':(1,1) # S3 리더 HP 바 확인 픽셀 상대 좌표
    },
    'S4': {
        'main_menu_button': (680, 20),
        'retreat_confirm_button': (350, 283),
        'leader_hp_pixel': (113, 121),
        'unlock_button':(1,1) # S4 리더 HP 바 확인 픽셀 상대 좌표
    },
    'S5': {
        'main_menu_button': (1172, 27),
        'retreat_confirm_button': (607, 520),
        'unlock_button':(1,1) # 정확한 좌표 측정 필요
    },
}
