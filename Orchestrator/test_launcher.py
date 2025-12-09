import sys
import os
import time
from pathlib import Path

# 프로젝트 루트 경로 설정 (import 문제 해결)
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

from Orchestrator.src.core.orchestrator import Orchestrator


def countdown(seconds=5):
    """실행 전 카운트다운"""
    print(f"\n⏳ {seconds}초 후에 시작합니다! (중단하려면 Ctrl+C)")
    try:
        for i in range(seconds, 0, -1):
            print(f"   {i}...")
            time.sleep(1)
        print("🚀 시작!\n")
    except KeyboardInterrupt:
        print("\n⛔ 카운트다운 중단됨.")
        raise  # 메인 루프에서 처리하도록 예외 다시 던짐


def print_menu():
    print("\n" + "=" * 40)
    print(" 🛠️  Orchestrator Development Launcher")
    print("=" * 40)
    print("1. [Main] 정상 실행 (NC -> Raven2)")
    print("2. [Test] Raven2 (VD2) 즉시 시작")
    print("3. [Test] NightCrows (VD1) 즉시 시작")
    print("4. [Test] SM2 (Raven2 시스템 모니터) 단독 테스트")
    print("5. [Test] MO2 (Raven2 우편) 단독 테스트")
    print("0. 종료")
    print("=" * 40)


def run_orchestrator(start_vd="VD1"):
    try:
        # 타임 슬라이스를 짧게 설정하여 테스트 용이하게 (예: 60분)
        # 실제 테스트시는 길게 해도 됨, 어차피 강제 전환 기능이 있으므로
        orchestrator = Orchestrator(vd1_slice_min=60, vd2_slice_min=60)
        orchestrator.run_orchestration_loop(start_vd=start_vd)
    except KeyboardInterrupt:
        print("\n중단됨.")
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'orchestrator' in locals() and orchestrator:
            orchestrator.shutdown()


def test_sm2_standalone():
    """SM2만 떼어내서 복구 로직 테스트"""
    print("\n>>> SM2 (Raven2 System Monitor) 단독 테스트 모드 <<<")
    # ... (생략) ...

    # 가짜 Orchestrator (IO 스케줄러만 빌려옴)
    from Orchestrator.src.core.io_scheduler import IOScheduler
    # [추가] 스크린샷 기능을 위해 필요
    import pyautogui
    from Orchestrator.Raven2.utils.screen_info import SCREEN_REGIONS

    class MockOrchestrator:
        def __init__(self):
            self.io_scheduler = IOScheduler()
            self.scheduler_stop_event = threading.Event()
            self.io_scheduler.start(self.scheduler_stop_event)

        def report_system_error(self, monitor_id, screen_id):
            print(f"[Mock] System Error Reported: {monitor_id} - {screen_id}")
            return False  # False Positive 아님

        # 🟢 [추가] 이 메소드가 없어서 에러가 났던 것입니다.
        def capture_screen_safely(self, screen_id):
            """SystemMonitor가 요청하는 스크린샷 기능을 가짜로 제공"""
            if screen_id in SCREEN_REGIONS:
                region = SCREEN_REGIONS[screen_id]
                return pyautogui.screenshot(region=region)
            else:
                print(f"[Mock] Unknown Screen ID for capture: {screen_id}")
                return None

        def shutdown(self):
            if self.scheduler_stop_event:
                self.scheduler_stop_event.set()

    try:
        from Orchestrator.Raven2.System_Monitor.src.core.monitor import SystemMonitor
        import threading

        # 가짜 스케줄러용 Stop Event
        stop_event = threading.Event()

        mock_orch = MockOrchestrator()
        sm2 = SystemMonitor("SM2_Test", "VD2", orchestrator=mock_orch)

        # SM2 루프 실행
        sm2.run_loop(stop_event)

    except ImportError:
        print("SM2 모듈을 찾을 수 없습니다.")
    except KeyboardInterrupt:
        print("SM2 테스트 중단.")


def main():
    while True:
        print_menu()
        choice = input("선택 >> ")

        try:
            if choice == '1':
                countdown(5)
                run_orchestrator(start_vd="VD1")
            elif choice == '2':
                countdown(5)
                run_orchestrator(start_vd="VD2")
            elif choice == '3':
                countdown(5)
                run_orchestrator(start_vd="VD1")
            elif choice == '4':
                countdown(5)
                test_sm2_standalone()
            elif choice == '5':
                countdown(5)
                # MO2 main.py 실행
                mo2_path = current_dir / "Orchestrator/Raven2/Mail_opener/main.py"
                os.system(f'python "{mo2_path}"')
            elif choice == '0':
                print("종료합니다.")
                break
            else:
                print("잘못된 선택입니다.")
        except KeyboardInterrupt:
            print("\n메인 메뉴로 돌아갑니다.")
            continue


if __name__ == "__main__":
    main()