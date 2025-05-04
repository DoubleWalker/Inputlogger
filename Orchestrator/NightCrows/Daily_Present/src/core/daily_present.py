# daily_present.py (DP1 - 수정됨)

from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional, Dict # Dict 추가
import cv2
import numpy as np
import traceback
import pyautogui
import keyboard
import time
import random
# NightCrows 경로 확인
from Orchestrator.NightCrows.utils.screen_info import SCREEN_REGIONS, EVENT_UI_REGIONS

# 화면별 빨간 점 감지 파라미터 (기존과 동일)
SCREEN_PARAMETERS = {
    'S1': {'min_area': 8.0, 'max_area': 28.0, 'min_circularity': 0.76, 'max_circularity': 1.0, 'min_ratio': 0.8,
           'max_ratio': 1.34},
    # ... (S2-S5 파라미터 생략) ...
     'S5': {'min_area': 34.0, 'max_area': 60.0, 'min_circularity': 0.82, 'max_circularity': 0.99, 'min_ratio': 0.83, 'max_ratio': 1.05}
}

class PresentState(Enum):
    """Daily Present 상태 머신의 상태들"""
    MAIN_SCREEN = 0
    EVENT_MENU = 1
    # LEFT_MENU_SCROLL 상태는 유지 (왼쪽 스크롤은 필요)
    LEFT_MENU_SCROLL = 2
    RIGHT_CONTENT = 3
    RIGHT_CONTENT_SCROLL = 4 # 오른쪽 스크롤 상태도 유지
    REWARD_CLAIM = 5

@dataclass
class Screen:
    screen_id: str
    main_event_icon: str

    @property
    def region(self):
        return SCREEN_REGIONS[self.screen_id]

