import threading
import time
from operator import truediv

import schedule
import enum
import queue
import subprocess
import numpy as np
import sys
from pathlib import Path
import pyautogui
import os
from .io_scheduler import IOScheduler, Priority
# [수정] Raven2용 ScreenState 추가 (별칭 사용)
from Orchestrator.NightCrows.Combat_Monitor.config.srm_config import ScreenState as NC_ScreenState
from Orchestrator.Raven2.Combat_Monitor.src.models.screen_info import ScreenState as R2_ScreenState
from .focus_monitor import FocusMonitor

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

# 실제 SRM 컴포넌트 임포트
try:
    from Orchestrator.NightCrows.Combat_Monitor.monitor import CombatMonitor as NightCrowsCombatMonitor

    print("INFO: Successfully imported NightCrows CombatMonitor (SRM1)")
except ImportError as e:
    print(f"ERROR: Failed to import NightCrows CombatMonitor: {e}")
    NightCrowsCombatMonitor = None

try:
    from Orchestrator.Raven2.Combat_Monitor.src.monitor import CombatMonitor as Raven2CombatMonitor

    print("INFO: Successfully imported Raven2 CombatMonitor (SRM2)")
except ImportError as e:
    print(f"ERROR: Failed to import Raven2 CombatMonitor: {e}")
    Raven2CombatMonitor = None

# SystemMonitor 컴포넌트 임포트 추가
try:
    from Orchestrator.NightCrows.System_Monitor.src.core.monitor import create_system_monitor

    print("INFO: Successfully imported NightCrows SystemMonitor (SM1)")
except ImportError as e:
    print(f"ERROR: Failed to import NightCrows SystemMonitor: {e}")
    create_system_monitor = None

try:
    from Orchestrator.Raven2.System_Monitor.src.core.monitor import \
        create_system_monitor as create_system_monitor_raven2

    print("INFO: Successfully imported Raven2 SystemMonitor (SM2)")
except ImportError as e:
    print(f"ERROR: Failed to import Raven2 SystemMonitor: {e}")
    create_system_monitor_raven2 = None

# BaseMonitor 제거 - None 체크로 대체


# 각 컴포넌트의 main.py 경로
COMPONENT_PATHS = {
    "DP1": Path("Orchestrator/NightCrows/Daily_Present/main.py"),
    "MO1": Path("Orchestrator/NightCrows/Mail_opener/main.py"),
    "DP2": Path("Orchestrator/Raven2/Daily_Present/main.py"),
    "MO2": Path("Orchestrator/Raven2/Mail_opener/main.py"),
}


class ActiveState(enum.Enum):
    MONITORING_VD1 = 1
    MONITORING_VD2 = 2
    EXECUTING_TASK_VD1 = 3
    EXECUTING_TASK_VD2 = 4
    SWITCHING = 5
    IDLE = 0


