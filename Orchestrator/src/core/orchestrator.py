import threading
import time
import schedule
import enum
import queue
import subprocess
import os
import sys
from pathlib import Path

# VDManager가 있는 코어 디렉토리의 부모 (src) 를 경로에 추가 (환경에 따라 조정 필요)
#current_dir = Path(__file__).parent
#src_dir = current_dir.parent
#project_root = src_dir.parent
#sys.path.insert(0, str(src_dir))
#sys.path.insert(0, str(project_root))

try:
    # VDManager 임포트 시도
    from .vd_manager import VDManager, VirtualDesktop
except ImportError:
    print("오류: VDManager를 'core.vd_manager'에서 임포트할 수 없습니다.")
    print("PYTHONPATH 또는 프로젝트 구조를 확인하세요.")
    # 임시 플레이스홀더 (테스트용)
    class VirtualDesktop(enum.Enum):
        VD1 = "VD1"
        VD2 = "VD2"
        OTHER = "OTHER"
    class VDManager:
        def get_current_vd(self): return VirtualDesktop.VD1
        def switch_to(self, target_vd): print(f"Switching to {target_vd.name}")

# --- 플레이스홀더: 실제 컴포넌트 클래스/함수로 대체 필요 ---
class BaseMonitor:
    """모니터 클래스의 기본 구조 (예시)"""
    def __init__(self, monitor_name, event_queue):
        self.monitor_name = monitor_name
        self.event_queue = event_queue
        print(f"Initialized placeholder for {monitor_name}")

    def run_loop(self, stop_event):
        print(f"{self.monitor_name}: Monitoring loop started.")
        while not stop_event.is_set():
            # 실제 모니터링 로직 (이미지 인식 등)
            print(f"{self.monitor_name}: Checking status...")
            # 예시: 문제가 발생하면 이벤트 큐에 넣기
            # if problem_detected:
            #    self.event_queue.put({'source': self.monitor_name, 'event': 'error', 'details': '...'})
            stop_event.wait(10) # 10초마다 체크 (실제 주기에 맞게 조절)
        print(f"{self.monitor_name}: Monitoring loop stopped.")

    def stop(self):
        # 필요한 경우 정리 작업 수행
        print(f"{self.monitor_name}: Stop signal received, cleaning up...")
        pass

# 각 컴포넌트의 main.py 경로 (실제 경로로 수정 필요)
# 프로젝트 루트 디렉토리를 기준으로 경로 설정
COMPONENT_PATHS = {
    "DP1": Path("NightCrows/Daily_Present/main.py"),
    "MO1": Path("NightCrows/Mail_Opener/main.py"),
    "SRM1": Path("NightCrows/Status_Recovery_Monitor/main.py"),
    "SM1": Path("NightCrows/System_Monitor/main.py"),
    "DP2": Path("Raven2/Daily_Present/main.py"),
    "MO2": Path("Raven2/Mail_Opener/main.py"),
    "SRM2": Path("Raven2/Combat_Monitor/monitor.py"),
    "SM2": Path("Raven2/System_Monitor/main.py"),
}

# ---------------------------------------------------------

class ActiveState(enum.Enum):
    MONITORING_VD1 = 1
    MONITORING_VD2 = 2
    EXECUTING_TASK_VD1 = 3
    EXECUTING_TASK_VD2 = 4
    SWITCHING = 5
    IDLE = 0

