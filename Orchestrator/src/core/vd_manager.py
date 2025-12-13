import cv2
import numpy as np
import pyautogui
import time
import win32api
import win32con
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

    # ✅ [추가] Moonlight 호환성을 위한 '꾹' 클릭 헬퍼
    def _atomic_click(self, x: int, y: int):
        """이동 -> 누름 -> 0.15초 대기 -> 뗌"""
        try:
            pyautogui.moveTo(x, y)
            pyautogui.mouseDown()
            time.sleep(0.15)  # Moonlight가 신호를 놓치지 않도록 충분히 대기
            pyautogui.mouseUp()
            time.sleep(0.1)  # 동작 완료 대기
        except Exception as e:
            print(f"Atomic Click Error: {e}")

    def get_current_vd(self) -> VirtualDesktop:
        # (기존 코드 동일)
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

    def send_key_combination(self, ctrl=False, win=False, key_code=None):
        # (기존 코드 동일 - 키보드용이라 마우스 클릭엔 사용 안 함)
        try:
            if ctrl:
                win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
            if win:
                win32api.keybd_event(win32con.VK_LWIN, 0, 0, 0)
            if key_code:
                win32api.keybd_event(key_code, 0, 0, 0)

            time.sleep(0.1)

            if key_code:
                win32api.keybd_event(key_code, 0, win32con.KEYEVENTF_KEYUP, 0)
            if win:
                win32api.keybd_event(win32con.VK_LWIN, 0, win32con.KEYEVENTF_KEYUP, 0)
            if ctrl:
                win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)

        except Exception as e:
            print(f"키 입력 오류: {e}")

    def switch_to(self, target_vd: VirtualDesktop):
        print(f"DEBUG: switch_to called - target: {target_vd.name}")

        if target_vd == VirtualDesktop.OTHER:
            return

        current_vd = self.get_current_vd()
        if current_vd == target_vd:
            return

        print(f"DEBUG: Switching from {current_vd.name} to {target_vd.name}")

        # 1단계: 작업보기 버튼 클릭
        task_view_x = 351
        task_view_y = 1064

        # [수정] pyautogui.click -> self._atomic_click
        self._atomic_click(task_view_x, task_view_y)

        time.sleep(1.0)  # 작업보기 UI 로딩 대기

        # 2단계: 목표 VD 클릭
        vd_positions = {
            VirtualDesktop.VD1: (282, 63),
            VirtualDesktop.VD2: (463, 63)
        }

        target_pos = vd_positions.get(target_vd)
        if target_pos:
            # [수정] pyautogui.click -> self._atomic_click
            self._atomic_click(target_pos[0], target_pos[1])

            time.sleep(1.5)  # VD 전환 완료 대기
            print(f"DEBUG: VD switch completed to {target_vd.name}")