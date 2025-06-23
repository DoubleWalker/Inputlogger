# Orchestrator/NightCrows/System_Monitor/src/core/monitor.py

import time
import threading
import numpy as np
import pyautogui
from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Tuple, Optional
from Orchestrator.NightCrows.utils.screen_info import SCREEN_REGIONS, FIXED_UI_COORDS
from Orchestrator.NightCrows.utils.image_utils import (
    set_focus, is_image_present, return_ui_location, click_image
)


class SystemState(Enum):
    """시스템 모니터링 상태"""
    NORMAL = auto()
    CONNECTION_ERROR = auto()
    CLIENT_CRASHED = auto()
    RECOVERING_CONNECTION = auto()
    RESTARTING_APP = auto()
    LOADING = auto()
    LOGIN_REQUIRED = auto()
    LOGGING_IN = auto()
    RETURNING_TO_GAME = auto()


@dataclass
class ScreenInfo:
    """모니터링할 화면 정보"""
    screen_id: str
    region: Tuple[int, int, int, int]
    current_state: SystemState = SystemState.NORMAL
    retry_count: int = 0
    last_state_change_time: float = 0.0


class SystemMonitor:
    """NightCrows 시스템 모니터 (SM1)"""

    def __init__(self, monitor_id="SM1", config=None, vd_name="VD1"):
        self.monitor_id = monitor_id
        self.config = config if isinstance(config, dict) else {}
        self.vd_name = vd_name
        self.io_lock = threading.Lock()

        self.screens: List[ScreenInfo] = []
        self.confidence_threshold = self.config.get('confidence', 0.85)
        self.check_interval = 5.0  # 5초 간격

        print(f"INFO: [{self.monitor_id}] SystemMonitor initialized")

    def add_screen(self, screen_id: str, region: Tuple[int, int, int, int]):
        """모니터링할 화면 영역 추가 (S1~S4만, S5 제외)"""
        if screen_id == 'S5':
            print(f"INFO: [{self.monitor_id}] Skipping S5 (PC native screen)")
            return

        screen = ScreenInfo(screen_id=screen_id, region=region)
        self.screens.append(screen)
        print(f"INFO: [{self.monitor_id}] Added screen: {screen_id}, Region: {region}")

    def _click_relative(self, screen: ScreenInfo, coord_key: str, delay_after: float = 0.5) -> bool:
        """고정 좌표 클릭 (SRM과 동일한 구조)"""
        if screen.screen_id not in FIXED_UI_COORDS:
            print(f"ERROR: [{self.monitor_id}] No fixed coords for {screen.screen_id}")
            return False

        if coord_key not in FIXED_UI_COORDS[screen.screen_id]:
            print(f"ERROR: [{self.monitor_id}] Coord key '{coord_key}' not found for {screen.screen_id}")
            return False

        try:
            screen_x, screen_y = screen.region[0], screen.region[1]
            relative_coords = FIXED_UI_COORDS[screen.screen_id][coord_key]

            click_x = screen_x + relative_coords[0] + np.random.randint(-2, 3)
            click_y = screen_y + relative_coords[1] + np.random.randint(-2, 3)

            pyautogui.click(click_x, click_y)
            if delay_after > 0:
                time.sleep(delay_after)
            return True

        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Click relative failed: {e}")
            return False

    def _detect_system_state(self, screen: ScreenInfo) -> SystemState:
        """현재 화면 상태 감지 (소거법 방식)"""
        # TODO: 템플릿 매칭으로 비정상 상태만 체크
        # - is_image_present()로 연결 에러 확인버튼 감지
        # - is_image_present()로 앱 아이콘 감지
        # - is_image_present()로 로그인 화면 감지
        # - is_image_present()로 로딩 화면 감지
        # 모든 비정상이 아니면 → NORMAL
        return SystemState.NORMAL

    def _handle_connection_error(self, screen: ScreenInfo) -> bool:
        """연결 에러 처리 - 확인버튼 클릭"""
        # TODO: click_image()로 연결 에러 확인버튼 클릭
        print(f"INFO: [{self.monitor_id}] Handling connection error for {screen.screen_id}")
        return True

    def _handle_client_restart(self, screen: ScreenInfo) -> bool:
        """클라이언트 재시작"""
        # TODO: click_image()로 앱 아이콘 클릭하여 재시작
        print(f"INFO: [{self.monitor_id}] Restarting client for {screen.screen_id}")
        return True

    def _handle_login_process(self, screen: ScreenInfo) -> bool:
        """로그인 과정 처리 (단순화된 로직)"""
        # TODO: 단순화된 로그인 수행
        # if is_image_present(get_template(screen.screen_id, 'LOGIN_SCREEN')):
        #     # 가운데 두 번 클릭 (로그인 화면 넘기기)
        #     center_x = screen.region[0] + screen.region[2] // 2
        #     center_y = screen.region[1] + screen.region[3] // 2
        #     pyautogui.click(center_x, center_y)
        #     time.sleep(2.0)
        #     pyautogui.click(center_x, center_y)
        #     return False  # 아직 진행 중
        # elif is_image_present(get_template(screen.screen_id, 'CONNECT_BUTTON')):
        #     # 접속 버튼 클릭
        #     click_image(get_template(screen.screen_id, 'CONNECT_BUTTON'))
        #     return True   # 로그인 처리 완료
        print(f"INFO: [{self.monitor_id}] Processing login for {screen.screen_id}")
        return True

    def _handle_return_to_game(self, screen: ScreenInfo) -> bool:
        """게임 복귀 처리"""
        # TODO: 게임 내 적절한 상태로 복귀
        # - set_focus()로 화면 포커스 설정
        # - _click_relative()로 자동사냥 재시작
        # - click_image()로 기본 설정 확인
        print(f"INFO: [{self.monitor_id}] Returning to game for {screen.screen_id}")
        return True

    def _change_state(self, screen: ScreenInfo, new_state: SystemState):
        """화면 상태 변경"""
        old_state = screen.current_state
        screen.current_state = new_state
        screen.last_state_change_time = time.time()

        if new_state != old_state:
            screen.retry_count = 0
            print(f"INFO: [{self.monitor_id}] {screen.screen_id}: {old_state.name} → {new_state.name}")

    def _handle_screen_state(self, screen: ScreenInfo, stop_event: threading.Event):
        """화면 상태별 처리"""
        state = screen.current_state

        if state == SystemState.NORMAL:
            # 정상 상태에서 이상 감지
            detected_state = self._detect_system_state(screen)
            if detected_state != SystemState.NORMAL:
                self._change_state(screen, detected_state)

        elif state == SystemState.CONNECTION_ERROR:
            if self._handle_connection_error(screen):
                self._change_state(screen, SystemState.RECOVERING_CONNECTION)
            else:
                screen.retry_count += 1

        elif state == SystemState.CLIENT_CRASHED:
            if self._handle_client_restart(screen):
                self._change_state(screen, SystemState.RESTARTING_APP)
            else:
                screen.retry_count += 1

        elif state == SystemState.RECOVERING_CONNECTION:
            # TODO: 연결 복구 확인
            self._change_state(screen, SystemState.RETURNING_TO_GAME)

        elif state == SystemState.RESTARTING_APP:
            # TODO: 앱 시작 확인
            self._change_state(screen, SystemState.LOADING)

        elif state == SystemState.LOADING:
            # TODO: 로딩 완료 확인
            self._change_state(screen, SystemState.LOGIN_REQUIRED)

        elif state == SystemState.LOGIN_REQUIRED:
            if self._handle_login_process(screen):
                self._change_state(screen, SystemState.LOGGING_IN)
            else:
                screen.retry_count += 1

        elif state == SystemState.LOGGING_IN:
            # TODO: 로그인 완료 확인
            self._change_state(screen, SystemState.RETURNING_TO_GAME)

        elif state == SystemState.RETURNING_TO_GAME:
            if self._handle_return_to_game(screen):
                self._change_state(screen, SystemState.NORMAL)
            else:
                screen.retry_count += 1

    def run_loop(self, stop_event: threading.Event):
        """Orchestrator와 호환되는 메인 모니터링 루프"""
        print(f"INFO: [{self.monitor_id}] System monitoring started")

        while not stop_event.is_set():
            try:
                for screen in self.screens:
                    if stop_event.is_set():
                        break

                    self._handle_screen_state(screen, stop_event)

                    # 재시도 횟수 체크
                    if screen.retry_count > 5:
                        print(f"WARN: [{self.monitor_id}] {screen.screen_id}: Max retries reached")
                        self._change_state(screen, SystemState.NORMAL)

                # 5초 대기 (stop_event 확인)
                if stop_event.wait(timeout=self.check_interval):
                    break

            except Exception as e:
                print(f"ERROR: [{self.monitor_id}] Exception in main loop: {e}")
                if stop_event.wait(timeout=5.0):
                    break

        print(f"INFO: [{self.monitor_id}] System monitoring stopped")

    def stop(self):
        """모니터 중지 및 정리"""
        print(f"INFO: [{self.monitor_id}] SystemMonitor stop called")
        # TODO: 필요시 추가 정리 작업