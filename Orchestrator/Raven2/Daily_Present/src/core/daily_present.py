# Orchestrator/Raven2/Daily_Present/src/core/daily_present.py
# DP1의 상태 머신 로직을 적용하여 수정한 버전

from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional, Dict # Dict 추가 (DP1 참고)
import cv2
import numpy as np
import traceback
import pyautogui
import keyboard
import time
import random
import os
from Orchestrator.Raven2.utils.screen_info import SCREEN_REGIONS, EVENT_UI_REGIONS


DEBUG_OUTPUT_FOLDER = r"C:\Users\yjy16\template\test"
if not os.path.exists(DEBUG_OUTPUT_FOLDER):
    os.makedirs(DEBUG_OUTPUT_FOLDER)

# 상태 정의 (DP1과 동일)
class PresentState(Enum):
    """Daily Present 상태 머신의 상태들"""
    MAIN_SCREEN = 0
    EVENT_MENU = 1
    LEFT_MENU_SCROLL = 2
    RIGHT_CONTENT = 3
    RIGHT_CONTENT_SCROLL = 4
    REWARD_CLAIM = 5

@dataclass
class Screen:
    screen_id: str
    main_event_icon: str

    @property
    def region(self):
        """화면의 전체 영역 반환"""
        return SCREEN_REGIONS[self.screen_id]

