import cv2
import numpy as np
import pyautogui
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
def return_ui_location(template_path, region=None, threshold=0.8):
    """
    화면 전체 또는 지정된 영역에서 템플릿 이미지를 찾아 중심 좌표 (x, y)를 반환합니다.
    :param template_path: 찾을 템플릿 이미지 파일 경로
    :param region: 검색할 화면 영역 (x, y, width, height), None이면 전체 화면
    :param threshold: 유사도 임계값
    :return: 찾은 이미지의 중심 좌표 (x, y) 튜플, 못 찾으면 None
    """
    if not os.path.exists(template_path):
        print(f"Template file not found: {template_path}")
        return None

    try:
        template_img = cv2.imread(template_path, 0) # Grayscale로 로드
        if template_img is None:
            print(f"Failed to load template: {template_path}")
            return None
        template_h, template_w = template_img.shape[:2]

        # screenshot_img = pyautogui.screenshot(region=region)
        # region이 None일 때 pyautogui가 전체 화면을 제대로 처리하도록 명시적으로 None 전달
        screenshot_img = pyautogui.screenshot(region=region if region else None)

        screen_gray = cv2.cvtColor(np.array(screenshot_img), cv2.COLOR_RGB2GRAY)

        result = cv2.matchTemplate(screen_gray, template_img, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            center_x = max_loc[0] + template_w // 2
            center_y = max_loc[1] + template_h // 2

            # region이 지정되었으면 절대 좌표로 변환
            if region:
                center_x += region[0]
                center_y += region[1]
            # (x, y) 좌표 튜플 반환
            return (center_x, center_y)
        else:
            return None
    except Exception as e:
        print(f"Error in return_ui_location: {e}")
        return None

# 이름 변경된 함수를 호출하도록 수정
def is_image_present(template_path, region=None, threshold=0.8):
    """
    화면 전체 또는 지정된 영역에서 템플릿 이미지가 존재하는지 확인합니다.
    :return: 존재하면 True, 아니면 False
    """
    # return_ui_location 호출 결과가 None이 아니면 True
    return return_ui_location(template_path, region, threshold) is not None

# 이름 변경된 함수를 호출하도록 수정
def click_image(template_path, region=None, threshold=0.8, button='left', clicks=1, interval=0.1):
    """
    화면 전체 또는 지정된 영역에서 템플릿 이미지를 찾아 클릭합니다.
    :param button: 'left', 'right', 'middle'
    :param clicks: 클릭 횟수
    :param interval: 클릭 간 간격 (초)
    :return: 클릭 성공 시 True, 실패 시 False
    """
    # return_ui_location 호출
    location = return_ui_location(template_path, region, threshold)
    if location:
        try:
            # 반환된 (x, y) 좌표 사용
            pyautogui.click(location[0], location[1], clicks=clicks, interval=interval, button=button)
            return True
        except Exception as e:
            print(f"Error during click at {location}: {e}")
            return False
    else:
        return False