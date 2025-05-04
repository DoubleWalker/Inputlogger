from dataclasses import dataclass
import cv2
import numpy as np
import pyautogui
import keyboard
import time
from typing import List
from dataclasses import dataclass
from pymsgbox import confirm

from Orchestrator.Raven2.utils.screen_info import SCREEN_REGIONS, FIXED_UI_COORDS


@dataclass
class Screen:
    screen_id: str
    mail_icon: str  # 메일 아이콘 템플릿 경로
    collect_all: str  # 모두받기 버튼 템플릿 경로
    notice_tab: str
    envelope: str
    confirm: str

    @property
    def region(self):
        return SCREEN_REGIONS[self.screen_id]


class MailOpener:
    def __init__(self, confidence_threshold: float = 0.85):
        self.screens: List[Screen] = []
        self.threshold = confidence_threshold

    def add_screen(self, screen_id: str, mail_icon: str, collect_all: str, notice_tab: str, envelope: str, confirm: str):
        """화면 정보 추가"""
        self.screens.append(Screen(screen_id, mail_icon, collect_all, notice_tab, envelope, confirm))

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

    # opener.py (MO2 용, process_screen 수정)

    # Screen 데이터클래스 (MO2용으로 필요한 템플릿 경로 추가 가정)
    # 예: screen.notice_tab, screen.envelope, screen.collect_all, screen.confirm 등

    def process_screen(self, screen: Screen):  # Screen 타입은 MO2에 맞게 수정된 것으로 가정
        print(f"Processing screen: {screen.screen_id} for Raven2 Mail")

        # 1. 초기 진입 ========================================
        # 1-1. (필요시) 메인 메뉴 클릭
        if not self.click_fixed_coord(screen, 'main_menu_button'):
            print(f"Failed to click main menu on {screen.screen_id}. Aborting.")
            return
        time.sleep(1.0)

        # 1-2. 메일 아이콘 클릭
        if not self.find_and_click(screen, screen.mail_icon):  # screen 객체에 mail_icon 경로 필요
            print(f"Mail icon not found on {screen.screen_id}. Aborting.")
            return
        time.sleep(1.0)  # 메일함 로딩 대기

        # 1-3. "공지" 탭 클릭
        if not self.find_and_click(screen, screen.notice_tab):  # screen 객체에 notice_tab 경로 필요
            print(f"'Notice' tab not found on {screen.screen_id}. Aborting.")
            keyboard.press_and_release('esc')  # 일단 나가기
            return
        time.sleep(0.5)  # 탭 전환 대기
        print("Entered Mailbox and selected 'Notice' tab.")

        # 2. 반복 구간 ========================================
        mail_processed_count = 0
        max_attempts = 15  # 최대 시도 횟수 (값 조절)
        print("Starting envelope processing loop...")
        for attempt in range(max_attempts):
            print(f"Loop {attempt + 1}/{max_attempts}: Searching for envelope...")

            # 2-1. 편지 봉투 찾기
            if self.find_and_click(screen, screen.envelope):  # screen 객체에 envelope 경로 필요
                print("  Envelope found and clicked.")
                time.sleep(0.7)  # 메일 내용 로딩

                # 2-2. 모두 받기 찾기 및 클릭
                if self.find_and_click(screen, screen.collect_all):  # screen 객체에 collect_all 경로 필요
                    print("    Collect All button clicked.")
                    time.sleep(0.7)  # 확인 버튼 로딩

                    # 2-3. 확인 찾기 및 클릭
                    if self.find_and_click(screen, screen.confirm):  # screen 객체에 confirm 경로 필요
                        print("      Confirm button clicked.")
                        mail_processed_count += 1
                        print("        Waiting 0.7s and pressing ESC...")
                        time.sleep(0.8)
                        keyboard.press_and_release('esc')
                        # ESC 후 다음 검색까지 약간의 간격 주기 (선택 사항)
                        time.sleep(0.8)
                        # 다음 봉투 찾으러 루프 계속
                        continue  # 다음 for 루프 반복 실행
                    else:
                        print(
                            f"      Error: Confirm button not found after Collect All on {screen.screen_id}. Stopping.")
                        break  # 확인 못찾으면 루프 중단
                else:
                    print(
                        f"    Error: Collect All button not found after clicking envelope on {screen.screen_id}. Stopping.")
                    # 메일 종류에 따라 모두 받기가 없을 수도 있음. 이 경우 다른 처리가 필요할 수 있지만, 일단 루프 중단.
                    break  # 모두 받기 못찾으면 루프 중단
            else:
                # 더 이상 편지 봉투가 없으면 루프 종료
                print(f"  No more envelopes found on attempt {attempt + 1}.")
                break  # 봉투 못찾으면 루프 중단
        else:  # for 루프가 break 없이 정상 종료된 경우 (max_attempts 도달 시)
            print(f"Warning: Reached max attempts ({max_attempts}). Ending loop.")

        # 3. 최종 나가기 =======================================
        print(
            f"Finishing mail processing for {screen.screen_id}. Processed {mail_processed_count} items. Exiting...")
        # time.sleep(0.7) # ESC 전에 0.7초 대기? -> 사용자 설명에는 없었음. 필요시 추가.
        keyboard.press_and_release('esc')  # 최종적으로 ESC 한 번
        print("Exited mail screen.")

        # ... run 메소드는 기존과 동일하게 사용 가능 ...
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
        mail_icon=r"C:\Users\yjy16\template\RAVEN2\MO\mail_s1.png",
        collect_all=r"C:\Users\yjy16\template\RAVEN2\MO\open_s1.png",
        notice_tab=r"C:\Users\yjy16\template\RAVEN2\MO\notice_s1.png",
        envelope=r"C:\Users\yjy16\template\RAVEN2\MO\env_s1.png",
        confirm=r"C:\Users\yjy16\template\RAVEN2\MO\cf_s1.png"
    )

    # S2 화면
    mo.add_screen(
        screen_id='S2',
        mail_icon=r"C:\Users\yjy16\template\RAVEN2\MO\mail_s2.png",
        collect_all=r"C:\Users\yjy16\template\RAVEN2\MO\open_s2.png",
        notice_tab=r"C:\Users\yjy16\template\RAVEN2\MO\notice_s2.png",
        envelope=r"C:\Users\yjy16\template\RAVEN2\MO\env_s2.png",
        confirm=r"C:\Users\yjy16\template\RAVEN2\MO\cf_s2.png"
    )

    # S3 화면
    mo.add_screen(
        screen_id='S3',
        mail_icon=r"C:\Users\yjy16\template\RAVEN2\MO\mail_s3.png",
        collect_all=r"C:\Users\yjy16\template\RAVEN2\MO\open_s3.png",
        notice_tab=r"C:\Users\yjy16\template\RAVEN2\MO\notice_s3.png",
        envelope=r"C:\Users\yjy16\template\RAVEN2\MO\env_s3.png",
        confirm=r"C:\Users\yjy16\template\RAVEN2\MO\cf_s3.png"
    )

    # S4 화면
    mo.add_screen(
        screen_id='S4',
        mail_icon=r"C:\Users\yjy16\template\RAVEN2\MO\mail_s4.png",
        collect_all=r"C:\Users\yjy16\template\RAVEN2\MO\open_s4.png",
        notice_tab=r"C:\Users\yjy16\template\RAVEN2\MO\notice_s4.png",
        envelope=r"C:\Users\yjy16\template\RAVEN2\MO\env_s4.png",
        confirm=r"C:\Users\yjy16\template\RAVEN2\MO\cf_s4.png"
    )

    # S5 화면
    mo.add_screen(
        screen_id='S5',
        mail_icon=r"C:\Users\yjy16\template\RAVEN2\MO\mail_s5.png",
        collect_all=r"C:\Users\yjy16\template\RAVEN2\MO\open_s5.png",
        notice_tab=r"C:\Users\yjy16\template\RAVEN2\MO\notice_s5.png",
        envelope=r"C:\Users\yjy16\template\RAVEN2\MO\env_s5.png",
        confirm=r"C:\Users\yjy16\template\RAVEN2\MO\cf_s5.png"
    )

    mo.run()