class DailyPresent:
    def __init__(self, confidence_threshold: float = 0.85):
        self.screens: List[Screen] = []
        self.threshold = confidence_threshold
        self.current_state = PresentState.MAIN_SCREEN
        self.current_screen_index = 0
        self.left_scroll_attempts = 0
        # self.right_scroll_attempts = 0 # <<< 이 변수는 더 이상 사용하지 않음
        self.max_scroll_attempts = 3 # 왼쪽 스크롤용 + 오른쪽 스크롤 최대치 제한용으로 재활용 가능
        self.left_scroll_direction_down = True
        self.right_scroll_direction_down = True
        self.is_first_entry_to_event_menu = True

        # --- 상태 변수 추가 ---
        # 마지막 클릭된 왼쪽 붉은 점 정보 (좌표 저장)
        self.last_clicked_left_dot_pos: Optional[Tuple[int, int]] = None
        # 오른쪽 스크롤 필요 여부 플래그
        self.right_scroll_needed: bool = False
        # 오른쪽 스크롤 시도 횟수 (같은 왼쪽 아이템에 대해)
        self.current_item_right_scroll_attempts: int = 0
        self.max_right_scroll_per_item: int = 3 # 오른쪽 스크롤 최대 횟수
        # --------------------

    def add_screen(self, screen_id: str, main_event_icon: str ):
        self.screens.append(Screen(screen_id=screen_id, main_event_icon=main_event_icon))

    # --- get_left_menu_region, get_right_content_region (변경 없음) ---
    def get_left_menu_region(self, screen: Screen) -> Tuple[int, int, int, int]:
        return EVENT_UI_REGIONS[screen.screen_id]['left_menu']

    def get_right_content_region(self, screen: Screen) -> Tuple[int, int, int, int]:
        return EVENT_UI_REGIONS[screen.screen_id]['right_content']

    # --- find_ui_location_in_region, find_ui_location (변경 없음) ---
    def find_ui_location_in_region(self, region: Tuple[int, int, int, int], template_path: str) -> Optional[Tuple[int, int]]:
        # ... (기존 코드와 동일) ...
        try:
            screenshot = pyautogui.screenshot(region=region)
            template = cv2.imread(template_path)
            if template is None: return None
            screen_gray = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            result = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            if max_val > self.threshold:
                template_height, template_width = template_gray.shape
                center_x = region[0] + max_loc[0] + template_width // 2
                center_y = region[1] + max_loc[1] + template_height // 2
                random_offset_x = random.randint(-3, 3)
                random_offset_y = random.randint(-3, 3)
                return (center_x + random_offset_x, center_y + random_offset_y)
            return None
        except Exception as e: print(f"Error in find_ui_location_in_region: {e}"); return None

    def find_ui_location(self, screen: Screen, template_path: str) -> Optional[Tuple[int, int]]:
        return self.find_ui_location_in_region(screen.region, template_path)

    # --- find_all_red_dots_with_blob_detector (변경 없음 - 핵심 로직 유지) ---
    def find_all_red_dots_with_blob_detector(self, region: Tuple[int, int, int, int], screen_id: str) -> List[Tuple[int, int]]:
        # ... (기존의 긴 코드 내용 그대로 유지) ...
        # 이 함수는 주어진 영역(region)에서 빨간 점들의 좌표 리스트를 반환
        # 내부 로직 및 파라미터는 그대로 사용
        try:
            full_screenshot = pyautogui.screenshot(); full_img_np = np.array(full_screenshot)
            full_hsv = cv2.cvtColor(full_img_np, cv2.COLOR_RGB2HSV)
            lower_red1 = np.array([0, 100, 100]); upper_red1 = np.array([6, 255, 255])
            lower_red2 = np.array([172, 100, 100]); upper_red2 = np.array([180, 255, 255])
            full_mask1 = cv2.inRange(full_hsv, lower_red1, upper_red1); full_mask2 = cv2.inRange(full_hsv, lower_red2, upper_red2)
            full_red_mask = cv2.bitwise_or(full_mask1, full_mask2)
            kernel = np.ones((3, 3), np.uint8); full_red_mask = cv2.morphologyEx(full_red_mask, cv2.MORPH_OPEN, kernel)
            full_contours, _ = cv2.findContours(full_red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            x, y, w, h = region; screen_img = full_img_np[y:y + h, x:x + w]
            screen_hsv = cv2.cvtColor(screen_img, cv2.COLOR_RGB2HSV)
            screen_mask1 = cv2.inRange(screen_hsv, lower_red1, upper_red1); screen_mask2 = cv2.inRange(screen_hsv, lower_red2, upper_red2)
            screen_red_mask = cv2.bitwise_or(screen_mask1, screen_mask2); screen_red_mask = cv2.morphologyEx(screen_red_mask, cv2.MORPH_OPEN, kernel)
            screen_params = cv2.SimpleBlobDetector_Params(); screen_params.filterByArea = True
            if screen_id == 'S5': screen_params.minArea = 36.0; screen_params.maxArea = 120.0
            else: screen_params.minArea = 11.0; screen_params.maxArea = 64.0
            screen_params.filterByCircularity = False; screen_params.filterByConvexity = False
            screen_params.filterByInertia = False; screen_params.filterByColor = False
            screen_detector = cv2.SimpleBlobDetector_create(screen_params)
            screen_inverted_mask = cv2.bitwise_not(screen_red_mask)
            screen_keypoints = screen_detector.detect(screen_inverted_mask)
            valid_keypoints = []
            for kp in screen_keypoints:
                orig_x, orig_y = kp.pt; global_x, global_y = orig_x + x, orig_y + y
                kp_contour = None; kp_contour_idx = -1
                for i, contour in enumerate(full_contours):
                    if cv2.pointPolygonTest(contour, (global_x, global_y), False) >= 0: kp_contour = contour; kp_contour_idx = i; break
                if kp_contour is not None:
                    area = cv2.contourArea(kp_contour); perimeter = cv2.arcLength(kp_contour, True)
                    circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
                    hull = cv2.convexHull(kp_contour); hull_area = cv2.contourArea(hull); convexity = area / hull_area if hull_area > 0 else 0
                    _, (width, height), _ = cv2.minAreaRect(kp_contour); inertia_ratio = min(width, height) / max(width, height) if max(width, height) > 0 else 0
                    x_rect, y_rect, w, h = cv2.boundingRect(kp_contour); aspect_ratio = float(w) / h if h > 0 else 0
                    size_pass = (screen_params.minArea <= area <= screen_params.maxArea)
                    if size_pass:
                        circularity_pass = circularity > 0.7; convexity_pass = convexity > 0.7
                        inertia_ratio_pass = inertia_ratio > 0.65; aspect_ratio_pass = 0.8 < aspect_ratio < 1.2
                        remaining_pass_count = circularity_pass + convexity_pass + inertia_ratio_pass + aspect_ratio_pass
                        remaining_criteria_pass = remaining_pass_count >= 2
                        has_nearby_contours = False
                        for i, contour in enumerate(full_contours):
                            if i == kp_contour_idx: continue
                            for point in contour:
                                px, py = point[0][0], point[0][1]; distance = np.sqrt((global_x - px) ** 2 + (global_y - py) ** 2)
                                if distance <= 20: has_nearby_contours = True; break
                            if has_nearby_contours: break
                        if remaining_criteria_pass and not has_nearby_contours:
                            final_x = int(global_x) + random.randint(-2, 2); final_y = int(global_y) + random.randint(-2, 2)
                            valid_keypoints.append((final_x, final_y))
            # print(f"{screen_id} 영역에서 검출된 빨간점: {len(screen_keypoints)}개, 유효한 빨간점: {len(valid_keypoints)}개") # 로그 간소화 위해 주석 처리 가능
            return valid_keypoints
        except Exception as e: print(f"빨간점 감지 중 오류 발생: {e}"); traceback.print_exc(); return []

    # --- find_red_dot_in_left_menu, find_red_dot_in_right_content (변경 없음) ---
    def find_red_dot_in_left_menu(self, screen: Screen) -> List[Tuple[int, int]]:
        menu_region = self.get_left_menu_region(screen)
        return self.find_all_red_dots_with_blob_detector(menu_region, screen.screen_id)

    def find_red_dot_in_right_content(self, screen: Screen) -> List[Tuple[int, int]]:
        content_region = self.get_right_content_region(screen)
        return self.find_all_red_dots_with_blob_detector(content_region, screen.screen_id)

    # --- click_with_offset (변경 없음) ---
    def click_with_offset(self, position: Tuple[int, int], offset_x: int = -2, offset_y: int = 2):
        pyautogui.click(position[0] + offset_x, position[1] + offset_y)

    # --- scroll_in_left_menu, scroll_in_right_content (변경 없음, 단 sleep 시간은 이전 논의대로 수정 가정) ---
    def scroll_in_left_menu(self, screen: Screen):
        # ... (기존 스크롤 로직, sleep 시간 단축 적용 가정) ...
        try:
            menu_region = self.get_left_menu_region(screen); start_x = menu_region[0] + menu_region[2] // 2
            if self.left_scroll_direction_down: start_y = menu_region[1] + menu_region[3] * 2 // 3; end_y = menu_region[1] + menu_region[3] // 3; direction_str = "DOWN"
            else: start_y = menu_region[1] + menu_region[3] // 3; end_y = menu_region[1] + menu_region[3] * 2 // 3; direction_str = "UP"
            end_x = start_x; print(f"[{screen.screen_id}] 왼쪽 메뉴 {direction_str} 스크롤 시작")
            pyautogui.moveTo(start_x, start_y);  time.sleep(0.01) # 필요시 아주 짧게
            pyautogui.mouseDown(button='left');  time.sleep(0.01) # 필요시 아주 짧게
            pyautogui.moveTo(end_x, end_y, duration=0.15) # duration 조절
            pyautogui.mouseUp(button='left'); time.sleep(1.0) # 스크롤 후 짧은 대기
            self.left_scroll_direction_down = not self.left_scroll_direction_down
            print(f"[{screen.screen_id}] {direction_str} 스크롤 완료"); return True
        except Exception as e: print(f"Error in scroll_in_left_menu: {e}"); pyautogui.mouseUp(button='left'); return False

    def scroll_in_right_content(self, screen: Screen):
        # ... (기존 스크롤 로직, sleep 시간 단축 적용 가정) ...
        try:
            content_region = self.get_right_content_region(screen); start_x = content_region[0] + content_region[2] // 2
            if self.right_scroll_direction_down: start_y = content_region[1] + content_region[3] * 3 //4; end_y = content_region[1] + content_region[3] // 4; direction_str = "DOWN"
            else: start_y = content_region[1] + content_region[3] * 2 // 5; end_y = content_region[1] + content_region[3] * 2 // 3; direction_str = "UP"
            end_x = start_x; print(f"[{screen.screen_id}] 오른쪽 콘텐츠 {direction_str} 스크롤 시작")
            pyautogui.moveTo(start_x, start_y);  time.sleep(0.01)
            pyautogui.mouseDown(button='left');  time.sleep(0.01)
            pyautogui.moveTo(end_x, end_y, duration=0.15) # duration 조절
            pyautogui.mouseUp(button='left'); time.sleep(0.1) # 스크롤 후 짧은 대기
            self.right_scroll_direction_down = not self.right_scroll_direction_down
            print(f"[{screen.screen_id}] {direction_str} 스크롤 완료"); return True
        except Exception as e: print(f"Error in scroll_in_right_content: {e}"); pyautogui.mouseUp(button='left'); return False

    # === 상태 처리 메소드 수정 ===

    def process_main_screen(self, screen: Screen):
        """메인 화면 처리 (변경 없음)"""
        print(f"[{screen.screen_id}] 메인 화면 처리 중...")
        event_icon_pos = self.find_ui_location(screen, screen.main_event_icon)
        if event_icon_pos:
            print(f"[{screen.screen_id}] 이벤트 아이콘 발견, 클릭")
            pyautogui.click(event_icon_pos[0], event_icon_pos[1])
            time.sleep(0.2) # 메뉴 로딩 대기 (값 조절 가능)
            # 초기 상태 재설정: 다음 화면으로 넘어갈 때를 대비해 여기서도 초기화
            self.last_clicked_left_dot_pos = None
            self.right_scroll_needed = False
            self.current_item_right_scroll_attempts = 0
            self.is_first_entry_to_event_menu = True # 첫 진입 플래그도 여기서 관리하는게 나을 수 있음
            self.current_state = PresentState.EVENT_MENU
            return True
        print(f"[{screen.screen_id}] 이벤트 아이콘을 찾을 수 없음")
        # 실패 시 다음 화면으로 넘어가도록 처리 (run 메소드에서 처리됨)
        return False # 실패 시 False 반환

    def process_event_menu(self, screen: Screen):
        """이벤트 메뉴 처리 (수정됨)"""
        print(f"[{screen.screen_id}] 이벤트 메뉴 처리 중...")

        # 왼쪽 메뉴에서 붉은 점 찾기
        red_dot_positions = self.find_red_dot_in_left_menu(screen)

        if red_dot_positions:
            # 처리할 다음 붉은 점 선택 (여기서는 간단히 첫 번째 것 선택)
            # TODO: 이전에 처리한 점을 건너뛰는 로직 추가 가능 (더 복잡해짐)
            # 현재는 항상 찾은 목록의 첫번째 점을 시도함
            target_dot_pos = red_dot_positions[0]
            print(f"[{screen.screen_id}] 왼쪽 붉은 점 발견: {target_dot_pos}")

            # 이전에 클릭한 점과 같은지 비교
            if self.last_clicked_left_dot_pos == target_dot_pos:
                # 같은 점을 다시 클릭하는 경우 -> 오른쪽 스크롤 필요
                self.current_item_right_scroll_attempts += 1
                print(f"  -> 같은 항목 재클릭 감지. 오른쪽 스크롤 시도 ({self.current_item_right_scroll_attempts}/{self.max_right_scroll_per_item}).")
                if self.current_item_right_scroll_attempts > self.max_right_scroll_per_item:
                    print(f"  -> 오른쪽 최대 스크롤 도달. 이 항목 건너뛰기.")
                    # TODO: 이 항목을 '처리 완료' 또는 '오류'로 기록하고 다음 붉은 점을 찾도록 개선 가능
                    # 현재 로직에서는 그냥 다음 왼쪽 스크롤로 넘어감 (아래 else if 조건으로)
                    self.current_state = PresentState.LEFT_MENU_SCROLL # 강제로 왼쪽 스크롤 시도
                    return True # 상태 전환 했으므로 True 반환
                else:
                    self.right_scroll_needed = True
            else:
                # 다른 점을 클릭하는 경우 -> 오른쪽 스크롤 불필요, 카운터 리셋
                print(f"  -> 새로운 항목 클릭.")
                self.right_scroll_needed = False
                self.current_item_right_scroll_attempts = 0 # 새 항목이므로 리셋

            # 선택된 붉은 점 클릭
            self.click_with_offset(target_dot_pos, -2, 2)
            self.last_clicked_left_dot_pos = target_dot_pos # 마지막 클릭 정보 업데이트
            time.sleep(0.2) # 클릭 후 오른쪽 로딩 대기 (값 조절 가능)
            self.current_state = PresentState.RIGHT_CONTENT # 오른쪽 처리하러 전환
            return True

        # 붉은 점이 없다면 왼쪽 스크롤 시도
        elif self.left_scroll_attempts < self.max_scroll_attempts:
            print(f"[{screen.screen_id}] 왼쪽 붉은 점 없음, 스크롤 시도 ({self.left_scroll_attempts + 1}/{self.max_scroll_attempts})")
            self.current_state = PresentState.LEFT_MENU_SCROLL
            return True
        else:
            # 왼쪽 스크롤 다 했는데도 붉은 점 없으면 종료
            print(f"[{screen.screen_id}] 왼쪽 붉은 점 없음, 최대 스크롤 시도 도달, DP 종료.")
            keyboard.press_and_release('esc') # 이벤트 메뉴 나가기
            time.sleep(0.3)
            # 다음 화면으로 넘어가기 위해 상태를 MAIN_SCREEN으로 하고 current_screen_index 증가 필요
            # 이 로직은 run() 메소드에서 처리하는 것이 더 깔끔할 수 있음
            # 여기서는 일단 MAIN_SCREEN으로 보내서 run() 메소드의 실패 처리 로직 타도록 유도
            self.current_state = PresentState.MAIN_SCREEN # run()에서 다음 화면으로 넘길 것임
            # run()에서 실패 시 index 증가 로직이 있으므로 여기서는 index 증가 안함
            # 다음 화면 처리를 위해 플래그 초기화
            self.is_first_entry_to_event_menu = True
            self.last_clicked_left_dot_pos = None
            self.right_scroll_needed = False
            self.current_item_right_scroll_attempts = 0
            return False # run() 메소드에서 다음 화면으로 넘어가도록 False 반환

    def process_left_menu_scroll(self, screen: Screen):
        """왼쪽 메뉴 스크롤 처리 (변경 없음)"""
        print(f"[{screen.screen_id}] 왼쪽 메뉴 스크롤 중... (시도 {self.left_scroll_attempts + 1}/{self.max_scroll_attempts})")
        if self.scroll_in_left_menu(screen):
            self.left_scroll_attempts += 1
            print(f"[{screen.screen_id}] 스크롤 완료 (총 {self.left_scroll_attempts}회)")
            self.current_state = PresentState.EVENT_MENU # 스크롤 후 다시 이벤트 메뉴 확인
            return True
        print(f"[{screen.screen_id}] 스크롤 실패")
        # 스크롤 실패 시에도 일단 EVENT_MENU로 돌아가서 최종 종료 로직 타도록 함
        self.current_state = PresentState.EVENT_MENU
        return False # 실패 처리

    def process_right_content(self, screen: Screen):
        """오른쪽 콘텐츠 처리 (수정됨)"""
        print(f"[{screen.screen_id}] 오른쪽 콘텐츠 처리 중...")

        # 스크롤이 필요한 경우인지 확인
        if self.right_scroll_needed:
            print(f"  -> 오른쪽 스크롤 필요 플래그 감지.")
            self.right_scroll_needed = False # 플래그 사용했으니 리셋
            self.current_state = PresentState.RIGHT_CONTENT_SCROLL # 스크롤 상태로 전환
            return True

        # 스크롤 필요 없으면 보이는 영역에서 붉은 점 찾기
        print(f"  -> 보이는 영역에서 오른쪽 붉은 점(보상) 찾기 시도...")
        red_dot_positions = self.find_red_dot_in_right_content(screen)

        if red_dot_positions:
            # 붉은 점(보상)을 찾았으면 클릭하고 REWARD_CLAIM 상태로
            target_dot_pos = red_dot_positions[0]
            print(f"    -> 오른쪽 붉은 점 발견: {target_dot_pos}, 클릭.")
            self.click_with_offset(target_dot_pos, -2, 2)
            time.sleep(0.2) # 클릭 후 상태 전환 전 잠시 대기
            self.current_state = PresentState.REWARD_CLAIM
            return True
        else:
            # 보이는 영역에 붉은 점 없으면 -> 왼쪽 메뉴 확인하러 돌아감 (스크롤 X)
            print(f"    -> 보이는 영역에 오른쪽 붉은 점 없음. 왼쪽 메뉴로 복귀.")
            # 왼쪽 메뉴로 돌아갈 때, 마지막 클릭 정보는 유지해야 함 (같은 왼쪽 항목을 다시 처리할 수 있으므로)
            self.current_state = PresentState.EVENT_MENU
            return True

    def process_right_content_scroll(self, screen: Screen):
        """오른쪽 콘텐츠 스크롤 처리 (변경 없음)"""
        # 이 메소드는 스크롤만 하고 다시 RIGHT_CONTENT로 돌아감
        print(f"[{screen.screen_id}] 오른쪽 콘텐츠 스크롤 중... (시도 {self.current_item_right_scroll_attempts}/{self.max_right_scroll_per_item})") # 카운터 표시
        if self.scroll_in_right_content(screen):
            print(f"[{screen.screen_id}] 스크롤 완료")
            time.sleep(0.1) # 스크롤 후 짧은 대기
            self.current_state = PresentState.RIGHT_CONTENT # 스크롤 했으니 다시 오른쪽 확인
            return True
        print(f"[{screen.screen_id}] 스크롤 실패")
        # 스크롤 실패 시, 해당 아이템 처리 포기하고 왼쪽 메뉴로 돌아가도록 함
        self.current_state = PresentState.EVENT_MENU
        return False

    def process_reward_claim(self, screen: Screen):
        """보상 수령 처리 (수정됨)"""
        print(f"[{screen.screen_id}] 보상 수령 중...")

        # 보상 수령 후 약간의 시간을 두고 처리 (애니메이션 대기 등)

        print(f"  -> 대기 시간 시작 (0.3초)...")
        time.sleep(0.3)

        # === ESC 대신 마우스 클릭으로 변경 ===
        print(f"  -> 대기 시간 종료. 마우스 클릭 실행 (현재 위치).")
        pyautogui.click() # 현재 마우스 위치에서 싱글 클릭
        # === 변경 완료 ===

        time.sleep(0.5) # 클릭 후 안정화 시간

        # === 다음 상태를 EVENT_MENU로 변경 ===
        print(f"  -> 보상 처리 완료. 왼쪽 메뉴 확인하러 복귀.")
        self.current_state = PresentState.EVENT_MENU
        # === 변경 완료 ===
        return True

    def process_current_state(self, screen: Screen):
        """현재 상태에 따른 처리 (변경 없음)"""
        if self.current_state == PresentState.MAIN_SCREEN:
            return self.process_main_screen(screen)
        elif self.current_state == PresentState.EVENT_MENU:
            return self.process_event_menu(screen)
        elif self.current_state == PresentState.LEFT_MENU_SCROLL:
            return self.process_left_menu_scroll(screen)
        elif self.current_state == PresentState.RIGHT_CONTENT:
            return self.process_right_content(screen)
        elif self.current_state == PresentState.RIGHT_CONTENT_SCROLL:
            return self.process_right_content_scroll(screen)
        elif self.current_state == PresentState.REWARD_CLAIM:
            return self.process_reward_claim(screen)
        print(f"!!! 알 수 없는 상태: {self.current_state} !!!")
        return False

    def run(self):
        """모든 화면에서 Daily Present 처리 (수정됨 - 초기화 로직 위치 수정)""" # 독스트링 수정
        print("Daily Present 처리 시작...")
        countdown_time = 5
        for i in range(countdown_time, 0, -1):
            print(f"시작까지 {i}초...")
            time.sleep(1)

        try:
            # 화면 처리 루프 시작 전 초기화 (index는 여기서 하는게 맞음)
            self.current_screen_index = 0
            while self.current_screen_index < len(self.screens):
                # ... (키보드 중단 체크) ...

                screen = self.screens[self.current_screen_index]
                print(f"\n--- 화면 {screen.screen_id} 처리 시작 --- (상태: {self.current_state.name})")

                # 상태 처리
                result = self.process_current_state(screen)

                # process_current_state의 반환값에 따른 처리
                if result:
                    # 성공 시: 같은 화면에서 다음 상태 진행 (특별한 처리 없음)
                    pass
                else:
                    # 실패 또는 화면 처리 완료 시 (False 반환 시): 다음 화면으로 넘어감
                    print(f"화면 {screen.screen_id} 처리 완료 또는 실패 감지. 다음 화면으로 이동.")
                    self.current_screen_index += 1
                    self.current_state = PresentState.MAIN_SCREEN # 다음 화면은 항상 메인부터

                    # ================================================
                    # >> 다음 화면 처리를 위한 상태 변수 초기화 <<
                    # ================================================
                    print(f"  -> 다음 화면({self.current_screen_index})을 위해 상태 변수 초기화") # 로그 추가
                    self.left_scroll_attempts = 0 # <<< 왼쪽 스크롤 횟수 초기화
                    self.last_clicked_left_dot_info = None # 마지막 클릭 정보 초기화
                    self.right_scroll_needed = False # 오른쪽 스크롤 필요 플래그 초기화
                    self.current_item_right_scroll_attempts = 0 # 오른쪽 스크롤 횟수 초기화
                    # self.is_first_entry_to_event_menu = True # 이 플래그도 필요 시 초기화
                    # ================================================

                time.sleep(0.3) # 메인 루프 지연

            print("\n--- 모든 화면의 Daily Present 처리 완료 ---")

        # ... (except, finally 블록은 동일) ...
        except KeyboardInterrupt:
            print("키보드 인터럽트로 중단됨")
        except Exception as e:
            print(f"에러 발생: {e}")
            traceback.print_exc()
        finally:
            print("Daily Present 처리 종료")

if __name__ == "__main__":
    # 샘플 실행 코드
    dp = DailyPresent()
    # 화면 추가 (실제 경로 및 screen_info.py 설정 필요)
    dp.add_screen(screen_id='S1', main_event_icon=r"C:\Users\yjy16\template\NightCrows\DP\event_icon_s1.png")
    dp.add_screen(screen_id='S2', main_event_icon=r"C:\Users\yjy16\template\NightCrows\DP\event_icon_s2.png")
    # ... S3, S4, S5 추가 ...
    dp.run()