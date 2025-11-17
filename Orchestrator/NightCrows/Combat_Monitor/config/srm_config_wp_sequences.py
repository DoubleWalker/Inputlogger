"""
스크린별 WP(Waypoint) 이동 시퀀스 정의
녹화된 이동 경로를 operation 형식으로 저장
"""

# S1 WP3 시퀀스 (ARENA)
S1_WP3_ARENA = [
    # 여기에 변환된 S1 시퀀스 붙여넣기
    # 예시:
    # {'operation': 'key_press', 'key': 'w', 'delay_after': 0.1, 'context': 'ARENA'},
    # {'operation': 'key_hold', 'key': 'w', 'duration': 2.0, 'delay_after': 0.5, 'context': 'ARENA'},
]

# S2 WP3 시퀀스 (ARENA)
S2_WP3_ARENA = [
    # 여기에 변환된 S2 시퀀스 붙여넣기
]

# S3 WP3 시퀀스 (ARENA)
S3_WP3_ARENA = [
    # 여기에 변환된 S3 시퀀스 붙여넣기
]

# S4 WP3 시퀀스 (ARENA)
S4_WP3_ARENA = [
    {'operation': 'key_press_raw', 'key': 'w', 'event': 'press', 'delay_after': 0, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'w', 'event': 'release', 'delay_after': 0, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'w', 'event': 'press', 'delay_after': 0, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'w', 'event': 'release', 'delay_after': 1.879, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'w', 'event': 'press', 'delay_after': 0, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'w', 'event': 'release', 'delay_after': 1.392, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'w', 'event': 'press', 'delay_after': 0, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'w', 'event': 'release', 'delay_after': 1.425, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'w', 'event': 'press', 'delay_after': 0, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'w', 'event': 'release', 'delay_after': 3.664, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 'a', 'duration': 10.977, 'delay_after': 0.104, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 1.024, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.568, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'w', 'event': 'press', 'delay_after': 0, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'w', 'event': 'release', 'delay_after': 0.392, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 'a', 'duration': 1.536, 'delay_after': 0.016, 'context': 'ARENA'},
    {'operation': 'key_press', 'key': 'shift', 'delay_after': 0.192, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.519, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 's', 'duration': 0.993, 'delay_after': 0.641, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 'shift', 'duration': 0.136, 'delay_after': 0.632, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 'shift', 'duration': 0.16, 'delay_after': 1.832, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.608, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.304, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 's', 'duration': 0.888, 'delay_after': 0.136, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 'shift', 'duration': 0.16, 'delay_after': 1.152, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 'shift', 'duration': 0.152, 'delay_after': 1.48, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.648, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 's', 'duration': 0.968, 'delay_after': 0.52, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 'shift', 'duration': 0.168, 'delay_after': 0.936, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 'a', 'duration': 0.103, 'delay_after': 0.752, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 'shift', 'duration': 0.136, 'delay_after': 0.576, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.729, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.304, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.232, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 's', 'duration': 1.041, 'delay_after': 0.12, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 'shift', 'duration': 0.136, 'delay_after': 1.159, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 'shift', 'duration': 0.152, 'delay_after': 1.336, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 1.24, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.233, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 's', 'duration': 0.563, 'delay_after': 0.151, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 'shift', 'duration': 0.152, 'delay_after': 0.752, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 'shift', 'duration': 0.152, 'delay_after': 1.945, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 1.023, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.256, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.168, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 's', 'duration': 0.656, 'delay_after': 0.12, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 'shift', 'duration': 0.152, 'delay_after': 0.985, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 'shift', 'duration': 0.16, 'delay_after': 1.552, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 1.64, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.248, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 's', 'duration': 0.753, 'delay_after': 0.368, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 'shift', 'duration': 0.137, 'delay_after': 0.256, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 'shift', 'duration': 0.128, 'delay_after': 2.224, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.352, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.232, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.208, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 's', 'duration': 0.904, 'delay_after': 0.168, 'context': 'ARENA'},
    {'operation': 'key_press', 'key': 'f', 'delay_after': 2.056, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'd', 'event': 'press', 'delay_after': 0, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'd', 'event': 'release', 'delay_after': 0.888, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'd', 'event': 'press', 'delay_after': 0, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'd', 'event': 'release', 'delay_after': 0.329, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'd', 'event': 'press', 'delay_after': 0, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'd', 'event': 'release', 'delay_after': 0.232, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'd', 'event': 'press', 'delay_after': 0, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'd', 'event': 'release', 'delay_after': 0.256, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 'w', 'duration': 1.408, 'delay_after': 0.416, 'context': 'ARENA'},
    {'operation': 'key_press', 'key': 'q', 'delay_after': 0.335, 'context': 'ARENA'},
]

# S5 WP3 시퀀스 (ARENA)
S5_WP3_ARENA = [
    # 여기에 변환된 S5 시퀀스 붙여넣기
]


def get_wp_sequence(screen_id: str, wp_name: str = 'wp3', context: str = 'ARENA'):
    """
    스크린별 WP 시퀀스 반환

    Args:
        screen_id: 화면 ID (S1~S5)
        wp_name: 웨이포인트 이름 (현재는 wp3만 사용)
        context: 컨텍스트 (ARENA 또는 FIELD)

    Returns:
        list: operation 리스트, 없으면 빈 리스트
    """
    key = f"{screen_id.upper()}_WP3_{context.upper()}"

    sequences = {
        'S1_WP3_ARENA': S1_WP3_ARENA,
        'S2_WP3_ARENA': S2_WP3_ARENA,
        'S3_WP3_ARENA': S3_WP3_ARENA,
        'S4_WP3_ARENA': S4_WP3_ARENA,
        'S5_WP3_ARENA': S5_WP3_ARENA,
    }

    sequence = sequences.get(key, [])

    if not sequence:
        print(f"WARN: WP sequence not found for key '{key}'")

    return sequence