class DailyPresent:
    def __init__(self, confidence_threshold: float = 0.85):
        self.screens: List[Screen] = []
        self.threshold = confidence_threshold
        self.current_state = PresentState.MAIN_SCREEN
        self.current_screen_index = 0

        # === DP1 로직 기반 상태 변수 ===
        self.left_scroll_attempts = 0
        self.max_scroll_attempts = 3 # 왼쪽 스크롤 + 오른쪽 스크롤 최대치 공용 사용 가능
        self.left_scroll_direction_down = True
        self.right_scroll_direction_down = True # 오른쪽 스크롤 방향

        # 마지막 클릭된 왼쪽 붉은 점 정보 (좌표 저장)
        self.last_clicked_left_dot_pos: Optional[Tuple[int, int]] = None
        # 오른쪽 스크롤 필요 여부 플래그
        self.right_scroll_needed: bool = False
        # 오른쪽 스크롤 시도 횟수 (같은 왼쪽 아이템에 대해)
        self.current_item_right_scroll_attempts: int = 0
        self.max_right_scroll_per_item: int = 3 # 오른쪽 스크롤 최대 횟수 (DP1 참고)
        # ==============================

        # --- DP2 고유 변수 제거 ---
        # self.right_scroll_attempts = 0 # 제거
        # self.is_first_entry_to_event_menu = True # 제거
        # -------------------------

    def add_screen(self, screen_id: str, main_event_icon: str):
        """화면 정보 추가"""
        self.screens.append(Screen(
            screen_id=screen_id,
            main_event_icon=main_event_icon
        ))

    # --- 영역 가져오기 메서드 (변경 없음) ---
    def get_left_menu_region(self, screen: Screen) -> Tuple[int, int, int, int]:
        return EVENT_UI_REGIONS[screen.screen_id]['left_menu']

    def get_right_content_region(self, screen: Screen) -> Tuple[int, int, int, int]:
        return EVENT_UI_REGIONS[screen.screen_id]['right_content']

    # --- UI 위치 찾기 메서드 (변경 없음) ---
    def find_ui_location_in_region(self, region: Tuple[int, int, int, int], template_path: str) -> Optional[Tuple[int, int]]:
        # ... (기존 DP2 코드와 동일) ...
        try:
            screenshot = pyautogui.screenshot(region=region)
            template = cv2.imread(template_path)
            if template is None: return None # 경로 오류 등
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

    # --- 핵심 탐지 메서드들 (내부 로직은 DP2 것 유지) ---
        # Orchestrator/Raven2/Daily_Present/src/core/daily_present.py 내부에 포함될 함수
        # (SimpleBlobDetector 및 복잡한 필터링 대신 단순 Contour 및 Area 필터링 사용)

    def find_all_red_dots_with_blob_detector(self, region: Tuple[int, int, int, int], screen_id: str) -> List[
            Tuple[int, int]]:
            """
            지정된 영역에서 빨간색 Contour를 찾아 면적 기준으로 필터링하고 중심 좌표 리스트를 반환합니다.
            (형태 필터링 제거)
            """
            x_region, y_region, w_region, h_region = region
            valid_centers = []  # 최종 반환될 중심 좌표 리스트

            try:
                # 1. 지정된 영역만 캡처
                screenshot_roi = pyautogui.screenshot(region=region)
                img_roi = np.array(screenshot_roi)
                img_roi_bgr = cv2.cvtColor(img_roi, cv2.COLOR_RGB2BGR)

                # 2. HSV 변환 및 빨간색 마스크 생성
                hsv = cv2.cvtColor(img_roi_bgr, cv2.COLOR_BGR2HSV)
                lower_red1 = np.array([0, 100, 100])
                upper_red1 = np.array([6, 255, 255])
                lower_red2 = np.array([170, 100, 100])
                upper_red2 = np.array([180, 255, 255])
                mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
                mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
                red_mask = cv2.bitwise_or(mask1, mask2)

                # 3. (선택 사항) 모폴로지 연산으로 노이즈 제거
                kernel = np.ones((3, 3), np.uint8)
                red_mask_opened = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)
                # 필요시 Closing도 추가 가능:
                # red_mask_closed = cv2.morphologyEx(red_mask_opened, cv2.MORPH_CLOSE, kernel)
                # target_mask = red_mask_closed
                target_mask = red_mask_opened  # 최종 사용할 마스크

                # --- (디버깅용) 마스크 이미지 저장 ---
                # DEBUG_OUTPUT_FOLDER = r"C:\Users\yjy16\template\test"
                # if not os.path.exists(DEBUG_OUTPUT_FOLDER): os.makedirs(DEBUG_OUTPUT_FOLDER, exist_ok=True)
                # timestamp = time.strftime('%Y%m%d_%H%M%S')
                # cv2.imwrite(os.path.join(DEBUG_OUTPUT_FOLDER, f"debug_red_mask_{screen_id}_{timestamp}.png"), target_mask)
                # --- 디버깅용 코드 끝 ---

                # 4. 마스크에서 Contour 찾기
                contours, _ = cv2.findContours(target_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                # 5. Contour 크기 필터링 및 중심 좌표 계산
                # 크기 기준값 (기존 BlobDetector 값 참고 또는 조정)
                min_area = 25.0 if screen_id == 'S5' else 4.0
                max_area = 60.0 if screen_id == 'S5' else 30.0

                for contour in contours:
                    area = cv2.contourArea(contour)
                    # 크기 필터링
                    if min_area <= area <= max_area:
                        # 중심 좌표 계산 (Moments 사용)
                        M = cv2.moments(contour)
                        if M["m00"] != 0:
                            center_x_rel = int(M["m10"] / M["m00"])  # ROI 내 상대 좌표
                            center_y_rel = int(M["m01"] / M["m00"])  # ROI 내 상대 좌표

                            # 전체 화면 기준 절대 좌표로 변환
                            center_x_abs = x_region + center_x_rel
                            center_y_abs = y_region + center_y_rel

                            # 랜덤 오프셋 추가 (기존 로직 유지)
                            final_x = center_x_abs + random.randint(-2, 2)
                            final_y = center_y_abs + random.randint(-2, 2)
                            valid_centers.append((final_x, final_y))

                print(f"{screen_id} 영역에서 감지된 빨간색 요소 (단순 필터링): {len(valid_centers)}개")
                return valid_centers

            except Exception as e:
                print(f"단순 빨간점 감지 중 오류 발생 ({screen_id}): {e}")
                traceback.print_exc()
                return []
    def find_glowing_items_in_region(self, region: Tuple[int, int, int, int], screen_id: str) -> List[Tuple[int, int]]: # 반환 타입 좌표 튜플 리스트 유지
        try:
            x, y, w, h = region
            screenshot = pyautogui.screenshot(region=region)
            image_roi = np.array(screenshot) # ROI 이미지

            # --- 가우시안 블러 제거 ---
            # if screen_id == 'S5':
            #     image_roi_processed = cv2.GaussianBlur(image_roi, (5, 5), 0)
            # else:
            #     image_roi_processed = image_roi.copy()
            image_roi_processed = image_roi.copy() # 모든 화면에서 블러 사용 안 함
            # --- 블러 제거 완료 ---

            # BGR 변환 (OpenCV 처리용)
            image_bgr = cv2.cvtColor(image_roi_processed, cv2.COLOR_RGB2BGR)

            # 그레이스케일 변환 및 이진화 (Threshold)
            gray_img = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
            # --- Threshold 값 수정 ---
            threshold_value = 55 # 70에서 55로 변경
            # --- Threshold 값 수정 완료 ---
            _, binary_img = cv2.threshold(gray_img, threshold_value, 255, cv2.THRESH_BINARY)
            # print(f"Applied threshold: {threshold_value}") # 필요시 로그 유지

            # Contour 찾기
            # --- Contour 검색 모드 수정 ---
            # contours, _ = cv2.findContours(binary_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            contours, _ = cv2.findContours(binary_img, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE) # RETR_LIST로 변경
            # --- Contour 검색 모드 수정 완료 ---
            # print(f"Found {len(contours)} initial contours (using RETR_LIST)") # 필요시 로그 유지

            found_items = [] # 최종 반환될 좌표 리스트

            for i, contour in enumerate(contours):
                # 필터링 조건 (조정된 기준 적용)
                area = cv2.contourArea(contour)
                # 면적 범위는 이전 기준 유지 (S5: 300-3000, Others: 200-2000) - 필요시 조정
                min_area = 300 if screen_id == 'S5' else 200
                max_area = 3000 if screen_id == 'S5' else 2000

                passes_area = min_area <= area <= max_area
                if not passes_area: continue

                epsilon = 0.04 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                num_vertices = len(approx)
                is_convex = cv2.isContourConvex(approx) if num_vertices >= 3 else False

                passes_vertices = 4 <= num_vertices <= 6 # 꼭지점 수 조건은 일단 유지 (필요시 조정)
                passes_convexity = is_convex             # 볼록성 조건 유지 (필요시 조정)

                if not (passes_vertices and passes_convexity): continue

                rx, ry, rw, rh = cv2.boundingRect(approx)
                aspect_ratio = float(rw) / rh if rh != 0 else 0
                area_ratio = area / (rw * rh) if (rw * rh) != 0 else 0

                passes_aspect_ratio = 0.9 <= aspect_ratio <= 1.1 # 종횡비 조건 유지 (필요시 조정)
                # --- 면적 비율 조건 수정 ---
                passes_area_ratio = area_ratio >= 0.7         # 0.75 또는 0.6에서 0.65로 변경
                # --- 면적 비율 조건 수정 완료 ---

                # 모든 필터 통과 여부
                if passes_aspect_ratio and passes_area_ratio: # 면적, 모양 조건은 이미 위에서 continue로 처리됨
                    center_x = x + rx + rw // 2
                    center_y = y + ry + rh // 2
                    final_x = center_x + random.randint(-3, 3) # 랜덤 오프셋은 유지 (DP2 원래 로직)
                    final_y = center_y + random.randint(-3, 3)
                    found_items.append((final_x, final_y))

            # print(f"{screen_id} 영역에서 감지된 빛나는 UI 요소: {len(found_items)}개") # 필요시 로그 유지
            return found_items

        except Exception as e:
            print(f"빛나는 UI 요소 감지 중 오류 발생 ({screen_id}): {e}") # 에러 로그에 screen_id 추가
            traceback.print_exc()
            return []

    # --- Wrapper 메서드 (DP1 구조 참고하되, 내부 호출은 DP2 탐지 메서드 유지) ---
    def find_red_dot_in_left_menu(self, screen: Screen) -> List[Tuple[int, int]]:
        """왼쪽 메뉴 영역 내에서 모든 유효한 빨간 점 위치 리스트 찾기 (DP2 탐지 로직 호출)"""
        menu_region = self.get_left_menu_region(screen)
        # DP2의 빨간 점 탐지 로직 호출
        return self.find_all_red_dots_with_blob_detector(menu_region, screen.screen_id)

    # DP1과의 일관성을 위해 이름을 맞추되, 내부에서는 glowing item 탐색 (주석으로 명시)
    def find_red_dot_in_right_content(self, screen: Screen) -> List[Tuple[int, int]]:
        """오른쪽 콘텐츠 영역 내에서 모든 빛나는 UI 요소 위치 리스트 찾기 (DP2 탐지 로직 호출)"""
        content_region = self.get_right_content_region(screen)
        # DP2의 빛나는 아이템 탐지 로직 호출
        return self.find_glowing_items_in_region(content_region, screen.screen_id)
        # === 만약 '빛나는 아이템'이라는 이름이 더 명확하다면 아래처럼 유지하고 호출부 수정 ===
        # def find_glowing_items_in_right_content(self, screen: Screen) -> List[Tuple[int, int]]:
        #     content_region = self.get_right_content_region(screen)
        #     return self.find_glowing_items_in_region(content_region, screen.screen_id)

    # --- 클릭/스크롤 메서드 (변경 없음) ---
    def click_with_offset(self, position: Tuple[int, int], offset_x: int = -2, offset_y: int = 2):
        pyautogui.click(position[0] + offset_x, position[1] + offset_y)

    def scroll_in_left_menu(self, screen: Screen):
        # ... (기존 DP2 스크롤 로직 유지 또는 DP1 로직 적용 - DP1 로직 적용) ...
        try:
            menu_region = self.get_left_menu_region(screen); start_x = menu_region[0] + menu_region[2] // 2
            # DP1의 스크롤 방향 및 위치 로직 적용
            if self.left_scroll_direction_down: start_y = menu_region[1] + menu_region[3] * 3 // 4; end_y = menu_region[1] + menu_region[3] // 3; direction_str = "DOWN"
            else: start_y = menu_region[1] + menu_region[3] // 3; end_y = menu_region[1] + menu_region[3] * 3 // 4; direction_str = "UP"
            end_x = start_x; print(f"[{screen.screen_id}] 왼쪽 메뉴 {direction_str} 스크롤 시작")
            pyautogui.moveTo(start_x, start_y); time.sleep(0.05) # DP1 스타일 sleep
            pyautogui.mouseDown(button='left'); time.sleep(0.05) # DP1 스타일 sleep
            pyautogui.moveTo(end_x, end_y, duration=0.15) # DP1 스타일 duration
            pyautogui.mouseUp(button='left'); time.sleep(0.5) # DP1 스타일 sleep (0.1->0.5로 약간 늘림)
            self.left_scroll_direction_down = not self.left_scroll_direction_down
            print(f"[{screen.screen_id}] {direction_str} 스크롤 완료"); return True
        except Exception as e: print(f"Error in scroll_in_left_menu: {e}"); pyautogui.mouseUp(button='left'); return False

    def scroll_in_right_content(self, screen: Screen):
        # ... (기존 DP2 스크롤 로직 유지 또는 DP1 로직 적용 - DP1 로직 적용) ...
        try:
            content_region = self.get_right_content_region(screen); start_x = content_region[0] + content_region[2] // 2
            # DP1의 스크롤 방향 및 위치 로직 적용 (비율은 DP2 것 유지)
            if self.right_scroll_direction_down: start_y = content_region[1] + content_region[3] * 5 // 6; end_y = content_region[1] + content_region[3] // 3; direction_str = "DOWN" # DP2 비율
            else: start_y = content_region[1] + content_region[3] * 1 // 5; end_y = content_region[1] + content_region[3] * 4 // 5; direction_str = "UP" # DP2 비율
            end_x = start_x; print(f"[{screen.screen_id}] 오른쪽 콘텐츠 {direction_str} 스크롤 시작")
            pyautogui.moveTo(start_x, start_y); time.sleep(0.05) # DP1 스타일 sleep
            pyautogui.mouseDown(button='left'); time.sleep(0.05) # DP1 스타일 sleep
            pyautogui.moveTo(end_x, end_y, duration=0.15) # DP1 스타일 duration (0.3->0.15)
            pyautogui.mouseUp(button='left'); time.sleep(0.1) # DP1 스타일 sleep (0.2->0.1)
            self.right_scroll_direction_down = not self.right_scroll_direction_down
            print(f"[{screen.screen_id}] {direction_str} 스크롤 완료"); return True
        except Exception as e: print(f"Error in scroll_in_right_content: {e}"); pyautogui.mouseUp(button='left'); return False


    # === 상태 처리 메소드 수정 (DP1 로직 기반) ===

    def process_main_screen(self, screen: Screen):
        """메인 화면 처리 (DP1 로직 적용)"""
        print(f"[{screen.screen_id}] 메인 화면 처리 중...")
        event_icon_pos = self.find_ui_location(screen, screen.main_event_icon)
        if event_icon_pos:
            print(f"[{screen.screen_id}] 이벤트 아이콘 발견, 클릭")
            pyautogui.click(event_icon_pos[0], event_icon_pos[1])
            time.sleep(0.3) # DP1과 유사한 대기 시간 (0.3)
            # <<< DP1의 상태 변수 초기화 로직 추가 >>>
            self.last_clicked_left_dot_pos = None
            self.right_scroll_needed = False
            self.current_item_right_scroll_attempts = 0
            # self.is_first_entry_to_event_menu = True # 이 플래그는 사용 안 함
            # <<< 초기화 끝 >>>
            self.current_state = PresentState.EVENT_MENU
            return True
        print(f"[{screen.screen_id}] 이벤트 아이콘을 찾을 수 없음")
        return False # 실패 시 False 반환 (run 메소드에서 처리)

    def process_event_menu(self, screen: Screen):
        """이벤트 메뉴 처리 (DP1 로직 적용 + 근접성 체크 추가)"""
        print(f"[{screen.screen_id}] 이벤트 메뉴 처리 중...")

        # 왼쪽 메뉴에서 붉은 점 찾기 (DP2 탐지 메서드 호출)
        red_dot_positions = self.find_red_dot_in_left_menu(screen)

        if red_dot_positions:
            target_dot_pos = red_dot_positions[0]  # 첫 번째 점 선택
            print(f"[{screen.screen_id}] 왼쪽 붉은 점 발견: {target_dot_pos}")

            # --- 근접성 체크 로직 ---
            is_same_item = False
            if self.last_clicked_left_dot_pos:
                # 유클리드 거리 계산 (math.dist 사용 가능, 여기서는 수동 계산)
                dist_sq = (target_dot_pos[0] - self.last_clicked_left_dot_pos[0]) ** 2 + \
                          (target_dot_pos[1] - self.last_clicked_left_dot_pos[1]) ** 2
                proximity_threshold_sq = 10 ** 2  # 예: 10픽셀 이내면 같은 것으로 간주 (제곱값으로 비교)
                if dist_sq < proximity_threshold_sq:
                    is_same_item = True
            # ------------------------

            # DP1의 이전 클릭 비교 및 오른쪽 스크롤 필요 여부 판단 로직 적용 (근접성 체크 결과 사용)
            # if self.last_clicked_left_dot_pos == target_dot_pos: # 기존 비교 제거
            if is_same_item:  # 수정된 비교 사용
                self.current_item_right_scroll_attempts += 1
                print(
                    f"  -> 근접한 항목 재클릭 감지 (거리 제곱: {dist_sq:.2f}). 오른쪽 스크롤 시도 ({self.current_item_right_scroll_attempts}/{self.max_right_scroll_per_item}).")
                if self.current_item_right_scroll_attempts > self.max_right_scroll_per_item:
                    print(f"  -> 오른쪽 최대 스크롤 도달. 이 항목 건너뛰고 왼쪽 스크롤 시도.")
                    self.current_state = PresentState.LEFT_MENU_SCROLL
                    # 다음 왼쪽 스크롤 시도를 위해 현재 아이템 정보 초기화 (선택 사항)
                    # self.last_clicked_left_dot_pos = None # 필요시 주석 해제
                    return True
                else:
                    self.right_scroll_needed = True  # 오른쪽 스크롤 필요 플래그 설정
                    # 같은 아이템이므로 last_clicked_left_dot_pos 업데이트 안 함
            else:
                # 다른 점 클릭 시 초기화
                print(f"  -> 새로운 항목 클릭.")
                self.right_scroll_needed = False
                self.current_item_right_scroll_attempts = 0  # 새 항목이므로 리셋
                self.last_clicked_left_dot_pos = target_dot_pos  # 마지막 클릭 정보 업데이트 (새 항목일 때만)

            # 선택된 붉은 점 클릭 (같은 아이템이어도 클릭은 다시 수행)
            self.click_with_offset(target_dot_pos, -2, 2)
            # last_clicked_left_dot_pos 업데이트는 is_same_item == False 일 때 위에서 처리됨
            time.sleep(0.2)
            self.current_state = PresentState.RIGHT_CONTENT
            return True

        # 붉은 점이 없다면 왼쪽 스크롤 시도 (DP1 로직)
        elif self.left_scroll_attempts < self.max_scroll_attempts:
            print(
                f"[{screen.screen_id}] 왼쪽 붉은 점 없음, 스크롤 시도 ({self.left_scroll_attempts + 1}/{self.max_scroll_attempts})")
            self.current_state = PresentState.LEFT_MENU_SCROLL
            return True
        else:
            # 왼쪽 스크롤 다 했는데도 붉은 점 없으면 종료 (DP1 로직)
            print(f"[{screen.screen_id}] 왼쪽 붉은 점 없음, 최대 스크롤 시도 도달, DP 종료.")
            keyboard.press_and_release('esc')
            time.sleep(0.3)
            self.current_state = PresentState.MAIN_SCREEN
            return False
    def process_left_menu_scroll(self, screen: Screen):
        """왼쪽 메뉴 스크롤 처리 (DP1 로직과 동일)"""
        print(f"[{screen.screen_id}] 왼쪽 메뉴 스크롤 중... (시도 {self.left_scroll_attempts + 1}/{self.max_scroll_attempts})")
        if self.scroll_in_left_menu(screen):
            self.left_scroll_attempts += 1
            print(f"[{screen.screen_id}] 스크롤 완료 (총 {self.left_scroll_attempts}회)")
            self.current_state = PresentState.EVENT_MENU # 스크롤 후 다시 이벤트 메뉴 확인
            return True
        print(f"[{screen.screen_id}] 스크롤 실패")
        # 스크롤 실패 시에도 일단 EVENT_MENU로 돌아가서 최종 종료 로직 타도록 함 (DP1과 동일)
        self.current_state = PresentState.EVENT_MENU
        return False # 실패 처리

    def process_right_content(self, screen: Screen):
        """오른쪽 콘텐츠 처리 (DP1 로직 적용, 탐지 메서드는 DP2 것 사용)"""
        print(f"[{screen.screen_id}] 오른쪽 콘텐츠 처리 중...")

        # 스크롤이 필요한 경우인지 확인 (DP1 로직)
        if self.right_scroll_needed:
            print(f"  -> 오른쪽 스크롤 필요 플래그 감지.")
            self.right_scroll_needed = False # 플래그 사용했으니 리셋
            self.current_state = PresentState.RIGHT_CONTENT_SCROLL # 스크롤 상태로 전환
            return True

        # 스크롤 필요 없으면 보이는 영역에서 아이템 찾기
        print(f"  -> 보이는 영역에서 오른쪽 빛나는 아이템(보상) 찾기 시도...")
        # <<< DP2의 빛나는 아이템 탐지 메서드 호출 >>>
        glowing_item_positions = self.find_red_dot_in_right_content(screen) # 이름은 find_red_dot이지만 실제로는 glowing 탐색

        if glowing_item_positions:
            # 아이템(보상)을 찾았으면 클릭하고 REWARD_CLAIM 상태로
            target_item_pos = glowing_item_positions[0]
            print(f"    -> 오른쪽 빛나는 아이템 발견: {target_item_pos}, 클릭.")
            self.click_with_offset(target_item_pos, -2, 2)
            time.sleep(0.2) # 클릭 후 상태 전환 전 잠시 대기 (DP1 값)
            self.current_state = PresentState.REWARD_CLAIM
            return True
        else:
            # 보이는 영역에 아이템 없으면 -> 왼쪽 메뉴 확인하러 돌아감 (스크롤 X) (DP1 로직)
            print(f"    -> 보이는 영역에 오른쪽 빛나는 아이템 없음. 왼쪽 메뉴로 복귀.")
            self.current_state = PresentState.EVENT_MENU
            return True

    def process_right_content_scroll(self, screen: Screen):
        """오른쪽 콘텐츠 스크롤 처리 (DP1 로직 적용)"""
        # 이 메소드는 스크롤만 하고 다시 RIGHT_CONTENT로 돌아감
        print(f"[{screen.screen_id}] 오른쪽 콘텐츠 스크롤 중... (항목 내 시도 {self.current_item_right_scroll_attempts}/{self.max_right_scroll_per_item})") # 카운터 표시 (DP1 참고)
        if self.scroll_in_right_content(screen):
            print(f"[{screen.screen_id}] 스크롤 완료")
            time.sleep(0.1) # 스크롤 후 짧은 대기 (DP1 값)
            self.current_state = PresentState.RIGHT_CONTENT # 스크롤 했으니 다시 오른쪽 확인
            return True
        print(f"[{screen.screen_id}] 스크롤 실패")
        # 스크롤 실패 시, 해당 아이템 처리 포기하고 왼쪽 메뉴로 돌아가도록 함 (DP1 로직)
        self.current_state = PresentState.EVENT_MENU
        return False

    def process_reward_claim(self, screen: Screen):
        """보상 수령 처리 (DP1 로직 적용)"""
        print(f"[{screen.screen_id}] 보상 수령 중...")

        # 보상 수령 후 처리 (DP1은 마우스 클릭, DP2는 ESC 사용 -> 우선 DP2의 ESC 유지)
        # 대기 시간은 DP2의 값(2.5초)을 사용 (게임별 애니메이션 시간 다를 수 있음)
        print(f"  -> 대기 시간 시작 (2.5초)...")
        time.sleep(2.5)
        print(f"  -> 대기 시간 종료. ESC 키 입력 실행.")
        keyboard.press_and_release('esc')
        time.sleep(0.6) # ESC 후 안정화 시간 (DP2 값 유지)

        # === 다음 상태를 EVENT_MENU로 변경 (DP1 로직 적용) ===
        print(f"  -> 보상 처리 완료. 왼쪽 메뉴 확인하러 복귀.")
        self.current_state = PresentState.EVENT_MENU
        # ==============================================
        return True

    def process_current_state(self, screen: Screen):
        """현재 상태에 따른 처리 (분기 로직은 DP1/DP2 동일)"""
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
        """모든 화면에서 Daily Present 처리 (DP1 로직 기반 - 상태 초기화 위치 등)"""
        print("Daily Present 처리 시작...")
        countdown_time = 5
        for i in range(countdown_time, 0, -1):
            print(f"시작까지 {i}초...")
            time.sleep(1)

        try:
            # 화면 처리 루프 시작 전 초기화 (index는 여기서)
            self.current_screen_index = 0
            while self.current_screen_index < len(self.screens):
                # 키보드 중단 체크 ('p' 키)
                if keyboard.is_pressed('p'):
                    print("사용자에 의해 중단됨 ('p' 키 입력)")
                    break

                screen = self.screens[self.current_screen_index]
                print(f"\n--- 화면 {screen.screen_id} 처리 시작 --- (상태: {self.current_state.name})")

                # 상태 처리
                result = self.process_current_state(screen)

                # process_current_state의 반환값에 따른 처리 (DP1 로직)
                if result:
                    # 성공 시: 같은 화면에서 다음 상태 진행 (별도 처리 없음)
                    pass
                else:
                    # 실패 또는 화면 처리 완료 시 (False 반환 시): 다음 화면으로 넘어감
                    print(f"화면 {screen.screen_id} 처리 완료 또는 실패 감지. 다음 화면으로 이동.")
                    self.current_screen_index += 1
                    self.current_state = PresentState.MAIN_SCREEN # 다음 화면은 항상 메인부터

                    # ================================================
                    # >> 다음 화면 처리를 위한 상태 변수 초기화 (DP1 위치) <<
                    # ================================================
                    if self.current_screen_index < len(self.screens): # 다음 화면이 있을 경우에만 초기화
                        print(f"  -> 다음 화면({self.screens[self.current_screen_index].screen_id})을 위해 상태 변수 초기화")
                        self.left_scroll_attempts = 0
                        self.last_clicked_left_dot_pos = None # DP1 스타일 초기화
                        self.right_scroll_needed = False      # DP1 스타일 초기화
                        self.current_item_right_scroll_attempts = 0 # DP1 스타일 초기화
                    # ================================================

                time.sleep(0.3) # 메인 루프 지연 (DP1 값)

            # while 루프 정상 종료 시
            if self.current_screen_index >= len(self.screens):
                 print("\n--- 모든 화면의 Daily Present 처리 완료 ---")

        # 예외 처리 (DP1/DP2 동일)
        except KeyboardInterrupt:
            print("키보드 인터럽트로 중단됨")
        except Exception as e:
            print(f"에러 발생: {e}")
            traceback.print_exc()
        finally:
            print("Daily Present 처리 종료")

# main 실행 부분은 기존 DP2의 main.py를 그대로 사용하면 됩니다.
# 이 파일은 클래스 정의만 포함합니다.