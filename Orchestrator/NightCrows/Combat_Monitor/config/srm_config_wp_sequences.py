"""
스크린별 WP(Waypoint) 이동 시퀀스 정의
녹화된 이동 경로를 operation 형식으로 저장
"""
from matplotlib.style.core import context

# S1 WP3 시퀀스 (ARENA)
S1_WP3_ARENA = [
    # 2. 지도 뷰 정렬 (Ctrl + 드래그)
    {'operation': 'key_press_raw', 'key': 'ctrl', 'event': 'press', 'context': 'ARENA'},

    # [수정] 좌표 대신 screen_info의 Key 사용 (또는 숫자로 유지 가능)
    # monitor.py를 수정하지 않으셨다면 아래 숫자 좌표 그대로 사용:
    {'operation': 'mouse_drag', 'button': 'left', 'from_x': 438, 'from_y': 175, 'to_x': 700, 'to_y': 175,
     'duration': 0.5, 'delay_after': 0.2, 'context': 'ARENA'},

    {'operation': 'key_press_raw', 'key': 'ctrl', 'event': 'release', 'delay_after': 0.5, 'context': 'ARENA'},

    # 3. 목적지(점프대) 클릭 - ★ 여기가 핵심 수정 사항 ★
    # x, y 대신 key를 사용하여 screen_info.py의 좌표를 불러옵니다.
    {'operation': 'click_relative', 'key': 'map_marker_reference', 'delay_after': 0.8},
    {'operation': 'click_relative', 'key': 'wp3_jump_point_1', 'delay_after': 0.8, 'context': 'ARENA'},
    {'operation': 'click_relative', 'key': 'wp3_jump_point_2', 'delay_after': 0.5, 'context': 'ARENA'},

    # S1 WP3 시퀀스 (ARENA) - 녹화 데이터 랙 방지 튜닝 버전
    {'operation': 'key_press', 'key': 'm', 'delay_after': 0.5, 'context': 'ARENA'},
    {'operation': 'wait_duration', 'duration': 10.0, 'context': 'ARENA'},
    # =========================================================================

    # [이륙 구간]
    {'operation': 'key_press', 'key': 'space', 'delay_after': 0.3, 'context': 'ARENA'},  # 0.168 -> 0.3 (확실하게)
    {'operation': 'key_press', 'key': 'space', 'delay_after': 0.3, 'context': 'ARENA'},  # 0.152 -> 0.3
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 0.2, 'context': 'ARENA', 'duration': 0.2},  # duration 늘림

    # [상승 기동 1]
    {'operation': 'key_press_raw', 'key': 's', 'event': 'press', 'delay_after': 0.2, 'context': 'ARENA'},
    # 0.152 -> 0.2
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.2, 'context': 'ARENA'},
    # 0.128 -> 0.2
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.4, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 's', 'event': 'release', 'delay_after': 0.8, 'context': 'ARENA'},

    # [활강 및 정지 1]
    {'operation': 'key_press', 'key': 'shift', 'delay_after': 2.0, 'context': 'ARENA'},  # 1.984 -> 2.0

    # [상승 기동 2 - 여기가 랙 취약 구간]
    # Shift 직후 바로 S+Space가 들어가면 씹힐 수 있음 -> delay_after 0.3으로 확보
    {'operation': 'key_press', 'key': 'shift', 'delay_after': 0.3, 'context': 'ARENA'},  # 0.129 -> 0.3 (중요!)

    {'operation': 'key_press_raw', 'key': 's', 'event': 'press', 'delay_after': 0.3, 'context': 'ARENA'},
    # 0.263 -> 0.3
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    # 0.088 -> 0.15
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    # 0.12 -> 0.15
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    # 0.088 -> 0.15
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.2, 'context': 'ARENA'},
    # 0.192 -> 0.2
    {'operation': 'key_press_raw', 'key': 's', 'event': 'release', 'delay_after': 0.9, 'context': 'ARENA'},

    # [활강 및 정지 2]
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 2.0, 'context': 'ARENA', 'duration': 0.15},  # 1.936 -> 2.0

    # [상승 기동 3]
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 0.3, 'context': 'ARENA', 'duration': 0.2},
    # 0.096 -> 0.3 (중요!)
    {'operation': 'key_press_raw', 'key': 's', 'event': 'press', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 's', 'event': 'release', 'delay_after': 0.7, 'context': 'ARENA'},

    # [활강 및 정지 3]
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 2.2, 'context': 'ARENA', 'duration': 0.15},  # 2.113 -> 2.2

    # [상승 기동 4]
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 0.3, 'context': 'ARENA', 'duration': 0.2},  # 0.088 -> 0.3
    {'operation': 'key_press_raw', 'key': 's', 'event': 'press', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 's', 'event': 'release', 'delay_after': 1.1, 'context': 'ARENA'},

    # [활강 및 정지 4]
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 2.1, 'context': 'ARENA', 'duration': 0.15},  # 2.04 -> 2.1

    # [상승 기동 5]
    {'operation': 'key_press_raw', 'key': 's', 'event': 'press', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 's', 'event': 'release', 'delay_after': 0.7, 'context': 'ARENA'},

    # [활강 및 정지 5]
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 2.0, 'context': 'ARENA', 'duration': 0.15},

    # [마지막 전진 비행]
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 0.3, 'context': 'ARENA', 'duration': 0.2},  # 0.08 -> 0.3
    {'operation': 'key_press_raw', 'key': 's', 'event': 'press', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 's', 'event': 'release', 'delay_after': 2.6, 'context': 'ARENA'},

    # [착륙 시퀀스]
    {'operation': 'key_press', 'key': 'space', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press', 'key': 'space', 'delay_after': 2.3, 'context': 'ARENA'},  # 길게 날아가기
    {'operation': 'key_press', 'key': 'space', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press', 'key': 'space', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press', 'key': 'space', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press', 'key': 'space', 'delay_after': 1.3, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 'f', 'delay_after': 0.3, 'context': 'ARENA', 'duration': 0.2},
    {'operation': 'key_hold', 'key': 'q', 'delay_after': 0, 'context': 'ARENA', 'duration': 0.2},

]

# S2 WP3 시퀀스 (ARENA)
S2_WP3_ARENA = [

    # 2. 지도 뷰 정렬 (Ctrl + 드래그)
    {'operation': 'key_press_raw', 'key': 'ctrl', 'event': 'press', 'context': 'ARENA'},

    # [수정] 좌표 대신 screen_info의 Key 사용 (또는 숫자로 유지 가능)
    # monitor.py를 수정하지 않으셨다면 아래 숫자 좌표 그대로 사용:
    {'operation': 'mouse_drag', 'button': 'left', 'from_x': 490, 'from_y': 195, 'to_x': 730, 'to_y': 195,
     'duration': 0.5, 'delay_after': 0.2, 'context': 'ARENA'},

    {'operation': 'key_press_raw', 'key': 'ctrl', 'event': 'release', 'delay_after': 0.5, 'context': 'ARENA'},

    # 3. 목적지(점프대) 클릭 - ★ 여기가 핵심 수정 사항 ★
    # x, y 대신 key를 사용하여 screen_info.py의 좌표를 불러옵니다.
    {'operation': 'click_relative', 'key': 'map_marker_reference', 'delay_after': 0.8},
    {'operation': 'click_relative', 'key': 'wp3_jump_point_1', 'delay_after': 0.8, 'context': 'ARENA'},
    {'operation': 'click_relative', 'key': 'wp3_jump_point_2', 'delay_after': 0.5, 'context': 'ARENA'},

    # 4. 이동 대기
    {'operation': 'key_press', 'key': 'm', 'delay_after': 0.5, 'context': 'ARENA'},
    {'operation': 'wait_duration', 'duration': 10.0, 'context': 'ARENA'},
    # [이륙 구간]
    {'operation': 'key_press', 'key': 'space', 'delay_after': 0.3, 'context': 'ARENA'},  # 0.168 -> 0.3 (확실하게)
    {'operation': 'key_press', 'key': 'space', 'delay_after': 0.3, 'context': 'ARENA'},  # 0.152 -> 0.3
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 0.2, 'context': 'ARENA', 'duration': 0.2},  # duration 늘림

    # [상승 기동 1]
    {'operation': 'key_press_raw', 'key': 's', 'event': 'press', 'delay_after': 0.2, 'context': 'ARENA'},
    # 0.152 -> 0.2
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.2, 'context': 'ARENA'},
    # 0.128 -> 0.2
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.4, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 's', 'event': 'release', 'delay_after': 0.8, 'context': 'ARENA'},

    # [활강 및 정지 1]
    {'operation': 'key_press', 'key': 'shift', 'delay_after': 2.0, 'context': 'ARENA'},  # 1.984 -> 2.0

    # [상승 기동 2 - 여기가 랙 취약 구간]
    # Shift 직후 바로 S+Space가 들어가면 씹힐 수 있음 -> delay_after 0.3으로 확보
    {'operation': 'key_press', 'key': 'shift', 'delay_after': 0.3, 'context': 'ARENA'},  # 0.129 -> 0.3 (중요!)

    {'operation': 'key_press_raw', 'key': 's', 'event': 'press', 'delay_after': 0.3, 'context': 'ARENA'},
    # 0.263 -> 0.3
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    # 0.088 -> 0.15
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    # 0.12 -> 0.15
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    # 0.088 -> 0.15
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.2, 'context': 'ARENA'},
    # 0.192 -> 0.2
    {'operation': 'key_press_raw', 'key': 's', 'event': 'release', 'delay_after': 0.9, 'context': 'ARENA'},

    # [활강 및 정지 2]
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 2.0, 'context': 'ARENA', 'duration': 0.15},  # 1.936 -> 2.0

    # [상승 기동 3]
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 0.3, 'context': 'ARENA', 'duration': 0.2},
    # 0.096 -> 0.3 (중요!)
    {'operation': 'key_press_raw', 'key': 's', 'event': 'press', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 's', 'event': 'release', 'delay_after': 0.7, 'context': 'ARENA'},

    # [활강 및 정지 3]
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 2.2, 'context': 'ARENA', 'duration': 0.15},  # 2.113 -> 2.2

    # [상승 기동 4]
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 0.3, 'context': 'ARENA', 'duration': 0.2},  # 0.088 -> 0.3
    {'operation': 'key_press_raw', 'key': 's', 'event': 'press', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 's', 'event': 'release', 'delay_after': 1.1, 'context': 'ARENA'},

    # [활강 및 정지 4]
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 2.1, 'context': 'ARENA', 'duration': 0.15},  # 2.04 -> 2.1

    # [상승 기동 5]
    {'operation': 'key_press_raw', 'key': 's', 'event': 'press', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 's', 'event': 'release', 'delay_after': 0.7, 'context': 'ARENA'},

    # [활강 및 정지 5]
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 2.0, 'context': 'ARENA', 'duration': 0.15},

    # [마지막 전진 비행]
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 0.3, 'context': 'ARENA', 'duration': 0.2},  # 0.08 -> 0.3
    # 2. 전진 비행 (Space 3회 반복, 3초 간격)
    {'operation': 'key_press', 'key': 'space', 'delay_after': 3.0, 'context': 'ARENA'},
    {'operation': 'key_press', 'key': 'space', 'delay_after': 3.0, 'context': 'ARENA'},
    {'operation': 'key_press', 'key': 'space', 'delay_after': 3.0, 'context': 'ARENA'},

    # =========================================================================
    # 4. [착륙] 사냥 시작
    # =========================================================================
    {'operation': 'wait_duration', 'duration': 1.0, 'context': 'ARENA'},  # 착륙 지점 확인용 대기
    {'operation': 'key_hold', 'key': 'f', 'delay_after': 0.3, 'context': 'ARENA', 'duration': 0.2},  # 날개 접기
    {'operation': 'key_hold', 'key': 'q', 'delay_after': 0, 'context': 'ARENA', 'duration': 0.2},  # 자동사냥

    # 시퀀스 종료 대기
    {'operation': 'wait_duration', 'duration': 1.0, 'context': 'ARENA'},



]

