import sys
import os
import time

# 상대 경로 임포트를 위한 경로 설정 - 단순화
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.append(project_root)

# 직접적인 상대 경로 임포트 사용
from src.core.daily_present import DailyPresent


def main():
    """Daily Present 모듈의 진입점"""
    print("Daily Present 모듈 시작...")

    # 인스턴스 생성
    dp = DailyPresent()

    # 화면 정보 추가 - daily_present.py의 샘플과 동일하게 하려면 S1, S2만 유지
    dp.add_screen(
        screen_id='S1',
        main_event_icon=r"C:\Users\yjy16\template\NightCrows\DP\event_icon_s1.png"
    )

    dp.add_screen(
        screen_id='S2',
        main_event_icon=r"C:\Users\yjy16\template\NightCrows\DP\event_icon_s2.png"
    )

    # daily_present.py와 동일하게 하려면 S3-S5 부분은 제거하거나 주석 처리
    # 만약 5개 화면 모두 필요하다면 그대로 유지
    dp.add_screen(
        screen_id='S3',
        main_event_icon=r"C:\Users\yjy16\template\NightCrows\DP\event_icon_s3.png"
    )

    dp.add_screen(
        screen_id='S4',
        main_event_icon=r"C:\Users\yjy16\template\NightCrows\DP\event_icon_s4.png"
    )

    dp.add_screen(
        screen_id='S5',
        main_event_icon=r"C:\Users\yjy16\template\NightCrows\DP\event_icon_s5.png"
    )

    # Daily Present 실행
    try:
        dp.run()
    except Exception as e:
        print(f"예외 발생: {e}")
    finally:
        print("Daily Present 모듈 종료")


if __name__ == "__main__":
    main()