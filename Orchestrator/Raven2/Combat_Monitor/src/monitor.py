from typing import List, Tuple, Optional
import time
import win32api
import win32con
import keyboard
import pyautogui
import numpy as np
import cv2
import os
from threading import Lock, Event # Event 추가
import traceback

# 경로 및 모델 임포트
from Orchestrator.Raven2.Combat_Monitor.src.models.screen_info import CombatScreenInfo, ScreenState
from Orchestrator.Raven2.Combat_Monitor.src.config.template_paths import TEMPLATE_PATHS
from Orchestrator.Raven2.utils.screen_info import SCREEN_REGIONS, FIXED_UI_COORDS # FIXED_UI_COORDS 사용 가정

def verify_template_paths():
    # (이 함수 내용은 변경 없음)
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
    # __init__ 수정: self.running 제거 또는 기본값 False 설정 가능, 필요 없는 인자 제거
    def __init__(self):
        self.screens: List[CombatScreenInfo] = []
        # self.running = True # Orchestrator의 stop_event로 제어되므로 제거 또는 False로 초기화
        self.check_interval = 0.5
        self.confidence_threshold = 0.85
        self.io_lock = Lock()

        if not verify_template_paths():
            raise FileNotFoundError("필요한 템플릿 파일들을 찾을 수 없습니다.")

    def add_screen(self, window_id: str, region: Tuple[int, int, int, int], ratio: float = 1.0):
        # (변경 없음)
        screen = CombatScreenInfo(window_id=window_id, region=region, ratio=ratio)
        self.screens.append(screen)
        print(f"Screen registered - ID: {window_id}, Region: {region}, Ratio: {ratio}")

    def return_ui_location(self, screen_info: CombatScreenInfo, template_path: str, threshold: float = None) -> \
            Optional[Tuple[int, int]]:
        # (변경 없음)
        if threshold is None:
            threshold = self.confidence_threshold

        if not os.path.exists(template_path):
            print(f"[{screen_info.window_id}] 템플릿 파일을 찾을 수 없습니다: {template_path}")
            return None
        try:
            screen = pyautogui.screenshot(region=screen_info.region)
            if screen is None:
                 print(f"[{screen_info.window_id}] 스크린샷 실패 (region: {screen_info.region})")
                 return None
            template = cv2.imread(template_path)
            if template is None:
                print(f"[{screen_info.window_id}] 템플릿 이미지를 로드할 수 없습니다: {template_path}")
                return None

            screen_gray = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2GRAY)
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

            result = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

            if max_val > threshold:
                template_height, template_width = template_gray.shape
                center_x = screen_info.region[0] + max_loc[0] + template_width // 2
                center_y = screen_info.region[1] + max_loc[1] + template_height // 2
                return center_x, center_y
            return None
        except Exception as e:
            print(f"[{screen_info.window_id}] UI 위치 확인 중 오류 발생: {str(e)}")
            return None

    def compare_images(self, screen_img, template_img, threshold=None):
        # (변경 없음)
        if threshold is None:
            threshold = self.confidence_threshold
        try:
            screen_gray = cv2.cvtColor(np.array(screen_img), cv2.COLOR_RGB2GRAY)
            template_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)
            result = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)
            return max_val > threshold
        except cv2.error as e:
             print(f"OpenCV error during image comparison: {e}")
             return False
        except Exception as e:
             print(f"Unexpected error during image comparison: {e}")
             return False

    def check_status(self, screen_info: CombatScreenInfo) -> ScreenState:
        # (변경 없음)
        try:
            screen = pyautogui.screenshot(region=screen_info.region)
            if screen is None: return screen_info.current_state # 스크린샷 실패 시 이전 상태 유지

            template_dead_path = TEMPLATE_PATHS['status']['dead'].get(screen_info.window_id)
            if template_dead_path and os.path.exists(template_dead_path):
                template_dead = cv2.imread(template_dead_path)
                if template_dead is not None and self.compare_images(screen, template_dead):
                    return ScreenState.DEAD

            template_abnormal_path = TEMPLATE_PATHS['status']['abnormal'].get(screen_info.window_id)
            if template_abnormal_path and os.path.exists(template_abnormal_path):
                template_abnormal = cv2.imread(template_abnormal_path)
                if template_abnormal is not None and self.compare_images(screen, template_abnormal):
                    return ScreenState.ABNORMAL

            template_awake_path = TEMPLATE_PATHS['status']['awake'].get(screen_info.window_id)
            if template_awake_path and os.path.exists(template_awake_path):
                template_awake = cv2.imread(template_awake_path)
                if template_awake is not None and self.compare_images(screen, template_awake):
                    return ScreenState.AWAKE

            return ScreenState.SLEEP

        except KeyError as e:
             print(f"[{screen_info.window_id}] Error accessing TEMPLATE_PATHS key: {e}. Check config/template_paths.py")
             return screen_info.current_state
        except Exception as e:
            print(f"[{screen_info.window_id}] Error in check_status: {e}")
            return screen_info.current_state

    # --- 액션 함수들 (내부 로직 변경 없음) ---
    def process_death_recovery(self, screen_info: CombatScreenInfo) -> bool:
        try:
            center_x = screen_info.region[0] + (screen_info.region[2] // 2)
            center_y = screen_info.region[1] + (screen_info.region[3] // 2)
            pyautogui.click(center_x, center_y); time.sleep(0.2)

            template_path = TEMPLATE_PATHS['death']['return_button'].get(screen_info.window_id)
            if not template_path: return False

            return_pos = self.return_ui_location(screen_info, template_path)
            if not return_pos: return False

            pyautogui.click(return_pos[0], return_pos[1]); time.sleep(0.5) # 클릭 후 잠시 대기 추가
            return True
        except Exception as e:
            print(f"[{screen_info.window_id}] Error in process_death_recovery: {e}")
            return False

    def retreat_to_safe_zone(self, screen_info: CombatScreenInfo) -> bool:
        try:
            print(f"[{screen_info.window_id}] 후퇴 시도")
            confirm_clicked = False
            # 확인 버튼 클릭 (고정 좌표 또는 템플릿 매칭)
            confirm_button_path = TEMPLATE_PATHS['retreat']['confirm_button'].get(screen_info.window_id)
            confirm_pos = None
            if confirm_button_path:
                confirm_pos = self.return_ui_location(screen_info, confirm_button_path, threshold=0.8)

            if confirm_pos:
                 print(f"[{screen_info.window_id}] 템플릿으로 확인 버튼 클릭 시도 at ({confirm_pos[0]}, {confirm_pos[1]})")
                 pyautogui.click(confirm_pos[0], confirm_pos[1])
                 time.sleep(0.5)
                 confirm_clicked = True
            elif screen_info.window_id in FIXED_UI_COORDS and 'retreat_confirm_button' in FIXED_UI_COORDS[screen_info.window_id]:
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
            if not template_path: return False

            retreat_pos = self.return_ui_location(screen_info, template_path)
            if retreat_pos:
                print(f"[{screen_info.window_id}] 후퇴 버튼 클릭")
                pyautogui.click(retreat_pos[0], retreat_pos[1]); time.sleep(0.5) # 클릭 후 잠시 대기
                return True
            print(f"[{screen_info.window_id}] 후퇴 버튼 못찾음 (확인 버튼 클릭 여부: {confirm_clicked})")
            return False
        except Exception as e:
            print(f"[{screen_info.window_id}] 후퇴 실패: {str(e)}")
            return False

    def replenish_potions(self, screen_info: CombatScreenInfo) -> bool:
        try:
            print(f"[{screen_info.window_id}] 물약 보충 시작")
            time.sleep(2.5) # 대기 시간 줄임

            # 상점 UI 찾기 (최대 3번 시도)
            shop_ui_path = TEMPLATE_PATHS['potion']['shop_ui'].get(screen_info.window_id)
            if not shop_ui_path: return False
            shop_pos = self.wait_for_ui(screen_info, shop_ui_path, max_wait_time=3.0, interval=0.5, threshold=0.8)
            if not shop_pos:
                print(f"[{screen_info.window_id}] 상점 UI를 찾을 수 없음 (3초)")
                return False

            print(f"[{screen_info.window_id}] 상점 UI 클릭")
            pyautogui.click(shop_pos[0], shop_pos[1])
            time.sleep(1.5) # 상점 로딩 대기 시간 조정

            # 구매 버튼 찾기 (최대 3번 시도)
            buy_button_path = TEMPLATE_PATHS['potion']['buy_button'].get(screen_info.window_id)
            if not buy_button_path: return False
            buy_pos = self.wait_for_ui(screen_info, buy_button_path, max_wait_time=3.0, interval=0.5, threshold=0.75)
            if not buy_pos:
                print(f"[{screen_info.window_id}] 구매 버튼을 찾을 수 없음 (3초)")
                keyboard.press_and_release('esc'); time.sleep(1.0)
                return False

            print(f"[{screen_info.window_id}] 구매 버튼 클릭")
            pyautogui.click(buy_pos[0], buy_pos[1])
            time.sleep(0.8) # 대기 시간 조정

            # 확인 버튼 찾기 (최대 3번 시도)
            confirm_path = TEMPLATE_PATHS['potion']['confirm'].get(screen_info.window_id)
            if not confirm_path: return False
            confirm_pos = self.wait_for_ui(screen_info, confirm_path, max_wait_time=3.0, interval=0.5, threshold=0.8)
            if not confirm_pos:
                print(f"[{screen_info.window_id}] 확인 버튼을 찾을 수 없음 (구매 후, 3초)")
                keyboard.press_and_release('esc'); time.sleep(1.0)
                return False

            print(f"[{screen_info.window_id}] 확인 버튼 클릭 (구매 후)")
            pyautogui.click(confirm_pos[0], confirm_pos[1])
            time.sleep(0.8) # 확인 후 대기 시간 조정

            print(f"[{screen_info.window_id}] 물약 보충 완료")
            keyboard.press_and_release('esc') # 상점 닫기
            time.sleep(1.0)
            return True

        except Exception as e:
            print(f"[{screen_info.window_id}] 물약 보충 중 예외 발생: {str(e)}")
            try: keyboard.press_and_release('esc')
            except: pass
            return False

    # return_to_combat 수정: S3 추가 오프셋 적용 및 sleep 위치 조정
    def return_to_combat(self, screen_info: CombatScreenInfo) -> bool:
        try:
            # 1. 첫 번째 UI 클릭
            template1_path = TEMPLATE_PATHS['combat']['template1'].get(screen_info.window_id)
            if not template1_path: return False
            pos1 = self.return_ui_location(screen_info, template1_path)
            if not pos1:
                print(f"[{screen_info.window_id}] Combat Template 1 (마을 UI?) not found.")
                return False
            pyautogui.click(pos1[0], pos1[1]) # 클릭 후 바로 sleep 없음

            # 2. 상대 좌표 클릭
            relative_click_x = pos1[0] - int(100 * screen_info.ratio) # 필요시 이 오프셋도 조정
            relative_click_y = pos1[1] + int(20 * screen_info.ratio)  # 필요시 이 오프셋도 조정
            pyautogui.click(relative_click_x, relative_click_y)

            # 상대 좌표 클릭 후 딜레이
            time.sleep(0.8) # <<< 딜레이 위치 변경됨 (1.0 -> 0.8 또는 원하는 값)

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

            pyautogui.moveTo(start_drag_abs_x, start_drag_abs_y); time.sleep(0.3) # 대기 시간 조정
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0); time.sleep(0.1)
            pyautogui.moveTo(end_drag_abs_x, end_drag_abs_y, duration=drag_duration); time.sleep(0.1)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0); time.sleep(1.0) # 대기 시간 조정

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
            pyautogui.click(target_pos[0], target_pos[1]); time.sleep(0.5)

            # 5. Template 2 찾아서 클릭
            template2_path = TEMPLATE_PATHS['combat']['template2'].get(screen_info.window_id)
            if not template2_path: return False
            pos = self.wait_for_ui(screen_info, template2_path, max_wait_time=3.0, interval=0.5)
            if not pos:
                print(f"[{screen_info.window_id}] Template2를 찾을 수 없음 - 3초")
                return False
            pyautogui.click(pos[0], pos[1]); time.sleep(0.2)

            # 6. 마지막 상대 이동 후 클릭
            move_pixels_x = int(277 * screen_info.ratio)
            move_pixels_y = int(64 * screen_info.ratio)
            pyautogui.moveRel(-move_pixels_x, -move_pixels_y); pyautogui.click(); time.sleep(0.2)

            return True
        except Exception as e:
            print(f"[{screen_info.window_id}] Error in return_to_combat: {e}")
            try: win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)
            except: pass
            return False

    # perform_repeated_combat_return 수정: 불필요한 코드 제거 가능성
    def perform_repeated_combat_return(self, screen_info: CombatScreenInfo) -> None:
        """
        파티 집결을 위한 '재시도 액션'을 1회 수행합니다.
        (Combat spot 확인 후 호출될 경우, 실제로는 불필요할 수 있음)
        """
        if screen_info.window_id == "S5":
            # print(f"[{screen_info.window_id}] S5 should not call perform_repeated_combat_return. Skipping.")
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
            pyautogui.click(target_pos[0], target_pos[1]); time.sleep(0.6)

            # 2. Template2 찾아서 클릭
            template2_path = TEMPLATE_PATHS['combat']['template2'].get(screen_info.window_id)
            if not template2_path:
                 print(f"[{screen_info.window_id}] Template2 path not found.")
                 return

            pos = self.wait_for_ui(screen_info, template2_path, max_wait_time=4.0, interval=0.5, threshold=0.8)
            if not pos:
                print(f"[{screen_info.window_id}] Template2를 찾을 수 없음 (within perform_repeated_combat_return).")
                return

            pyautogui.click(pos[0], pos[1]); time.sleep(0.2)

            # 3. 상대 이동 후 클릭
            move_pixels_x = int(277 * screen_info.ratio)
            move_pixels_y = int(64 * screen_info.ratio)
            pyautogui.moveRel(-move_pixels_x, -move_pixels_y); pyautogui.click(); time.sleep(0.2)

            print(f"[{screen_info.window_id}] Single attempt of repeated return actions finished.")

        except Exception as e:
            print(f"[{screen_info.window_id}] Error in perform_repeated_combat_return: {e}")

    # wait_for_ui 수정: stop_event 확인 추가
    def wait_for_ui(self, screen_info, template_path, max_wait_time=3.0, interval=0.5, threshold = None, stop_event: Event = None):
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            # Orchestrator로부터 중지 신호 확인
            if stop_event and stop_event.is_set():
                print(f"[{screen_info.window_id}] Stop event received while waiting for UI: {os.path.basename(template_path)}")
                return None
            pos = self.return_ui_location(screen_info, template_path, threshold)
            if pos: return pos
            # time.sleep 대신 stop_event.wait 사용 (더 반응성 좋음)
            if stop_event:
                if stop_event.wait(timeout=interval): # 이벤트 설정되면 즉시 반환 (True)
                     print(f"[{screen_info.window_id}] Stop event received during wait interval for UI: {os.path.basename(template_path)}")
                     return None
            else:
                time.sleep(interval)
        # print(f"[{screen_info.window_id}] UI not found after {max_wait_time}s: {os.path.basename(template_path)}") # 필요시 로그
        return None

    # is_at_combat_spot 수정: 디버깅 코드 제거, stop_event 확인 추가
    def is_at_combat_spot(self, screen_info: CombatScreenInfo, check_duration: float = 3.0,
                                  interval: float = 0.3, stop_event: Event = None) -> bool:
        if screen_info.window_id == "S5":
            return True

        try:
            if screen_info.window_id in FIXED_UI_COORDS and 'leader_hp_pixel' in FIXED_UI_COORDS[
                screen_info.window_id]:
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
                    return False # 중지 시 실패로 간주

                check_count += 1
                current_time_elapsed = time.time() - start_time

                try:
                    match = pyautogui.pixelMatchesColor(absolute_x, absolute_y, target_hp_color,
                                                   tolerance=tolerance_level)
                    if match:
                        # print(f"[{screen_info.window_id}] Combat spot confirmed at check {check_count} ({current_time_elapsed:.1f}s).") # 성공 로그는 run_loop에서 출력하므로 주석 처리
                        return True
                except OSError:
                    # print(f"    WARN: OS Error reading pixel at check {check_count}, retrying.") # 로그 간소화
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

            # print(f"[{screen_info.window_id}] Combat spot NOT confirmed within {check_duration}s after {check_count} checks.") # 실패 로그는 run_loop에서 출력하므로 주석 처리
            return False

        except KeyError:
            print(f"[{screen_info.window_id}] Error accessing FIXED_UI_COORDS key.")
            return False
        except Exception as e:
            print(f"[{screen_info.window_id}] Error checking combat spot pixel: {e}")
            return False

    # is_in_safe_zone, is_potion_purchase_complete, is_recovered 는 변경 없음
    def is_in_safe_zone(self, screen_info: CombatScreenInfo) -> bool:
        try:
            template_path = TEMPLATE_PATHS['combat']['template1'].get(screen_info.window_id)
            if not template_path: return False
            location = self.return_ui_location(screen_info, template_path, threshold=0.8)
            return bool(location)
        except Exception as e:
            print(f"[{screen_info.window_id}] Error checking safe zone status: {e}")
            return False

    def is_potion_purchase_complete(self, screen_info: CombatScreenInfo) -> bool:
        try:
            shop_ui_path = TEMPLATE_PATHS['potion']['confirm'].get(screen_info.window_id) # 확인 버튼이 안 보이면 완료로 간주
            if not shop_ui_path: return True # 경로 없으면 확인 불가 -> 완료 간주 (정책 변경 가능)
            location = self.return_ui_location(screen_info, shop_ui_path, threshold=0.8)
            return not bool(location) # UI가 안보이면 True
        except Exception as e:
            print(f"[{screen_info.window_id}] Error checking potion purchase completion: {e}")
            return False

    def is_recovered(self, screen_info: CombatScreenInfo) -> bool:
        return self.is_in_safe_zone(screen_info)


    # ===============================================
    # <<< 메인 루프 수정 >>>
    # ===============================================
    # monitor_all_windows -> run_loop 로 이름 변경 및 stop_event 인자 추가
    def run_loop(self, stop_event: Event):
        """Orchestrator와 호환되는 메인 모니터링 루프"""
        print(f"CombatMonitor run_loop started for screens: {[s.window_id for s in self.screens]}")

        # 루프 조건 변경: while not stop_event.is_set()
        while not stop_event.is_set():
            try:
                for screen in self.screens:
                    # 루프 초반에 stop_event 다시 확인 (빠른 종료 위해)
                    if stop_event.is_set(): break

                    state = screen.current_state
                    # print(f"DEBUG: [{screen.window_id}] Current State: {state.name}") # 필요시 활성화

                    # --- 상태별 처리 로직 (내부 로직 유지, wait_for_ui/is_at_combat_spot 호출 시 stop_event 전달) ---
                    if state == ScreenState.SLEEP or state == ScreenState.AWAKE:
                        visual_status = self.check_status(screen)
                        if visual_status != state:
                             print(f"[{screen.window_id}] Visual state changed: {state.name} -> {visual_status.name}.")
                             screen.current_state = visual_status
                             screen.retry_count = 0 # 상태 변경 시 리트라이 카운트 초기화

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
                            print(f"[{screen.window_id}] Retreat initiation failed (Attempt {screen.retry_count + 1}). Retrying ABNORMAL state.")
                            screen.retry_count += 1
                            if screen.retry_count > 3:
                                print(f"[{screen.window_id}] Retreat failed after multiple retries. Setting state to SLEEP for manual check.")
                                screen.current_state = ScreenState.SLEEP
                        time.sleep(0.5) # 액션 후 짧은 대기

                    elif state == ScreenState.RETREATING:
                        print(f"[{screen.window_id}] State is RETREATING. Checking for safe zone.")
                        if self.is_in_safe_zone(screen):
                            print(f"[{screen.window_id}] Safe zone confirmed. Changing state to SAFE_ZONE.")
                            screen.current_state = ScreenState.SAFE_ZONE
                            screen.retry_count = 0
                        else:
                            screen.retry_count += 1
                            # print(f"[{screen.window_id}] Still retreating... (Check {screen.retry_count})") # 로그 간소화
                            if screen.retry_count > 60: # 약 30초 타임아웃
                                 print(f"[{screen.window_id}] Retreat timeout. Setting state to SLEEP for manual check.")
                                 screen.current_state = ScreenState.SLEEP

                    elif state == ScreenState.SAFE_ZONE:
                         print(f"[{screen.window_id}] State is SAFE_ZONE. Attempting to purchase potions.")
                         action_success = False
                         with self.io_lock:
                             action_success = self.replenish_potions(screen)
                         if action_success:
                             print(f"[{screen.window_id}] Potion purchase seems complete. Changing state to POTIONS_PURCHASED.")
                             screen.current_state = ScreenState.POTIONS_PURCHASED
                             screen.retry_count = 0
                         else:
                             print(f"[{screen.window_id}] Potion purchase failed (Attempt {screen.retry_count + 1}). Retrying SAFE_ZONE state.")
                             screen.retry_count += 1
                             if screen.retry_count > 3:
                                 print(f"[{screen.window_id}] Potion purchase failed after multiple retries. Setting state to SLEEP.")
                                 screen.current_state = ScreenState.SLEEP
                         time.sleep(0.5) # 액션 후 짧은 대기

                    elif state == ScreenState.POTIONS_PURCHASED:
                         print(f"[{screen.window_id}] State is POTIONS_PURCHASED. Attempting return to combat.")
                         action_success = False
                         with self.io_lock:
                             action_success = self.return_to_combat(screen)
                         if action_success:
                             print(f"[{screen.window_id}] Return to combat initiated. Changing state to RETURNING_TO_COMBAT.")
                             screen.current_state = ScreenState.RETURNING_TO_COMBAT
                             screen.retry_count = 0
                         else:
                             print(f"[{screen.window_id}] Return to combat initiation failed (Attempt {screen.retry_count + 1}). Retrying POTIONS_PURCHASED.")
                             screen.retry_count += 1
                             if screen.retry_count > 3:
                                  print(f"[{screen.window_id}] Return to combat failed after multiple retries. Setting state to SLEEP.")
                                  screen.current_state = ScreenState.SLEEP
                         time.sleep(0.5) # 액션 후 짧은 대기

                    elif state == ScreenState.RETURNING_TO_COMBAT:
                         wait_time = 3.3 # 대기 시간 유지
                         print(f"[{screen.window_id}] State is RETURNING_TO_COMBAT. Waiting {wait_time}s before checking combat spot...")
                         # time.sleep 대신 stop_event.wait 사용
                         if stop_event.wait(timeout=wait_time): break # 대기 중 중지 신호 받으면 루프 탈출

                         print(f"[{screen.window_id}] Checking combat spot.")
                         # is_at_combat_spot 호출 시 stop_event 전달
                         if self.is_at_combat_spot(screen, stop_event=stop_event):
                             print(f"[{screen.window_id}] Combat spot confirmed.")
                             screen.retry_count = 0
                             # Combat spot 확인 후 Party check 로직 제거 (주석처리된 이전 버전 기준)
                             # if screen.window_id != "S5":
                             #     print(f"[{screen.window_id}] Performing party check.")
                             #     with self.io_lock:
                             #         self.perform_repeated_combat_return(screen)
                             #     print(f"[{screen.window_id}] Party check finished.")
                             print(f"[{screen.window_id}] Setting state to AWAKE.")
                             screen.current_state = ScreenState.AWAKE
                         else:
                             # is_at_combat_spot 이 False를 반환했거나 stop_event로 중단된 경우
                             if not stop_event.is_set(): # stop_event 때문이 아니라면 실패 로직 수행
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
                                         if stop_event.wait(timeout=0.5): break # 재시도 후 짧은 대기 및 중지 확인

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
                            print(f"[{screen.window_id}] Recovery initiation failed (Attempt {screen.retry_count + 1}). Retrying DEAD state.")
                            screen.retry_count += 1
                            if screen.retry_count > 3:
                                print(f"[{screen.window_id}] Recovery failed after multiple retries. Setting state to SLEEP.")
                                screen.current_state = ScreenState.SLEEP
                        time.sleep(0.5) # 액션 후 짧은 대기

                    elif state == ScreenState.RECOVERING:
                         print(f"[{screen.window_id}] State is RECOVERING. Checking for recovery completion.")
                         if self.is_recovered(screen):
                             print(f"[{screen.window_id}] Recovery seems complete (in safe zone). Changing state to SAFE_ZONE.")
                             screen.current_state = ScreenState.SAFE_ZONE
                             screen.retry_count = 0
                         else:
                             screen.retry_count += 1
                             # print(f"[{screen.window_id}] Still recovering... (Check {screen.retry_count})") # 로그 간소화
                             if screen.retry_count > 60: # 약 30초 타임아웃
                                 print(f"[{screen.window_id}] Recovery timeout. Setting state to SLEEP.")
                                 screen.current_state = ScreenState.SLEEP

                    else:
                        # SLEEP/AWAKE 외 처리되지 않은 상태
                        print(f"[{screen.window_id}] Unhandled state: {state.name}")
                        screen.current_state = ScreenState.SLEEP # 안전하게 SLEEP으로 변경

                # --- 모든 화면 처리 후 루프 지연 ---
                # time.sleep(self.check_interval) 대신 stop_event.wait 사용
                if stop_event.is_set(): break # 이미 중지 신호 왔으면 바로 종료
                if stop_event.wait(timeout=self.check_interval): # check_interval 동안 대기, 중간에 set되면 True 반환
                    break # 중지 신호 받으면 루프 탈출

            except Exception as e:
                 # 루프 내에서 예상치 못한 오류 발생 시 로깅하고 계속 진행 (또는 루프 탈출 결정)
                 print(f"!!! Unhandled exception in CombatMonitor run_loop: {e} !!!")
                 traceback.print_exc()
                 # 오류 발생 시 안전하게 루프를 잠시 멈추거나 상태 초기화 고려
                 if stop_event.wait(timeout=5.0): break # 5초 대기하며 중지 신호 확인

        # 루프 종료 (stop_event 설정됨)
        print(f"CombatMonitor run_loop stopped.")

    # ===============================================
    # <<< stop 메서드 추가 >>>
    # ===============================================
    def stop(self):
        """Orchestrator가 호출할 수 있는 종료 처리 메서드"""
        # 현재 구조에서는 stop_event가 주된 종료 메커니즘이므로,
        # 이 메서드는 추가적인 정리 작업이 필요할 경우에 사용합니다.
        # 예를 들어, 특정 리소스 해제 등.
        # 여기서는 간단히 로그만 남깁니다.
        print("CombatMonitor stop() method called. Performing cleanup if necessary...")
        # 만약 self.running 플래그를 내부적으로 사용한다면 여기서 설정 가능:
        # self.running = False

# --- 클래스 종료 ---


if __name__ == "__main__":
    print("CombatMonitor 모듈 직접 실행 테스트 (Orchestrator 없이)")
    # 이 부분은 Orchestrator 없이 CombatMonitor만 테스트할 때 사용합니다.
    # 실제 Orchestrator 환경에서는 Orchestrator가 이 클래스를 import하여 사용합니다.

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
        test_stop_event.set() # 루프에 종료 신호 보내기
        monitor.stop() # stop 메서드 호출 (테스트)
    except Exception as e:
        print(f"테스트 중 오류 발생: {e}")
        traceback.print_exc()
        test_stop_event.set()
        monitor.stop()
    finally:
        print("테스트 종료.")