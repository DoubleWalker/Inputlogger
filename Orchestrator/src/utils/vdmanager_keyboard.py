import cv2
import numpy as np
import pyautogui
import keyboard
import time
from enum import Enum
from ..utils.config import TASKBAR_CONFIG


class VirtualDesktop(Enum):
    VD1 = "VD1"  # 게임1
    VD2 = "VD2"  # 게임2
    OTHER = "OTHER"


class VDManager:
    def __init__(self):
        self.taskbar_region = TASKBAR_CONFIG.region
        self.game1_icon = TASKBAR_CONFIG.game1_icon
        self.game2_icon = TASKBAR_CONFIG.game2_icon
        self.confidence_threshold = TASKBAR_CONFIG.confidence_threshold

    def get_current_vd(self) -> VirtualDesktop:
        """현재 VD 위치 확인"""
        try:
            taskbar = pyautogui.screenshot(region=self.taskbar_region)
            taskbar_cv = cv2.cvtColor(np.array(taskbar), cv2.COLOR_RGB2GRAY)

            game1_template = cv2.imread(self.game1_icon, 0)
            game1_result = cv2.matchTemplate(taskbar_cv, game1_template, cv2.TM_CCOEFF_NORMED)
            game1_match = cv2.minMaxLoc(game1_result)[1]

            game2_template = cv2.imread(self.game2_icon, 0)
            game2_result = cv2.matchTemplate(taskbar_cv, game2_template, cv2.TM_CCOEFF_NORMED)
            game2_match = cv2.minMaxLoc(game2_result)[1]

            if game1_match > self.confidence_threshold:
                return VirtualDesktop.VD1
            elif game2_match > self.confidence_threshold:
                return VirtualDesktop.VD2
            else:
                return VirtualDesktop.OTHER

        except Exception as e:
            print(f"VD 체크 중 에러 발생: {e}")
            return VirtualDesktop.OTHER

    def send_key_combination(self, key_combination):
        """keyboard 라이브러리로 키 조합 전송"""
        try:
            keyboard.press_and_release(key_combination)
            print(f"DEBUG: Sent key combination: {key_combination}")
        except Exception as e:
            print(f"키 입력 오류: {e}")

    def switch_to(self, target_vd: VirtualDesktop):
        print(f"DEBUG: switch_to called - target: {target_vd.name}")

        if target_vd == VirtualDesktop.OTHER:
            print("DEBUG: Target is OTHER, returning")
            return

        current_vd = self.get_current_vd()
        print(f"DEBUG: Current VD detected: {current_vd.name}")

        if current_vd == target_vd:
            print(f"DEBUG: Already at target {target_vd.name}, returning")
            return

        print(f"DEBUG: About to send keyboard input for {current_vd.name} → {target_vd.name}")

        # OTHER에서 VD1으로 = 오른쪽 한 번
        if current_vd == VirtualDesktop.OTHER and target_vd == VirtualDesktop.VD1:
            time.sleep(0.1)
            self.send_key_combination('ctrl+win+right')
            time.sleep(0.5)

        # OTHER에서 VD2로 = 오른쪽 두 번
        elif current_vd == VirtualDesktop.OTHER and target_vd == VirtualDesktop.VD2:
            for _ in range(2):
                time.sleep(0.1)
                self.send_key_combination('ctrl+win+right')
                time.sleep(0.2)

        # VD1에서 VD2로 = 오른쪽 한 번
        elif current_vd == VirtualDesktop.VD1 and target_vd == VirtualDesktop.VD2:
            print("DEBUG: Sending Ctrl+Win+Right...")
            time.sleep(0.1)
            self.send_key_combination('ctrl+win+right')
            time.sleep(0.5)
            print("DEBUG: Keyboard input sent")

        # VD2에서 VD1로 = 왼쪽 한 번
        elif current_vd == VirtualDesktop.VD2 and target_vd == VirtualDesktop.VD1:
            time.sleep(0.1)
            self.send_key_combination('ctrl+win+left')
            time.sleep(0.5)