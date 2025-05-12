# Orchestrator/NightCrows/Combat_Monitor/monitor.py
# add_screen 방식을 사용하고, config/template_paths.py 에서 템플릿 경로를 읽도록 수정된 버전

import pyautogui
import traceback
import cv2
import time
import threading
import os
import keyboard
import sys # if __name__ == "__main__" 에서 경로 설정 위해 추가
import numpy as np
import random
from enum import Enum, auto
from dataclasses import dataclass
from typing import Tuple, List, Dict, Optional
from Orchestrator.NightCrows.utils import image_utils
from Orchestrator.NightCrows.utils.screen_info import FIXED_UI_COORDS
from .config import template_paths



# (Placeholder - BaseMonitor 클래스는 Orchestrator에서 제공될 것으로 가정)
class BaseMonitor:
    """오케스트레이터와 호환되는 모니터의 기본 클래스"""
    def __init__(self, monitor_id: str, config: Optional[Dict], vd_name: str):
        self.monitor_id = monitor_id
        self.config = config if isinstance(config, dict) else {}
        self.vd_name = vd_name

    def run_loop(self, stop_event: threading.Event):
        """Orchestrator가 스레드에서 실행할 메인 루프. stop_event로 종료 제어."""
        raise NotImplementedError("Subclasses should implement this method.")

    def stop(self):
        """Orchestrator가 모니터 종료 시 호출할 메서드. 리소스 정리 등."""
        print(f"INFO: Stopping BaseMonitor for {self.monitor_id}")

# --- Enum 정의 ---
class CharacterState(Enum):
    """캐릭터의 주요 상태"""
    NORMAL = auto()         # 정상
    HOSTILE_ENGAGE = auto() # 적대적 교전
    DEAD = auto()           # 사망

class Location(Enum):
    """캐릭터의 주요 위치"""
    ARENA = auto()          # 아레나 (또는 특정 던전 내부)
    FIELD = auto()          # 필드 (또는 마을 등 안전 지역)
    UNKNOWN = auto()        # 알 수 없음

# --- 화면 정보 데이터 클래스 ---
@dataclass
class ScreenMonitorInfo:
    """모니터링할 개별 화면의 정보"""
    screen_id: str
    region: Tuple[int, int, int, int]

# ----------------------------------------------------------------------------
# [주의] 아래 함수들은 플레이스홀더입니다. 실제 게임 상호작용 로직 구현 필요
#        (CombatMonitor 클래스 외부 정의 유지, 필요시 내부 메서드로 변경 가능)
# ----------------------------------------------------------------------------
def _move_to_wp(self, screen: ScreenMonitorInfo, wp_index: int) -> bool:
    """특정 웨이포인트로 이동 시작 (공통 인터페이스)"""
    print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Moving to waypoint {wp_index}")

    try:
        # 직접 UI 클릭 방식 이동 (WP1, WP2)
        if wp_index in [1, 2]:
            return self._move_to_arena_wp(screen, wp_index)

        # 파티 리더-팔로워 방식 이동 (WP3, WP4)
        elif wp_index in [3, 4]:
            return self._move_to_party_shared_wp(screen, wp_index)

        else:
            print(f"ERROR: [{self.monitor_id}] Unknown waypoint index: {wp_index}")
            return False

    except Exception as e:
        print(f"ERROR: [{self.monitor_id}] Exception during move to waypoint {wp_index}: {e}")
        return False



def _move_to_arena_wp(self, screen: ScreenMonitorInfo, wp_index: int) -> bool:
    """격전지 내 웨이포인트(WP1, WP2)로 UI 클릭을 통해 이동"""
    try:
        if wp_index == 1:
            # WP1 (아레나) 이동 로직
            # 1. 메뉴 버튼 클릭 (고정 위치)
            if not self._click_relative(screen, 'main_menu_button', delay_after=1.0):
                print(f"ERROR: [{self.monitor_id}] Failed to click main menu button")
                return False

            # 2. 격전지 아이콘 클릭
            arena_icon_template = template_paths.get_template(screen.screen_id, 'ARENA_MENU_ICON')
            if not arena_icon_template or not os.path.exists(arena_icon_template):
                print(f"ERROR: [{self.monitor_id}] Arena menu icon template not found")
                keyboard.press_and_release('esc')  # 메뉴창 닫기
                return False

            icon_pos = image_utils.return_ui_location(arena_icon_template, screen.region, self.confidence)
            if not icon_pos:
                print(f"ERROR: [{self.monitor_id}] Arena menu icon not found")
                keyboard.press_and_release('esc')  # 메뉴창 닫기
                return False

            pyautogui.click(icon_pos)
            time.sleep(1.0)

            # 3. 확인창에서 Y 키 입력
            keyboard.press_and_release('y')
            print(f"INFO: [{self.monitor_id}] Pressed Y to confirm arena teleport")

            # 4. 이동 대기 (최소 30초)
            loading_wait_time = 35  # 여유있게 35초
            print(f"INFO: [{self.monitor_id}] Waiting for arena loading ({loading_wait_time}s)...")
            time.sleep(loading_wait_time)

            # 5. 격전지 입장 UI에서 선택 (3개 중 첫번째 옵션)
            arena_entry_path = template_paths.get_template(screen.screen_id, 'ARENA_ENTRY_UI')

            # UI가 있는지 확인 (여러 번 시도)
            entry_found = False
            max_entry_attempts = 5

            for attempt in range(max_entry_attempts):
                if image_utils.is_image_present(arena_entry_path, screen.region, self.confidence):
                    entry_found = True
                    break

                print(
                    f"INFO: [{self.monitor_id}] Arena entry UI not found yet (attempt {attempt + 1}/{max_entry_attempts})")
                time.sleep(2.0)

            if not entry_found:
                print(f"ERROR: [{self.monitor_id}] Arena entry UI not found after {max_entry_attempts} attempts")
                return False

            # 첫 번째 옵션 클릭 (고정 위치 사용)
            if not self._click_relative(screen, 'arena_entry_option1', delay_after=1.0):
                print(f"ERROR: [{self.monitor_id}] Failed to click arena entry option")
                return False

            print(f"INFO: [{self.monitor_id}] Successfully initiated arena entry")
            return True

        elif wp_index == 2:
            # WP2 (격전지 내 특정 위치/탑) 이동 로직
            print(f"INFO: [{self.monitor_id}] Moving to WP2 (Arena Tower)...")

            # 1. 맵 인터페이스 열기 (M 키)
            keyboard.press_and_release('m')
            print(f"INFO: [{self.monitor_id}] Opened map interface")
            time.sleep(1.0)  # 맵 로딩 대기

            # 2. 첫 번째 고정 좌표 클릭
            if not self._click_relative(screen, 'tower_click_1', delay_after=0.5):
                print(f"ERROR: [{self.monitor_id}] Failed to click first tower location")
                keyboard.press_and_release('m')  # 맵 닫기
                return False

            # 3. 두 번째 고정 좌표 클릭
            if not self._click_relative(screen, 'tower_click_2', delay_after=0.5):
                print(f"ERROR: [{self.monitor_id}] Failed to click second tower location")
                keyboard.press_and_release('m')  # 맵 닫기
                return False

            # 4. 세 번째 고정 좌표 클릭
            if not self._click_relative(screen, 'tower_click_3', delay_after=0.5):
                print(f"ERROR: [{self.monitor_id}] Failed to click third tower location")
                keyboard.press_and_release('m')  # 맵 닫기
                return False

            # 5. Y 키 입력으로 확인
            keyboard.press_and_release('y')
            print(f"INFO: [{self.monitor_id}] Pressed Y to confirm teleport")

            print(f"INFO: [{self.monitor_id}] Successfully initiated tower teleport")
            return True

        else:
            print(f"ERROR: [{self.monitor_id}] Unsupported arena waypoint index: {wp_index}")
            return False

    except Exception as e:
        print(f"ERROR: [{self.monitor_id}] Exception during arena WP{wp_index} movement: {e}")
        # 오류 시 맵/메뉴 닫기 시도
        try:
            keyboard.press_and_release('esc')
            if wp_index == 2:  # WP2는 맵을 열었을 수 있음
                keyboard.press_and_release('m')
        except:
            pass
        return False