# S3 WP3 시퀀스 (ARENA)
S3_WP3_ARENA = [
    # 2. 지도 뷰 정렬 (Ctrl + 드래그)
    {'operation': 'key_press_raw', 'key': 'ctrl', 'event': 'press', 'context': 'ARENA'},

    # [수정] 좌표 대신 screen_info의 Key 사용 (또는 숫자로 유지 가능)
    # monitor.py를 수정하지 않으셨다면 아래 숫자 좌표 그대로 사용:
    {'operation': 'mouse_drag', 'button': 'left', 'from_x': 438, 'from_y': 175, 'to_x': 700, 'to_y': 175,
     'duration': 0.5, 'delay_after': 0.2, 'context': 'ARENA'},

    {'operation': 'key_press_raw', 'key': 'ctrl', 'event': 'release', 'delay_after': 0.5, 'context': 'ARENA'},

    # 3. 목적지(점프대) 클릭 - ★ 여기가 핵심 수정 사항 ★
    # x, y 대신 key를 사용하여 screen_info.py의 좌표를 불러옵니다.
    {'operation': 'click_relative', 'key': 'map_marker_reference', 'delay_after': 0.8},
    {'operation': 'click_relative', 'key': 'wp3_jump_point_1', 'delay_after': 0.8, 'context': 'ARENA'},
    {'operation': 'click_relative', 'key': 'wp3_jump_point_2', 'delay_after': 0.5, 'context': 'ARENA'},
    # 4. 이동 대기
    {'operation': 'key_press', 'key': 'm', 'delay_after': 0.5, 'context': 'ARENA'},
    {'operation': 'wait_duration', 'duration': 8.0, 'context': 'ARENA'},
    # 1. W 누르기 (떼지 않음)
    {'operation': 'key_press_raw', 'key': 'w', 'event': 'press', 'delay_after': 0.05, 'context': 'ARENA'},

    # 2. A 누르기 (이제 W+A 상태) -> 0.1~0.2초 정도 유지 (이 시간이 이동 거리 결정)
    {'operation': 'key_press_raw', 'key': 'a', 'event': 'press', 'delay_after': 0.6, 'context': 'ARENA'},

    # 3. 키 떼기 (이동 멈춤)
    {'operation': 'key_press_raw', 'key': 'w', 'event': 'release', 'delay_after': 0, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'a', 'event': 'release', 'delay_after': 0.2, 'context': 'ARENA'},
    # [이륙 구간]
    {'operation': 'key_press', 'key': 'space', 'delay_after': 0.3, 'context': 'ARENA'},  # 0.168 -> 0.3 (확실하게)
    {'operation': 'key_press', 'key': 'space', 'delay_after': 0.3, 'context': 'ARENA'},  # 0.152 -> 0.3
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 0.2, 'context': 'ARENA', 'duration': 0.2},  # duration 늘림

    # [상승 기동 1]
    {'operation': 'key_press_raw', 'key': 's', 'event': 'press', 'delay_after': 0.2, 'context': 'ARENA'},
    # 0.152 -> 0.2
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.2, 'context': 'ARENA'},
    # 0.128 -> 0.2
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.4, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 's', 'event': 'release', 'delay_after': 0.8, 'context': 'ARENA'},

    # [활강 및 정지 1]
    {'operation': 'key_press', 'key': 'shift', 'delay_after': 2.0, 'context': 'ARENA'},  # 1.984 -> 2.0

    # [상승 기동 2 - 여기가 랙 취약 구간]
    # Shift 직후 바로 S+Space가 들어가면 씹힐 수 있음 -> delay_after 0.3으로 확보
    {'operation': 'key_press', 'key': 'shift', 'delay_after': 0.3, 'context': 'ARENA'},  # 0.129 -> 0.3 (중요!)

    {'operation': 'key_press_raw', 'key': 's', 'event': 'press', 'delay_after': 0.3, 'context': 'ARENA'},
    # 0.263 -> 0.3
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    # 0.088 -> 0.15
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    # 0.12 -> 0.15
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    # 0.088 -> 0.15
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.2, 'context': 'ARENA'},
    # 0.192 -> 0.2
    {'operation': 'key_press_raw', 'key': 's', 'event': 'release', 'delay_after': 0.9, 'context': 'ARENA'},

    # [활강 및 정지 2]
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 2.0, 'context': 'ARENA', 'duration': 0.15},  # 1.936 -> 2.0

    # [상승 기동 3]
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 0.3, 'context': 'ARENA', 'duration': 0.2},
    # 0.096 -> 0.3 (중요!)
    {'operation': 'key_press_raw', 'key': 's', 'event': 'press', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 's', 'event': 'release', 'delay_after': 0.7, 'context': 'ARENA'},

    # [활강 및 정지 3]
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 2.2, 'context': 'ARENA', 'duration': 0.15},  # 2.113 -> 2.2

    # [상승 기동 4]
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 0.3, 'context': 'ARENA', 'duration': 0.2},  # 0.088 -> 0.3
    {'operation': 'key_press_raw', 'key': 's', 'event': 'press', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 's', 'event': 'release', 'delay_after': 1.1, 'context': 'ARENA'},

    # [활강 및 정지 4]
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 2.1, 'context': 'ARENA', 'duration': 0.15},  # 2.04 -> 2.1

    # [상승 기동 5]
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 0.3, 'context': 'ARENA', 'duration': 0.2},  # 0.088 -> 0.3
    {'operation': 'key_press_raw', 'key': 's', 'event': 'press', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 's', 'event': 'release', 'delay_after': 0.7, 'context': 'ARENA'},

    # [활강 및 정지 5]
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 2.0, 'context': 'ARENA', 'duration': 0.15},

    # [마지막 전진 비행]
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 0.3, 'context': 'ARENA', 'duration': 0.2},  # 0.08 -> 0.3
    {'operation': 'key_press_raw', 'key': 's', 'event': 'press', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 's', 'event': 'release', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.75, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},

    # [착륙 시퀀스]
    {'operation': 'key_press', 'key': 'space', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press', 'key': 'space', 'delay_after': 2.3, 'context': 'ARENA'},  # 길게 날아가기
    {'operation': 'key_press', 'key': 'space', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press', 'key': 'space', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press', 'key': 'space', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press', 'key': 'space', 'delay_after': 1.3, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 'f', 'delay_after': 0.3, 'context': 'ARENA', 'duration': 0.2},
    {'operation': 'key_hold', 'key': 'q', 'delay_after': 0, 'context': 'ARENA', 'duration': 0.2},

]

# S4 WP3 시퀀스 (ARENA)
S4_WP3_ARENA = [
    # 2. 지도 뷰 정렬 (Ctrl + 드래그)
    {'operation': 'key_press_raw', 'key': 'ctrl', 'event': 'press', 'context': 'ARENA'},

    # [수정] 좌표 대신 screen_info의 Key 사용 (또는 숫자로 유지 가능)
    # monitor.py를 수정하지 않으셨다면 아래 숫자 좌표 그대로 사용:
    {'operation': 'mouse_drag', 'button': 'left', 'from_x': 438, 'from_y': 175, 'to_x': 700, 'to_y': 175,
     'duration': 0.5, 'delay_after': 0.2, 'context': 'ARENA'},

    {'operation': 'key_press_raw', 'key': 'ctrl', 'event': 'release', 'delay_after': 0.5, 'context': 'ARENA'},

    # 3. 목적지(점프대) 클릭 - ★ 여기가 핵심 수정 사항 ★
    # x, y 대신 key를 사용하여 screen_info.py의 좌표를 불러옵니다.
    {'operation': 'click_relative', 'key': 'map_marker_reference', 'delay_after': 0.8},
    {'operation': 'click_relative', 'key': 'wp3_jump_point_1', 'delay_after': 0.8, 'context': 'ARENA'},
    {'operation': 'click_relative', 'key': 'wp3_jump_point_2', 'delay_after': 0.5, 'context': 'ARENA'},
    # 4. 이동 대기
    {'operation': 'key_press', 'key': 'm', 'delay_after': 0.5, 'context': 'ARENA'},
    {'operation': 'wait_duration', 'duration': 8.0, 'context': 'ARENA'},
    # 1. W 누르기 (떼지 않음)
    {'operation': 'key_press_raw', 'key': 'w', 'event': 'press', 'delay_after': 0.05, 'context': 'ARENA'},

    # 2. A 누르기 (이제 W+A 상태) -> 0.1~0.2초 정도 유지 (이 시간이 이동 거리 결정)
    {'operation': 'key_press_raw', 'key': 'a', 'event': 'press', 'delay_after': 0.3, 'context': 'ARENA'},

    # 3. 키 떼기 (이동 멈춤)
    {'operation': 'key_press_raw', 'key': 'w', 'event': 'release', 'delay_after': 0, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'a', 'event': 'release', 'delay_after': 0.3, 'context': 'ARENA'},
    # 다음 동작 전 안정화
    # [이륙 구간]
    {'operation': 'key_press', 'key': 'space', 'delay_after': 0.3, 'context': 'ARENA'},  # 0.168 -> 0.3 (확실하게)
    {'operation': 'key_press', 'key': 'space', 'delay_after': 0.3, 'context': 'ARENA'},  # 0.152 -> 0.3
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 0.2, 'context': 'ARENA', 'duration': 0.2},  # duration 늘림

    # [상승 기동 1]
    {'operation': 'key_press_raw', 'key': 's', 'event': 'press', 'delay_after': 0.2, 'context': 'ARENA'},
    # 0.152 -> 0.2
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.2, 'context': 'ARENA'},
    # 0.128 -> 0.2
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.4, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 's', 'event': 'release', 'delay_after': 0.8, 'context': 'ARENA'},

    # [활강 및 정지 1]
    {'operation': 'key_press', 'key': 'shift', 'delay_after': 2.0, 'context': 'ARENA'},  # 1.984 -> 2.0

    # [상승 기동 2 - 여기가 랙 취약 구간]
    # Shift 직후 바로 S+Space가 들어가면 씹힐 수 있음 -> delay_after 0.3으로 확보
    {'operation': 'key_press', 'key': 'shift', 'delay_after': 0.3, 'context': 'ARENA'},  # 0.129 -> 0.3 (중요!)

    {'operation': 'key_press_raw', 'key': 's', 'event': 'press', 'delay_after': 0.3, 'context': 'ARENA'},
    # 0.263 -> 0.3
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    # 0.088 -> 0.15
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    # 0.12 -> 0.15
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    # 0.088 -> 0.15
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.2, 'context': 'ARENA'},
    # 0.192 -> 0.2
    {'operation': 'key_press_raw', 'key': 's', 'event': 'release', 'delay_after': 0.9, 'context': 'ARENA'},

    # [활강 및 정지 2]
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 2.0, 'context': 'ARENA', 'duration': 0.15},  # 1.936 -> 2.0

    # [상승 기동 3]
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 0.3, 'context': 'ARENA', 'duration': 0.2},
    # 0.096 -> 0.3 (중요!)
    {'operation': 'key_press_raw', 'key': 's', 'event': 'press', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 's', 'event': 'release', 'delay_after': 0.7, 'context': 'ARENA'},

    # [활강 및 정지 3]
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 2.2, 'context': 'ARENA', 'duration': 0.15},  # 2.113 -> 2.2

    # [상승 기동 4]
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 0.3, 'context': 'ARENA', 'duration': 0.2},  # 0.088 -> 0.3
    {'operation': 'key_press_raw', 'key': 's', 'event': 'press', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 's', 'event': 'release', 'delay_after': 1.1, 'context': 'ARENA'},

    # [활강 및 정지 4]
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 2.1, 'context': 'ARENA', 'duration': 0.15},  # 2.04 -> 2.1

    # [상승 기동 5]
    {'operation': 'key_press_raw', 'key': 's', 'event': 'press', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 's', 'event': 'release', 'delay_after': 0.7, 'context': 'ARENA'},

    # [활강 및 정지 5]
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 2.0, 'context': 'ARENA', 'duration': 0.15},

    # [마지막 전진 비행]
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 0.3, 'context': 'ARENA', 'duration': 0.2},  # 0.08 -> 0.3
    {'operation': 'key_press_raw', 'key': 's', 'event': 'press', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 's', 'event': 'release', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.75, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.15, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.15, 'context': 'ARENA'},

    # [착륙 시퀀스]
    {'operation': 'key_press', 'key': 'space', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press', 'key': 'space', 'delay_after': 2.3, 'context': 'ARENA'},  # 길게 날아가기
    {'operation': 'key_press', 'key': 'space', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press', 'key': 'space', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press', 'key': 'space', 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'key_press', 'key': 'space', 'delay_after': 1.3, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 'f', 'delay_after': 0.3, 'context': 'ARENA', 'duration': 0.2},
    {'operation': 'key_hold', 'key': 'q', 'delay_after': 0, 'context': 'ARENA', 'duration': 0.2},


]

