from typing import List, Tuple, Optional
import time
import win32api
import win32con
import keyboard
import pyautogui
import numpy as np
import cv2
import os
from threading import Lock, Event
import traceback

# 경로 및 모델 임포트
from Orchestrator.Raven2.Combat_Monitor.src.models.screen_info import CombatScreenInfo, ScreenState
from Orchestrator.Raven2.Combat_Monitor.src.config.template_paths import TEMPLATE_PATHS
from Orchestrator.Raven2.utils.screen_info import SCREEN_REGIONS, FIXED_UI_COORDS

# 공통 유틸리티 import 추가 (RAVEN2용)
from Orchestrator.Raven2.utils.image_utils import (
    return_ui_location,
    compare_images
)


def verify_template_paths():
    base_path = 'C:/Users/yjy16/template/RAVEN2'
    if not os.path.exists(base_path):
        print(f"기본 경로가 존재하지 않습니다: {base_path}")
        return False
    for category in TEMPLATE_PATHS:
        for template_type in TEMPLATE_PATHS[category]:
            for window_id in ['S1', 'S2', 'S3', 'S4', 'S5']:
                if window_id in TEMPLATE_PATHS[category][template_type]:
                    path = TEMPLATE_PATHS[category][template_type][window_id]
                    if not os.path.exists(path):
                        print(f"템플릿 파일이 없습니다: {path}")
                        return False
    print("모든 (정의된) 템플릿 파일이 정상적으로 존재합니다.")
    return True


