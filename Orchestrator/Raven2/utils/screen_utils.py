# Orchestrator/Raven2/utils/screen_utils.py
from typing import Dict
import cv2
import numpy as np
import pyautogui
import keyboard
import time
import random
from .screen_info import SCREEN_REGIONS, FIXED_UI_COORDS
from .image_utils import set_focus, is_image_present


class TaskScreenPreparer:
    """Raven2 DP/MO 작업 실행 전 화면 준비 및 정리"""

    def __init__(self, confidence_threshold: float = 0.85):
        self.confidence_threshold = confidence_threshold
        # 화면별 X 버튼 템플릿
        self.close_x_templates = {
            'S1': r"C:\Users\yjy16\template\RAVEN2\close_x_s1.png",
            'S2': r"C:\Users\yjy16\template\RAVEN2\close_x_s2.png",
            'S3': r"C:\Users\yjy16\template\RAVEN2\close_x_s3.png",
            'S4': r"C:\Users\yjy16\template\RAVEN2\close_x_s4.png",
            'S5': r"C:\Users\yjy16\template\RAVEN2\close_x_s5.png",
        }

    def prepare_all_screens(self):
        """모든 화면(S1~S5) 정리 및 준비"""
        print("TaskScreenPreparer: Preparing Raven2 screens for task execution...")

        for screen_id in ['S1', 'S2', 'S3', 'S4', 'S5']:
            print(f"  Preparing screen {screen_id}...")
            self._prepare_single_screen(screen_id)
            time.sleep(0.3)  # 화면 간 딜레이

        print("TaskScreenPreparer: All Raven2 screens prepared successfully")

    def _prepare_single_screen(self, screen_id: str):
        try:
            # 1. 잠금 해제 버튼 클릭
            self._click_fixed_coord(screen_id, 'unlock_button')
            time.sleep(0.3)

            # 2. 확인버튼 클릭 (기존 retreat_confirm_button 사용)
            self._click_fixed_coord(screen_id, 'retreat_confirm_button')
            time.sleep(0.3)

        except Exception as e:
            print(f"    Error preparing screen {screen_id}: {e}")

    def _click_fixed_coord(self, screen_id: str, coord_key: str):
        """FIXED_UI_COORDS에서 지정된 좌표를 클릭"""
        try:
            # FIXED_UI_COORDS에서 좌표 가져오기
            if screen_id in FIXED_UI_COORDS and coord_key in FIXED_UI_COORDS[screen_id]:
                screen_region = SCREEN_REGIONS[screen_id]
                relative_coords = FIXED_UI_COORDS[screen_id][coord_key]  # ← coord_key 사용

                # 절대 좌표 계산
                click_x = screen_region[0] + relative_coords[0]
                click_y = screen_region[1] + relative_coords[1]

                # 클릭
                pyautogui.click(click_x, click_y)
                time.sleep(0.2)
                print(f"    Clicked {coord_key} on {screen_id}")  # ← coord_key 출력
            else:
                print(f"    Warning: {coord_key} coordinates not found for {screen_id}")  # ← coord_key 출력

        except Exception as e:
            print(f"    Error clicking {coord_key} on {screen_id}: {e}")  # ← coord_key 출력

    def _has_close_button(self, screen_id: str) -> bool:
        """X 버튼이 있는지 확인"""
        template_path = self.close_x_templates.get(screen_id)
        if not template_path:
            return False

        if screen_id not in SCREEN_REGIONS:
            return False

        screen_region = SCREEN_REGIONS[screen_id]
        return is_image_present(template_path, screen_region, self.confidence_threshold)

    def _click_close_button(self, screen_id: str):
        """X 버튼 템플릿 찾아서 클릭"""
        screen_region = SCREEN_REGIONS[screen_id]
        template_path = self.close_x_templates.get(screen_id)

        if not template_path:
            print(f"    Warning: No close button template for {screen_id}")
            return

        try:
            print(f"    Found close button on {screen_id}, clicking...")

            # X 버튼 위치 찾아서 클릭
            screenshot = pyautogui.screenshot(region=screen_region)
            template = cv2.imread(template_path)

            if template is not None:
                screen_gray = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
                template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

                result = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(result)

                if max_val > self.confidence_threshold:
                    template_h, template_w = template_gray.shape

                    # X 버튼 중앙 좌표 계산
                    center_x = screen_region[0] + max_loc[0] + template_w // 2
                    center_y = screen_region[1] + max_loc[1] + template_h // 2

                    # 1픽셀 랜덤 오프셋 추가
                    random_offset_x = random.randint(-1, 1)
                    random_offset_y = random.randint(-1, 1)

                    click_x = center_x + random_offset_x
                    click_y = center_y + random_offset_y

                    # X 버튼 클릭
                    pyautogui.click(click_x, click_y)
                    time.sleep(0.2)
                    print(f"    Closed popup on {screen_id} at ({click_x}, {click_y})")

        except Exception as e:
            print(f"    Error cleaning close button on {screen_id}: {e}")