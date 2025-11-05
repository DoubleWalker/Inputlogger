import cv2
import numpy as np
import pyautogui
import time
import os

def compare_images(screen_img_obj, template_img_obj, threshold=0.8):
    """
    주어진 스크린샷 이미지 객체와 템플릿 이미지 객체를 비교합니다.
    :param screen_img_obj: pyautogui.screenshot() 등으로 얻은 Pillow 이미지 또는 NumPy 배열
    :param template_img_obj: cv2.imread()로 로드한 템플릿 이미지 (NumPy 배열)
    :param threshold: 유사도 임계값 (0.0 ~ 1.0)
    :return: 임계값 이상이면 True, 아니면 False
    """
    try:
        # ✅ 입력값 안전성 체크 추가
        if template_img_obj is None:
            return False
        if not hasattr(template_img_obj, 'shape'):
            return False

        screen_gray = cv2.cvtColor(np.array(screen_img_obj), cv2.COLOR_RGB2GRAY)
        if len(template_img_obj.shape) == 3:
            template_gray = cv2.cvtColor(template_img_obj, cv2.COLOR_BGR2GRAY)
        else:
            template_gray = template_img_obj

        result = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)
        return max_val > threshold
    except Exception as e:
        print(f"Error in compare_images: {e}")
        return False


def return_ui_location(template_path, region=None, threshold=0.8, screenshot_img=None):
    """
    화면 전체 또는 지정된 영역에서 템플릿 이미지를 찾아 중심 좌표 (x, y)를 반환합니다.
    :param template_path: 찾을 템플릿 이미지 파일 경로
    :param region: 검색할 화면 영역 (x, y, width, height), None이면 전체 화면
    :param threshold: 유사도 임계값
    :param screenshot_img: Orchestrator가 제공한 캡쳐 이미지 (None이면 새로 캡쳐)
    :return: 찾은 이미지의 중심 좌표 (x, y) 튜플, 못 찾으면 None
    """
    if not os.path.exists(template_path):
        print(f"Template file not found: {template_path}")
        return None

    # ✅ 엄격한 검증
    if screenshot_img is None:
        raise ValueError(f"screenshot_img must be provided by Orchestrator for {template_path}")

    try:
        template_img = cv2.imread(template_path, 0)
        if template_img is None:
            print(f"Failed to load template: {template_path}")
            return None
        template_h, template_w = template_img.shape[:2]

        screen_gray = cv2.cvtColor(np.array(screenshot_img), cv2.COLOR_RGB2GRAY)
        result = cv2.matchTemplate(screen_gray, template_img, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            center_x = max_loc[0] + template_w // 2
            center_y = max_loc[1] + template_h // 2

            if region:
                center_x += region[0]
                center_y += region[1]

            return (center_x, center_y)
        else:
            return None
    except Exception as e:
        print(f"Error in return_ui_location: {e}")
        return None

# 이름 변경된 함수를 호출하도록 수정
def is_image_present(template_path, region=None, threshold=0.8, screenshot_img=None):
    """
    화면 전체 또는 지정된 영역에서 템플릿 이미지가 존재하는지 확인합니다.
    :param template_path: 찾을 템플릿 이미지 파일 경로
    :param region: 검색할 화면 영역 (x, y, width, height), None이면 전체 화면
    :param threshold: 유사도 임계값 (0.0 ~ 1.0)
    :param screenshot_img: Orchestrator가 제공한 캡쳐 이미지 (None이면 새로 캡쳐)
    :return: 존재하면 True, 아니면 False
    """
    return return_ui_location(template_path, region, threshold, screenshot_img) is not None

# 이름 변경된 함수를 호출하도록 수정
def click_image(template_path, region=None, threshold=0.8, button='left', clicks=1, interval=0.1, screenshot_img=None):
    """
    화면 전체 또는 지정된 영역에서 템플릿 이미지를 찾아 클릭합니다.
    :param template_path: 찾을 템플릿 이미지 파일 경로
    :param region: 검색할 화면 영역 (x, y, width, height), None이면 전체 화면
    :param threshold: 유사도 임계값
    :param button: 'left', 'right', 'middle'
    :param clicks: 클릭 횟수
    :param interval: 클릭 간 간격 (초)
    :param screenshot_img: Orchestrator가 제공한 캡쳐 이미지 (None이면 새로 캡쳐)
    :return: 클릭 성공 시 True, 실패 시 False
    """
    """
    화면 전체 또는 지정된 영역에서 템플릿 이미지를 찾아 클릭합니다.
    :param screenshot_img: Orchestrator가 제공한 캡쳐 이미지 (None이면 새로 캡쳐)
    """
    location = return_ui_location(template_path, region, threshold, screenshot_img)
    if location:
        try:
            pyautogui.click(location[0], location[1], clicks=clicks, interval=interval, button=button)
            return True
        except Exception as e:
            print(f"Error during click at {location}: {e}")
            return False
    else:
        return False

def set_focus(screen_id: str, delay_after: float = 0.2) -> bool:
    """
    지정된 화면 ID의 중앙을 클릭하여 포커스를 설정합니다.

    Args:
        screen_id: 포커스를 설정할 화면 ID (예: 'S1', 'S2' 등)
        delay_after: 클릭 후 대기 시간 (초)

    Returns:
        성공 시 True, 실패 시 False
    """
    try:
        from Orchestrator.NightCrows.utils.screen_info import SCREEN_REGIONS

        if screen_id not in SCREEN_REGIONS:
            print(f"Error: Screen ID '{screen_id}' not found in SCREEN_REGIONS.")
            return False

        region = SCREEN_REGIONS[screen_id]
        center_x = region[0] + region[2] // 2
        center_y = region[1] + region[3] // 2

        pyautogui.click(center_x, center_y)
        if delay_after > 0:
            time.sleep(delay_after)

        print(f"Focus set on screen {screen_id} at ({center_x}, {center_y})")
        return True

    except Exception as e:
        print(f"Error setting focus on screen {screen_id}: {e}")
        return False