class CombatMonitor:
    def __init__(self, orchestrator=None):
        self.screens: List[CombatScreenInfo] = []
        self.orchestrator = orchestrator  # Orchestrator 참조 추가
        self.check_interval = 0.5
        self.confidence_threshold = 0.85
        self.io_lock = Lock()

        if not verify_template_paths():
            raise FileNotFoundError("필요한 템플릿 파일들을 찾을 수 없습니다.")

    def add_screen(self, window_id: str, region: Tuple[int, int, int, int], ratio: float = 1.0):
        screen = CombatScreenInfo(window_id=window_id, region=region, ratio=ratio)
        self.screens.append(screen)
        print(f"Screen registered - ID: {window_id}, Region: {region}, Ratio: {ratio}")

    def check_status(self, screen_info: CombatScreenInfo) -> ScreenState:
        """상태 확인 - 중앙집중식 스크린샷 사용"""
        try:
            # 변경: 중앙집중식 스크린샷 사용
            screen_img = self.orchestrator.capture_screen_safely(screen_info.window_id)
            if screen_img is None:
                return screen_info.current_state

            template_dead_path = TEMPLATE_PATHS['status']['dead'].get(screen_info.window_id)
            if template_dead_path and os.path.exists(template_dead_path):
                template_dead = cv2.imread(template_dead_path)
                if template_dead is not None and compare_images(screen_img, template_dead):
                    return ScreenState.DEAD

            template_abnormal_path = TEMPLATE_PATHS['status']['abnormal'].get(screen_info.window_id)
            if template_abnormal_path and os.path.exists(template_abnormal_path):
                template_abnormal = cv2.imread(template_abnormal_path)
                if template_abnormal is not None and compare_images(screen_img, template_abnormal):
                    return ScreenState.ABNORMAL

            template_awake_path = TEMPLATE_PATHS['status']['awake'].get(screen_info.window_id)
            if template_awake_path and os.path.exists(template_awake_path):
                template_awake = cv2.imread(template_awake_path)
                if template_awake is not None and compare_images(screen_img, template_awake):
                    return ScreenState.AWAKE

            return ScreenState.SLEEP

        except KeyError as e:
            print(f"[{screen_info.window_id}] Error accessing TEMPLATE_PATHS key: {e}. Check config/template_paths.py")
            return screen_info.current_state
        except Exception as e:
            print(f"[{screen_info.window_id}] Error in check_status: {e}")
            return screen_info.current_state

    def process_death_recovery(self, screen_info: CombatScreenInfo) -> bool:
        """사망 복구 처리 - 공통 유틸리티 사용"""
        try:
            center_x = screen_info.region[0] + (screen_info.region[2] // 2)
            center_y = screen_info.region[1] + (screen_info.region[3] // 2)
            pyautogui.click(center_x, center_y)
            time.sleep(0.2)

            template_path = TEMPLATE_PATHS['death']['return_button'].get(screen_info.window_id)
            if not template_path:
                return False

            # 변경: 중앙집중식 스크린샷 + 공통 유틸리티 사용
            screenshot_img = self.orchestrator.capture_screen_safely(screen_info.window_id)
            return_pos = return_ui_location(template_path, screen_info.region, self.confidence_threshold,
                                            screenshot_img)
            if not return_pos:
                return False

            pyautogui.click(return_pos[0], return_pos[1])
            time.sleep(0.5)
            return True
        except Exception as e:
            print(f"[{screen_info.window_id}] Error in process_death_recovery: {e}")
            return False

    def retreat_to_safe_zone(self, screen_info: CombatScreenInfo) -> bool:
        """안전지대 후퇴 - 공통 유틸리티 사용"""
        try:
            print(f"[{screen_info.window_id}] 후퇴 시도")
            confirm_clicked = False

            # 중앙집중식 스크린샷 획득
            screenshot_img = self.orchestrator.capture_screen_safely(screen_info.window_id)

            # 확인 버튼 클릭 (템플릿 매칭 시도)
            confirm_button_path = TEMPLATE_PATHS['retreat']['confirm_button'].get(screen_info.window_id)
            confirm_pos = None
            if confirm_button_path:
                confirm_pos = return_ui_location(confirm_button_path, screen_info.region, 0.8, screenshot_img)

            if confirm_pos:
                print(f"[{screen_info.window_id}] 템플릿으로 확인 버튼 클릭 시도 at ({confirm_pos[0]}, {confirm_pos[1]})")
                pyautogui.click(confirm_pos[0], confirm_pos[1])
                time.sleep(0.5)
                confirm_clicked = True
            elif screen_info.window_id in FIXED_UI_COORDS and 'retreat_confirm_button' in FIXED_UI_COORDS[
                screen_info.window_id]:
                # 템플릿 못 찾으면 고정 좌표 시도
                relative_coords = FIXED_UI_COORDS[screen_info.window_id]['retreat_confirm_button']
                screen_x, screen_y = screen_info.region[0], screen_info.region[1]
                absolute_x = screen_x + relative_coords[0]
                absolute_y = screen_y + relative_coords[1]
                click_x = absolute_x + np.random.randint(-1, 2)
                click_y = absolute_y + np.random.randint(-1, 2)
                print(f"[{screen_info.window_id}] 고정 좌표로 확인 버튼 클릭 시도 at ({click_x}, {click_y})")
                pyautogui.click(click_x, click_y)
                time.sleep(0.5)
                confirm_clicked = True
            else:
                print(f"[{screen_info.window_id}] 확인 버튼(템플릿/고정좌표) 정보 없음. 확인 버튼 건너뛰기.")

            # 후퇴 버튼 클릭
            template_path = TEMPLATE_PATHS['retreat']['retreat_button'].get(screen_info.window_id)
            if not template_path:
                return False

            # 새 스크린샷으로 후퇴 버튼 찾기
            screenshot_img = self.orchestrator.capture_screen_safely(screen_info.window_id)
            retreat_pos = return_ui_location(template_path, screen_info.region, self.confidence_threshold,
                                             screenshot_img)
            if retreat_pos:
                print(f"[{screen_info.window_id}] 후퇴 버튼 클릭")
                pyautogui.click(retreat_pos[0], retreat_pos[1])
                time.sleep(0.5)
                return True
            print(f"[{screen_info.window_id}] 후퇴 버튼 못찾음 (확인 버튼 클릭 여부: {confirm_clicked})")
            return False
        except Exception as e:
            print(f"[{screen_info.window_id}] 후퇴 실패: {str(e)}")
            return False

    def replenish_potions(self, screen_info: CombatScreenInfo) -> bool:
        """물약 보충 - 공통 유틸리티 사용"""
        try:
            print(f"[{screen_info.window_id}] 물약 보충 시작")
            time.sleep(2.5)

            # 상점 UI 찾기
            shop_ui_path = TEMPLATE_PATHS['potion']['shop_ui'].get(screen_info.window_id)
            if not shop_ui_path:
                return False

            shop_pos = self.wait_for_ui(screen_info, shop_ui_path, max_wait_time=3.0, interval=0.5, threshold=0.8)
            if not shop_pos:
                print(f"[{screen_info.window_id}] 상점 UI를 찾을 수 없음 (3초)")
                return False

            print(f"[{screen_info.window_id}] 상점 UI 클릭")
            pyautogui.click(shop_pos[0], shop_pos[1])
            time.sleep(1.5)

            # 구매 버튼 찾기
            buy_button_path = TEMPLATE_PATHS['potion']['buy_button'].get(screen_info.window_id)
            if not buy_button_path:
                return False

            buy_pos = self.wait_for_ui(screen_info, buy_button_path, max_wait_time=3.0, interval=0.5, threshold=0.75)
            if not buy_pos:
                print(f"[{screen_info.window_id}] 구매 버튼을 찾을 수 없음 (3초)")
                keyboard.press_and_release('esc')
                time.sleep(1.0)
                return False

            print(f"[{screen_info.window_id}] 구매 버튼 클릭")
            pyautogui.click(buy_pos[0], buy_pos[1])
            time.sleep(0.8)

            # 확인 버튼 찾기
            confirm_path = TEMPLATE_PATHS['potion']['confirm'].get(screen_info.window_id)
            if not confirm_path:
                return False

            confirm_pos = self.wait_for_ui(screen_info, confirm_path, max_wait_time=3.0, interval=0.5, threshold=0.8)
            if not confirm_pos:
                print(f"[{screen_info.window_id}] 확인 버튼을 찾을 수 없음 (구매 후, 3초)")
                keyboard.press_and_release('esc')
                time.sleep(1.0)
                return False

            print(f"[{screen_info.window_id}] 확인 버튼 클릭 (구매 후)")
            pyautogui.click(confirm_pos[0], confirm_pos[1])
            time.sleep(0.8)

            print(f"[{screen_info.window_id}] 물약 보충 완료")
            keyboard.press_and_release('esc')
            time.sleep(1.0)
            return True

        except Exception as e:
            print(f"[{screen_info.window_id}] 물약 보충 중 예외 발생: {str(e)}")
            try:
                keyboard.press_and_release('esc')
            except:
                pass
            return False

    def return_to_combat(self, screen_info: CombatScreenInfo) -> bool:
        """전투 복귀 - 공통 유틸리티 사용"""
        try:
            # 1. 첫 번째 UI 클릭
            template1_path = TEMPLATE_PATHS['combat']['template1'].get(screen_info.window_id)
            if not template1_path:
                return False

            screenshot_img = self.orchestrator.capture_screen_safely(screen_info.window_id)
            pos1 = return_ui_location(template1_path, screen_info.region, self.confidence_threshold, screenshot_img)
            if not pos1:
                print(f"[{screen_info.window_id}] Combat Template 1 (마을 UI?) not found.")
                return False
            pyautogui.click(pos1[0], pos1[1])

            # 2. 상대 좌표 클릭
            relative_click_x = pos1[0] - int(100 * screen_info.ratio)
            relative_click_y = pos1[1] + int(20 * screen_info.ratio)
            pyautogui.click(relative_click_x, relative_click_y)
            time.sleep(0.8)

            # 3. 드래그 로직 (S3 추가 오프셋 적용)
            screen_x, screen_y, screen_w, screen_h = screen_info.region
            center_x = screen_x + (screen_w // 2)
            center_y = screen_y + (screen_h // 2)

            base_start_offset_x = 100
            base_start_offset_y = 50
            base_drag_dist_x = 210
            base_drag_dist_y = 150
            drag_duration = 1.0

            s3_start_offset_x_adj = 0
            s3_start_offset_y_adj = 0
            s3_drag_dist_x_adj = 0
            s3_drag_dist_y_adj = 0

            if screen_info.window_id == "S3":
                print(f"[{screen_info.window_id}] Applying additional drag adjustments for S3.")
                s3_start_offset_x_adj = -20
                s3_start_offset_y_adj = -10
                s3_drag_dist_x_adj = -20
                s3_drag_dist_y_adj = -20

            final_start_offset_x = base_start_offset_x + s3_start_offset_x_adj
            final_start_offset_y = base_start_offset_y + s3_start_offset_y_adj
            final_drag_dist_x = base_drag_dist_x + s3_drag_dist_x_adj
            final_drag_dist_y = base_drag_dist_y + s3_drag_dist_y_adj

            start_drag_abs_x = center_x + final_start_offset_x
            start_drag_abs_y = center_y + final_start_offset_y
            end_drag_abs_x = center_x - final_drag_dist_x
            end_drag_abs_y = center_y + final_drag_dist_y

            start_drag_abs_x = max(screen_x, min(start_drag_abs_x, screen_x + screen_w - 1))
            start_drag_abs_y = max(screen_y, min(start_drag_abs_y, screen_y + screen_h - 1))
            end_drag_abs_x = max(screen_x, min(end_drag_abs_x, screen_x + screen_w - 1))
            end_drag_abs_y = max(screen_y, min(end_drag_abs_y, screen_y + screen_h - 1))

            print(f"[{screen_info.window_id}] Drag Start (Clamped): ({start_drag_abs_x}, {start_drag_abs_y})")
            print(f"[{screen_info.window_id}] Drag End (Clamped): ({end_drag_abs_x}, {end_drag_abs_y})")

            pyautogui.moveTo(start_drag_abs_x, start_drag_abs_y)
            time.sleep(0.3)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
            time.sleep(0.1)
            pyautogui.moveTo(end_drag_abs_x, end_drag_abs_y, duration=drag_duration)
            time.sleep(0.1)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)
            time.sleep(1.0)

            # 4. 드래그 후 UI 클릭
            after_drag_positions = {
                "S1": (410, 60), "S2": (1106, 76), "S3": (367, 427),
                "S4": (416, 766), "S5": (900, 600)
            }
            target_pos = after_drag_positions.get(screen_info.window_id)
            if not target_pos:
                print(f"[{screen_info.window_id}] 드래그 후 UI 절대 좌표 정보를 찾을 수 없음")
                return False
            print(f"[{screen_info.window_id}] 드래그 후 UI 클릭 (절대 좌표: {target_pos})")
            pyautogui.click(target_pos[0], target_pos[1])
            time.sleep(0.5)

            # 5. Template 2 찾아서 클릭
            template2_path = TEMPLATE_PATHS['combat']['template2'].get(screen_info.window_id)
            if not template2_path:
                return False

            pos = self.wait_for_ui(screen_info, template2_path, max_wait_time=3.0, interval=0.5)
            if not pos:
                print(f"[{screen_info.window_id}] Template2를 찾을 수 없음 - 3초")
                return False
            pyautogui.click(pos[0], pos[1])
            time.sleep(0.2)

            # 6. 마지막 상대 이동 후 클릭
            move_pixels_x = int(277 * screen_info.ratio)
            move_pixels_y = int(64 * screen_info.ratio)
            pyautogui.moveRel(-move_pixels_x, -move_pixels_y)
            pyautogui.click()
            time.sleep(0.2)

            return True
        except Exception as e:
            print(f"[{screen_info.window_id}] Error in return_to_combat: {e}")
            try:
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)
            except:
                pass
            return False

    def perform_repeated_combat_return(self, screen_info: CombatScreenInfo) -> None:
        """파티 집결을 위한 재시도 액션"""
        if screen_info.window_id == "S5":
            return

        try:
            print(f"[{screen_info.window_id}] Performing single attempt of repeated return actions...")

            # 1. Map UI 활성화 클릭 (하드코딩된 절대 좌표)
            map_ui_activate = {
                "S1": (92, 77), "S2": (791, 86), "S3": (114, 435), "S4": (79, 783)
            }
            target_pos = map_ui_activate.get(screen_info.window_id)
            if not target_pos:
                print(f"[{screen_info.window_id}] Map UI 활성화 좌표 없음.")
                return

            print(f"[{screen_info.window_id}] Map UI 활성화 클릭 (절대 좌표: {target_pos})")
            pyautogui.click(target_pos[0], target_pos[1])
            time.sleep(0.6)

            # 2. Template2 찾아서 클릭
            template2_path = TEMPLATE_PATHS['combat']['template2'].get(screen_info.window_id)
            if not template2_path:
                print(f"[{screen_info.window_id}] Template2 path not found.")
                return

            pos = self.wait_for_ui(screen_info, template2_path, max_wait_time=4.0, interval=0.5, threshold=0.8)
            if not pos:
                print(f"[{screen_info.window_id}] Template2를 찾을 수 없음 (within perform_repeated_combat_return).")
                return

            pyautogui.click(pos[0], pos[1])
            time.sleep(0.2)

            # 3. 상대 이동 후 클릭
            move_pixels_x = int(277 * screen_info.ratio)
            move_pixels_y = int(64 * screen_info.ratio)
            pyautogui.moveRel(-move_pixels_x, -move_pixels_y)
            pyautogui.click()
            time.sleep(0.2)

            print(f"[{screen_info.window_id}] Single attempt of repeated return actions finished.")

        except Exception as e:
            print(f"[{screen_info.window_id}] Error in perform_repeated_combat_return: {e}")

    def wait_for_ui(self, screen_info, template_path, max_wait_time=3.0, interval=0.5, threshold=None,
                    stop_event: Event = None):
        """UI 대기 - 공통 유틸리티 사용"""
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            # Orchestrator로부터 중지 신호 확인
            if stop_event and stop_event.is_set():
                print(
                    f"[{screen_info.window_id}] Stop event received while waiting for UI: {os.path.basename(template_path)}")
                return None

            # 변경: 중앙집중식 스크린샷 + 공통 유틸리티 사용
            screenshot_img = self.orchestrator.capture_screen_safely(screen_info.window_id)
            pos = return_ui_location(template_path, screen_info.region, threshold or self.confidence_threshold,
                                     screenshot_img)
            if pos:
                return pos

            # time.sleep 대신 stop_event.wait 사용 (더 반응성 좋음)
            if stop_event:
                if stop_event.wait(timeout=interval):
                    print(
                        f"[{screen_info.window_id}] Stop event received during wait interval for UI: {os.path.basename(template_path)}")
                    return None
            else:
                time.sleep(interval)
        return None

    def is_at_combat_spot(self, screen_info: CombatScreenInfo, check_duration: float = 3.0,
                          interval: float = 0.3, stop_event: Event = None) -> bool:
        """전투 지점 확인 - 픽셀 체크"""
        if screen_info.window_id == "S5":
            return True

        try:
            if screen_info.window_id in FIXED_UI_COORDS and 'leader_hp_pixel' in FIXED_UI_COORDS[screen_info.window_id]:
                relative_coords = FIXED_UI_COORDS[screen_info.window_id]['leader_hp_pixel']
            else:
                print(f"[{screen_info.window_id}] 'leader_hp_pixel' coordinate not found.")
                return False

            screen_x, screen_y = screen_info.region[0], screen_info.region[1]
            absolute_x = screen_x + relative_coords[0]
            absolute_y = screen_y + relative_coords[1]

            target_hp_color = (108, 69, 71)
            tolerance_level = 15

            start_time = time.time()
            check_count = 0
            while time.time() - start_time < check_duration:
                # Orchestrator로부터 중지 신호 확인
                if stop_event and stop_event.is_set():
                    print(f"[{screen_info.window_id}] Stop event received while checking combat spot.")
                    return False

                check_count += 1
                current_time_elapsed = time.time() - start_time

                try:
                    match = pyautogui.pixelMatchesColor(absolute_x, absolute_y, target_hp_color,
                                                        tolerance=tolerance_level)
                    if match:
                        return True
                except OSError:
                    pass
                except Exception as pixel_err:
                    print(f"    ERROR: Error during pixel check {check_count}: {pixel_err}")

                # time.sleep 대신 stop_event.wait 사용
                if stop_event:
                    if stop_event.wait(timeout=interval):
                        print(f"[{screen_info.window_id}] Stop event received during check interval for combat spot.")
                        return False
                else:
                    time.sleep(interval)

            return False

        except KeyError:
            print(f"[{screen_info.window_id}] Error accessing FIXED_UI_COORDS key.")
            return False
        except Exception as e:
            print(f"[{screen_info.window_id}] Error checking combat spot pixel: {e}")
            return False

    def is_in_safe_zone(self, screen_info: CombatScreenInfo) -> bool:
        """안전지대 확인"""
        try:
            template_path = TEMPLATE_PATHS['combat']['template1'].get(screen_info.window_id)
            if not template_path:
                return False

            # 변경: 중앙집중식 스크린샷 + 공통 유틸리티 사용
            screenshot_img = self.orchestrator.capture_screen_safely(screen_info.window_id)
            location = return_ui_location(template_path, screen_info.region, 0.8, screenshot_img)
            return bool(location)
        except Exception as e:
            print(f"[{screen_info.window_id}] Error checking safe zone status: {e}")
            return False

    def is_potion_purchase_complete(self, screen_info: CombatScreenInfo) -> bool:
        """물약 구매 완료 확인"""
        try:
            shop_ui_path = TEMPLATE_PATHS['potion']['confirm'].get(screen_info.window_id)
            if not shop_ui_path:
                return True

            # 변경: 중앙집중식 스크린샷 + 공통 유틸리티 사용
            screenshot_img = self.orchestrator.capture_screen_safely(screen_info.window_id)
            location = return_ui_location(shop_ui_path, screen_info.region, 0.8, screenshot_img)
            return not bool(location)  # UI가 안보이면 True
        except Exception as e:
            print(f"[{screen_info.window_id}] Error checking potion purchase completion: {e}")
            return False

    def is_recovered(self, screen_info: CombatScreenInfo) -> bool:
        """복구 완료 확인"""
        return self.is_in_safe_zone(screen_info)

    def run_loop(self, stop_event: Event):
        """Orchestrator와 호환되는 메인 모니터링 루프"""
        print(f"CombatMonitor run_loop started for screens: {[s.window_id for s in self.screens]}")

        while not stop_event.is_set():
            try:
                for screen in self.screens:
                    if stop_event.is_set():
                        break

                    state = screen.current_state

                    # 상태별 처리 로직
                    if state == ScreenState.SLEEP or state == ScreenState.AWAKE:
                        visual_status = self.check_status(screen)
                        if visual_status != state:
                            print(f"[{screen.window_id}] Visual state changed: {state.name} -> {visual_status.name}.")
                            screen.current_state = visual_status
                            screen.retry_count = 0

                    elif state == ScreenState.ABNORMAL:
                        print(f"[{screen.window_id}] State is ABNORMAL. Attempting retreat.")
                        action_success = False
                        with self.io_lock:
                            action_success = self.retreat_to_safe_zone(screen)
                        if action_success:
                            print(f"[{screen.window_id}] Retreat initiated. Changing state to RETREATING.")
                            screen.current_state = ScreenState.RETREATING
                            screen.retry_count = 0
                        else:
                            print(
                                f"[{screen.window_id}] Retreat initiation failed (Attempt {screen.retry_count + 1}). Retrying ABNORMAL state.")
                            screen.retry_count += 1
                            if screen.retry_count > 3:
                                print(
                                    f"[{screen.window_id}] Retreat failed after multiple retries. Setting state to SLEEP for manual check.")
                                screen.current_state = ScreenState.SLEEP
                        time.sleep(0.5)

                    elif state == ScreenState.RETREATING:
                        print(f"[{screen.window_id}] State is RETREATING. Checking for safe zone.")
                        if self.is_in_safe_zone(screen):
                            print(f"[{screen.window_id}] Safe zone confirmed. Changing state to SAFE_ZONE.")
                            screen.current_state = ScreenState.SAFE_ZONE
                            screen.retry_count = 0
                        else:
                            screen.retry_count += 1
                            if screen.retry_count > 60:
                                print(f"[{screen.window_id}] Retreat timeout. Setting state to SLEEP for manual check.")
                                screen.current_state = ScreenState.SLEEP

                    elif state == ScreenState.SAFE_ZONE:
                        print(f"[{screen.window_id}] State is SAFE_ZONE. Attempting to purchase potions.")
                        action_success = False
                        with self.io_lock:
                            action_success = self.replenish_potions(screen)
                        if action_success:
                            print(
                                f"[{screen.window_id}] Potion purchase seems complete. Changing state to POTIONS_PURCHASED.")
                            screen.current_state = ScreenState.POTIONS_PURCHASED
                            screen.retry_count = 0
                        else:
                            print(
                                f"[{screen.window_id}] Potion purchase failed (Attempt {screen.retry_count + 1}). Retrying SAFE_ZONE state.")
                            screen.retry_count += 1
                            if screen.retry_count > 3:
                                print(
                                    f"[{screen.window_id}] Potion purchase failed after multiple retries. Setting state to SLEEP.")
                                screen.current_state = ScreenState.SLEEP
                        time.sleep(0.5)

                    elif state == ScreenState.POTIONS_PURCHASED:
                        print(f"[{screen.window_id}] State is POTIONS_PURCHASED. Attempting return to combat.")
                        action_success = False
                        with self.io_lock:
                            action_success = self.return_to_combat(screen)
                        if action_success:
                            print(
                                f"[{screen.window_id}] Return to combat initiated. Changing state to RETURNING_TO_COMBAT.")
                            screen.current_state = ScreenState.RETURNING_TO_COMBAT
                            screen.retry_count = 0
                        else:
                            print(
                                f"[{screen.window_id}] Return to combat initiation failed (Attempt {screen.retry_count + 1}). Retrying POTIONS_PURCHASED.")
                            screen.retry_count += 1
                            if screen.retry_count > 3:
                                print(
                                    f"[{screen.window_id}] Return to combat failed after multiple retries. Setting state to SLEEP.")
                                screen.current_state = ScreenState.SLEEP
                        time.sleep(0.5)

                    elif state == ScreenState.RETURNING_TO_COMBAT:
                        wait_time = 3.3
                        print(
                            f"[{screen.window_id}] State is RETURNING_TO_COMBAT. Waiting {wait_time}s before checking combat spot...")
                        if stop_event.wait(timeout=wait_time):
                            break

                        print(f"[{screen.window_id}] Checking combat spot.")
                        if self.is_at_combat_spot(screen, stop_event=stop_event):
                            print(f"[{screen.window_id}] Combat spot confirmed.")
                            screen.retry_count = 0
                            print(f"[{screen.window_id}] Setting state to AWAKE.")
                            screen.current_state = ScreenState.AWAKE
                        else:
                            if not stop_event.is_set():
                                screen.retry_count += 1
                                print(f"[{screen.window_id}] Combat spot not confirmed (Check {screen.retry_count}).")
                                if screen.retry_count > 10:
                                    print(f"[{screen.window_id}] Combat spot check timeout. Setting state to SLEEP.")
                                    screen.current_state = ScreenState.SLEEP
                                else:
                                    if screen.window_id != "S5":
                                        print(f"[{screen.window_id}] Attempting repeated return action.")
                                        with self.io_lock:
                                            self.perform_repeated_combat_return(screen)
                                        print(f"[{screen.window_id}] Repeated return action finished.")
                                        if stop_event.wait(timeout=0.5):
                                            break

                    elif state == ScreenState.DEAD:
                        print(f"[{screen.window_id}] State is DEAD. Attempting recovery.")
                        action_success = False
                        with self.io_lock:
                            action_success = self.process_death_recovery(screen)
                        if action_success:
                            print(f"[{screen.window_id}] Recovery initiated. Changing state to RECOVERING.")
                            screen.current_state = ScreenState.RECOVERING
                            screen.retry_count = 0
                        else:
                            print(
                                f"[{screen.window_id}] Recovery initiation failed (Attempt {screen.retry_count + 1}). Retrying DEAD state.")
                            screen.retry_count += 1
                            if screen.retry_count > 3:
                                print(
                                    f"[{screen.window_id}] Recovery failed after multiple retries. Setting state to SLEEP.")
                                screen.current_state = ScreenState.SLEEP
                        time.sleep(0.5)

                    elif state == ScreenState.RECOVERING:
                        print(f"[{screen.window_id}] State is RECOVERING. Checking for recovery completion.")
                        if self.is_recovered(screen):
                            print(
                                f"[{screen.window_id}] Recovery seems complete (in safe zone). Changing state to SAFE_ZONE.")
                            screen.current_state = ScreenState.SAFE_ZONE
                            screen.retry_count = 0
                        else:
                            screen.retry_count += 1
                            if screen.retry_count > 60:
                                print(f"[{screen.window_id}] Recovery timeout. Setting state to SLEEP.")
                                screen.current_state = ScreenState.SLEEP

                    else:
                        # SLEEP/AWAKE 외 처리되지 않은 상태
                        print(f"[{screen.window_id}] Unhandled state: {state.name}")
                        screen.current_state = ScreenState.SLEEP

                # 모든 화면 처리 후 루프 지연
                if stop_event.is_set():
                    break
                if stop_event.wait(timeout=self.check_interval):
                    break

            except Exception as e:
                print(f"!!! Unhandled exception in CombatMonitor run_loop: {e} !!!")
                traceback.print_exc()
                if stop_event.wait(timeout=5.0):
                    break

        print(f"CombatMonitor run_loop stopped.")

    def stop(self):
        """Orchestrator가 호출할 수 있는 종료 처리 메서드"""
        print("CombatMonitor stop() method called. Performing cleanup if necessary...")


if __name__ == "__main__":
    print("CombatMonitor 모듈 직접 실행 테스트 (Orchestrator 없이)")

    monitor = CombatMonitor()

    # 테스트용 화면 등록 (실제 환경에 맞게 수정 필요)
    try:
        monitor.add_screen(window_id="S1", region=SCREEN_REGIONS['S1'], ratio=0.85)
        monitor.add_screen(window_id="S2", region=SCREEN_REGIONS['S2'], ratio=1.0)
        monitor.add_screen(window_id="S3", region=SCREEN_REGIONS['S3'], ratio=1.0)
        monitor.add_screen(window_id="S4", region=SCREEN_REGIONS['S4'], ratio=1.0)
        monitor.add_screen(window_id="S5", region=SCREEN_REGIONS['S5'], ratio=1.4)
    except KeyError as e:
        print(f"스크린 ID '{e}'에 대한 정보가 screen_info.py에 없습니다. 확인해주세요.")
        exit()

    print("테스트 시작... Ctrl+C 로 종료")

    # 테스트용 stop_event 생성
    test_stop_event = Event()

    try:
        # 실제 run_loop 실행
        monitor.run_loop(stop_event=test_stop_event)
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt 수신! 종료 중...")
        test_stop_event.set()
        monitor.stop()
    except Exception as e:
        print(f"테스트 중 오류 발생: {e}")
        traceback.print_exc()
        test_stop_event.set()
        monitor.stop()
    finally:
        print("테스트 종료.")