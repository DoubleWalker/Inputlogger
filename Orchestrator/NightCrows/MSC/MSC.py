from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Optional
import pyautogui
import keyboard
import numpy as np
import time
import cv2
import random
from threading import Thread
from queue import Queue


class ScreenState(Enum):
    UNKNOWN = 0
    AWAKE = 1
    SLEEP = 2


@dataclass
class ScreenInfo:
    template_path: str
    additional_templates: List[str]
    map_templates: List[str]
    completion_ui_template: str
    party_ui_templates: List[str]
    region: Tuple[int, int, int, int]
    scale: float = 1.0
    state: ScreenState = ScreenState.UNKNOWN
    attempts: int = 0


class MultiScreenChecker:
    def __init__(self, max_attempts: int = 5, confidence_threshold: float = 0.85):
        self.screens: List[ScreenInfo] = []
        self.max_attempts = max_attempts
        self.running = True
        self.confidence_threshold = confidence_threshold
        self.all_awake_message_printed = False  # 추가된 변수
        self.last_interaction_time = 0    # Add cooldown tracking
        self.interaction_cooldown = 0.5  # seconds between interaction sequences
        self.screen_completion_status = {}
        self.screen_ready = {}

    def add_screen(self, template_path: str, region: Tuple[int, int, int, int], additional_templates: List[str], map_templates: List[str],completion_ui_template: str,party_ui_templates: List[str],scale: float=1.0):
        screen_info = ScreenInfo(template_path=template_path, region=region, additional_templates=additional_templates,map_templates=map_templates,completion_ui_template=completion_ui_template,party_ui_templates=party_ui_templates, scale = scale)
        self.screens.append(screen_info)
        self.screen_completion_status[id(screen_info)] = False  # 새로운 화면 추가시 상태 초기화

    def return_ui_location(self, screen_info: ScreenInfo, template_path: str, threshold=None) -> Optional[Tuple[int, int]]:
        """Find the UI element location based on the given template path."""
        if threshold is None:
           threshold = self.confidence_threshold
        try:
            screen = pyautogui.screenshot(region=screen_info.region)
            template = cv2.imread(template_path)

            if template is None:
                print(f"Error: Could not load template image at {template_path}")
                return None

            screen_gray = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2GRAY)
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

            result = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            print(f"Template matching confidence: {max_val}")  # Add this debug print

            # Only return location if confidence threshold is met
            if max_val > threshold:
                template_height, template_width = template_gray.shape
                center_x = max_loc[0] + template_width // 2
                center_y = max_loc[1] + template_height // 2

                random_offset_x = random.randint(-3, 3)
                random_offset_y = random.randint(-3, 3)

                final_x = screen_info.region[0] + center_x + random_offset_x
                final_y = screen_info.region[1] + center_y + random_offset_y

                return (final_x, final_y)
            return None

        except Exception as e:
            print(f"Error in return_ui_location: {e}")
            return None

    def additional_ui_interaction(self, screen_info: ScreenInfo):
        try:
            # 이미 완료된 화면은 스킵
            if self.screen_completion_status.get(id(screen_info), False):
                return

            for i, template_path in enumerate(screen_info.additional_templates):
                if not self.running:
                    return

                time.sleep(0.3)
                click_pos = self.return_ui_location(screen_info, template_path=template_path)
                if click_pos:
                    time.sleep(0.3)
                    x, y = click_pos
                    pyautogui.click(x, y)
                    time.sleep(0.2)
                    print(f"Clicked at {click_pos} with template {template_path}")

                    if i == len(screen_info.additional_templates) - 1:
                        self.screen_completion_status[id(screen_info)] = True
                        print(f"마지막 템플릿 클릭 완료 - Screen {screen_info.region}")
                        return

                    time.sleep(0.1)

                time.sleep(0.1)

        except Exception as e:
            print(f"Error in additional_ui_interaction: {e}")

    def check_screen(self, screen_info: ScreenInfo) -> bool:
        try:
            screen = pyautogui.screenshot(region=screen_info.region)
            template = cv2.imread(screen_info.template_path)

            if template is None:
                print(f"Error: Could not load template image at {screen_info.template_path}")
                return False

            is_sleep = self.compare_images(screen, template)

            screen_info.state = ScreenState.SLEEP if is_sleep else ScreenState.AWAKE
            return is_sleep

        except Exception as e:
            print(f"Error in check_screen: {e}")
            return False

    def handle_screen(self, screen_info: ScreenInfo):
        if screen_info.state == ScreenState.SLEEP and screen_info.attempts < self.max_attempts:
            click_pos = self.return_ui_location(screen_info, screen_info.template_path)
            if click_pos:
                x, y = click_pos
                pyautogui.click(x, y)
                time.sleep(0.1)
                keyboard.press_and_release('esc')
                screen_info.attempts += 1
                time.sleep(0.1)

                if not self.check_screen(screen_info):
                    screen_info.state = ScreenState.AWAKE
                    screen_info.attempts = 0

    def compare_images(self, screen_img, template_img, threshold=None):
        if threshold is None:
            threshold = self.confidence_threshold

        screen_gray = cv2.cvtColor(np.array(screen_img), cv2.COLOR_RGB2GRAY)
        template_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)
        result = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)
        print(f"Compare images max_val: {max_val}")  # 이렇게 디버그 출력 추가
        return max_val > threshold

    def debug_template_matching(self, screen_info):
        for template_path in screen_info.additional_templates:
            print(f"Testing template: {template_path}")
            location = self.return_ui_location(screen_info, template_path)
            if location:
                print(f"Template matched at location: {location}")
            else:
                print("No match found or template load error.")

    def perform_click_sequence(self, random_range: int = 3):
        """시작 위치를 포함한 모든 클릭 위치에서 ±random_range 픽셀 내에서 랜덤하게 클릭"""
        positions = [
            (600, 103),  # 시작 위치
            (1430, 109),  # 두 번째 위치
            (568, 450),  # 세 번째 위치
            (600, 797),  # 네 번째 위치
            (1667, 549) #다섯 번째 위치
        ]

        for x, y in positions:
            final_x = x + random.randint(-random_range, random_range)
            final_y = y + random.randint(-random_range, random_range)
            pyautogui.click(final_x, final_y)
            print(f"Clicked at ({final_x}, {final_y})")
            time.sleep(0.2)  # 클릭 간 약간의 딜레이
            keyboard.press_and_release('esc')  # esc키 입력
            time.sleep(0.2)
            pyautogui.click(final_x, final_y)
            time.sleep(0.2)
            keyboard.press_and_release('y')
            time.sleep(0.1)
            keyboard.press_and_release('y')

    def situate_at_the_scene(self):


        #두 번째 클릭 - 상대좌표 이동
        screen_moverel = {
            (0, 0, 766, 346): (6, -32),  # S1
            (770, 0, 840, 378): (6, -32),  # S2
            (0, 350, 767, 343): (6, -33),  # S3
            (0, 697, 767, 343): (6, -33),  # S4
            (770, 394, 1140, 642): (6, -36)  # S5
        }

        map_confidence_threshold = 0.7
        # 지도 인터페이스 활성화는 각 화면마다 수행

        current_map = 2  # 또는 1부터 시작하도록 수정
        while current_map >= 1 and current_map <= 5 and self.running:

            # 매칭 및 클릭 수행
            for screen in self.screens:
                region_center_x = screen.region[0] + screen.region[2] // 2
                region_center_y = screen.region[1] + screen.region[3] // 2
                pyautogui.click(region_center_x, region_center_y)
                time.sleep(0.2)
                keyboard.press_and_release('m')
                time.sleep(0.2)
                print(f"Map interface activated for screen: {screen.region}")

            time.sleep(4.0)

            for screen in self.screens:

                print(f"\nStarting process for screen: {screen.region}")
                time.sleep(0.5)
                current_map_templates = [template for template in screen.map_templates
                                         if f"map{current_map}_" in template]

                for template_path in current_map_templates:
                    print(f"Trying template: {template_path}")
                    click_pos = self.return_ui_location(screen, template_path, threshold=map_confidence_threshold)
                    print(f"Return value from return_ui_location: {click_pos}")
                    if click_pos:
                        print(f"Match found! Confidence above threshold")
                        print(f"About to click at: {click_pos}")

                        try:
                            pyautogui.click(click_pos[0], click_pos[1])
                            print("First click completed")
                            time.sleep(0.5)
                            moverel_x, moverel_y = screen_moverel[screen.region]
                            pyautogui.moveRel(moverel_x, moverel_y)
                            print("Moved relative position")
                            time.sleep(0.3)
                            pyautogui.click()
                            print("Second click completed")
                            keyboard.press_and_release('m')

                        except Exception as e:
                            print(f"Error during mouse operations: {e}")
                        break

            time.sleep(24)
            for screen in self.screens:
                region_center_x = screen.region[0] + screen.region[2] // 2
                region_center_y = screen.region[1] + screen.region[3] // 2

                # 화면 활성화를 위한 클릭
                pyautogui.click(region_center_x, region_center_y)
                time.sleep(0.2)  # 약간의 딜레이
                keyboard.press_and_release('q')
                time.sleep(0.3)

            time.sleep(65)

            # completion UI 처리
            attempts_per_screen = 16
            completion_found = {id(screen): False for screen in self.screens}

            for attempt in range(attempts_per_screen):
                # 모든 스크린을 한 번씩 체크
                for screen in self.screens:
                    if not completion_found[id(screen)]:  # 아직 찾지 못한 스크린만 체크
                        completion_ui_pos = self.return_ui_location(
                            screen,
                            template_path=screen.completion_ui_template
                        )
                        if completion_ui_pos:
                            print(f"Screen {screen.region}: Completion UI found and clicked")
                            pyautogui.click(completion_ui_pos[0], completion_ui_pos[1])
                            completion_found[id(screen)] = True

                # 모든 스크린에서 찾았는지 체크
                if all(completion_found.values()):
                    break

                time.sleep(11)  # 다음 시도 전 대기

            all_completed = all(completion_found.values())

            if all_completed:
                current_map += 1  # map5가 완료되면 current_map이 6이 되어 while 조건에서 false가 됨
                if current_map > 5:
                    print("Map 5 completed. Exiting map sequence.")
                    break  # 필요없음 - 이미 다음 while 조건 검사에서 종료될 것이기 때문

                time.sleep(0.5)
                print(f"Moving to map {current_map}...")

                # perform_click_sequence의 positions 동작 수행
                positions = [
                    (600, 103),  # 시작 위치
                    (1430, 109),  # 두 번째 위치
                    (568, 450),  # 세 번째 위치
                    (600, 797),  # 네 번째 위치
                    (1667, 549)
                ]

                for x, y in positions:
                    final_x = x + random.randint(-3, 3)
                    final_y = y + random.randint(-3, 3)
                    pyautogui.click(final_x, final_y)
                    print(f"Clicked at ({final_x}, {final_y})")
                    time.sleep(0.2)
                    keyboard.press_and_release('y')
                    time.sleep(0.2)
                    keyboard.press_and_release('y')

                print(f"Positions clicked. Current map: {current_map}, self.running: {self.running}")
                time.sleep(15)

            else:
                print(f"Completion UI not confirmed for all screens on map {current_map}")

    def check_screen_thread(self, screen_info, result_queue):
        result = self.check_ui_state_with_samples(screen_info)
        result_queue.put((screen_info, result))

    def repetitive_party_check(self):
        for screen_info in self.screens:
            self.screen_ready[id(screen_info)] = screen_info.region == (0, 0, 766, 346)

        pyautogui.click(600 + random.randint(-3, 3), 103 + random.randint(-3, 3))
        time.sleep(0.2)
        keyboard.press_and_release('y')

        positions = {
            (770, 0, 840, 378): (1430, 109),
            (0, 350, 767, 343): (568, 450),
            (0, 697, 767, 343): (600, 797),
            (770, 394, 1140, 642): (1667, 549)
        }

        while self.running:
            if keyboard.is_pressed('alt+q'):
                return

            threads = []
            result_queue = Queue()
            not_ready_screens = []

            for screen_info in self.screens:
                if screen_info.region != (0, 0, 766, 346) and not self.screen_ready.get(id(screen_info)):
                    thread = Thread(target=self.check_screen_thread, args=(screen_info, result_queue))
                    thread.start()
                    threads.append(thread)

            for thread in threads:
                thread.join()

            while not result_queue.empty():
                screen, is_ready = result_queue.get()
                if not is_ready:
                    not_ready_screens.append(screen)
                else:
                    self.screen_ready[id(screen)] = True

            if not_ready_screens:
                for screen in not_ready_screens:
                    x, y = positions[screen.region]
                    pyautogui.click(x + random.randint(-3, 3), y + random.randint(-3, 3))
                    time.sleep(0.1)
                    keyboard.press_and_release('y')
            time.sleep(2.0)

            if all(self.screen_ready.values()):
                time.sleep(30)
                attempts_per_screen = 16
                completion_found = {id(screen): False for screen in self.screens}

                for attempt in range(attempts_per_screen):
                    if not self.running or keyboard.is_pressed('alt+q'):
                        return

                    for screen in self.screens:
                        if not completion_found[id(screen)]:
                            completion_ui_pos = self.return_ui_location(
                                screen,
                                template_path=screen.completion_ui_template
                            )
                            if completion_ui_pos:
                                print(f"Screen {screen.region}: Completion UI found and clicked")
                                pyautogui.click(completion_ui_pos[0], completion_ui_pos[1])
                                completion_found[id(screen)] = True

                    if all(completion_found.values()):
                        positions_list = [(600, 103), (1430, 109), (568, 450), (600, 797), (1667, 549)]
                        for x, y in positions_list:
                            final_x = x + random.randint(-3, 3)
                            final_y = y + random.randint(-3, 3)
                            pyautogui.click(final_x, final_y)
                            time.sleep(0.2)
                            keyboard.press_and_release('y')
                            time.sleep(0.2)
                            keyboard.press_and_release('y')

                        time.sleep(10)
                        for screen_info in self.screens:
                            if screen_info.region != (0, 0, 766, 346):
                                self.screen_ready[id(screen_info)] = False
                        break

                    time.sleep(11)

    def check_ui_state_with_samples(self, screen_info, samples=7, threshold=0.15, sample_interval=0.5):
        if len(screen_info.party_ui_templates) == 0:
            return False

        min_vals = []  # max_vals 대신 min_vals 사용
        template = cv2.imread(screen_info.party_ui_templates[0])
        if template is None:
            return False

        for i in range(samples):
            screen_img = pyautogui.screenshot(region=screen_info.region)
            match_result = cv2.matchTemplate(
                cv2.cvtColor(np.array(screen_img), cv2.COLOR_RGB2GRAY),
                cv2.cvtColor(template, cv2.COLOR_BGR2GRAY),
                cv2.TM_SQDIFF_NORMED
            )
            min_val, _, _, _ = cv2.minMaxLoc(match_result)
            min_vals.append(min_val)
            print(f"Screen {screen_info.region}: Sample {i + 1} match = {min_val:.4f}")

            if min_val < threshold:  # threshold보다 작으면 매칭 성공
                print(f"Screen {screen_info.region}: Match found below threshold")
                return True

            time.sleep(sample_interval)

        print(f"Screen {screen_info.region}: Best match = {min(min_vals):.4f}")
        return False


    def run(self):
        countdown_time = 7
        for i in range(countdown_time, 0, -1):
            print(f"Starting in {i} seconds...")
            time.sleep(1)

        print("Monitoring started... Press 'p' to stop")

        try:
            while self.running:
                if keyboard.is_pressed('p'):
                    print("\nStop key pressed. Shutting down...")
                    self.running = False
                    break

                all_awake = True

                # 1단계: 화면 체크 및 깨우기
                for screen in self.screens:
                    if not self.running:
                        break

                    if self.check_screen(screen):
                        self.handle_screen(screen)
                        print(f"Screen at region {screen.region} is sleeping. Attempting to wake...")
                        all_awake = False
                    else:
                        print(f"Screen at region {screen.region} is awake.")

                # 2단계: UI 상호작용
                if all_awake and self.running:
                    if not self.all_awake_message_printed:
                        print("All screens are awake. Proceeding with additional UI interactions.")
                        self.all_awake_message_printed = True

                    # UI 상호작용 실행
                    for screen in self.screens:
                        if not self.running:
                            break
                        self.debug_template_matching(screen)
                        self.additional_ui_interaction(screen)

                    # 3단계: 완료 체크 및 다음 작업
                    all_completed = all(self.screen_completion_status.get(id(screen), False)
                                        for screen in self.screens)

                    if all_completed:
                        print("모든 화면의 작업이 완료되었습니다.")
                        self.perform_click_sequence()
                        time.sleep(12)
                        print("\nStarting map sequence...")
                        self.situate_at_the_scene()  # 모든 screen을 한번에 전달

                        time.sleep(12)
                        print("\nStarting repetitive party check...")
                        self.repetitive_party_check()
                        self.running = False

                    time.sleep(1)  # Delay between complete interaction cycles

                else:
                    self.all_awake_message_printed = False
                    print("Not all screens are awake. Continuing to check...")
                    time.sleep(1)

        except KeyboardInterrupt:
            print("\nKeyboard interrupt detected. Exiting program...")
        finally:
            print("Monitoring stopped.")

