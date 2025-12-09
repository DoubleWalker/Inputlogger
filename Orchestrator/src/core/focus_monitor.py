import threading
import time
import win32gui
import win32process


class FocusMonitor:
    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = None
        self._last_hwnd = None
        self._last_title = ""
        # 창 제목을 보고 S1, S2 등을 식별하기 위한 매핑 (필요시 설정)
        self.window_mapping = {
            "NightCrows": "NC_Client",  # 예시
            # "게임창제목1": "S1",
            # "게임창제목2": "S2",
        }

    def start(self):
        """감시 시작"""
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._thread.start()
            print("INFO: [FocusMonitor] Started tracking active window.")

    def stop(self):
        """감시 종료"""
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join(timeout=2.0)
            print("INFO: [FocusMonitor] Stopped.")

    def _monitor_loop(self):
        while not self._stop_event.is_set():
            try:
                # 1. 현재 활성 창 핸들(HWND) 가져오기
                current_hwnd = win32gui.GetForegroundWindow()

                # 2. 포커스가 바뀌었는지 확인
                if current_hwnd != self._last_hwnd:
                    # 창 제목 가져오기
                    title = win32gui.GetWindowText(current_hwnd)

                    # (선택) 프로세스 ID 가져오기
                    # _, pid = win32process.GetWindowThreadProcessId(current_hwnd)

                    # 로그 출력 (식별하기 쉽게 매핑된 이름이 있으면 사용)
                    # 예: "[Focus Changed] Old: S1 -> New: Chrome"
                    #print(f"👀 [Focus Changed] '{self._last_title}' -> '{title}' (HWND: {current_hwnd})") <<< "나중에 살리기!!"

                    self._last_hwnd = current_hwnd
                    self._last_title = title

                time.sleep(0.2)  # 0.2초마다 체크 (부하 거의 없음)

            except Exception as e:
                print(f"WARN: [FocusMonitor] Error: {e}")
                time.sleep(1)