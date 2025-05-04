from dataclasses import dataclass
import cv2
import numpy as np
import pyautogui
import keyboard
import time
from typing import List
from dataclasses import dataclass
from Orchestrator.NightCrows.utils.screen_info import SCREEN_REGIONS, FIXED_UI_COORDS


@dataclass
class Screen:
    screen_id: str
    mail_icon: str  # 메일 아이콘 템플릿 경로
    collect_all: str  # 모두받기 버튼 템플릿 경로

    @property
    def region(self):
        return SCREEN_REGIONS[self.screen_id]


class MailOpener:
    def __init__(self, confidence_threshold: float = 0.85):
        self.screens: List[Screen] = []
        self.threshold = confidence_threshold

    def add_screen(self, screen_id: str, mail_icon: str, collect_all: str):
        """화면 정보 추가"""
        self.screens.append(Screen(screen_id, mail_icon, collect_all))

    def find_and_click(self, screen: Screen, template_path: str) -> bool:
        """템플릿 매칭으로 요소를 찾아 클릭"""
        try:
            screenshot = pyautogui.screenshot(region=screen.region)
            template = cv2.imread(template_path)

            if template is None:
                return False

            screen_gray = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

            result = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if max_val > self.threshold:
                template_h, template_w = template_gray.shape
                center_x = screen.region[0] + max_loc[0] + template_w // 2
                center_y = screen.region[1] + max_loc[1] + template_h // 2

                pyautogui.click(
                    center_x + np.random.randint(-2, 3),
                    center_y + np.random.randint(-2, 3)
                )
                return True

            return False

        except Exception as e:
            print(f"Error in find_and_click: {e}")
            return False

    def click_fixed_coord(self, screen: Screen, coord_key: str) -> bool:
        """screen_info에 정의된 고정 좌표를 클릭"""
        try:
            # 화면 영역 정보 가져오기
            screen_region = screen.region  # 예: (0, 0, 600, 900)
            screen_x, screen_y = screen_region[0], screen_region[1]

            # 해당 화면의 고정 UI 좌표 정보 가져오기
            if screen.screen_id not in FIXED_UI_COORDS or coord_key not in FIXED_UI_COORDS[screen.screen_id]:
                print(
                    f"Error: Fixed coordinate '{coord_key}' not defined for screen '{screen.screen_id}' in screen_info.py")
                return False

            relative_coords = FIXED_UI_COORDS[screen.screen_id][coord_key]  # 예: (550, 50)
            relative_x, relative_y = relative_coords

            # 절대 좌표 계산 (모니터 기준)
            absolute_x = screen_x + relative_x
            absolute_y = screen_y + relative_y

            # 계산된 절대 좌표 클릭 (약간의 랜덤 오프셋 추가 가능)
            click_x = absolute_x + np.random.randint(-1, 2)
            click_y = absolute_y + np.random.randint(-1, 2)
            pyautogui.click(click_x, click_y)
            print(f"Clicked fixed coord '{coord_key}' for screen {screen.screen_id} at ({click_x}, {click_y})")
            return True

        except Exception as e:
            print(f"Error in click_fixed_coord: {e}")
            return False

    def process_screen(self, screen: Screen):
        """한 화면의 메일 수집 처리"""
        print(f"Processing screen: {screen.screen_id}")

        # 0. (추가됨) 메인 메뉴(三) 버튼 클릭
        print("Clicking main menu button...")
        if self.click_fixed_coord(screen, 'main_menu_button'):
            time.sleep(1.0)  # 메뉴가 열릴 때까지 잠시 대기 (시간 조절 필요)

            # 1. 메일 아이콘 클릭
            print("Finding and clicking mail icon...")
            if self.find_and_click(screen, screen.mail_icon):
                time.sleep(0.5)

                # 2. 모두받기 버튼 클릭
                print("Finding and clicking collect all button...")
                if self.find_and_click(screen, screen.collect_all):
                    time.sleep(0.5)

                    # 3. ESC 두 번 입력
                    print("Closing mail window with ESC...")
                    keyboard.press_and_release('esc')
                    time.sleep(0.3)
                    keyboard.press_and_release('esc')
                    print(f"Screen {screen.screen_id} processed.")
                else:
                    print(f"Collect all button not found on screen {screen.screen_id}. Closing menu.")
                    # 모두 받기 실패 시에도 메뉴는 닫도록 ESC 추가
                    keyboard.press_and_release('esc')
                    time.sleep(0.3)
                    keyboard.press_and_release('esc')

    def run(self):
        """모든 화면 처리"""
        for screen in self.screens:
            self.process_screen(screen)
            time.sleep(0.5)  # 화면 간 딜레이


if __name__ == "__main__":
    mo = MailOpener()

    # S1 화면
    mo.add_screen(
        screen_id='S1',
        mail_icon=r"C:\Users\yjy16\template\NightCrows\MO\mail_s1.png",
        collect_all=r"C:\Users\yjy16\template\NightCrows\MO\open_s1.png"
    )

    # S2 화면
    mo.add_screen(
        screen_id='S2',
        mail_icon=r"C:\Users\yjy16\template\NightCrows\MO\mail_s2.png",
        collect_all=r"C:\Users\yjy16\template\NightCrows\MO\open_s2.png"
    )

    # S3 화면
    mo.add_screen(
        screen_id='S3',
        mail_icon=r"C:\Users\yjy16\template\NightCrows\MO\mail_s3.png",
        collect_all=r"C:\Users\yjy16\template\NightCrows\MO\open_s3.png"
    )

    # S4 화면
    mo.add_screen(
        screen_id='S4',
        mail_icon=r"C:\Users\yjy16\template\NightCrows\MO\mail_s4.png",
        collect_all=r"C:\Users\yjy16\template\NightCrows\MO\open_s4.png"
    )

    # S5 화면
    mo.add_screen(
        screen_id='S5',
        mail_icon=r"C:\Users\yjy16\template\NightCrows\MO\mail_s5.png",
        collect_all=r"C:\Users\yjy16\template\NightCrows\MO\open_s5.png"
    )

    mo.run()