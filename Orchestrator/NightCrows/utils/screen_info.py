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
        'left_menu': (127, 390, 115, 265),
        'right_content': (250, 408, 388, 243)
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
        'main_menu_button': (750, 18),
        'field_return_reset': (535, 327),  #
        'field_return_start': (716, 328),  #
        'graveyard_confirm': (1, 2),  # 실제 좌표 측정 필요
        'field_schedule_button': (688, 212),
        'flight_button':(470,310),
        'field_return_button': (499,311),
        'arena_entry_option1': (508, 186),  # 실제 좌표 측정 필요
        'jump_start_point': (1, 20),  # ← 점프 시작점
        'jump_start_point_up': (1, 10),  # ← 살짝 위 (방향 조정)
        'shop_button': (56, 43),
        'tower_click_1': (711, 66),  #
        'tower_click_2': (724, 185),  #
          #
    },
    'S2': {
        # 기존 좌표 유지
        'main_menu_button': (820, 18),
        'field_return_reset': (571, 359),  #
        'field_return_start': (763, 355),  #
        'graveyard_confirm': (1, 2),  # 실제 좌표 측정 필요
        'field_schedule_button': (750, 224),  #
        'field_return_button':(554,349),
        'flight_button':(515,349),  #
        'shop_button':(51,45),
        'arena_entry_option1': (578, 210),  #
        'tower_click_1': (795, 76),  #
        'tower_click_2': (818, 205),  #
          #
    },
    'S3': {
        # 기존 좌표 유지
        'main_menu_button': (713, 15),
        'field_return_reset': (512, 327),  #
        'field_return_start': (688, 327),  #
        'graveyard_confirm': (1, 2),  # 실제 좌표 측정 필요
        'field_schedule_button': (657, 203),  #
        'flight_button':(467,316),  #
        'field_return_button': (502,308),
        'shop_button': (79, 42),
        # 새로 추가된 좌표 (빈칸)
        'arena_entry_option1': (511, 184),  #
        'tower_click_1': (683, 70),  #
        'tower_click_2': (714, 185),  #
          #
    },
    'S4': {
        # 기존 좌표 유지
        'main_menu_button': (748, 15),
        'field_return_reset': (543, 324),  #
        'field_return_start': (732, 323),  #
        'graveyard_confirm': (1, 2),  #
        'field_schedule_button': (689, 197),  #
        'shop_button': (56, 43),
        'flight_button':(469,311),  #
        'field_return_button': (507,316),
        'arena_entry_option1': (502, 184),  #
        'tower_click_1': (700, 62),  #
        'tower_click_2': (714, 186),  #
          #
    },
    'S5': {
        # 기존 좌표 유지
        'main_menu_button': (1117, 28),
        'field_return_reset': (822, 621),  #
        'field_return_start': (1057, 618),  #
        'graveyard_confirm': (1, 2),  # 실제 좌표 측정 필요
        'field_schedule_button': (1033, 304),  #
        'shop_button': (77, 67),
        'flight_button':(700,596),
        'field_return_button': (750,591),
        'arena_entry_option1': (754, 353),  #
        'tower_click_1': (1084, 98),  #
        'tower_click_2': (1114, 290),  #
          #
    },
}