# S5 WP3 시퀀스 (ARENA)
S5_WP3_ARENA = [
    # 1. 지도 뷰 정렬 (마우스 휠 스크롤 UP)
    # amount: 양수(+)는 UP(줌인), 음수(-)는 DOWN(줌아웃)
    # x, y 좌표를 지정하지 않으면 화면 중앙에서 스크롤하도록 로직을 짤 것입니다.
    {'operation': 'mouse_scroll', 'amount': 1500, 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'mouse_scroll', 'amount': 1500, 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'mouse_scroll', 'amount': 1500, 'delay_after': 0.2, 'context': 'ARENA'},
    {'operation': 'mouse_scroll', 'amount': 1500, 'delay_after': 1.0, 'context': 'ARENA'},  # 마지막엔 충분한 대기

    # 2. 목적지(점프대) 클릭 (S1~S4와 동일하게 사용)
    {'operation': 'click_relative', 'key': 'wp3_jump_point_1', 'delay_after': 0.8, 'context': 'ARENA'},
    {'operation': 'click_relative', 'key': 'wp3_jump_point_2', 'delay_after': 0.5, 'context': 'ARENA'},
    # 3. 이동대기
    {'operation': 'key_press', 'key': 'm', 'delay_after': 0.5, 'context': 'ARENA'},
    {'operation': 'wait_duration', 'duration': 10.0, 'context': 'ARENA'},
    # ========================================================================
    {'operation': 'key_hold', 'key': 'space', 'delay_after': 0.272, 'context': 'ARENA', 'duration': 0.103},
    {'operation': 'key_hold', 'key': 'space', 'delay_after': 0.168, 'context': 'ARENA', 'duration': 0.104},
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 0.08, 'context': 'ARENA', 'duration': 0.112},
    {'operation': 'key_press_raw', 'key': 's', 'event': 'press', 'delay_after': 0.128, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.129, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.216, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 's', 'event': 'release', 'delay_after': 1.024, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 0.696, 'context': 'ARENA', 'duration': 0.152},
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 0.088, 'context': 'ARENA', 'duration': 0.127},
    {'operation': 'key_press_raw', 'key': 's', 'event': 'press', 'delay_after': 0.128, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.112, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.096, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.129, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.096, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.112, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.112, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.104, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.536, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 's', 'event': 'release', 'delay_after': 1.168, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 0.592, 'context': 'ARENA', 'duration': 0.112},
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 0.336, 'context': 'ARENA', 'duration': 0.152},
    {'operation': 'key_press_raw', 'key': 's', 'event': 'press', 'delay_after': 0.176, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.112, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.128, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.08, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.128, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 's', 'event': 'release', 'delay_after': 1.673, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 0.424, 'context': 'ARENA', 'duration': 0.152},
    {'operation': 'key_hold', 'key': 'shift', 'delay_after': 0.528, 'context': 'ARENA', 'duration': 0.168},
    {'operation': 'key_press_raw', 'key': 's', 'event': 'press', 'delay_after': 0.184, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.096, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.112, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.145, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.103, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 's', 'event': 'release', 'delay_after': 0.937, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 'a', 'delay_after': 1.112, 'context': 'ARENA', 'duration': 0.807},
    {'operation': 'key_press_raw', 'key': 's', 'event': 'press', 'delay_after': 0.216, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.129, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.383, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 's', 'event': 'release', 'delay_after': 2.361, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 's', 'event': 'press', 'delay_after': 0.191, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'press', 'delay_after': 0.12, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 'space', 'event': 'release', 'delay_after': 0.304, 'context': 'ARENA'},
    {'operation': 'key_press_raw', 'key': 's', 'event': 'release', 'delay_after': 1.761, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 'a', 'delay_after': 1.376, 'context': 'ARENA', 'duration': 0.2},
    {'operation': 'key_press', 'key': 'f', 'delay_after': 0.264, 'context': 'ARENA'},
    {'operation': 'key_hold', 'key': 'q', 'delay_after': 0, 'context': 'ARENA', 'duration': 0.112},
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