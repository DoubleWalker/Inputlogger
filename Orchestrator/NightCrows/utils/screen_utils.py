# Orchestrator/NightCrows/utils/screen_utils.py
from typing import Dict
import cv2
import numpy as np
import pyautogui
import keyboard
import time
import random
from .screen_info import SCREEN_REGIONS
from .image_utils import set_focus, is_image_present


class TaskScreenPreparer:
    """NightCrows DP/MO 작업 실행 전 화면 준비 및 정리"""

    def __init__(self, confidence_threshold: float = 0.85):
        self.confidence_threshold = confidence_threshold
        # 화면별 X 버튼 템플릿
        self.close_x_templates = {
            'S1': r"C:\Users\yjy16\template\NightCrows\close_x_s1.png",
            'S2': r"C:\Users\yjy16\template\NightCrows\close_x_s2.png",
            'S3': r"C:\Users\yjy16\template\NightCrows\close_x_s3.png",
            'S4': r"C:\Users\yjy16\template\NightCrows\close_x_s4.png",
            'S5': r"C:\Users\yjy16\template\NightCrows\close_x_s5.png",
        }

    def prepare_all_screens(self):
        """모든 화면(S1~S5) 정리 및 준비"""
        print("TaskScreenPreparer: Preparing NightCrows screens for task execution...")

        for screen_id in ['S1', 'S2', 'S3', 'S4', 'S5']:
            print(f"  Preparing screen {screen_id}...")
            self._prepare_single_screen(screen_id)
            time.sleep(0.3)  # 화면 간 딜레이

        print("TaskScreenPreparer: All NightCrows screens prepared successfully")

    def _prepare_single_screen(self, screen_id: str):
        """개별 화면 정리"""
        try:
            # 1. 포커스 설정
            if not set_focus(screen_id, delay_after=0.2):
                print(f"    Warning: Failed to set focus on {screen_id}")
                return

            # 2. ESC 키 입력 (기본 UI 정리)
            keyboard.press_and_release('esc')
            time.sleep(0.3)

            # 3. X 버튼이 있는 경우에만 팝업 정리
            if self._has_close_button(screen_id):
                self._clean_popups_nightcrows(screen_id)

        except Exception as e:
            print(f"    Error preparing screen {screen_id}: {e}")

    def _has_close_button(self, screen_id: str) -> bool:
        """X 버튼이 있는지 확인"""
        template_path = self.close_x_templates.get(screen_id)
        if not template_path:
            return False

        if screen_id not in SCREEN_REGIONS:
            return False

        screen_region = SCREEN_REGIONS[screen_id]
        return is_image_present(template_path, screen_region, self.confidence_threshold)

    def _clean_popups_nightcrows(self, screen_id: str):
        """NightCrows 팝업 정리 - X 템플릿 찾아서 클릭"""
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
            print(f"    Error cleaning popups on {screen_id}: {e}")
# Orchestrator/NightCrows/utils/screen_utils.py (기존 파일에 추가)

def detect_designated_template_image(screen_id: str, screen_region: tuple, template_path: str) -> bool:
    """지정된 템플릿 이미지 감지 - 진짜 글로벌 조합된 액션"""
    if not template_path:
        return False
    return is_image_present(template_path, screen_region)

def click_designated_template_image(screen_id: str, screen_region: tuple, template_path: str) -> bool:
    """지정된 템플릿 이미지 클릭 - 진짜 글로벌 조합된 액션"""
    if not template_path:
        return False
    from .image_utils import click_image
    return click_image(template_path, screen_region)