class Orchestrator:
    def __init__(self, vd1_slice_min=3, vd2_slice_min=3):
        print("Initializing Orchestrator...")
        self.start_time = time.time()  # 전체 실행 시간 추적

        try:
            self.vd_manager = VDManager()
            print("VDManager initialized.")
        except Exception as e:
            print(f"Failed to initialize VDManager: {e}")
            self.vd_manager = None
        self.io_scheduler = IOScheduler()  # ← 추가
        self.active_monitors = {}
        self.current_focus = None
        self.active_state = ActiveState.IDLE
        self.monitor_event_queue = queue.Queue()
        self.vd1_slice_duration = vd1_slice_min * 60
        self.vd2_slice_duration = vd2_slice_min * 60
        self.last_focus_switch_time = time.time()
        self.pending_scheduled_task = None
        self.task_execution_lock = threading.Lock()
        self.focus_monitor = FocusMonitor()

        # 1. [신규] 공유 상태 저장소 생성 (화면 ID: 상태 Enum)
        self.vd1_shared_states = {}  # SRM1 ←→ SM1
        self.vd2_shared_states = {}  # SRM2 ←→ SM2

        # 2. 하위 모듈 초기화 시 공유 저장소 주입
        # --- Initialize Real SRM Components ---
        self._initialize_srm_components()
        self._initialize_sm_components()
        print("Component initialization complete.")

        self.setup_schedule()
        self.capture_lock = threading.Lock()

        # 양쪽 게임의 SCREEN_REGIONS 로드
        from Orchestrator.NightCrows.utils.screen_info import SCREEN_REGIONS as NC_REGIONS
        from Orchestrator.Raven2.utils.screen_info import SCREEN_REGIONS as R2_REGIONS

        self.screen_regions = {
            VirtualDesktop.VD1: NC_REGIONS,
            VirtualDesktop.VD2: R2_REGIONS
        }

    def capture_screen_safely(self, screen_id: str):
        """중앙집중식 화면 캡처 - PIL Image 반환"""
        with self.capture_lock:
            try:
                regions = self.screen_regions.get(self.current_focus)
                if not regions or screen_id not in regions:
                    print(f"Error: Screen region not found for {screen_id} on {self.current_focus}")
                    return None

                region = regions[screen_id]
                screenshot = pyautogui.screenshot(region=region)
                return screenshot  # ✅ PIL Image 그대로 반환
            except Exception as e:
                print(f"Error capturing screen for {screen_id}: {e}")
                return None

    def _initialize_srm_components(self):
        """실제 SRM 컴포넌트 초기화"""
        # SRM1 (NightCrows)
        if NightCrowsCombatMonitor:
            try:
                srm1_config = {'confidence': 0.85}
                # [수정] shared_states 전달
                self.srm1 = NightCrowsCombatMonitor(
                    monitor_id="SRM1",
                    config=srm1_config,
                    vd_name="VD1",
                    orchestrator=self,
                    io_scheduler=self.io_scheduler,
                    shared_states=self.vd1_shared_states
                )

                # 화면 정보 추가
                from Orchestrator.NightCrows.utils.screen_info import SCREEN_REGIONS
                for screen_id in ['S1', 'S2', 'S3', 'S4', 'S5']:
                    if screen_id in SCREEN_REGIONS:
                        self.srm1.add_screen(screen_id=screen_id, region=SCREEN_REGIONS[screen_id])

                print(f"INFO: SRM1 initialized with {len(self.srm1.screens)} screens")
            except Exception as e:
                print(f"ERROR: Failed to initialize SRM1: {e}")
                self.srm1 = None
        else:
            self.srm1 = None

        # SRM2 (Raven2)
        if Raven2CombatMonitor:
            try:
                # [수정] shared_states 전달
                self.srm2 = Raven2CombatMonitor(
                    orchestrator=self,
                    io_scheduler=self.io_scheduler,
                    shared_states=self.vd2_shared_states
                )

                # 화면 정보 추가
                from Orchestrator.Raven2.utils.screen_info import SCREEN_REGIONS as RAVEN2_REGIONS
                for screen_id in ['S1', 'S2', 'S3', 'S4', 'S5']:
                    if screen_id in RAVEN2_REGIONS:
                        # Raven2는 ratio 파라미터도 필요할 수 있음
                        ratio = 1.4 if screen_id == 'S5' else 1.0
                        self.srm2.add_screen(window_id=screen_id, region=RAVEN2_REGIONS[screen_id], ratio=ratio)

                print(f"INFO: SRM2 initialized with {len(self.srm2.screens)} screens")
            except Exception as e:
                print(f"ERROR: Failed to initialize SRM2: {e}")
                self.srm2 = None
        else:
            self.srm2 = None

    def _initialize_sm_components(self):
        """실제 SM 컴포넌트 초기화"""
        # SM1 (NightCrows)
        if create_system_monitor:
            try:
                # [수정] shared_states 전달
                self.sm1 = create_system_monitor("SM1", "VD1", orchestrator=self, shared_states=self.vd1_shared_states)
                print("INFO: SM1 initialized successfully")
            except Exception as e:
                print(f"ERROR: Failed to initialize SM1: {e}")
                self.sm1 = None
        else:
            self.sm1 = None

        # SM2 (Raven2)
        if create_system_monitor_raven2:
            try:
                # [수정] shared_states 전달
                self.sm2 = create_system_monitor_raven2("SM2", "VD2", orchestrator=self, shared_states=self.vd2_shared_states)
                print("INFO: SM2 initialized successfully")
            except Exception as e:
                print(f"ERROR: Failed to initialize SM2: {e}")
                self.sm2 = None
        else:
            self.sm2 = None

    def setup_schedule(self):
        print("Setting up schedule...")
        # Daily Present (05:00 AM)
        schedule.every().day.at("05:00").do(self.request_scheduled_task, task_key="DP1", target_vd=VirtualDesktop.VD1)
        schedule.every().day.at("05:10").do(self.request_scheduled_task, task_key="DP2", target_vd=VirtualDesktop.VD2)

        # Mail Opener (12:00 PM / 09:00 PM)
        schedule.every().day.at("12:00").do(self.request_scheduled_task, task_key="MO1", target_vd=VirtualDesktop.VD1)
        schedule.every().day.at("12:02").do(self.request_scheduled_task, task_key="MO2", target_vd=VirtualDesktop.VD2)
        schedule.every().day.at("21:00").do(self.request_scheduled_task, task_key="MO1", target_vd=VirtualDesktop.VD1)
        schedule.every().day.at("21:02").do(self.request_scheduled_task, task_key="MO2", target_vd=VirtualDesktop.VD2)

        print("Schedule setup complete.")
        print(f"Current scheduled jobs: {len(schedule.get_jobs())}")

    def request_scheduled_task(self, task_key, target_vd):
        """Scheduler가 호출하는 함수. 실제 실행은 메인 루프에 위임."""
        if self.pending_scheduled_task:
            print(f"Scheduler triggered for {task_key}, but another task is pending. Ignoring for now.")
            return

        print(f"Scheduler triggered: Task '{task_key}' for {target_vd.name} is requested.")
        self.pending_scheduled_task = {'key': task_key, 'vd': target_vd}

    def _start_monitor_thread(self, monitor_key, monitor_instance):
        """모니터 스레드 시작 (중복 실행 방지 포함)"""
        # None 체크 추가
        if monitor_instance is None:
            print(f"Skipping monitor thread start for {monitor_key}: instance is None")
            return

        if monitor_key in self.active_monitors and self.active_monitors[monitor_key]['thread'].is_alive():
            return

        print(f"Starting monitor thread: {monitor_key}")
        stop_event = threading.Event()
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
                stop_event.set()
                if hasattr(instance, 'stop'):
                    try:
                        instance.stop()
                    except Exception as e:
                        print(f"Error calling stop() for {monitor_key}: {e}")
                thread.join(timeout=10)
                if thread.is_alive():
                    print(f"Warning: Monitor {monitor_key} did not stop gracefully after 10 seconds.")
            del self.active_monitors[monitor_key]

    def set_focus(self, vd_to_focus, new_state):
        """VD 포커스 설정 및 관련 모니터 관리"""
        if self.current_focus == vd_to_focus and self.active_state == new_state:
            return

        print(f"--- Setting focus: VD={vd_to_focus.name}, State={new_state.name} ---")
        previous_focus = self.current_focus
        self.active_state = ActiveState.SWITCHING

        # 1. 이전 포커스 VD의 모니터 중지 및 완전 종료 대기
        if previous_focus:
            if previous_focus == VirtualDesktop.VD1:
                self._stop_monitor_thread('srm1')
                self._stop_monitor_thread('sm1')
            elif previous_focus == VirtualDesktop.VD2:
                self._stop_monitor_thread('srm2')
                self._stop_monitor_thread('sm2')

            print("INFO: Waiting for monitor threads to fully terminate...")
            time.sleep(3.0)  # 모니터 스레드 완전 종료 대기

        # 2. 깨끗한 환경에서 VD 전환
        if self.vd_manager:
            current_actual_vd = self.vd_manager.get_current_vd()
            if current_actual_vd != vd_to_focus and vd_to_focus != VirtualDesktop.OTHER:
                print(f"Clean VD switch: {current_actual_vd.name} → {vd_to_focus.name}")
                self.vd_manager.switch_to(vd_to_focus)
                time.sleep(2.0)  # VD 전환 완료 대기

                # VD 전환 성공 여부 확인
                after_vd = self.vd_manager.get_current_vd()
                if after_vd == vd_to_focus:
                    print(f"SUCCESS: VD switch to {vd_to_focus.name} completed")
                else:
                    print(f"FAILED: VD switch failed. Still at {after_vd.name}")
            else:
                time.sleep(0.5)
        else:
            print("Warning: VDManager not available. Skipping VD switch.")
            time.sleep(1)

        self.current_focus = vd_to_focus

        # 3. 새 상태에 따른 모니터 시작
        if new_state == ActiveState.MONITORING_VD1:
            self._start_monitor_thread('srm1', self.srm1)
            self._start_monitor_thread('sm1', self.sm1)
        elif new_state == ActiveState.MONITORING_VD2:
            self._start_monitor_thread('srm2', self.srm2)
            self._start_monitor_thread('sm2', self.sm2)

        self.active_state = new_state
        self.last_focus_switch_time = time.time()
        print(f"--- Focus set: VD={self.current_focus.name}, State={self.active_state.name} ---")

    def _execute_task(self, task_info):
        """예약된 작업을 별도 프로세스로 실행"""
        task_key = task_info['key']
        target_vd = task_info['vd']
        task_main_py = COMPONENT_PATHS.get(task_key)

        # 디버그 로그 추가
        print(f"DEBUG: task_key = {task_key}")
        print(f"DEBUG: task_main_py = {task_main_py}")
        print(f"DEBUG: task_main_py.parent = {task_main_py.parent}")
        print(f"DEBUG: task_main_py.exists() = {task_main_py.exists()}")

        if not task_main_py or not task_main_py.exists():
            print(f"Error: main.py path not found or invalid for task '{task_key}': {task_main_py}")
            new_monitoring_state = ActiveState.MONITORING_VD1 if target_vd == VirtualDesktop.VD1 else ActiveState.MONITORING_VD2
            self.set_focus(target_vd, new_monitoring_state)
            return

        task_state = ActiveState.EXECUTING_TASK_VD1 if target_vd == VirtualDesktop.VD1 else ActiveState.EXECUTING_TASK_VD2
        self.active_state = task_state
        print(f"--- Executing Task: {task_key} on {target_vd.name} ---")
        print(f"Running command: python \"{task_main_py}\"")

        start_time = time.time()
        try:
            process = subprocess.run([sys.executable, str(task_main_py)],
                                     check=True,
                                     capture_output=True,
                                     text=True,
                                     encoding='utf-8'
                                     )
            print(f"Task '{task_key}' completed successfully.")
            print(f"Output:\n{process.stdout}")
        except FileNotFoundError:
            print(f"Error: Python executable not found at '{sys.executable}'")
        except subprocess.CalledProcessError as e:
            print(f"Error running task '{task_key}': Process returned non-zero exit code {e.returncode}")
            print(f"Stderr:\n{e.stderr}")
        except Exception as e:
            print(f"An unexpected error occurred while running task '{task_key}': {e}")
            import traceback
            traceback.print_exc()
        finally:
            end_time = time.time()
            print(f"Task '{task_key}' finished in {end_time - start_time:.2f} seconds.")

            # next_task가 있는지 확인
            if hasattr(self, 'next_task') and self.next_task:
                print(f"Executing next task: {self.next_task['key']}")
                next_task_info = self.next_task
                self.next_task = None  # 중복 실행 방지

                # 즉시 다음 작업 실행
                next_task_state = ActiveState.EXECUTING_TASK_VD1 if next_task_info[
                                                                        'vd'] == VirtualDesktop.VD1 else ActiveState.EXECUTING_TASK_VD2
                self.set_focus(next_task_info['vd'], next_task_state)
                self._execute_task(next_task_info)
            else:
                # 기존 로직: 모니터링으로 복귀
                new_monitoring_state = ActiveState.MONITORING_VD1 if target_vd == VirtualDesktop.VD1 else ActiveState.MONITORING_VD2
                self.set_focus(target_vd, new_monitoring_state)

    def _check_vd_switch_safety(self) -> bool:
        """현재 활성 SRM의 상태를 체크해서 VD 전환 가능 여부 판단"""
        try:
            current_srm = self.srm1 if self.current_focus == VirtualDesktop.VD1 else self.srm2

            # None이거나 screens 속성이 없는 경우 항상 전환 허용
            if current_srm is None or not hasattr(current_srm, 'screens'):
                return True

            # 위험한 상태들 정의
            critical_states = ['HOSTILE', 'DEAD', 'RECOVERING', 'RETURNING', 'BUYING_POTIONS']

            # 위험 상태인 화면 개수 체크
            critical_count = 0
            for screen in current_srm.screens:
                # [수정] shared_states에서 상태 조회
                screen_state = screen.current_state # 프로퍼티 사용
                if hasattr(screen_state, 'name') and screen_state.name in critical_states:
                    critical_count += 1

            if critical_count > 0:
                print(f"INFO: VD switch delayed - {critical_count} screen(s) in critical state")
                return False

            return True

        except Exception as e:
            print(f"WARN: Error checking VD switch safety: {e}. Allowing switch.")
            return True

    def run_orchestration_loop(self,start_vd: str = "VD1"):
        """
        메인 오케스트레이션 루프
        :param start_vd: 시작할 가상 데스크톱 ("VD1" or "VD2")
        """
        if not self.vd_manager:
            print("Critical Error: VDManager is not available. Orchestrator cannot run.")
            return

        stop_event_for_io = threading.Event()
        self.io_scheduler.start(stop_event_for_io)

        print(f"Orchestrator starting main loop... (Start Target: {start_vd})")
        self.pending_scheduled_task = None

        # 로그 제어 변수들
        io_busy_logged = False
        io_busy_start = None
        last_busy_log = None

        self.focus_monitor.start()
        print(f"Orchestrator starting main loop... (Start Target: {start_vd})")

        # 🚀 [수정됨] 시작 VD 분기 처리
        if start_vd == "VD2":
            print(">>> [TEST MODE] Starting immediately with VD2 (Raven2) <<<")
            self.set_focus(VirtualDesktop.VD2, ActiveState.MONITORING_VD2)
        else:
            print(">>> Starting with VD1 (NightCrows) <<<")
            self.set_focus(VirtualDesktop.VD1, ActiveState.MONITORING_VD1)

        while True:
            try:
                # 1. 스케줄 확인 및 실행 요청 설정
                schedule.run_pending()

                # 2. 요청된 예약 작업 처리 (최우선)
                if self.pending_scheduled_task:
                    with self.task_execution_lock:
                        if self.pending_scheduled_task:
                            task_info = self.pending_scheduled_task
                            self.pending_scheduled_task = None

                            target_vd = task_info['vd']
                            task_state = ActiveState.EXECUTING_TASK_VD1 if target_vd == VirtualDesktop.VD1 else ActiveState.EXECUTING_TASK_VD2
                            self.set_focus(target_vd, task_state)
                            self._execute_task(task_info)

                            time.sleep(1)
                            continue

                # 3. IO 작업 상태 체크
                io_is_busy = self.io_scheduler.lock.locked()

                if io_is_busy:
                    # IO 작업 시작 감지
                    if not io_busy_logged:
                        io_busy_start = time.time()
                        last_busy_log = io_busy_start
                        print(f"INFO: [Orchestrator] IO operations in progress - VD switch paused")
                        io_busy_logged = True

                    # 5초마다 진행 상황 요약
                    now = time.time()
                    if now - last_busy_log >= 10.0:
                        elapsed = int(now - io_busy_start)
                        print(f"INFO: [Orchestrator] IO still busy ({elapsed}s elapsed)")
                        last_busy_log = now

                else:
                    # IO 작업 완료 감지
                    if io_busy_logged:
                        elapsed = time.time() - io_busy_start
                        print(f"INFO: [Orchestrator] IO operations completed ({elapsed:.1f}s total)")
                        io_busy_logged = False
                        io_busy_start = None

                    # IO 작업이 없을 때만 시간 분할 로직 실행
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
                            # 게임 상황을 고려한 안전 체크
                            total_elapsed = now - self.start_time
                            safety_check = self._check_vd_switch_safety()

                            if safety_check:
                                print(f"INFO: [T+{total_elapsed:.0f}s] All screens in safe state - ready for VD switch")

                                # 카운트다운 시작
                                print(f"INFO: Switching to {next_vd.name} in 5 seconds...")
                                for i in range(5, 0, -1):
                                    print(f"      {i}...")
                                    time.sleep(1)

                                print(
                                    f"INFO: Time slice expired on {self.current_focus.name} after {duration_on_current_vd:.0f}s. Switching NOW to {next_vd.name}")
                                next_state = ActiveState.MONITORING_VD1 if next_vd == VirtualDesktop.VD1 else ActiveState.MONITORING_VD2
                                self.set_focus(next_vd, next_state)
                            else:
                                print(
                                    f"INFO: [T+{total_elapsed:.0f}s] VD switch delayed - critical operations detected")
                                # 최대 지연 시간 체크 (15분 추가 대기)
                                max_delay = current_slice_duration + 900  # +15분
                                if duration_on_current_vd > max_delay:
                                    print(
                                        f"WARN: [T+{total_elapsed:.0f}s] Max delay reached ({duration_on_current_vd:.0f}s). Force switching to {next_vd.name}")
                                    next_state = ActiveState.MONITORING_VD1 if next_vd == VirtualDesktop.VD1 else ActiveState.MONITORING_VD2
                                    self.set_focus(next_vd, next_state)

                time.sleep(1)

            except KeyboardInterrupt:
                print("KeyboardInterrupt received. Shutting down Orchestrator...")
                stop_event_for_io.set()
                break
            except Exception as e:
                print(f"!!! Unhandled exception in main loop: {e} !!!")
                import traceback
                traceback.print_exc()
                time.sleep(5)

        self.shutdown()

    def request_io(self, component, screen_id, action, priority=Priority.NORMAL):
        """컴포넌트들이 호출할 IO 요청 메서드"""
        self.io_scheduler.request(component, screen_id, action, priority)

    def report_system_error(self, monitor_id: str, screen_id: str):
        try:
            # === [NightCrows: SRM1] ===
            if monitor_id == "SM1" and self.srm1:
                # [수정] 공유 상태를 직접 확인
                srm_state = self.shared_screen_states.get(screen_id)

                if srm_state in [NC_ScreenState.BUYING_POTIONS, NC_ScreenState.RETURNING]:
                    print(
                        f"Orchestrator: SM1 reported error on {screen_id}, but SRM1 is in a 'safe' state ({srm_state.name}). Ignoring report.")
                    return True

                print(
                    f"Orchestrator: SM1 reported a REAL error on {screen_id} (SRM State: {srm_state}). Forcing SRM1 to reset.")
                self.srm1.force_reset_screen(screen_id)
                return False

            # === [Raven2: SRM2] ===
            elif monitor_id == "SM2" and self.srm2:
                # [수정] 공유 상태를 직접 확인
                srm_state = self.shared_screen_states.get(screen_id)

                safe_states = [
                    R2_ScreenState.SAFE_ZONE,
                    R2_ScreenState.ABNORMAL
                ]

                if srm_state in safe_states:
                    print(
                        f"Orchestrator: SM2 reported error on {screen_id}, but SRM2 is in a 'safe' state ({srm_state.name}). Ignoring report.")
                    return True

                print(
                    f"Orchestrator: SM2 reported error on {screen_id} (State: {srm_state}). Forcing SRM2 to reset screen.")
                self.srm2.force_reset_screen(screen_id)
                return False

        except Exception as e:
            print(f"ERROR: [Orchestrator] Failed during report_system_error handling: {e}")
            return False
    def shutdown(self):
        """오케스트레이터 종료 시 정리 작업"""
        if self.focus_monitor:
            self.focus_monitor.stop()
        print("Shutting down Orchestrator...")
        for key in list(self.active_monitors.keys()):
            self._stop_monitor_thread(key)
        schedule.clear()
        print("Orchestrator shutdown complete.")