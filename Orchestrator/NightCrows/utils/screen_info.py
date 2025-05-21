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
        'left_menu': (129, 47, 111, 258),  # 왼쪽 20% 정도
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
        # 기존 좌표 유지
        'main_menu_button': (748, 15),
        'retry_confirm': (2, 2),  # 실제 좌표 측정 필요
        'retry_close': (1, 2),  # 실제 좌표 측정 필요
        'graveyard_confirm': (1, 2),  # 실제 좌표 측정 필요
        'field_schedule_button': (300, 150),  # 실제 좌표로 수정 필요
        # 새로 추가된 좌표 (빈칸)
        'arena_entry_option1': (0, 0),  # 실제 좌표 측정 필요
        'tower_click_1': (0, 0),  # 실제 좌표 측정 필요
        'tower_click_2': (0, 0),  # 실제 좌표 측정 필요
        'tower_click_3': (0, 0),  # 실제 좌표 측정 필요
    },
    'S2': {
        # 기존 좌표 유지
        'main_menu_button': (820, 18),
        'retry_confirm': (1, 1),  # 실제 좌표 측정 필요
        'retry_close': (1, 1),  # 실제 좌표 측정 필요
        'graveyard_confirm': (1, 2),  # 실제 좌표 측정 필요
        'field_schedule_button': (300, 150),  # 실제 좌표로 수정 필요
        # 새로 추가된 좌표 (빈칸)
        'arena_entry_option1': (0, 0),  # 실제 좌표 측정 필요
        'tower_click_1': (0, 0),  # 실제 좌표 측정 필요
        'tower_click_2': (0, 0),  # 실제 좌표 측정 필요
        'tower_click_3': (0, 0),  # 실제 좌표 측정 필요
    },
    'S3': {
        # 기존 좌표 유지
        'main_menu_button': (713, 15),
        'retry_confirm': (1, 1),  # 실제 좌표 측정 필요
        'retry_close': (1, 1),  # 실제 좌표 측정 필요
        'graveyard_confirm': (1, 2),  # 실제 좌표 측정 필요
        'field_schedule_button': (300, 150),  # 실제 좌표로 수정 필요
        # 새로 추가된 좌표 (빈칸)
        'arena_entry_option1': (0, 0),  # 실제 좌표 측정 필요
        'tower_click_1': (0, 0),  # 실제 좌표 측정 필요
        'tower_click_2': (0, 0),  # 실제 좌표 측정 필요
        'tower_click_3': (0, 0),  # 실제 좌표 측정 필요
    },
    'S4': {
        # 기존 좌표 유지
        'main_menu_button': (748, 15),
        'retry_confirm': (1, 1),  # 실제 좌표 측정 필요
        'retry_close': (1, 1),  # 실제 좌표 측정 필요
        'graveyard_confirm': (1, 2),  # 실제 좌표 측정 필요
        'field_schedule_button': (300, 150),  # 실제 좌표로 수정 필요
        # 새로 추가된 좌표 (빈칸)
        'arena_entry_option1': (0, 0),  # 실제 좌표 측정 필요
        'tower_click_1': (0, 0),  # 실제 좌표 측정 필요
        'tower_click_2': (0, 0),  # 실제 좌표 측정 필요
        'tower_click_3': (0, 0),  # 실제 좌표 측정 필요
    },
    'S5': {
        # 기존 좌표 유지
        'main_menu_button': (1117, 28),
        'retry_confirm': (2, 2),  # 실제 좌표 측정 필요
        'retry_close': (0, 1),  # 실제 좌표 측정 필요
        'graveyard_confirm': (1, 2),  # 실제 좌표 측정 필요
        'field_schedule_button': (300, 150),  # 실제 좌표로 수정 필요
        # 새로 추가된 좌표 (빈칸)
        'arena_entry_option1': (0, 0),  # 실제 좌표 측정 필요
        'tower_click_1': (0, 0),  # 실제 좌표 측정 필요
        'tower_click_2': (0, 0),  # 실제 좌표 측정 필요
        'tower_click_3': (0, 0),  # 실제 좌표 측정 필요
    },
}