class Orchestrator:
    def __init__(self, vd1_slice_min=5, vd2_slice_min=5):
        print("Initializing Orchestrator...")
        try:
            self.vd_manager = VDManager()
            print("VDManager initialized.")
        except Exception as e:
            print(f"Failed to initialize VDManager: {e}")
            self.vd_manager = None # Fallback or raise error

        self.active_monitors = {}
        self.current_focus = None
        self.active_state = ActiveState.IDLE
        self.monitor_event_queue = queue.Queue()
        self.vd1_slice_duration = vd1_slice_min * 60
        self.vd2_slice_duration = vd2_slice_min * 60
        self.last_focus_switch_time = time.time()
        self.pending_scheduled_task = None
        self.task_execution_lock = threading.Lock() # 동시 작업 실행 방지

        # --- Initialize Placeholder Components ---
        # 실제 컴포넌트 클래스/모듈로 대체해야 함
        # SM: System Monitor - 미러링된 디바이스/앱의 비정상 상태 감지 및 복구 담당
        self.sm1 = BaseMonitor("SM1", self.monitor_event_queue)
        self.sm2 = BaseMonitor("SM2", self.monitor_event_queue)
        # SRM: Status Recovery Monitor - 게임 내 캐릭터 상태(사망 등) 감지 및 복구 담당
        self.srm1 = BaseMonitor("SRM1", self.monitor_event_queue)
        self.srm2 = BaseMonitor("SRM2", self.monitor_event_queue) # SRM2는 실제 CombatMonitor 사용 가능
        print("Placeholder components initialized.")
        # ---------------------------------------

        self.setup_schedule()

    def setup_schedule(self):
        print("Setting up schedule...")
        # Daily Present (05:00 AM)
        schedule.every().day.at("05:00").do(self.request_scheduled_task, task_key="DP1", target_vd=VirtualDesktop.VD1)
        schedule.every().day.at("05:10").do(self.request_scheduled_task, task_key="DP2", target_vd=VirtualDesktop.VD2) # 10분 텀

        # Mail Opener (12:00 PM / 09:00 PM)
        schedule.every().day.at("12:00").do(self.request_scheduled_task, task_key="MO1", target_vd=VirtualDesktop.VD1)
        schedule.every().day.at("12:05").do(self.request_scheduled_task, task_key="MO2", target_vd=VirtualDesktop.VD2) # 5분 텀
        schedule.every().day.at("21:00").do(self.request_scheduled_task, task_key="MO1", target_vd=VirtualDesktop.VD1)
        schedule.every().day.at("21:05").do(self.request_scheduled_task, task_key="MO2", target_vd=VirtualDesktop.VD2) # 5분 텀

        # ... 다른 예약 작업 추가 ...
        print("Schedule setup complete.")
        print(f"Current scheduled jobs: {len(schedule.get_jobs())}")


    def request_scheduled_task(self, task_key, target_vd):
        """Scheduler가 호출하는 함수. 실제 실행은 메인 루프에 위임."""
        # 이미 다른 작업이 처리 대기 중이면 로그만 남기고 무시 (옵션)
        if self.pending_scheduled_task:
            print(f"Scheduler triggered for {task_key}, but another task is pending. Ignoring for now.")
            return

        print(f"Scheduler triggered: Task '{task_key}' for {target_vd.name} is requested.")
        self.pending_scheduled_task = {'key': task_key, 'vd': target_vd}

    def _start_monitor_thread(self, monitor_key, monitor_instance):
        """모니터 스레드 시작 (중복 실행 방지 포함)"""
        if monitor_key in self.active_monitors and self.active_monitors[monitor_key]['thread'].is_alive():
            # print(f"Monitor {monitor_key} already running.")
            return

        print(f"Starting monitor thread: {monitor_key}")
        stop_event = threading.Event()
        # 실제 모니터 클래스의 run_loop 메서드가 stop_event를 인자로 받도록 구현 필요
        thread = threading.Thread(target=monitor_instance.run_loop, args=(stop_event,), daemon=True)
        self.active_monitors[monitor_key] = {'thread': thread, 'stop_event': stop_event, 'instance': monitor_instance}
        thread.start()

    def _stop_monitor_thread(self, monitor_key):
        """모니터 스레드 중지"""
        if monitor_key in self.active_monitors:
            monitor_info = self.active_monitors[monitor_key]
            thread = monitor_info['thread']
            stop_event = monitor_info['stop_event']
            instance = monitor_info['instance']

            if thread.is_alive():
                print(f"Stopping monitor thread: {monitor_key}")
                stop_event.set() # 스레드에 중지 신호 보내기
                # 실제 모니터 클래스에 stop() 메서드가 있다면 호출 (리소스 정리 등)
                if hasattr(instance, 'stop'):
                    try:
                        instance.stop()
                    except Exception as e:
                        print(f"Error calling stop() for {monitor_key}: {e}")
                thread.join(timeout=10) # 스레드 종료 대기 (최대 10초)
                if thread.is_alive():
                    print(f"Warning: Monitor {monitor_key} did not stop gracefully after 10 seconds.")
            del self.active_monitors[monitor_key] # 목록에서 제거
        # else:
        #     print(f"Monitor {monitor_key} not found or already stopped.")


    def set_focus(self, vd_to_focus, new_state):
        """VD 포커스 설정 및 관련 모니터 관리"""
        # 상태 변화 없으면 종료
        if self.current_focus == vd_to_focus and self.active_state == new_state:
             return

        print(f"--- Setting focus: VD={vd_to_focus.name}, State={new_state.name} ---")
        previous_focus = self.current_focus
        self.active_state = ActiveState.SWITCHING # 전환 중 상태

        # 1. 이전 포커스 VD의 모니터 중지
        if previous_focus:
            if previous_focus == VirtualDesktop.VD1:
                self._stop_monitor_thread('srm1')
                self._stop_monitor_thread('sm1')
            elif previous_focus == VirtualDesktop.VD2:
                self._stop_monitor_thread('srm2')
                self._stop_monitor_thread('sm2')

        # 2. 실제 VD 전환 (필요 시)
        if self.vd_manager:
            current_actual_vd = self.vd_manager.get_current_vd()
            if current_actual_vd != vd_to_focus and vd_to_focus != VirtualDesktop.OTHER:
                print(f"Switching VD from {current_actual_vd.name} to {vd_to_focus.name}")
                self.vd_manager.switch_to(vd_to_focus)
                time.sleep(1.5) # 전환 대기 시간 (넉넉하게)
            else:
                 time.sleep(0.5) # 상태 변경 위한 짧은 대기
        else:
            print("Warning: VDManager not available. Skipping VD switch.")
            time.sleep(1)

        self.current_focus = vd_to_focus # 논리적 포커스 업데이트

        # 3. 새 상태에 따른 모니터 시작
        if new_state == ActiveState.MONITORING_VD1:
             self._start_monitor_thread('srm1', self.srm1)
             self._start_monitor_thread('sm1', self.sm1)
        elif new_state == ActiveState.MONITORING_VD2:
             self._start_monitor_thread('srm2', self.srm2)
             self._start_monitor_thread('sm2', self.sm2)
        # 작업 실행 상태에서는 모니터 시작 안 함

        self.active_state = new_state # 최종 상태 설정
        self.last_focus_switch_time = time.time() # 포커스 변경 시간 기록 (타임 슬라이스용)
        print(f"--- Focus set: VD={self.current_focus.name}, State={self.active_state.name} ---")


    def _execute_task(self, task_info):
        """예약된 작업을 별도 프로세스로 실행"""
        task_key = task_info['key']
        target_vd = task_info['vd']
        task_main_py = COMPONENT_PATHS.get(task_key)

        if not task_main_py or not task_main_py.exists():
            print(f"Error: main.py path not found or invalid for task '{task_key}': {task_main_py}")
            # 작업 실패 시 바로 모니터링 복귀
            new_monitoring_state = ActiveState.MONITORING_VD1 if target_vd == VirtualDesktop.VD1 else ActiveState.MONITORING_VD2
            self.set_focus(target_vd, new_monitoring_state)
            return

        # 작업 실행 중 상태 설정
        task_state = ActiveState.EXECUTING_TASK_VD1 if target_vd == VirtualDesktop.VD1 else ActiveState.EXECUTING_TASK_VD2
        self.active_state = task_state # 상태 변경 (set_focus 없이, 모니터는 이미 멈춘 상태)
        print(f"--- Executing Task: {task_key} on {target_vd.name} ---")
        print(f"Running command: python \"{task_main_py}\"")

        start_time = time.time()
        try:
            # subprocess.run으로 main.py 실행
            # check=True는 오류 발생 시 CalledProcessError 발생시킴
            # capture_output=True 로 표준 출력/오류 캡처 가능 (필요 시)
            process = subprocess.run([sys.executable, str(task_main_py)],
                                     check=True,
                                     capture_output=True,
                                     text=True,
                                     encoding='utf-8', # 또는 'cp949' (Windows 환경 고려)
                                     cwd=task_main_py.parent) # main.py가 있는 디렉토리에서 실행
            print(f"Task '{task_key}' completed successfully.")
            print(f"Output:\n{process.stdout}")
        except FileNotFoundError:
             print(f"Error: Python executable not found at '{sys.executable}'")
        except subprocess.CalledProcessError as e:
            print(f"Error running task '{task_key}': Process returned non-zero exit code {e.returncode}")
            print(f"Stderr:\n{e.stderr}")
            # 알림 로직 추가 가능
            # send_notification(f"Error in {task_key}: {e.stderr}")
        except Exception as e:
            print(f"An unexpected error occurred while running task '{task_key}': {e}")
            import traceback
            traceback.print_exc()
        finally:
            end_time = time.time()
            print(f"Task '{task_key}' finished in {end_time - start_time:.2f} seconds.")
            # 작업 완료 후, 해당 VD 모니터링으로 복귀
            new_monitoring_state = ActiveState.MONITORING_VD1 if target_vd == VirtualDesktop.VD1 else ActiveState.MONITORING_VD2
            # set_focus 를 호출하여 상태 전환 및 모니터 재시작
            self.set_focus(target_vd, new_monitoring_state)


    def run_orchestration_loop(self):
        """메인 오케스트레이션 루프"""
        if not self.vd_manager:
            print("Critical Error: VDManager is not available. Orchestrator cannot run.")
            return

        print("Orchestrator starting main loop...")
        self.pending_scheduled_task = None

        # 초기 상태: VD1 모니터링 시작
        self.set_focus(VirtualDesktop.VD1, ActiveState.MONITORING_VD1)

        while True:
            try:
                # 1. 스케줄 확인 및 실행 요청 설정
                schedule.run_pending() # -> self.request_scheduled_task 호출됨

                # 2. 요청된 예약 작업 처리 (최우선)
                if self.pending_scheduled_task:
                    # 다른 작업이 동시에 실행되지 않도록 lock 사용 (옵션)
                    with self.task_execution_lock:
                        if self.pending_scheduled_task: # lock 획득 후 다시 확인
                            task_info = self.pending_scheduled_task
                            self.pending_scheduled_task = None # 요청 처리 시작, 플래그 초기화

                            # 포커스 설정 및 작업 실행
                            target_vd = task_info['vd']
                            task_state = ActiveState.EXECUTING_TASK_VD1 if target_vd == VirtualDesktop.VD1 else ActiveState.EXECUTING_TASK_VD2
                            self.set_focus(target_vd, task_state)
                            self._execute_task(task_info) # 작업 완료 후 모니터링으로 자동 복귀됨

                            # 작업 완료 후 잠시 대기 (다음 루프에서 바로 타임슬라이스 체크 방지)
                            time.sleep(1)
                            continue # 작업 처리했으므로 타임 슬라이스 체크 건너뜀

                # 3. 시간 분할 로직 (예약 작업 없고 모니터링 중일 때만)
                if self.active_state in [ActiveState.MONITORING_VD1, ActiveState.MONITORING_VD2]:
                    now = time.time()
                    duration_on_current_vd = now - self.last_focus_switch_time
                    switch_needed = False
                    next_vd = None
                    current_slice_duration = 0

                    if self.active_state == ActiveState.MONITORING_VD1:
                        current_slice_duration = self.vd1_slice_duration
                        if duration_on_current_vd > current_slice_duration:
                             switch_needed = True
                             next_vd = VirtualDesktop.VD2
                    elif self.active_state == ActiveState.MONITORING_VD2:
                        current_slice_duration = self.vd2_slice_duration
                        if duration_on_current_vd > current_slice_duration:
                             switch_needed = True
                             next_vd = VirtualDesktop.VD1

                    if switch_needed:
                        print(f"Time slice expired on {self.current_focus.name} after {duration_on_current_vd:.0f}s (limit {current_slice_duration}s).")
                        next_state = ActiveState.MONITORING_VD1 if next_vd == VirtualDesktop.VD1 else ActiveState.MONITORING_VD2
                        self.set_focus(next_vd, next_state)

                # 4. 모니터 이벤트 처리 (필요 시 구현)
                # try:
                #     monitor_event = self.monitor_event_queue.get_nowait()
                #     print(f"Received event from monitor: {monitor_event}")
                #     # 이벤트 처리 로직
                # except queue.Empty:
                #     pass

                time.sleep(1) # 메인 루프 지연 시간

            except KeyboardInterrupt:
                print("KeyboardInterrupt received. Shutting down Orchestrator...")
                break
            except Exception as e:
                print(f"!!! Unhandled exception in main loop: {e} !!!")
                import traceback
                traceback.print_exc()
                # 심각한 오류 시 알림 또는 재시작 로직 고려
                time.sleep(5) # 잠시 대기 후 계속

        self.shutdown()

    def shutdown(self):
        """오케스트레이터 종료 시 정리 작업"""
        print("Shutting down Orchestrator...")
        # 모든 모니터 스레드 중지
        for key in list(self.active_monitors.keys()):
            self._stop_monitor_thread(key)
        # 스케줄러 정리 (필요 시)
        schedule.clear()
        print("Orchestrator shutdown complete.")