if __name__ == "__main__":
    checker = MultiScreenChecker(max_attempts=5)

    checker.add_screen(

        template_path=r"C:\Users\yjy16\template\NightCrows\mon_s1.png",
        region=(0, 0, 766, 346),
        scale = 1.0,
        additional_templates=[
            r"C:\Users\yjy16\template\NightCrows\msdqm\menu_741_11.png",
            r"C:\Users\yjy16\template\NightCrows\msdqm\Q_622_87.png",
            r"C:\Users\yjy16\template\NightCrows\msdqm\1_280_40.png",
            r"C:\Users\yjy16\template\NightCrows\msdqm\a_8_314.png"
        ],
        map_templates=[
            r"C:\Users\yjy16\template\NightCrows\map\map1_228_30.png",
            r"C:\Users\yjy16\template\NightCrows\map\map2_228_30.png",
            r"C:\Users\yjy16\template\NightCrows\map\map3_228_30.png",
            r"C:\Users\yjy16\template\NightCrows\map\map4_228_30.png",
            r"C:\Users\yjy16\template\NightCrows\map\map5_228_30.png"

        ],
        completion_ui_template= r"C:\Users\yjy16\template\NightCrows\map\c_660_395.png",

        party_ui_templates=[]

    )

    checker.add_screen(
        template_path=r"C:\Users\yjy16\template\NightCrows\mon_s2.png",
        region=(770, 0, 840, 378),
        scale=1.1,
        additional_templates=[
            r"C:\Users\yjy16\template\NightCrows\msdqm\menu_1580_12.png",
            r"C:\Users\yjy16\template\NightCrows\msdqm\Q_1449_93.png",
            r"C:\Users\yjy16\template\NightCrows\msdqm\1_1086_43.png",
            r"C:\Users\yjy16\template\NightCrows\msdqm\a_780_344.png"
        ],
        map_templates=[
            r"C:\Users\yjy16\template\NightCrows\map\map1_1040_48.png",
            r"C:\Users\yjy16\template\NightCrows\map\map2_1040_48.png",
            r"C:\Users\yjy16\template\NightCrows\map\map3_1040_48.png",
            r"C:\Users\yjy16\template\NightCrows\map\map4_1040_48.png",
            r"C:\Users\yjy16\template\NightCrows\map\map5_1040_48.png"
        ],
        completion_ui_template= r"C:\Users\yjy16\template\NightCrows\map\c_1534_50.png",
        party_ui_templates=[
            r"C:\Users\yjy16\template\NightCrows\party\pui_s2.png"
        ]
    )

    checker.add_screen(
        template_path=r"C:\Users\yjy16\template\NightCrows\mon_s3.png",
        region=(0, 350, 767, 343),
        scale=1.0,
        additional_templates=[
            r"C:\Users\yjy16\template\NightCrows\msdqm\menu_708_359.png",
            r"C:\Users\yjy16\template\NightCrows\msdqm\Q_591_435.png",
            r"C:\Users\yjy16\template\NightCrows\msdqm\1_310_389.png",
            r"C:\Users\yjy16\template\NightCrows\msdqm\a_28_659.png"
        ],
        map_templates=[
            r"C:\Users\yjy16\template\NightCrows\map\map1_251_384.png",
            r"C:\Users\yjy16\template\NightCrows\map\map2_251_384.png",
            r"C:\Users\yjy16\template\NightCrows\map\map3_251_384.png",
            r"C:\Users\yjy16\template\NightCrows\map\map4_251_384.png",
            r"C:\Users\yjy16\template\NightCrows\map\map5_251_384.png"
        ],
        completion_ui_template = r"C:\Users\yjy16\template\NightCrows\map\c_700_45.png",
        party_ui_templates=[
            r"C:\Users\yjy16\template\NightCrows\party\pui_s3.png"
        ]

    )

    checker.add_screen(
        template_path=r"C:\Users\yjy16\template\NightCrows\mon_s4.png",
        region=(0, 697, 767, 343),
        scale=0.9,
        additional_templates=[
            r"C:\Users\yjy16\template\NightCrows\msdqm\menu_740_703.png",
            r"C:\Users\yjy16\template\NightCrows\msdqm\Q_622_781.png",
            r"C:\Users\yjy16\template\NightCrows\msdqm\1_280_732.png",
            r"C:\Users\yjy16\template\NightCrows\msdqm\a_7_1007.png"
        ],
        map_templates=[
            r"C:\Users\yjy16\template\NightCrows\map\map1_245_722.png",
            r"C:\Users\yjy16\template\NightCrows\map\map2_245_722.png",
            r"C:\Users\yjy16\template\NightCrows\map\map3_245_722.png",
            r"C:\Users\yjy16\template\NightCrows\map\map4_245_722.png",
            r"C:\Users\yjy16\template\NightCrows\map\map5_245_722.png"
        ],
        completion_ui_template= r"C:\Users\yjy16\template\NightCrows\map\c_700_740.png",
        party_ui_templates=[
            r"C:\Users\yjy16\template\NightCrows\party\pui_s4.png"
        ]
    )

    checker.add_screen(
        template_path=r"C:\Users\yjy16\template\NightCrows\mon_s5.png",
        region=(770, 394, 1140, 642),
        scale=1.5,
        additional_templates=[
            r"C:\Users\yjy16\template\NightCrows\msdqm\menu_1872_411.png",
            r"C:\Users\yjy16\template\NightCrows\msdqm\Q_1702_423.png",
            r"C:\Users\yjy16\template\NightCrows\msdqm\1_1196_452.png",
            r"C:\Users\yjy16\template\NightCrows\msdqm\a_777_992.png"
        ],
        map_templates=[
            r"C:\Users\yjy16\template\NightCrows\map\map1_1095_477.png",
            r"C:\Users\yjy16\template\NightCrows\map\map2_1095_477.png",
            r"C:\Users\yjy16\template\NightCrows\map\map3_1095_477.png",
            r"C:\Users\yjy16\template\NightCrows\map\map4_1095_477.png",
            r"C:\Users\yjy16\template\NightCrows\map\map5_1095_477.png"
        ],
        completion_ui_template=r"C:\Users\yjy16\template\NightCrows\map\c_1807_464.png",
        party_ui_templates=[
            r"C:\Users\yjy16\template\NightCrows\party\s5.png"
        ]
    )

    # Add other screens similarly
    checker.run()