def _check_reached_wp(self, screen: ScreenMonitorInfo, wp_index: int) -> bool:
    """웨이포인트 도착 여부를 확인합니다 (공통 인터페이스)"""
    print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Checking if reached Waypoint #{wp_index}")

    try:
        # 현재는 모든 웨이포인트가 동작 완료 시 도착한 것으로 간주
        if wp_index in [1, 2]:  # 현재 구현된 웨이포인트들
            print(f"INFO: [{self.monitor_id}] WP{wp_index} is considered reached after movement sequence completion")
            return True
        else:
            print(f"ERROR: [{self.monitor_id}] Unknown waypoint index: {wp_index}")
            return False

    except Exception as e:
        print(f"ERROR: [{self.monitor_id}] Exception during check waypoint {wp_index}: {e}")
        return False

def _look_for_wp(wp_index: int) -> None:
    """[플레이스홀더] 웨이포인트를 찾거나 경로를 조정하는 동작 수행"""
    print(f"INFO: [Placeholder Action] Looking for/Adjusting path to Waypoint #{wp_index}...")
    time.sleep(1)

def _get_max_wp_num() -> int:
    """[플레이스홀더] 전체 웨이포인트 개수 반환"""
    print("INFO: [Placeholder Action] Getting Max Waypoint Number...")
    return 5 # 예시 값


def _is_at_combat_spot(self, screen: ScreenMonitorInfo) -> bool:
    """최종 전투 지점 도착 여부를 최대 3번 확인합니다."""
    print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Checking if at combat spot")

    # 전투 지점 확인 템플릿 경로 가져오기
    template_path = template_paths.get_template(screen.screen_id, 'COMBAT_SPOT')

    if not template_path or not os.path.exists(template_path):
        print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: COMBAT_SPOT template not found")
        return False

    # 최대 3번 시도
    max_attempts = 3
    for attempt in range(max_attempts):
        if image_utils.is_image_present(
                template_path=template_path,
                region=screen.region,
                threshold=self.confidence
        ):
            print(f"INFO: [{self.monitor_id}] Combat spot reached confirmed on attempt {attempt + 1}")
            return True

        print(f"INFO: [{self.monitor_id}] Combat spot not detected on attempt {attempt + 1}/{max_attempts}")
        time.sleep(1.0)  # 1초 간격으로 재시도

    print(f"INFO: [{self.monitor_id}] Combat spot not confirmed after {max_attempts} attempts")
    return False

def _perform_combat_spot_adjustment() -> None:
    """[플레이스홀더] 최종 전투 지점 도착을 위한 위치 조정 동작 수행"""
    print("INFO: [Placeholder Action] Adjusting position to reach Combat Spot...")
    time.sleep(1)

