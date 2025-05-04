from dataclasses import dataclass
from enum import Enum
from typing import List
import cv2
import numpy as np
import pyautogui
import keyboard
import time
from .screen_info import SCREEN_REGIONS


class ScreenState(Enum):
    UNKNOWN = 0
    AWAKE = 1
    SLEEP = 2


@dataclass
class Screen:
    screen_id: str
    sleep_template: str
    state: ScreenState = ScreenState.UNKNOWN
    attempts: int = 0

    @property
    def region(self):
        return SCREEN_REGIONS[self.screen_id]


class ScreenWaker:
    def __init__(self, max_attempts: int = 5, confidence_threshold: float = 0.85):
        self.screens: List[Screen] = []
        self.max_attempts = max_attempts
        self.confidence_threshold = confidence_threshold

    def add_screen(self, screen_id: str, sleep_template: str):
        """화면 정보 추가"""
        screen = Screen(screen_id=screen_id, sleep_template=sleep_template)
        self.screens.append(screen)

    def is_sleeping(self, screen: Screen) -> bool:
        """화면이 슬립상태인지 확인"""
        try:
            screenshot = pyautogui.screenshot(region=screen.region)
            template = cv2.imread(screen.sleep_template)

            if template is None:
                print(f"Error: Could not load template image at {screen.sleep_template}")
                return False

            screen_gray = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

            result = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)

            return max_val > self.confidence_threshold

        except Exception as e:
            print(f"Error checking screen sleep state: {e}")
            return False

    def wake_screen(self, screen: Screen) -> bool:
        """슬립상태의 화면을 깨우기"""
        if screen.attempts >= self.max_attempts:
            return False

        try:
            screenshot = pyautogui.screenshot(region=screen.region)
            template = cv2.imread(screen.sleep_template)

            screen_gray = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

            result = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if max_val > self.confidence_threshold:
                template_h, template_w = template_gray.shape
                center_x = screen.region[0] + max_loc[0] + template_w // 2
                center_y = screen.region[1] + max_loc[1] + template_h // 2

                pyautogui.click(center_x, center_y)
                time.sleep(0.1)
                keyboard.press_and_release('esc')
                screen.attempts += 1
                return True

            return False

        except Exception as e:
            print(f"Error waking screen: {e}")
            return False

    def wake_all_screens(self) -> bool:
        """모든 화면 깨우기"""
        all_awake = False
        retry_count = 0
        max_retries = 3

        while not all_awake and retry_count < max_retries:
            all_awake = True
            for screen in self.screens:
                if self.is_sleeping(screen):
                    all_awake = False
                    self.wake_screen(screen)
                    time.sleep(0.5)

            retry_count += 1
            if not all_awake:
                time.sleep(1)

        return all_awake


if __name__ == "__main__":
    # 사용 예시
    waker = ScreenWaker()

    # S1 화면
    waker.add_screen(
        screen_id='S1',
        sleep_template=r"C:\Users\yjy16\template\NightCrows\S1.png"
    )

    # S2 화면
    waker.add_screen(
        screen_id='S2',
        sleep_template=r"C:\Users\yjy16\template\NightCrows\S2.png"
    )

    # S3 화면
    waker.add_screen(
        screen_id='S3',
        sleep_template=r"C:\Users\yjy16\template\NightCrows\S3.png"
    )

    # S4 화면
    waker.add_screen(
        screen_id='S4',
        sleep_template=r"C:\Users\yjy16\template\NightCrows\S4.png"
    )

    # S5 화면
    waker.add_screen(
        screen_id='S5',
        sleep_template=r"C:\Users\yjy16\template\NightCrows\S5.png"
    )

    # 모든 화면 깨우기 실행
    waker.wake_all_screens()