# ----------------------------------------------------------------------------
# Combat Monitor 클래스 구현
# ----------------------------------------------------------------------------
class CombatMonitor(BaseMonitor):
    """
    여러 NightCrows 화면의 캐릭터 상태를 모니터링합니다 (add_screen으로 추가).
    도주, 부활, 물약 구매, 웨이포인트 네비게이션을 처리합니다.
    Orchestrator에 의해 run_loop 및 stop_event로 제어됩니다.
    템플릿 경로는 config/template_paths.py에서 읽어옵니다.
    """
    def __init__(self, monitor_id="SRM1", config=None, vd_name="VD1"):
        """CombatMonitor 초기화."""
        super().__init__(monitor_id, config, vd_name)
        self.location_flag: Location = Location.UNKNOWN
        self.death_count: int = 0
        self.current_wp: int = 0
        self.max_wp: int = 0

        self.screens: List[ScreenMonitorInfo] = []
        self.confidence = self.config.get('confidence', 0.8) # 신뢰도 설정

        # 필수 템플릿 경로 로드 (getattr으로 안전하게)
        self.arena_template_path = getattr(template_paths, 'ARENA_TEMPLATE', None)
        self.dead_template_path = getattr(template_paths, 'DEAD_TEMPLATE', None)
        self.hostile_template_path = getattr(template_paths, 'HOSTILE_TEMPLATE', None)

        if not all([self.arena_template_path, self.dead_template_path, self.hostile_template_path]):
             print(f"WARNING: [{self.monitor_id}] Essential template attributes (ARENA, DEAD, HOSTILE) "
                   f"not found in template_paths module or config. State detection might fail.")

    def add_screen(self, screen_id: str, region: Tuple[int, int, int, int]):
        """모니터링할 화면 영역과 ID를 등록합니다."""
        if not isinstance(screen_id, str) or not screen_id:
             print(f"ERROR: [{self.monitor_id}] Invalid screen_id '{screen_id}' received. Skipping.")
             return
        if not isinstance(region, tuple) or len(region) != 4:
             print(f"ERROR: [{self.monitor_id}] Invalid region '{region}' for screen '{screen_id}'. Skipping.")
             return
        if any(s.screen_id == screen_id for s in self.screens):
            print(f"WARNING: [{self.monitor_id}] Screen ID '{screen_id}' already added. Skipping.")
            return

        screen = ScreenMonitorInfo(screen_id=screen_id, region=region)
        self.screens.append(screen)
        print(f"INFO: [{self.monitor_id}] Screen added: ID={screen_id}, Region={region}")

    def _load_template(self, template_path: Optional[str]) -> Optional[cv2.typing.MatLike]:
        """템플릿 이미지를 로드하고 유효성을 검사합니다."""
        if not template_path or not isinstance(template_path, str):
             return None
        if not os.path.exists(template_path):
             print(f"ERROR: [{self.monitor_id}] Template file not found: {template_path}")
             return None
        try:
            template = cv2.imread(template_path)
            if template is None:
                print(f"ERROR: [{self.monitor_id}] Failed to load template (imread returned None): {template_path}")
            return template
        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Exception loading template {template_path}: {e}")
            return None

    def _get_character_state_on_screen(self, screen: ScreenMonitorInfo) -> CharacterState:
        """지정된 화면 영역의 캐릭터 상태를 화면별 템플릿을 사용하여 확인합니다."""
        if not screen or not screen.region:
            print(f"ERROR: [{self.monitor_id}] Invalid screen object for state check.")
            return CharacterState.NORMAL

        try:
            screenshot = pyautogui.screenshot(region=screen.region)
            if screenshot is None:
                print(f"ERROR: [{self.monitor_id}] Failed screenshot (Screen: {screen.screen_id}).")
                return CharacterState.NORMAL
        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Failed screenshot (Screen: {screen.screen_id}): {e}")
            return CharacterState.NORMAL

        try:
            # 화면 ID에 맞는 템플릿 경로 가져오기 (없으면 기본 경로 사용 시도)
            dead_template_path = template_paths.get_template(screen.screen_id, 'DEAD') or self.dead_template_path
            hostile_template_path = template_paths.get_template(screen.screen_id, 'HOSTILE') or self.hostile_template_path

            # DEAD 상태 확인 (최우선)
            dead_template = self._load_template(dead_template_path)
            if dead_template is not None and image_utils.compare_images(screenshot, dead_template, threshold=self.confidence):
                return CharacterState.DEAD

            # HOSTILE 상태 확인
            hostile_template = self._load_template(hostile_template_path)
            if hostile_template is not None and image_utils.compare_images(screenshot, hostile_template, threshold=self.confidence):
                return CharacterState.HOSTILE_ENGAGE

            return CharacterState.NORMAL

        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] State check error (Screen: {screen.screen_id}): {e}")
            traceback.print_exc()
            return CharacterState.NORMAL

    def _is_character_in_arena(self, screen: ScreenMonitorInfo) -> bool:
        """지정된 화면을 사용하여 캐릭터가 아레나에 있는지 확인합니다."""
        if not screen or not screen.region:
            print(f"ERROR: [{self.monitor_id}] Invalid screen object for arena check.")
            return False

        arena_template_path = template_paths.get_template(screen.screen_id, 'ARENA') or self.arena_template_path
        arena_template = self._load_template(arena_template_path)
        if arena_template is None:
            return False # 템플릿 없으면 필드로 간주

        try:
            screen_capture = pyautogui.screenshot(region=screen.region)
            if screen_capture is None:
                print(f"ERROR: [{self.monitor_id}] Failed screenshot for arena check (Screen: {screen.screen_id}).")
                return False
            return image_utils.compare_images(screen_capture, arena_template, threshold=self.confidence)
        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Exception during arena check (Screen: {screen.screen_id}): {e}")
            return False

    def _determine_initial_location(self, stop_event: threading.Event) -> bool:
        """등록된 첫 번째 화면을 사용하여 시작 위치를 결정합니다."""
        if not self.screens:
            print(f"ERROR: [{self.monitor_id}] No screens added. Cannot determine initial location.")
            self.location_flag = Location.UNKNOWN
            return False

        first_screen = self.screens[0]
        print(f"INFO: [{self.monitor_id}] Determining initial location using screen {first_screen.screen_id}...")
        retry_count = 0
        max_retries = 3

        while not stop_event.is_set() and retry_count < max_retries:
            try:
                is_arena = self._is_character_in_arena(screen=first_screen)
                self.location_flag = Location.ARENA if is_arena else Location.FIELD
                print(f"INFO: [{self.monitor_id}] Initial Location determined: {self.location_flag.name}")
                return True
            except Exception as e:
                retry_count += 1
                print(f"ERROR: [{self.monitor_id}] Error checking location (Attempt {retry_count}/{max_retries}): {e}. Retrying...")
                if stop_event.wait(3):
                    print(f"INFO: [{self.monitor_id}] Stop event received during location check retry.")
                    return False

        print(f"ERROR: [{self.monitor_id}] Failed to determine initial location after {max_retries} retries or stop signal.")
        self.location_flag = Location.UNKNOWN
        return False

    # --- 게임 상호작용 메서드들 ---

    def _attempt_flight(self, screen: ScreenMonitorInfo) -> bool:
        """지정된 화면에서 '도주' 버튼 템플릿을 찾아 클릭을 시도합니다."""
        flight_template_path = template_paths.get_template(screen.screen_id, 'FLIGHT_BUTTON')
        if not flight_template_path:
            print(f"ERROR: [{self.monitor_id}] Flight template path not configured for screen {screen.screen_id}.")
            return False
        if not os.path.exists(flight_template_path):
            print(f"ERROR: [{self.monitor_id}] Flight template file not found: {flight_template_path}")
            return False

        try:
            center_coords = image_utils.return_ui_location(
                template_path=flight_template_path,
                region=screen.region,
                threshold=self.confidence
            )
            if center_coords:
                pyautogui.click(center_coords)
                print(f"INFO: [{self.monitor_id}] Flight (escape) initiated on screen {screen.screen_id}.")
                return True
            else:
                return False # 버튼 못 찾음
        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Exception during flight attempt on screen {screen.screen_id}: {e}")
            return False

    def _buy_potion_and_initiate_return(self, screen: ScreenMonitorInfo, context: Location) -> bool:
        """지정된 화면에서 물약을 구매하고, 상황(context)에 따라 귀환/복귀를 시작합니다."""
        print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Starting potion purchase sequence (Context: {context.name})...")
        try:
            # 1. 상점 열기
            shop_template_path = template_paths.get_template(screen.screen_id, 'SHOP_BUTTON')
            if not shop_template_path or not os.path.exists(shop_template_path):
                print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: SHOP_BUTTON template invalid or not found.")
                return False
            shop_button_loc = image_utils.return_ui_location(shop_template_path, screen.region, self.confidence)
            if not shop_button_loc:
                print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: SHOP_BUTTON not found.")
                return False
            pyautogui.click(shop_button_loc)
            print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Clicked SHOP_BUTTON.")
            time.sleep(1.5) # 상점 로딩 대기

            # 2. 구매 버튼 클릭
            purchase_template_path = template_paths.get_template(screen.screen_id, 'PURCHASE_BUTTON')
            if not purchase_template_path or not os.path.exists(purchase_template_path):
                print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: PURCHASE_BUTTON template invalid or not found.")
                pyautogui.press('esc'); time.sleep(0.5) # 상점 닫기 시도
                return False
            purchase_button_loc = image_utils.return_ui_location(purchase_template_path, screen.region, self.confidence)
            if not purchase_button_loc:
                print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: PURCHASE_BUTTON not found.")
                pyautogui.press('esc'); time.sleep(0.5) # 상점 닫기 시도
                return False
            pyautogui.click(purchase_button_loc)
            print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Clicked PURCHASE_BUTTON.")
            time.sleep(0.5) # 확인 창 대기

            # 3. 확인 ('Y' 키)
            pyautogui.press('y')
            print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Pressed 'Y' key.")
            time.sleep(0.5)

            # 4. 상점 닫기 (ESC 두 번)
            pyautogui.press('esc'); time.sleep(0.2)
            pyautogui.press('esc')
            print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Potion purchase sequence finished.")

            # 5. 귀환/복귀 시작 (Context에 따라 분기)
            if context == Location.FIELD:
                print(
                    f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Context is FIELD. Initiating return action...")

                # 1. 메뉴 클릭 (고정 위치)
                if not self._click_relative(screen, 'main_menu_button', delay_after=1.0):
                    return False

                # 2. 템플릿 위치 클릭
                template_path = template_paths.get_template(screen.screen_id, 'RETURN_TARGET_LOCATION')
                if not template_path or not os.path.exists(template_path):
                    return False

                target_location = image_utils.return_ui_location(template_path, screen.region, self.confidence)
                if not target_location:
                    return False

                pyautogui.click(target_location)
                time.sleep(1.0)

                # 3. 확인 클릭 (고정 위치)
                if not self._click_relative(screen, 'retry_confirm', delay_after=0.5):
                    return False

                # 4. 닫기 클릭 (고정 위치)
                self._click_relative(screen, 'retry_close', delay_after=1.5)

                return True

            elif context == Location.ARENA:
                print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Context is ARENA. Return initiation not needed here.")
                return True # 아레나에서는 후속 웨이포인트 네비게이션이 처리

            else: # UNKNOWN 등
                print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: Unknown context '{context.name}'. Cannot initiate return.")
                return False

        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: Exception during potion purchase/return: {e}")
            traceback.print_exc()
            try: # 에러 시 상점 닫기 시도
                pyautogui.press('esc'); time.sleep(0.2); pyautogui.press('esc')
            except Exception as esc_e:
                print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: Error pressing ESC during exception handling: {esc_e}")
            return False

    def _process_recovery(self, screen: ScreenMonitorInfo) -> bool:
        """지정된 화면에서 부활 동작을 수행합니다."""
        print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Processing RECOVERY (Revive)...")

        try:
            # 1. 부활 버튼 클릭
            revive_template_path = template_paths.get_template(screen.screen_id, 'REVIVE_BUTTON')
            if not revive_template_path or not os.path.exists(revive_template_path):
                print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: REVIVE_BUTTON template not found.")
                return False

            revive_location = image_utils.return_ui_location(revive_template_path, screen.region, self.confidence)
            if not revive_location:
                print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: REVIVE_BUTTON not found on screen.")
                return False

            pyautogui.click(revive_location)
            print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Clicked REVIVE_BUTTON.")

            # 2. 부활 후 마을 복귀 대기 (10-15초)
            wait_time = random.uniform(10, 15)
            print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Waiting {wait_time:.1f}s for respawn...")
            time.sleep(wait_time)

            # 3. 묘지 UI 찾기 (여러 번 시도)
            graveyard_template_path = template_paths.get_template(screen.screen_id, 'GRAVEYARD')
            if not graveyard_template_path or not os.path.exists(graveyard_template_path):
                print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: GRAVEYARD template not found.")
                return False

            max_attempts = 5
            graveyard_found = False

            for attempt in range(max_attempts):
                graveyard_location = image_utils.return_ui_location(graveyard_template_path, screen.region,
                                                                    self.confidence)
                if graveyard_location:
                    pyautogui.click(graveyard_location)
                    print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Clicked GRAVEYARD location.")
                    graveyard_found = True
                    break
                else:
                    print(
                        f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: GRAVEYARD not found (attempt {attempt + 1}/{max_attempts})")
                    time.sleep(1.0)

            if not graveyard_found:
                print(
                    f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: GRAVEYARD not found after {max_attempts} attempts.")
                return False

            # 4. 잠시 대기
            time.sleep(0.5)

            # 5. 고정 위치 클릭
            if not self._click_relative(screen, 'graveyard_confirm', delay_after=0.5):
                print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: Failed to click graveyard_confirm.")
                return False

            # 6. ESC 키 누르기
            pyautogui.press('esc')
            print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Pressed ESC. Recovery process completed.")

            return True

        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: Exception during recovery: {e}")
            return False

    def _check_returned_well(self, screen_info: 'ScreenInfo', samples: int = 7, threshold: float = 0.15, sample_interval: float = 0.5) -> bool:
        """
        주어진 화면(screen_info)에서 파티 UI 템플릿이 보이는지 (근거리 조우) 확인합니다.
        screen_id를 사용하여 template_paths에서 동적으로 템플릿 경로를 가져옵니다.

        Args:
            screen_info: 확인할 화면의 ScreenInfo 객체 (screen_id와 region 속성 필요).
            samples: 스크린샷 샘플링 횟수.
            threshold: TM_SQDIFF_NORMED 매칭 임계값 (이 값보다 작으면 매칭 성공).
            sample_interval: 샘플링 간격 (초).

        Returns:
            파티 UI 템플릿이 발견되면 True, 그렇지 않으면 False.
        """
        if not hasattr(screen_info, 'screen_id'):
             print(f"오류: screen_info 객체에 screen_id 속성이 없습니다.")
             return False

        # screen_id를 사용하여 template_paths 모듈에서 파티 UI 템플릿 경로 가져오기
        # template_paths.get_template 함수가 있다고 가정 (없으면 직접 PARTY_UI_TEMPLATES 딕셔너리 접근)
        try:
            # template_paths.get_template(screen_id, template_name, template_type) 형태라고 가정
            template_path = template_paths.get_template(screen_info.screen_id, '', template_type='party_ui')
        except AttributeError:
             print("오류: template_paths 모듈 또는 get_template 함수를 찾을 수 없습니다.")
             # 대체: 직접 딕셔너리 접근 (template_paths.PARTY_UI_TEMPLATES[screen_info.screen_id])
             try:
                 template_path = template_paths.PARTY_UI_TEMPLATES.get(screen_info.screen_id)
             except AttributeError:
                  print("오류: template_paths 모듈 또는 PARTY_UI_TEMPLATES 딕셔너리를 찾을 수 없습니다.")
                  return False
             except KeyError:
                  print(f"오류: template_paths.PARTY_UI_TEMPLATES에 Screen ID '{screen_info.screen_id}'에 대한 정의가 없습니다.")
                  return False


        if not template_path:
            print(f"경고: Screen {screen_info.screen_id}에 대한 파티 UI 템플릿 경로를 찾을 수 없습니다.")
            return False # 템플릿 경로 없으면 확인 불가

        if not os.path.exists(template_path):
            print(f"오류: 파티 UI 템플릿 파일을 찾을 수 없습니다: {template_path}")
            return False # 템플릿 파일 없으면 확인 불가

        try:
            template = cv2.imread(template_path)
            if template is None:
                print(f"오류: 파티 UI 템플릿 이미지 로드 실패: {template_path}")
                return False

            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            min_val_overall = 1.0 # TM_SQDIFF_NORMED의 최대값은 1.0

            print(f"Screen {screen_info.screen_id}: 파티 UI 확인 시작 (템플릿: {os.path.basename(template_path)}, 임계값: {threshold})")

            for i in range(samples):
                try:
                    screen_img = pyautogui.screenshot(region=screen_info.region)
                    screen_gray = cv2.cvtColor(np.array(screen_img), cv2.COLOR_RGB_GRAY)

                    # TM_SQDIFF_NORMED: 값이 작을수록 유사함
                    match_result = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_SQDIFF_NORMED)
                    min_val, _, min_loc, _ = cv2.minMaxLoc(match_result) # min_val 사용
                    min_val_overall = min(min_val_overall, min_val)

                    print(f"  - 샘플 {i + 1}: min_val = {min_val:.4f}")

                    if min_val < threshold:
                        print(f"Screen {screen_info.screen_id}: 파티 UI 발견 (매칭값: {min_val:.4f})")
                        return True # 임계값보다 작으면 매칭 성공

                except Exception as e:
                    print(f"오류: Screen {screen_info.screen_id} 샘플링 중 오류 발생: {e}")
                    # 샘플링 중 오류 발생 시 다음 샘플 시도 또는 실패 처리 가능

                if i < samples - 1: # 마지막 샘플 후에는 대기 불필요
                    time.sleep(sample_interval)

            print(f"Screen {screen_info.screen_id}: 파티 UI 미발견 (최소 매칭값: {min_val_overall:.4f})")
            return False # 모든 샘플 확인 후에도 임계값 이하 못 찾음

        except cv2.error as e:
            print(f"오류: OpenCV 오류 발생 (템플릿: {template_path}): {e}")
            return False
        except Exception as e:
            print(f"오류: _check_returned_well 처리 중 예외 발생: {e}")
            return False

    def _click_relative(self, screen: ScreenMonitorInfo, coord_key: str, delay_after: float = 0.5, random_offset: int = 2) -> bool:
        """
        지정된 화면 영역 내에서 FIXED_UI_COORDS에 정의된 키를 사용하여
        상대 좌표에 클릭을 수행합니다.

        Args:
            screen: 클릭을 수행할 ScreenMonitorInfo 객체.
            coord_key: utils.screen_info.FIXED_UI_COORDS 내 해당 screen_id 딕셔너리의 키.
            delay_after: 클릭 후 대기 시간 (초).
            random_offset: 클릭 좌표에 적용할 랜덤 오프셋 범위 (± 값).

        Returns:
            클릭 성공 시 True, 실패 시 False.
        """
        if not screen or not screen.region:
            print(f"ERROR:[{self.monitor_id}] Invalid screen for relative click.")
            return False
        if not hasattr(screen, 'screen_id'):
             print(f"ERROR:[{self.monitor_id}] screen_info object missing 'screen_id' for relative click.")
             return False

        # screen_info 모듈의 FIXED_UI_COORDS 에서 상대 좌표 가져오기
        screen_coords = FIXED_UI_COORDS.get(screen.screen_id)
        if not screen_coords:
            print(f"ERROR:[{self.monitor_id}] Relative coordinates not found for screen '{screen.screen_id}' in FIXED_UI_COORDS.")
            return False

        relative_coord = screen_coords.get(coord_key)
        if relative_coord is None:
            print(f"ERROR:[{self.monitor_id}] Relative coordinate key '{coord_key}' not found for screen '{screen.screen_id}'.")
            return False
        if not isinstance(relative_coord, tuple) or len(relative_coord) != 2:
            print(f"ERROR:[{self.monitor_id}] Invalid coordinate format for '{coord_key}' on screen '{screen.screen_id}': {relative_coord}")
            return False

        # 절대 좌표 계산
        region_x, region_y, _, _ = screen.region
        try:
            # 정수 좌표 보장 및 랜덤 오프셋 적용
            click_x = int(region_x + relative_coord[0] + np.random.randint(-random_offset, random_offset + 1))
            click_y = int(region_y + relative_coord[1] + np.random.randint(-random_offset, random_offset + 1))
        except ValueError: # relative_coord가 숫자가 아닐 경우 대비
             print(f"ERROR:[{self.monitor_id}] Invalid coordinate values for '{coord_key}' on screen '{screen.screen_id}': {relative_coord}")
             return False

        try:
            print(f"INFO:[{self.monitor_id}] Clicking relative '{coord_key}' at ({click_x}, {click_y}) on screen {screen.screen_id}...")
            pyautogui.click(click_x, click_y)
            if delay_after > 0:
                print(f"INFO:[{self.monitor_id}] Waiting {delay_after}s after clicking '{coord_key}'.")
                time.sleep(delay_after)
            return True
        except Exception as e:
            print(f"ERROR:[{self.monitor_id}] Failed to click relative coordinate '{coord_key}' on screen {screen.screen_id}: {e}")
            return False
    # ---------------------------------------------

    # ... (_get_character_state_on_screen 등 기존 메소드) ...

    def _retry_field_return(self, screen: ScreenMonitorInfo) -> bool:
        """필드 복귀 재시도: 메뉴-템플릿-확인-닫기 순으로 클릭"""
        try:
            # 1. 메뉴 클릭 (고정 위치)
            if not self._click_relative(screen, 'main_menu_button', delay_after=1.0):
                return False

            # 2. 템플릿 위치 클릭
            template_path = template_paths.get_template(screen.screen_id, 'RETURN_TARGET_LOCATION')
            if not template_path or not os.path.exists(template_path):
                return False

            target_location = image_utils.return_ui_location(template_path, screen.region, self.confidence)
            if not target_location:
                return False

            pyautogui.click(target_location)
            time.sleep(1.0)

            # 3. 확인 클릭 (고정 위치)
            if not self._click_relative(screen, 'retry_confirm', delay_after=0.5):
                return False

            # 4. 닫기 클릭 (고정 위치)
            self._click_relative(screen, 'retry_close', delay_after=1.5)

            return True

        except Exception as e:
            print(f"ERROR: Field return retry failed: {e}")
            return False

    # --- 상태 처리 핸들러 ---

    def _handle_hostile_engage(self, stop_event: threading.Event, screen: ScreenMonitorInfo):
        """HOSTILE_ENGAGE 상태를 처리합니다. (도주 시도 -> 물약 구매 -> 복귀 확인/웨이포인트)"""
        print(f"INFO: [{self.monitor_id}] Handling HOSTILE_ENGAGE state on screen {screen.screen_id}...")

        # 도주 전에 현재 컨텍스트 저장
        original_context = self.location_flag
        print(f"INFO: [{self.monitor_id}] Current context before flight: {original_context.name}")

        if self._attempt_flight(screen=screen):
            print(f"INFO: [{self.monitor_id}] Flight successful. Using original context: {original_context.name}")

            # 물약 구매 및 귀환 시작 - 저장된 원래 컨텍스트 사용
            if not self._buy_potion_and_initiate_return(screen=screen, context=original_context):
                print(
                    f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: Failed potion purchase/return after flight.")
                return

            # 원래 컨텍스트에 따라 후속 조치
            if original_context == Location.ARENA:
                print(f"INFO: [{self.monitor_id}] Original context was ARENA. Transitioning to Waypoint Navigation...")
                self._waypoint_navigation(stop_event)
                self.location_flag = Location.ARENA  # 웨이포인트 네비게이션 후 아레나 상태로 복원
                print(f"INFO: [{self.monitor_id}] Waypoint navigation finished, context set to ARENA.")
            else:  # Field
                print(f"INFO: [{self.monitor_id}] Original context was FIELD. Checking return status...")
                return_check_count = 0
                max_return_checks = 15
                while not stop_event.is_set() and return_check_count < max_return_checks:
                    if self._check_returned_well(screen=screen):
                        print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Returned well to Field.")
                        break
                    else:
                        return_check_count += 1
                        print(f"WARN: [{self.monitor_id}] Screen {screen.screen_id}: Field return check failed ({return_check_count}/{max_return_checks}). Retrying return...")
                        if not self._retry_field_return(screen=screen):
                            print(f"WARN: [{self.monitor_id}] Screen {screen.screen_id}: Failed to initiate field return retry.")
                        if stop_event.wait(2): break # 재시도 후 대기
                if return_check_count >= max_return_checks and not stop_event.is_set():
                     print(f"WARN: [{self.monitor_id}] Screen {screen.screen_id}: Field return check timed out after {max_return_checks} checks.")
        else:
            print(f"WARN: [{self.monitor_id}] Flight Failed on screen {screen.screen_id}. Returning to Monitoring.")

    def _handle_death(self, stop_event: threading.Event, screen: ScreenMonitorInfo):
        """DEAD 상태를 처리합니다. (부활 -> 물약 구매 -> 복귀 확인/웨이포인트)"""
        print(f"INFO: [{self.monitor_id}] Handling DEAD state on screen {screen.screen_id}...")

        # 1. 부활 시도
        if not self._process_recovery(screen=screen):
             print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: Failed to process recovery (revive).")
             return # 부활 실패 시 핸들러 종료

        # 2. 죽음 횟수 증가 및 로깅
        self.death_count += 1
        print(f"INFO: [{self.monitor_id}] Death Count: {self.death_count}")

        # 3. 죽음 횟수에 따른 분기
        if self.death_count > 2:
            # 3-A. 강제 필드 복귀
            print(f"INFO: [{self.monitor_id}] Death count > 2. Forcing FIELD context.")
            self.location_flag = Location.FIELD
            # 물약 구매 및 필드 귀환 시작
            if not self._buy_potion_and_initiate_return(screen=screen, context=Location.FIELD):
                 print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: Failed potion purchase/return after >2 deaths.")
                 return # 실패 시 핸들러 종료

            # 필드 복귀 확인
            print(f"INFO: [{self.monitor_id}] Checking Field return status (after >2 deaths)...")
            return_check_count = 0
            max_return_checks = 15
            while not stop_event.is_set() and return_check_count < max_return_checks:
                if self._check_returned_well(screen=screen):
                    print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Returned well to Field.")
                    break
                else:
                    return_check_count += 1
                    print(f"WARN: [{self.monitor_id}] Screen {screen.screen_id}: Field return check failed ({return_check_count}/{max_return_checks}). Retrying return...")
                    if not self._retry_field_return(screen=screen):
                        print(f"WARN: [{self.monitor_id}] Screen {screen.screen_id}: Failed to initiate field return retry.")
                    if stop_event.wait(2): break
            if return_check_count >= max_return_checks and not stop_event.is_set():
                 print(f"WARN: [{self.monitor_id}] Screen {screen.screen_id}: Field return check timed out after {max_return_checks} checks (death > 2).")

        else: # self.death_count <= 2
            # 3-B. 아레나 복귀 시도
            print(f"INFO: [{self.monitor_id}] Death count <= 2. Initiating Arena return & Waypoint Navigation.")
            # 물약 구매 (아레나 복귀 시나리오)
            if not self._buy_potion_and_initiate_return(screen=screen, context=Location.ARENA):
                print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: Failed potion purchase/return after <=2 deaths.")
                return # 실패 시 핸들러 종료

            # 웨이포인트 네비게이션 시작
            self._waypoint_navigation(stop_event) # 플레이스홀더 호출
            self.location_flag = Location.ARENA # 상태 업데이트
            print(f"INFO: [{self.monitor_id}] Waypoint navigation complete. Returning to Arena Monitoring.")

    def _execute_sequence(self, sequence_name: str, stop_event: threading.Event = None) -> bool:
        """YAML에 정의된 동작 시퀀스를 실행합니다."""
        try:
            # YAML 파일 경로 생성
            import yaml
            import os

            # 설정 폴더 경로 (프로젝트 루트 기준 상대 경로)
            config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                      "config", "sequences")
            yaml_path = os.path.join(config_dir, f"{sequence_name}.yaml")

            if not os.path.exists(yaml_path):
                print(f"ERROR: Sequence file not found: {yaml_path}")
                return False

            # YAML 파일 로드
            with open(yaml_path, 'r', encoding='utf-8') as f:
                sequence_data = yaml.safe_load(f)

            if not sequence_data:
                print(f"ERROR: Empty or invalid sequence data: {sequence_name}")
                return False

            # 첫 번째 키가 시퀀스 정의를 담고 있음
            sequence_key = next(iter(sequence_data))
            sequence = sequence_data[sequence_key]

            # 시퀀스의 각 단계(phase) 실행
            for phase in sequence:
                phase_name = phase.get('phase', 'unnamed')
                print(f"INFO: [{self.monitor_id}] Executing phase: {phase_name}")

                # 반복 실행이 필요한 경우
                repeat_count = phase.get('repeat', 1)
                interval = phase.get('interval', 0)

                for _ in range(repeat_count):
                    # 중지 신호 확인
                    if stop_event and stop_event.is_set():
                        print(f"INFO: [{self.monitor_id}] Sequence '{sequence_name}' interrupted by stop signal")
                        return False

                    # 단계 내 액션 실행
                    for action in phase.get('actions', []):
                        action_type = action.get('type', '')
                        key = action.get('key', '')
                        duration = action.get('duration', 0.1)

                        if action_type == 'key_press':
                            keyboard.press_and_release(key)
                        elif action_type == 'key_hold':
                            keyboard.press(key)
                        elif action_type == 'key_release':
                            keyboard.release(key)
                        elif action_type == 'wait':
                            pass  # duration으로만 대기

                        # 액션 후 지정된 시간만큼 대기
                        if duration > 0:
                            if stop_event and stop_event.wait(duration):
                                print(f"INFO: [{self.monitor_id}] Sequence interrupted during wait")
                                return False
                            else:
                                time.sleep(duration)

                    # 반복 간격 대기
                    if _ < repeat_count - 1 and interval > 0:
                        if stop_event and stop_event.wait(interval):
                            return False
                        else:
                            time.sleep(interval)

            print(f"INFO: [{self.monitor_id}] Sequence '{sequence_name}' completed successfully")
            return True

        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Failed to execute sequence '{sequence_name}': {e}")
            traceback.print_exc()
            # 안전을 위해 모든 키 해제
            keyboard.release('s')
            keyboard.release('w')
            keyboard.release('shift')
            keyboard.release('space')
            return False

    def _move_to_party_shared_wp(self, screen: ScreenMonitorInfo, wp_index: int) -> bool:
        """파티 리더-팔로워 방식 웨이포인트(WP3, WP4)로 이동"""
        try:
            if wp_index == 3:
                # WP3 - 점프 시작점으로 이동
                print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Moving to WP3 (Jump point)")

                # 1. 메뉴 열기 (필요시)
                if not self._click_relative(screen, 'main_menu_button', delay_after=0.5):
                    print(f"WARN: [{self.monitor_id}] Failed to click main menu, continuing...")

                # 2. 점프 시작점으로 이동하는 로직
                party_ui_template_path = template_paths.get_template(screen.screen_id, 'PARTY_UI')
                if party_ui_template_path and os.path.exists(party_ui_template_path):
                    party_ui_pos = image_utils.return_ui_location(party_ui_template_path, screen.region,
                                                                  self.confidence)
                    if party_ui_pos:
                        print(f"INFO: [{self.monitor_id}] Found Party UI, clicking")
                        pyautogui.click(party_ui_pos)
                        time.sleep(0.5)

                        # 3. 확인 또는 추가 액션 (필요시)
                        keyboard.press_and_release('y')
                        time.sleep(0.3)

                        # 4. 도착 대기
                        arrive_wait_time = 10  # 10초 대기
                        print(f"INFO: [{self.monitor_id}] Waiting {arrive_wait_time}s for arrival at jump point")
                        time.sleep(arrive_wait_time)

                        return True
                    else:
                        print(f"ERROR: [{self.monitor_id}] Party UI not found on screen")
                        return False
                else:
                    print(f"ERROR: [{self.monitor_id}] Party UI template not configured or not found")
                    return False

            elif wp_index == 4:
                # WP4 - 글라이더 비행 시퀀스
                print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Starting WP4 (Glider sequence)")

                # YAML 파일에 정의된 글라이더 시퀀스 실행
                return self._execute_sequence("wp4_glider", stop_event=self.stop_event)

            else:
                print(f"ERROR: [{self.monitor_id}] Unsupported party waypoint index: {wp_index}")
                return False

        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Exception during party shared waypoint {wp_index}: {e}")
            traceback.print_exc()
            return False

    def _waypoint_navigation(self, stop_event: threading.Event):
        """웨이포인트 네비게이션 로직을 처리합니다."""
        print(f"INFO: [{self.monitor_id}] Starting Waypoint Navigation...")

        # 현재 화면 결정 (일단 첫 번째 화면 사용)
        if not self.screens:
            print(f"ERROR: [{self.monitor_id}] No screens available for waypoint navigation.")
            return
        screen = self.screens[0]

        # 웨이포인트 초기화
        self.current_wp = 1
        self.max_wp = 5  # 임시 값, 필요시 동적 계산 가능

        while self.current_wp <= self.max_wp and not stop_event.is_set():
            print(f"INFO: [{self.monitor_id}] --- Waypoint Loop: Target WP {self.current_wp}/{self.max_wp} ---")

            # 1. 웨이포인트로 이동 시도
            if not self._move_to_wp(screen, self.current_wp):
                print(f"WARN: [{self.monitor_id}] Failed to initiate movement to WP {self.current_wp}.")
                # 실패 시 다음 웨이포인트로 넘어갈지, 재시도할지 결정
                # ...

            # 2. 웨이포인트 도착 확인 (여러 번 시도)
            reached = False
            check_attempts = 0
            max_check_attempts = 10

            while not reached and check_attempts < max_check_attempts and not stop_event.is_set():
                if self._check_reached_wp(screen, self.current_wp):
                    print(f"INFO: [{self.monitor_id}] Successfully reached WP {self.current_wp}.")
                    reached = True
                    break

                check_attempts += 1
                print(
                    f"INFO: [{self.monitor_id}] WP {self.current_wp} not reached yet ({check_attempts}/{max_check_attempts}).")

                # 못 찾으면 조정 시도
                if not self._look_for_wp(screen, self.current_wp):
                    print(f"WARN: [{self.monitor_id}] Failed to look for WP {self.current_wp}.")

                # 잠시 대기 후 다시 확인
                if stop_event.wait(1.0):
                    return  # 중지 신호 받으면 종료

            if not reached:
                print(
                    f"WARN: [{self.monitor_id}] Could not confirm reaching WP {self.current_wp}. Aborting navigation.")
                return

            # 마지막 웨이포인트에 도달한 경우
            if self.current_wp == self.max_wp:
                print(f"INFO: [{self.monitor_id}] Reached final WP {self.max_wp}. Checking combat spot...")

                # 전투 지점 확인 (여러 번 시도)
                spot_reached = False
                spot_check_attempts = 0
                max_spot_checks = 10

                while not spot_reached and spot_check_attempts < max_spot_checks and not stop_event.is_set():
                    if self._is_at_combat_spot(screen):
                        print(f"INFO: [{self.monitor_id}] Successfully arrived at combat spot.")
                        spot_reached = True
                        break

                    spot_check_attempts += 1
                    print(
                        f"INFO: [{self.monitor_id}] Combat spot not reached ({spot_check_attempts}/{max_spot_checks}).")

                    # 위치 조정 시도
                    if not self._perform_combat_spot_adjustment(screen):
                        print(f"WARN: [{self.monitor_id}] Failed to adjust position.")

                    if stop_event.wait(1.0):
                        return

                if not spot_reached:
                    print(
                        f"WARN: [{self.monitor_id}] Could not confirm arriving at combat spot. Navigation may be incomplete.")

                return  # 마지막 웨이포인트 처리 후 종료

            # 다음 웨이포인트로
            self.current_wp += 1

        print(f"INFO: [{self.monitor_id}] Waypoint navigation completed.")

    # === 메인 모니터링 루프 ===
    def run_loop(self, stop_event: threading.Event):
        """Orchestrator가 제어하는 메인 모니터링 루프."""
        print(f"INFO: Starting CombatMonitor {self.monitor_id} on {self.vd_name}...")
        if not self.screens:
             print(f"ERROR: [{self.monitor_id}] No screens added. Stopping monitor.")
             return

        # 초기화
        self.death_count = 0
        try:
            self.max_wp = _get_max_wp_num() # 플레이스홀더 호출
        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Error getting max waypoint number: {e}. Setting to 0.")
            self.max_wp = 0

        # 시작 위치 결정
        if not self._determine_initial_location(stop_event):
             print(f"INFO: [{self.monitor_id}] CombatMonitor stopped during initial location check.")
             return
        print(f"INFO: [{self.monitor_id}] Initial monitoring context: {self.location_flag.name}")

        # 메인 루프 시작
        while not stop_event.is_set():
            overall_state = CharacterState.NORMAL
            triggering_screen: Optional[ScreenMonitorInfo] = None

            try:
                # 모든 화면 상태 확인
                for screen in self.screens:
                    if stop_event.is_set(): break
                    current_screen_state = self._get_character_state_on_screen(screen)

                    # 상태 우선순위: DEAD > HOSTILE_ENGAGE > NORMAL
                    if current_screen_state == CharacterState.DEAD:
                        overall_state = CharacterState.DEAD
                        triggering_screen = screen
                        break # DEAD가 최우선
                    elif current_screen_state == CharacterState.HOSTILE_ENGAGE:
                        if overall_state == CharacterState.NORMAL:
                            overall_state = CharacterState.HOSTILE_ENGAGE
                            triggering_screen = screen
                            # HOSTILE은 다른 화면에서 DEAD가 나올 수 있으므로 break하지 않음

                if stop_event.is_set(): break # 상태 확인 중 종료 신호

                # 상태 변경 로깅
                current_context = self.location_flag.name
                triggering_id_for_log = triggering_screen.screen_id if triggering_screen else "N/A"
                if overall_state != CharacterState.NORMAL:
                     print(f"\nINFO: [{self.monitor_id}] Cycle Update. Overall State: {overall_state.name} "
                           f"(Triggered by: {triggering_id_for_log}, Context: {current_context})")

                # 상태별 핸들러 호출
                if overall_state == CharacterState.NORMAL:
                    pass # 정상 상태에서는 특별한 조치 없음
                elif overall_state == CharacterState.HOSTILE_ENGAGE:
                    if triggering_screen:
                        self._handle_hostile_engage(stop_event, triggering_screen)
                    else: # 이론적으로 발생하면 안 되지만 방어 코드
                        print(f"WARN: [{self.monitor_id}] HOSTILE_ENGAGE detected but triggering_screen is None.")
                elif overall_state == CharacterState.DEAD:
                    if triggering_screen:
                        self._handle_death(stop_event, triggering_screen)
                    else: # 이론적으로 발생하면 안 되지만 방어 코드
                       print(f"WARN: [{self.monitor_id}] DEAD detected but triggering_screen is None.")

                # 루프 주기 조절 (stop_event.wait 사용)
                if stop_event.wait(1.0): # 1초 대기하며 종료 신호 확인
                    break # 종료 신호 받으면 루프 탈출

            except Exception as e:
                # 메인 루프 내 예상치 못한 오류 처리
                print(f"ERROR: [{self.monitor_id}] Unhandled exception in main loop: {e}")
                traceback.print_exc()
                if stop_event.wait(5.0): # 오류 발생 시 5초 대기하며 종료 신호 확인
                     break # 종료 신호 받으면 루프 탈출

        # 루프 종료 시 stop 메서드 호출
        self.stop()

    def stop(self):
        """모니터를 중지하고 필요한 정리 작업을 수행합니다."""
        print(f"INFO: CombatMonitor {self.monitor_id} received stop signal. Cleaning up...")
        super().stop() # BaseMonitor의 stop 호출 (필요시)
        # 필요한 경우 추가적인 리소스 해제 로직

# === 독립 실행 테스트용 코드 ===
if __name__ == "__main__":
    print("INFO: Running CombatMonitor in standalone test mode...")
    stop_event = threading.Event()

    # 1. 모니터 인스턴스 생성
    monitor_config = {'confidence': 0.85}
    monitor = CombatMonitor(monitor_id="SRM1_Test", config=monitor_config, vd_name="TestVD")

    # 2. 화면 정보 로드 및 추가 (Orchestrator 역할 시뮬레이션)
    try:
        # utils.screen_info 모듈 임포트를 위한 경로 설정 (환경에 따라 조정 필요)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        utils_dir = os.path.join(os.path.dirname(os.path.dirname(current_dir)), 'NightCrows', 'utils')
        if utils_dir not in sys.path:
             sys.path.insert(0, utils_dir)

        from screen_info import SCREEN_REGIONS # NightCrows/utils/screen_info.py

        if SCREEN_REGIONS and isinstance(SCREEN_REGIONS, dict):
            for screen_id in ['S1', 'S2', 'S3', 'S4', 'S5']:
                 if screen_id in SCREEN_REGIONS:
                     monitor.add_screen(screen_id=screen_id, region=SCREEN_REGIONS[screen_id])
                 else:
                     print(f"WARN: Screen ID '{screen_id}' not found in SCREEN_REGIONS.")
        else:
            print("ERROR: Could not load or invalid SCREEN_REGIONS from screen_info.py")
            sys.exit(1)
    except ImportError:
        print("ERROR: Could not import SCREEN_REGIONS from NightCrows/utils/screen_info.py.")
        print(f"Current sys.path: {sys.path}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Error loading screen info: {e}")
        sys.exit(1)

    if not monitor.screens:
         print("ERROR: No screens were added to the monitor. Exiting test.")
         sys.exit(1)

    # 3. 모니터 스레드 시작
    print(f"INFO: Starting monitor thread for {len(monitor.screens)} screens...")
    monitor_thread = threading.Thread(target=monitor.run_loop, args=(stop_event,), daemon=True)
    monitor_thread.start()

    # 4. 테스트 실행 및 종료 처리
    try:
        test_duration = 120 # 테스트 실행 시간 (초)
        print(f"INFO: Monitor running for {test_duration} seconds... Press Ctrl+C to stop early.")
        start_time = time.time()
        # 메인 스레드는 모니터 스레드가 끝나거나 시간이 다 되거나 Ctrl+C 입력 전까지 대기
        while monitor_thread.is_alive() and time.time() - start_time < test_duration:
            # KeyboardInterrupt 를 잡기 위해 짧게 sleep
            time.sleep(0.5)

        if monitor_thread.is_alive():
             print(f"\nINFO: Standalone test duration ({test_duration}s) elapsed.")
        else:
             print("\nINFO: Monitor thread finished early.")

    except KeyboardInterrupt:
        print("\nINFO: Ctrl+C detected. Stopping monitor...")
    finally:
        # 모니터 스레드 종료 신호 및 대기
        if monitor_thread.is_alive():
            print("INFO: Signaling monitor thread to stop...")
            stop_event.set()
            monitor_thread.join(timeout=10) # 최대 10초 대기
            if monitor_thread.is_alive():
                print("WARN: Monitor thread did not stop gracefully.")
        print("INFO: Standalone test finished.")


# **주요 TODO 사항:**
# - 웨이포인트 관련 함수들 구현 필요 (_move_to_wp, _check_reached_wp 등)
# - screen_info.py의 FIXED_UI_COORDS 실제 좌표값 측정 필요
# - S2-S5 템플릿 경로 추가 필요 (template_paths.py)