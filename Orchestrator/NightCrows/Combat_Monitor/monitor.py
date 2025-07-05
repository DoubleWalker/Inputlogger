# Orchestrator/NightCrows/Combat_Monitor/monitor.py
# add_screen 방식을 사용하고, config/template_paths.py 에서 템플릿 경로를 읽도록 수정된 버전

import pyautogui
import traceback
import cv2
import time
import threading
import yaml
import os
import keyboard
import win32api
import win32con
import sys # if __name__ == "__main__" 에서 경로 설정 위해 추가
import numpy as np
import random
from enum import Enum, auto
from dataclasses import dataclass
from typing import Tuple, List, Dict, Optional
from Orchestrator.NightCrows.utils import image_utils
from Orchestrator.NightCrows.utils.screen_info import FIXED_UI_COORDS
from .config import template_paths



# (Placeholder - BaseMonitor 클래스는 Orchestrator에서 제공될 것으로 가정)
class BaseMonitor:
    """오케스트레이터와 호환되는 모니터의 기본 클래스"""

    def __init__(self, monitor_id: str, config: Optional[Dict], vd_name: str, orchestrator=None):
        # ... 기존 코드 ...
        self.orchestrator = orchestrator  # ← 이 줄 추가
        self.monitor_id = monitor_id
        self.config = config if isinstance(config, dict) else {}
        self.vd_name = vd_name
        self.io_lock = threading.Lock()  # ← 이 줄 추가

    def run_loop(self, stop_event: threading.Event):
        """Orchestrator가 스레드에서 실행할 메인 루프. stop_event로 종료 제어."""
        raise NotImplementedError("Subclasses should implement this method.")

    def stop(self):
        """Orchestrator가 모니터 종료 시 호출할 메서드. 리소스 정리 등."""
        print(f"INFO: Stopping BaseMonitor for {self.monitor_id}")

# --- Enum 정의 ---
class CharacterState(Enum):
    """캐릭터의 주요 상태"""
    NORMAL = auto()         # 정상
    HOSTILE_ENGAGE = auto() # 적대적 교전
    DEAD = auto()           # 사망

class Location(Enum):
    """캐릭터의 주요 위치"""
    ARENA = auto()          # 아레나 (또는 특정 던전 내부)
    FIELD = auto()          # 필드 (또는 마을 등 안전 지역)
    UNKNOWN = auto()        # 알 수 없음

class ScreenState(Enum):
    """화면 처리 상태"""
    NORMAL = auto()
    DEAD = auto()
    RECOVERING = auto()
    HOSTILE = auto()
    FLEEING = auto()
    BUYING_POTIONS = auto()
    RETURNING = auto()

# --- 화면 정보 데이터 클래스 ---
@dataclass

class ScreenMonitorInfo:
    """모니터링할 개별 화면의 정보"""
    screen_id: str
    region: Tuple[int, int, int, int]
    current_state: ScreenState = ScreenState.NORMAL
    retry_count: int = 0
    last_state_change_time: float = 0.0
    s1_completed: bool = False  # ← 새로 추가!
    wp1_step: int = 0             # WP1 진행 단계 (0: 시작, 1: 35초대기, 2: 완료확인)
    potion_step: int = 0          # 물약 구매 단계 (0: 시작, 1: 대기/재시도, 2: 완료)
    step_start_time: float = 0.0  # 현재 단계 시작 시간
    shop_retry_count: int = 0     # 상점 재클릭 횟수


# ----------------------------------------------------------------------------
# [주의] 아래 함수들은 플레이스홀더입니다. 실제 게임 상호작용 로직 구현 필요
#        (CombatMonitor 클래스 외부 정의 유지, 필요시 내부 메서드로 변경 가능)
# ----------------------------------------------------------------------------
# 외부함수로 존재하던 플레이스 홀더들 함수 내부로 이미그레이션 완료. 따라서 [주의]이하 무시 가능.
# IMPORTANT: 현재 SRM1을 상태머신으로 전환하는 작업을 진행하는 중. 조언 시 상태머신 전환 이슈를 최우선할 것.
#------------------------------------------------------------------------------


# ----------------------------------------------------------------------------
# Combat Monitor 클래스 구현
# ----------------------------------------------------------------------------
class CombatMonitor(BaseMonitor):
    """
    여러 NightCrows 화면의 캐릭터 상태를 모니터링합니다 (add_screen으로 추가).
    도주, 부활, 물약 구매, 웨이포인트 네비게이션을 처리합니다.
    Orchestrator에 의해 run_loop 및 stop_event로 제어됩니다.
    템플릿 경로는 config/template_paths.py에서 읽어옵니다.
    """

    def __init__(self, monitor_id="SRM1", config=None, vd_name="VD1", orchestrator=None):
        """CombatMonitor 초기화."""
        super().__init__(monitor_id, config, vd_name, orchestrator)  # orchestrator 추가!
        self.location_flag: Location = Location.UNKNOWN
        self.death_count: int = 0
        self.current_wp: int = 0
        self.max_wp: int = 0
        self.stop_event = None  # 추가: stop_event 초기화

        self.screens: List[ScreenMonitorInfo] = []
        self.confidence = self.config.get('confidence', 0.75) # 신뢰도 설정

        # 필수 템플릿 경로 로드 (getattr으로 안전하게)
        self.arena_template_path = getattr(template_paths, 'ARENA_TEMPLATE', None)
        self.dead_template_path = getattr(template_paths, 'DEAD_TEMPLATE', None)
        self.hostile_template_path = getattr(template_paths, 'HOSTILE_TEMPLATE', None)

        if not all([self.arena_template_path, self.dead_template_path, self.hostile_template_path]):
             print(f"WARNING: [{self.monitor_id}] Essential template attributes (ARENA, DEAD, HOSTILE) "
                   f"not found in template_paths module or config. State detection might fail.")

    def add_screen(self, screen_id: str, region: Tuple[int, int, int, int]):
        """모니터링할 화면 영역과 ID를 등록합니다."""
        if not isinstance(screen_id, str) or not screen_id:
             print(f"ERROR: [{self.monitor_id}] Invalid screen_id '{screen_id}' received. Skipping.")
             return
        if not isinstance(region, tuple) or len(region) != 4:
             print(f"ERROR: [{self.monitor_id}] Invalid region '{region}' for screen '{screen_id}'. Skipping.")
             return
        if any(s.screen_id == screen_id for s in self.screens):
            print(f"WARNING: [{self.monitor_id}] Screen ID '{screen_id}' already added. Skipping.")
            return

        screen = ScreenMonitorInfo(screen_id=screen_id, region=region)
        self.screens.append(screen)
        print(f"INFO: [{self.monitor_id}] Screen added: ID={screen_id}, Region={region}")

    def _load_template(self, template_path: Optional[str]) -> Optional[cv2.typing.MatLike]:
        """템플릿 이미지를 로드하고 유효성을 검사합니다."""
        if not template_path or not isinstance(template_path, str):
             return None
        if not os.path.exists(template_path):
             print(f"ERROR: [{self.monitor_id}] Template file not found: {template_path}")
             return None
        try:
            template = cv2.imread(template_path)
            if template is None:
                print(f"ERROR: [{self.monitor_id}] Failed to load template (imread returned None): {template_path}")
            return template
        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Exception loading template {template_path}: {e}")
            return None

    def _get_character_state_on_screen(self, screen: ScreenMonitorInfo) -> CharacterState:
        """지정된 화면 영역의 캐릭터 상태를 화면별 템플릿을 사용하여 확인합니다."""
        if not screen or not screen.region:
            print(f"ERROR: [{self.monitor_id}] Invalid screen object for state check.")
            return CharacterState.NORMAL

        try:
            screenshot = self.orchestrator.capture_screen_safely(screen.screen_id)
            if screenshot is None:
                print(f"ERROR: [{self.monitor_id}] Failed screenshot (Screen: {screen.screen_id}).")
                return CharacterState.NORMAL
        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Failed screenshot (Screen: {screen.screen_id}): {e}")
            return CharacterState.NORMAL

        try:
            # 템플릿 경로들을 한 번만 가져오기
            dead_template_path = template_paths.get_template(screen.screen_id, 'DEAD') or self.dead_template_path
            hostile_template_path = template_paths.get_template(screen.screen_id,
                                                                'HOSTILE') or self.hostile_template_path

            # DEAD 상태 확인
            dead_template = self._load_template(dead_template_path)
            if dead_template is not None and image_utils.compare_images(screenshot, dead_template,
                                                                        threshold=self.confidence):
                return CharacterState.DEAD

            # HOSTILE 상태 확인 (재선언 제거)
            if hostile_template_path is not None:
                hostile_template = self._load_template(hostile_template_path)
                # ... 나머지 로직
                if hostile_template is not None:
                    # 연속 샘플링 (최대 3회, 각 0.1초 간격)
                    max_samples = 3
                    sample_interval = 0.1

                    for sample_idx in range(max_samples):
                        # 새 스크린샷 캡처
                        try:
                            current_screenshot = self.orchestrator.capture_screen_safely(screen.screen_id)
                            if current_screenshot is None:
                                continue

                            # 템플릿 매칭 시도
                            if image_utils.compare_images(current_screenshot, hostile_template,
                                                          threshold=self.confidence):
                                # 로그 추가 (어떤 샘플에서 감지되었는지)
                                print(
                                    f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: HOSTILE detected on sample {sample_idx + 1}/{max_samples}")
                                return CharacterState.HOSTILE_ENGAGE
                        except Exception as e:
                            print(f"ERROR: [{self.monitor_id}] Error during HOSTILE sampling {sample_idx + 1}: {e}")

                        # 중지 신호 확인 (필요시)
                        if sample_idx < max_samples - 1:  # 마지막 샘플이 아니면 대기
                            time.sleep(sample_interval)

            # HOSTILE 감지 실패 시 NORMAL 반환 (기존과 동일)
            return CharacterState.NORMAL

        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] State check error (Screen: {screen.screen_id}): {e}")
            traceback.print_exc()
            return CharacterState.NORMAL

    def _notify_s1_completion(self):
        """S1 완료시 대기 중인 다른 화면들에게 알림"""
        print(f"INFO: [{self.monitor_id}] S1 party gathering completed! Notifying waiting screens...")

        for screen in self.screens:
            if screen.screen_id != 'S1' and screen.current_state == ScreenState.RETURNING:
                # 대기 중인 화면에 완료 플래그 설정
                screen.s1_completed = True
                print(f"INFO: [{self.monitor_id}] Notified {screen.screen_id} that S1 gathering is completed")

    def _is_character_in_arena(self, screen: ScreenMonitorInfo) -> bool:
        """지정된 화면을 사용하여 캐릭터가 아레나에 있는지 확인합니다."""
        if not screen or not screen.region:
            print(f"ERROR: [{self.monitor_id}] Invalid screen object for arena check.")
            return False

        arena_template_path = template_paths.get_template(screen.screen_id, 'ARENA') or self.arena_template_path
        arena_template = self._load_template(arena_template_path)
        if arena_template is None:
            return False # 템플릿 없으면 필드로 간주

        try:
            screen_capture = self.orchestrator.capture_screen_safely(screen.screen_id)
            if screen_capture is None:
                print(f"ERROR: [{self.monitor_id}] Failed screenshot for arena check (Screen: {screen.screen_id}).")
                return False
            return image_utils.compare_images(screen_capture, arena_template, threshold=self.confidence)
        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Exception during arena check (Screen: {screen.screen_id}): {e}")
            return False

    def _determine_initial_location(self, stop_event: threading.Event) -> bool:
        """S1 화면을 깨워서 ARENA 또는 FIELD 상태를 정확히 판단합니다."""
        if not self.screens:
            print(f"ERROR: [{self.monitor_id}] No screens added. Cannot determine initial location.")
            self.location_flag = Location.UNKNOWN
            return False

        first_screen = self.screens[0]  # S1 화면
        print(f"INFO: [{self.monitor_id}] Determining initial location using screen {first_screen.screen_id}...")

        # 1. 대기 화면 깨우기
        print(f"INFO: [{self.monitor_id}] Waking up screen {first_screen.screen_id}...")
        if not image_utils.set_focus(first_screen.screen_id, delay_after=0.5):
            print(f"ERROR: [{self.monitor_id}] Failed to set focus on screen {first_screen.screen_id}")
            return False

        # ESC 키를 눌러 대기화면 해제
        keyboard.press_and_release('esc')
        time.sleep(1.0)  # 대기화면 해제 후 잠시 대기

        # 2. Arena 상태 확인 (여러 번 시도)
        arena_template_path = template_paths.get_template(first_screen.screen_id, 'ARENA') or self.arena_template_path
        if not arena_template_path or not os.path.exists(arena_template_path):
            print(f"ERROR: [{self.monitor_id}] Arena template not found for screen {first_screen.screen_id}")
            self.location_flag = Location.FIELD  # 템플릿 없으면 기본값 FIELD 사용
            return False

        max_attempts = 5
        check_interval = 0.6  # 0.5초 간격으로 확인
        is_arena = False

        for attempt in range(max_attempts):
            if stop_event.is_set():
                return False

            try:
                # 화면 캡처 및 템플릿 매칭
                screen_capture = self.orchestrator.capture_screen_safely(first_screen.screen_id)
                if screen_capture:
                    # arena 인디케이터 체크
                    if image_utils.compare_images(
                            screen_capture,
                            self._load_template(arena_template_path),
                            threshold=self.confidence
                    ):
                        print(
                            f"INFO: [{self.monitor_id}] Arena indicator found on attempt {attempt + 1}/{max_attempts}")
                        is_arena = True
                        break
                    else:
                        print(
                            f"INFO: [{self.monitor_id}] Arena indicator not found on attempt {attempt + 1}/{max_attempts}")

                # 다음 시도 전 대기
                if attempt < max_attempts - 1 and not stop_event.wait(check_interval):
                    continue

            except Exception as e:
                print(f"ERROR: [{self.monitor_id}] Error during arena check (attempt {attempt + 1}): {e}")
                if attempt < max_attempts - 1:
                    continue

        # 3. 결과에 따라 FLAG 설정
        self.location_flag = Location.ARENA if is_arena else Location.FIELD
        print(
            f"INFO: [{self.monitor_id}] Initial Location determined after {max_attempts} checks: {self.location_flag.name}")
        return True

    # --- 게임 상호작용 메서드들 ---

    def _change_state(self, screen: ScreenMonitorInfo, new_state: ScreenState):
        """화면 상태 변경 및 관련 정보 업데이트"""
        old_state = screen.current_state
        screen.current_state = new_state
        screen.last_state_change_time = time.time()

        # 특정 상태에서는 retry_count 초기화
        if new_state != old_state:
            screen.retry_count = 0

        # ★ 새로 추가: 누군가 HOSTILE되면 S1을 BUYING_POTIONS로 강제 변경
        if (new_state == ScreenState.HOSTILE and
                screen.screen_id != 'S1' and
                self.location_flag == Location.FIELD):  # ← 이 조건 추가!

            s1_screen = next((s for s in self.screens if s.screen_id == 'S1'), None)
            if s1_screen and s1_screen.current_state == ScreenState.NORMAL:
                print(f"INFO: S1 emergency town return due to {screen.screen_id} attack (FIELD context)")
                # ... 나머지 S1 도망 로직

                # 즉시 마을 귀환
                image_utils.set_focus(s1_screen.screen_id, delay_after=0.2)
                keyboard.press_and_release('esc')
                time.sleep(0.3)
                self._click_relative(s1_screen, 'flight_button', delay_after=1.0)

                # BUYING_POTIONS로 상태 변경
                s1_screen.current_state = ScreenState.BUYING_POTIONS
                s1_screen.last_state_change_time = time.time()
                s1_screen.retry_count = 0

        print(
            f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: State changed: {old_state.name} -> {new_state.name}")

    def _handle_screen_state(self, screen: ScreenMonitorInfo, stop_event: threading.Event):
        """현재 화면 상태에 따라 처리"""
        state = screen.current_state

        # 1. NORMAL 상태 - 이상 상태 감지
        if state == ScreenState.NORMAL:
            character_state = self._get_character_state_on_screen(screen)
            if character_state == CharacterState.DEAD:
                # 사망 상태로 전환
                self._change_state(screen, ScreenState.DEAD)
            elif character_state == CharacterState.HOSTILE_ENGAGE:
                # 적대 상태로 전환
                self._change_state(screen, ScreenState.HOSTILE)

        # 2. DEAD 상태 - 부활 버튼 클릭
        elif state == ScreenState.DEAD:
            if self._initiate_recovery(screen):
                self._change_state(screen, ScreenState.RECOVERING)
            else:
                # 실패 시 재시도 로직
                screen.retry_count += 1
                if screen.retry_count > 3:
                    # 너무 많은 실패시 NORMAL로 리셋 (다음 검출 기회에)
                    self._change_state(screen, ScreenState.NORMAL)

        # 3. RECOVERING 상태 - 부활 완료 체크 및 물약 구매
        elif state == ScreenState.RECOVERING:
            # 최소 대기 시간 확인
            elapsed = time.time() - screen.last_state_change_time
            if elapsed < 10.0:
                return  # 아직 대기 중

            # 부활 완료 확인 (e.g., 묘지 UI, 필드 UI 등)
            if self._check_recovery_complete(screen):
                # 부활 완료 - 물약 구매로 전환
                self._change_state(screen, ScreenState.BUYING_POTIONS)
            elif elapsed > 30.0:
                # 타임아웃 - 너무 오래 기다림
                print(f"WARN: Recovery timeout for screen {screen.screen_id}")
                self._change_state(screen, ScreenState.NORMAL)

        # 4. HOSTILE 상태 - 도주 버튼 클릭
        elif state == ScreenState.HOSTILE:
            if self._initiate_flight(screen):
                self._change_state(screen, ScreenState.FLEEING)
            else:
                # 실패 시 재시도 로직
                screen.retry_count += 1
                if screen.retry_count > 3:
                    self._change_state(screen, ScreenState.NORMAL)

        # 5. FLEEING 상태 - 도주 완료 체크 및 물약 구매
        elif state == ScreenState.FLEEING:
            # 도주 완료 확인 (대기 후)
            elapsed = time.time() - screen.last_state_change_time
            if elapsed < 12.0:
                return  # 아직 대기 중

            # 물약 구매로 전환
            self._change_state(screen, ScreenState.BUYING_POTIONS)

        # 6. BUYING_POTIONS 상태 - 물약 구매 및 귀환 시작
        elif state == ScreenState.BUYING_POTIONS:
            context = self.location_flag
            result = self._buy_potion_and_initiate_return(screen, context)
            if result:
                self._change_state(screen, ScreenState.RETURNING)
            # else 블록 완전히 제거!
            # 진행 중일 때는 retry_count 올리지 않음

        elif state == ScreenState.RETURNING:
            elapsed = time.time() - screen.last_state_change_time

            if self.location_flag == Location.FIELD:
                if screen.screen_id == 'S1':
                    # === S1 우선 처리 로직 ===
                    if screen.retry_count == 0:
                        if self._check_returned_well_s1(screen):
                            print(f"INFO: [{self.monitor_id}] S1: Party found immediately after field_return_start!")
                            self._change_state(screen, ScreenState.NORMAL)
                            self._notify_s1_completion()
                            return

                    if self._check_returned_well_s1(screen):
                        print(f"INFO: [{self.monitor_id}] S1: Party gathering completed (member found).")
                        self._change_state(screen, ScreenState.NORMAL)
                        self._notify_s1_completion()
                    elif screen.retry_count >= 5:
                        print(f"WARN: [{self.monitor_id}] S1: Max retry attempts (5) reached. Giving up gathering.")
                        self._change_state(screen, ScreenState.NORMAL)
                        self._notify_s1_completion()
                    elif elapsed > 40.0:
                        print(f"WARN: [{self.monitor_id}] S1: Total timeout (40s). Giving up gathering.")
                        self._change_state(screen, ScreenState.NORMAL)
                        self._notify_s1_completion()
                    else:
                        if elapsed >= (screen.retry_count * 2.0):
                            screen.retry_count += 1
                            print(f"INFO: [{self.monitor_id}] S1: Retrying party gathering ({screen.retry_count}/5)...")
                            self._retry_field_return(screen, is_first_attempt=(screen.retry_count == 1))

                else:
                    # S2~S5 처리
                    if not screen.s1_completed:
                        print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Waiting for S1 completion notification...")
                        return
                    else:
                        if screen.retry_count == 0:
                            print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: S1 completion notification received! Starting own return...")
                            screen.s1_completed = False  # 알림 소모

                            if self._check_returned_well_others(screen):
                                print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Successfully returned to party immediately!")
                                self._change_state(screen, ScreenState.NORMAL)
                                return
                            else:
                                print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Starting field return retry...")
                                self._retry_field_return(screen, is_first_attempt=True)
                                screen.retry_count = 1

                        else:
                            if self._check_returned_well_others(screen):
                                print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Successfully returned to party.")
                                self._change_state(screen, ScreenState.NORMAL)
                            elif screen.retry_count >= 10:
                                print(f"WARN: [{self.monitor_id}] Screen {screen.screen_id}: Max retry attempts (10) reached. Forcing NORMAL.")
                                self._change_state(screen, ScreenState.NORMAL)
                            elif elapsed > 30.0:
                                print(f"WARN: [{self.monitor_id}] Screen {screen.screen_id}: Total timeout (30s). Forcing NORMAL.")
                                self._change_state(screen, ScreenState.NORMAL)
                            else:
                                if elapsed >= (screen.retry_count * 2.0):
                                    screen.retry_count += 1
                                    print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Retrying field return ({screen.retry_count}/10)...")
                                    self._retry_field_return(screen, is_first_attempt=False)

            elif self.location_flag == Location.ARENA:
                # === ARENA 컨텍스트: WP1 병렬 처리 후 WP2+ 순차 처리 ===

                # WP1 처리 (논블로킹, 병렬)
                # ARENA 컨텍스트에서 WP1 처리 부분만 수정
                if elapsed > 5.0:  # 5초 후 WP1 시작
                    if not hasattr(screen, 'wp1_completed'):
                        screen.wp1_completed = False

                    if not screen.wp1_completed and self._move_to_wp(screen, 1):  # WP1 완료됨
                        screen.wp1_completed = True
                        print(
                            f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: WP1 completed, starting WP2+ navigation")

                    if screen.wp1_completed:  # WP1이 완료된 상태에서만 WP2+ 체크
                        other_screens_in_navigation = [s for s in self.screens
                                                       if s.screen_id != screen.screen_id
                                                       and s.current_state == ScreenState.RETURNING
                                                       and self.location_flag == Location.ARENA]

                        # ↓ 여기서부터 기존 코드를 완전히 대체! ↓
                    if screen.wp1_completed:
                        # === 개선된 분기 구조가 여기에 들어갑니다! ===
                        # 1. 대기 큐 관리
                        if not hasattr(self, 'wp2_queue'):
                            self.wp2_queue = []

                        if screen not in self.wp2_queue:
                            screen.wp1_completion_time = time.time()
                            self.wp2_queue.append(screen)
                            self.wp2_queue.sort(key=lambda s: s.wp1_completion_time)
                            print(f"INFO: Screen {screen.screen_id} added to WP2+ queue")

                        # 2. 우선권 체크
                        has_priority = (self.wp2_queue and self.wp2_queue[0] == screen)

                        if has_priority:
                            # 우선권 있음 → 바로 실행
                            print(f"INFO: Screen {screen.screen_id} has priority! Starting WP2+...")
                            self._waypoint_navigation(stop_event, screen, start_wp=2)
                            self._change_state(screen, ScreenState.NORMAL)
                            self.wp2_queue.pop(0)
                        else:
                            # 우선권 없음 → 기존 로직으로 체크
                            other_screens_in_navigation = [s for s in self.screens
                                                           if s.screen_id != screen.screen_id
                                                           and s.current_state == ScreenState.RETURNING
                                                           and self.location_flag == Location.ARENA]

                            if not other_screens_in_navigation:
                                print(f"INFO: Screen {screen.screen_id}: No other screens, executing WP2+...")
                                self._waypoint_navigation(stop_event, screen, start_wp=2)
                                self._change_state(screen, ScreenState.NORMAL)
                            else:
                                queue_position = self.wp2_queue.index(
                                    screen) + 1 if screen in self.wp2_queue else "?"
                                print(
                                    f"INFO: Screen {screen.screen_id} waiting in queue (position: {queue_position})")
                        # === 기존 코드 대체 끝 ===


    # _check_recovery_complete 함수 (새로 추가 필요)
    def _check_recovery_complete(self, screen: ScreenMonitorInfo) -> bool:
        """부활 완료 여부 확인"""
        # 이 함수는 묘지 UI가 보이는지 확인하는 등의 로직 구현 필요
        # 기존 코드를 활용하거나 새로 구현

        # 예시 구현 (실제 코드에 맞게 조정 필요)
        graveyard_template_path = template_paths.get_template(screen.screen_id, 'GRAVEYARD')
        if not graveyard_template_path or not os.path.exists(graveyard_template_path):
            return False

        # 묘지 UI 확인
        screenshot = self.orchestrator.capture_screen_safely(screen.screen_id)
        graveyard_visible = image_utils.is_image_present(graveyard_template_path, screen.region, self.confidence,
                                                         screenshot)
        return graveyard_visible

    def _attempt_flight(self, screen: ScreenMonitorInfo) -> bool:
        """지정된 화면에서 '도주' 버튼 템플릿을 찾아 클릭을 시도합니다."""
        flight_template_path = template_paths.get_template(screen.screen_id, 'FLIGHT_BUTTON')
        if not flight_template_path:
            print(f"ERROR: [{self.monitor_id}] Flight 실패: 템플릿 경로가 설정되지 않음 (Screen {screen.screen_id})")
            return False
        if not os.path.exists(flight_template_path):
            print(f"ERROR: [{self.monitor_id}] Flight 실패: 템플릿 파일이 존재하지 않음: {flight_template_path}")
            return False

        try:
            # Orchestrator에서 중앙집중식 캡쳐
            screenshot = self.orchestrator.capture_screen_safely(screen.screen_id)

            # 1. 먼저 템플릿 매칭 시도
            center_coords = image_utils.return_ui_location(
                template_path=flight_template_path,
                region=screen.region,
                threshold=self.confidence,
                screenshot_img=screenshot
            )
            if center_coords:
                pyautogui.click(center_coords)
                print(f"INFO: [{self.monitor_id}] Flight initiated via template matching on screen {screen.screen_id}.")
                return True
            else:
                print(f"WARN: [{self.monitor_id}] 템플릿 매칭 실패, 고정 좌표 시도...")

                # 2. 템플릿 매칭 실패 시 고정 좌표 사용
                if self._click_relative(screen, 'flight_button', delay_after=0.2):
                    print(
                        f"INFO: [{self.monitor_id}] Flight initiated via fixed coordinates on screen {screen.screen_id}.")
                    return True
                else:
                    print(f"ERROR: [{self.monitor_id}] Flight 실패: 템플릿 매칭 및 고정 좌표 모두 실패")
                    return False
        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Flight 실패: 예외 발생: {e}")
            return False

    def win32_click(self,x, y):
        win32api.SetCursorPos((x, y))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)

    def _buy_potion_and_initiate_return(self, screen: ScreenMonitorInfo, context: Location) -> bool:
        try:
            print(f"DEBUG: [{self.monitor_id}] Screen {screen.screen_id}: potion_step = {screen.potion_step}")

            if screen.potion_step == 0:
                shop_clicked = False
                # 템플릿 시도
                shop_template_path = template_paths.get_template(screen.screen_id, 'SHOP_BUTTON')
                print(f"DEBUG: [{self.monitor_id}] Shop template path: {shop_template_path}")
                print(
                    f"DEBUG: [{self.monitor_id}] Template exists: {os.path.exists(shop_template_path) if shop_template_path else False}")
                if shop_template_path and os.path.exists(shop_template_path):
                    screenshot = self.orchestrator.capture_screen_safely(screen.screen_id)
                    shop_button_loc = image_utils.return_ui_location(shop_template_path, screen.region,
                                                                     self.confidence, screenshot)
                    print(f"DEBUG: [{self.monitor_id}] Shop button location: {shop_button_loc}")

                    if shop_button_loc:
                        with self.io_lock:
                            self.win32_click(shop_button_loc[0], shop_button_loc[1])
                            shop_clicked = True
                        print(f"DEBUG: [{self.monitor_id}] Shop clicked via template")
                    else:
                        print(f"DEBUG: [{self.monitor_id}] Template matching failed")
                else:
                    print(f"DEBUG: [{self.monitor_id}] Template path invalid or file not found")

                # 템플릿 실패시 고정 좌표
                if not shop_clicked:
                    print(f"DEBUG: [{self.monitor_id}] Trying fixed coordinates...")
                    with self.io_lock:
                        if self._click_relative(screen, 'shop_button', delay_after=0.5):
                            shop_clicked = True
                            print(f"DEBUG: [{self.monitor_id}] Shop clicked via fixed coords")
                        else:
                            print(f"DEBUG: [{self.monitor_id}] Fixed coords also failed")

                if not shop_clicked:
                    print(f"ERROR: [{self.monitor_id}] Both shop click methods failed!")
                    return False
                # 15초 대기 시작
                print(f"DEBUG: [{self.monitor_id}] Shop clicked successfully, starting 15s wait...")
                screen.step_start_time = time.time()
                screen.shop_retry_count = 0
                screen.potion_step = 1
                print(f"DEBUG: [{self.monitor_id}] potion_step changed to 1")
                return False  # 아직 완료 안됨

            elif screen.potion_step == 1:
                # 대기 및 구매 버튼 찾기 단계
                elapsed = time.time() - screen.step_start_time
                required_wait = 15.0 if screen.shop_retry_count == 0 else 10.0

                if elapsed >= required_wait:
                    # 구매 버튼 찾기 시도
                    image_utils.set_focus(screen.screen_id, delay_after=0.3)
                    purchase_template_path = template_paths.get_template(screen.screen_id, 'PURCHASE_BUTTON')
                    screenshot = self.orchestrator.capture_screen_safely(screen.screen_id)
                    purchase_button_loc = image_utils.return_ui_location(purchase_template_path, screen.region,
                                                                         self.confidence, screenshot)
                    print(f"DEBUG: Purchase button location: {purchase_button_loc}")

                    if purchase_button_loc:
                        # 구매 버튼 찾음 → 다음 단계로
                        screen.potion_step = 2
                        return False
                    else:
                        # 구매 버튼 못찾음 → 재클릭 시도 (최대 2회)
                        if screen.shop_retry_count < 2:
                            # 상점 재클릭
                            shop_reclicked = False
                            shop_template_path = template_paths.get_template(screen.screen_id, 'SHOP_BUTTON')
                            if shop_template_path and os.path.exists(shop_template_path):
                                screenshot2 = self.orchestrator.capture_screen_safely(screen.screen_id)
                                shop_button_loc = image_utils.return_ui_location(shop_template_path, screen.region,
                                                                                 self.confidence, screenshot2)
                                if shop_button_loc:
                                    with self.io_lock:
                                        self.win32_click(shop_button_loc[0], shop_button_loc[1])
                                        shop_reclicked = True

                            if not shop_reclicked:
                                with self.io_lock:
                                    if self._click_relative(screen, 'shop_button', delay_after=0.5):
                                        shop_reclicked = True

                            if shop_reclicked:
                                # 재클릭 성공 → 10초 대기 시작
                                screen.step_start_time = time.time()
                                screen.shop_retry_count += 1
                                return False
                            else:
                                # 재클릭 실패 → 포기
                                screen.potion_step = 0  # 리셋
                                return False
                        else:
                            # 최대 재시도 도달 → 포기
                            screen.potion_step = 0  # 리셋
                            return False
                else:
                    # 아직 대기 시간 안됨
                    return False

            elif screen.potion_step == 2:
                # 구매 완료 및 나머지 처리
                purchase_template_path = template_paths.get_template(screen.screen_id, 'PURCHASE_BUTTON')
                screenshot = self.orchestrator.capture_screen_safely(screen.screen_id)
                purchase_button_loc = image_utils.return_ui_location(purchase_template_path, screen.region,
                                                                     self.confidence, screenshot)

                if not purchase_button_loc:
                    screen.potion_step = 0  # 리셋
                    return False

                # 구매 버튼부터 ESC까지 하나의 락으로 처리
                with self.io_lock:
                    pyautogui.click(purchase_button_loc[0], purchase_button_loc[1])
                    time.sleep(1)

                    # 확인 버튼 처리
                    confirm_template_path = template_paths.get_template(screen.screen_id, 'CONFIRM_BUTTON')
                    if confirm_template_path and os.path.exists(confirm_template_path):
                        screenshot2 = self.orchestrator.capture_screen_safely(screen.screen_id)
                        confirm_button_loc = image_utils.return_ui_location(confirm_template_path, screen.region,
                                                                            self.confidence, screenshot2)
                        if confirm_button_loc:
                            pyautogui.click(confirm_button_loc[0], confirm_button_loc[1])
                            time.sleep(0.5)

                    # 상점 닫기
                    keyboard.press_and_release('esc')
                    time.sleep(0.5)
                    keyboard.press_and_release('esc')
                    time.sleep(1)

                # Context별 후속 처리 (기존 로직 유지)
                if context == Location.FIELD:
                    with self.io_lock:
                        if not self._click_relative(screen, 'main_menu_button', delay_after=1.0):
                            screen.potion_step = 0  # 리셋
                            return False
                        if not self._click_relative(screen, 'field_schedule_button', delay_after=1.0):
                            screen.potion_step = 0  # 리셋
                            return False
                        if not self._click_relative(screen, 'field_return_reset', delay_after=1.0):
                            screen.potion_step = 0  # 리셋
                            return False
                        self._click_relative(screen, 'field_return_start', delay_after=1.0)

                screen.potion_step = 0  # 리셋
                return True  # 완료

        except Exception as e:
            screen.potion_step = 0  # 오류 시 리셋
            return False

    def _process_recovery(self, screen: ScreenMonitorInfo) -> bool:
        """지정된 화면에서 부활 동작을 수행합니다."""
        print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Processing RECOVERY (Revive)...")

        try:
            # 1. 부활 버튼 클릭
            revive_template_path = template_paths.get_template(screen.screen_id, 'REVIVE_BUTTON')
            if not revive_template_path or not os.path.exists(revive_template_path):
                print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: REVIVE_BUTTON template not found.")
                return False

            screenshot = self.orchestrator.capture_screen_safely(screen.screen_id)
            revive_location = image_utils.return_ui_location(revive_template_path, screen.region, self.confidence,
                                                             screenshot)
            if not revive_location:
                print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: REVIVE_BUTTON not found on screen.")
                return False

            pyautogui.click(revive_location)
            print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Clicked REVIVE_BUTTON.")

            # 2. 부활 후 마을 복귀 대기 (10-15초)
            wait_time = random.uniform(10, 15)
            print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Waiting {wait_time:.1f}s for respawn...")
            time.sleep(wait_time)

            # 3. 묘지 UI 찾기 (여러 번 시도)
            graveyard_template_path = template_paths.get_template(screen.screen_id, 'GRAVEYARD')
            if not graveyard_template_path or not os.path.exists(graveyard_template_path):
                print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: GRAVEYARD template not found.")
                return False

            max_attempts = 5
            graveyard_found = False

            for attempt in range(max_attempts):
                screenshot2 = self.orchestrator.capture_screen_safely(screen.screen_id)
                graveyard_location = image_utils.return_ui_location(graveyard_template_path, screen.region,
                                                                    self.confidence, screenshot2)
                if graveyard_location:
                    pyautogui.click(graveyard_location)
                    print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Clicked GRAVEYARD location.")
                    graveyard_found = True
                    break
                else:
                    print(
                        f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: GRAVEYARD not found (attempt {attempt + 1}/{max_attempts})")
                    time.sleep(1.0)

            if not graveyard_found:
                print(
                    f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: GRAVEYARD not found after {max_attempts} attempts.")
                return False

            # 4. 잠시 대기
            time.sleep(0.5)

            # 5. 고정 위치 클릭
            if not self._click_relative(screen, 'graveyard_confirm', delay_after=0.5):
                print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: Failed to click graveyard_confirm.")
                return False

            # 6. ESC 키 누르기
            keyboard.press_and_release('esc')
            print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Pressed ESC. Recovery process completed.")

            return True

        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: Exception during recovery: {e}")
            return False

    def _check_single_party_template(self, screen: ScreenMonitorInfo, template_path: str, threshold: float = 0.15,
                                     samples: int = 7, sample_interval: float = 0.5) -> bool:
        """
        단일 파티 템플릿으로 파티 UI 체크 (공통 로직)
        """
        if not template_path or not os.path.exists(template_path):
            return False

        try:
            template = cv2.imread(template_path)
            if template is None:
                print(f"ERROR: [{self.monitor_id}] Failed to load PARTY_UI template: {template_path}")
                return False

            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            min_val_overall = 1.0

            for i in range(samples):
                try:
                    screen_img = self.orchestrator.capture_screen_safely(screen.screen_id)
                    screen_gray = cv2.cvtColor(np.array(screen_img), cv2.COLOR_RGB2GRAY)

                    match_result = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_SQDIFF_NORMED)
                    min_val, _, _, _ = cv2.minMaxLoc(match_result)
                    min_val_overall = min(min_val_overall, min_val)

                    if min_val < threshold:
                        print(
                            f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Party UI found (template: {os.path.basename(template_path)}, match: {min_val:.4f})")
                        return True

                except Exception as e:
                    print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id} sampling error: {e}")

                if i < samples - 1:
                    time.sleep(sample_interval)

            return False

        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Exception in _check_single_party_template: {e}")
            return False

    def _check_returned_well_s1(self, screen: ScreenMonitorInfo) -> bool:
        """S1용: S2~S5 중 하나라도 매칭되면 True"""
        print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: S1 searching for any party member (S2~S5)...")

        for member_id in ['S2', 'S3', 'S4', 'S5']:
            template_path = template_paths.get_template('S1', member_id)  # 'S1', 'S2' 이런 식으로
            if template_path and self._check_single_party_template(screen, template_path):
                print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Found party member {member_id}")
                return True

        print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: No party members found (S2~S5)")
        return False

    def _check_returned_well_others(self, screen: ScreenMonitorInfo) -> bool:
        """
        S2~S5용: S1 파티 템플릿만 체크
        """
        print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Searching for S1...")

        s1_template_path = template_paths.get_template('S1', 'PARTY_UI')
        if s1_template_path and self._check_single_party_template(screen, s1_template_path):
            print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Found S1")
            return True

        print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: S1 not found")
        return False


    def _check_returned_well(self, screen: ScreenMonitorInfo, samples: int = 7, threshold: float = 0.15,
                             sample_interval: float = 0.5) -> bool:
        """
        기존 호환성을 위한 함수 (자신의 화면 ID에 맞는 PARTY_UI 템플릿 사용)
        """
        template_path = template_paths.get_template(screen.screen_id, 'PARTY_UI')
        return self._check_single_party_template(screen, template_path, threshold, samples, sample_interval)

    def _click_relative(self, screen: ScreenMonitorInfo, coord_key: str, delay_after: float = 0.5, random_offset: int = 2) -> bool:
        """
        지정된 화면 영역 내에서 FIXED_UI_COORDS에 정의된 키를 사용하여
        상대 좌표에 클릭을 수행합니다.

        Args:
            screen: 클릭을 수행할 ScreenMonitorInfo 객체.
            coord_key: utils.screen_info.FIXED_UI_COORDS 내 해당 screen_id 딕셔너리의 키.
            delay_after: 클릭 후 대기 시간 (초).
            random_offset: 클릭 좌표에 적용할 랜덤 오프셋 범위 (± 값).

        Returns:
            클릭 성공 시 True, 실패 시 False.
        """
        if not screen or not screen.region:
            print(f"ERROR:[{self.monitor_id}] Invalid screen for relative click.")
            return False
        if not hasattr(screen, 'screen_id'):
             print(f"ERROR:[{self.monitor_id}] screen_info object missing 'screen_id' for relative click.")
             return False

        # screen_info 모듈의 FIXED_UI_COORDS 에서 상대 좌표 가져오기
        screen_coords = FIXED_UI_COORDS.get(screen.screen_id)
        if not screen_coords:
            print(f"ERROR:[{self.monitor_id}] Relative coordinates not found for screen '{screen.screen_id}' in FIXED_UI_COORDS.")
            return False

        relative_coord = screen_coords.get(coord_key)
        if relative_coord is None:
            print(f"ERROR:[{self.monitor_id}] Relative coordinate key '{coord_key}' not found for screen '{screen.screen_id}'.")
            return False
        if not isinstance(relative_coord, tuple) or len(relative_coord) != 2:
            print(f"ERROR:[{self.monitor_id}] Invalid coordinate format for '{coord_key}' on screen '{screen.screen_id}': {relative_coord}")
            return False

        # 절대 좌표 계산
        region_x, region_y, _, _ = screen.region
        try:
            # 정수 좌표 보장 및 랜덤 오프셋 적용
            click_x = int(region_x + relative_coord[0] + np.random.randint(-random_offset, random_offset + 1))
            click_y = int(region_y + relative_coord[1] + np.random.randint(-random_offset, random_offset + 1))
        except ValueError: # relative_coord가 숫자가 아닐 경우 대비
             print(f"ERROR:[{self.monitor_id}] Invalid coordinate values for '{coord_key}' on screen '{screen.screen_id}': {relative_coord}")
             return False

        try:
            print(f"INFO:[{self.monitor_id}] Clicking relative '{coord_key}' at ({click_x}, {click_y}) on screen {screen.screen_id}...")
            pyautogui.click(click_x, click_y)
            if delay_after > 0:
                print(f"INFO:[{self.monitor_id}] Waiting {delay_after}s after clicking '{coord_key}'.")
                time.sleep(delay_after)
            return True
        except Exception as e:
            print(f"ERROR:[{self.monitor_id}] Failed to click relative coordinate '{coord_key}' on screen {screen.screen_id}: {e}")
            return False

    def _move_to_wp(self, screen: ScreenMonitorInfo, wp_index: int) -> bool:
        """특정 웨이포인트로 이동 시작 (공통 인터페이스)"""
        print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Moving to waypoint {wp_index}")

        try:
            # 직접 UI 클릭 방식 이동 (WP1, WP2)
            if wp_index in [1, 2]:
                return self._move_to_arena_wp(screen, wp_index)

            # 파티 리더-팔로워 방식 이동 (WP3, WP4)
            elif wp_index in [3, 4]:
                return self._move_to_party_shared_wp(screen, wp_index)

            else:
                print(f"ERROR: [{self.monitor_id}] Unknown waypoint index: {wp_index}")
                return False

        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Exception during move to waypoint {wp_index}: {e}")
            return False

    def _move_to_arena_wp(self, screen: ScreenMonitorInfo, wp_index: int) -> bool:
        """격전지 내 웨이포인트(WP1, WP2)로 UI 클릭을 통해 이동"""
        try:
            if wp_index == 1:
                # WP1 - 단계별 논블로킹 처리
                if screen.wp1_step == 0:
                    # 초기 단계: 메뉴 클릭부터 Y키까지
                    with self.io_lock:
                        if not self._click_relative(screen, 'main_menu_button', delay_after=1.0):
                            return False

                        # 아이콘 찾기 및 클릭
                        arena_icon_template = template_paths.get_template(screen.screen_id, 'ARENA_MENU_ICON')
                        if not arena_icon_template or not os.path.exists(arena_icon_template):
                            keyboard.press_and_release('esc')
                            return False

                        screenshot = self.orchestrator.capture_screen_safely(screen.screen_id)
                        icon_pos = image_utils.return_ui_location(arena_icon_template, screen.region, self.confidence,
                                                                  screenshot)
                        if not icon_pos:
                            keyboard.press_and_release('esc')
                            return False

                        pyautogui.click(icon_pos)
                        time.sleep(1.0)
                        keyboard.press_and_release('y')

                    # 35초 대기 시작
                    screen.step_start_time = time.time()
                    screen.wp1_step = 1
                    return False  # 아직 완료 안됨

                elif screen.wp1_step == 1:
                    # 35초 대기 중
                    elapsed = time.time() - screen.step_start_time
                    if elapsed >= 35.0:
                        screen.wp1_step = 2
                    return False  # 아직 대기 중

                elif screen.wp1_step == 2:
                    # 아레나 입장 UI 확인 및 완료 처리
                    arena_entry_path = template_paths.get_template(screen.screen_id, 'ARENA_ENTRY_UI')
                    if not arena_entry_path:
                        screen.wp1_step = 0  # 리셋
                        return False

                    # UI 확인 (임계값 단계적 시도)
                    entry_found = False
                    for threshold in [self.confidence, 0.8, 0.72]:
                        screenshot = self.orchestrator.capture_screen_safely(screen.screen_id)
                        if image_utils.is_image_present(arena_entry_path, screen.region, threshold=threshold,
                                                        screenshot_img=screenshot):
                            entry_found = True
                            break
                        time.sleep(1.0)

                    if not entry_found:
                        screen.wp1_step = 0  # 리셋
                        return False

                    # 최종 클릭 및 완료
                    with self.io_lock:
                        if not self._click_relative(screen, 'arena_entry_option1', delay_after=1.0):
                            screen.wp1_step = 0  # 리셋
                            return False

                    # 15초 대기를 논블로킹으로 변경
                    screen.step_start_time = time.time()  # 대기 시작 시간 기록
                    screen.wp1_step = 3  # 새로운 단계 추가
                    return False  # 아직 완료 안됨

                elif screen.wp1_step == 3:
                    # 15초 대기 중
                    elapsed = time.time() - screen.step_start_time
                    if elapsed >= 15.0:
                        screen.wp1_step = 0  # 리셋
                        return True  # 완료
                    return False  # 아직 대기 중

            elif wp_index == 2:
                # WP2 (격전지 내 특정 위치/탑) 이동 로직
                print(f"INFO: [{self.monitor_id}] Moving to WP2 (Arena Tower)...")

                # 1. 포커스 설정 (락 밖에서)
                if not image_utils.set_focus(screen.screen_id):
                    print(f"ERROR: [{self.monitor_id}] Failed to set focus for WP2 on screen {screen.screen_id}")
                    return False

                # 2. 맵 인터페이스 열기 및 클릭 시퀀스 (IO_LOCK 필요)
                with self.io_lock:
                    # 맵 열기
                    keyboard.press_and_release('m')
                    print(f"INFO: [{self.monitor_id}] Opened map interface")
                    time.sleep(2.0)  # 맵 로딩 대기

                    # 첫 번째 고정 좌표 클릭
                    if not self._click_relative(screen, 'tower_click_1', delay_after=0.5):
                        print(f"ERROR: [{self.monitor_id}] Failed to click first tower location")
                        keyboard.press_and_release('m')  # 맵 닫기
                        return False

                    # 두 번째 고정 좌표 더블클릭 (tower_click_2와 3이 동일한 위치)
                    if not self._click_relative(screen, 'tower_click_2', delay_after=0.3):
                        print(f"ERROR: [{self.monitor_id}] Failed to click second tower location")
                        keyboard.press_and_release('m')  # 맵 닫기
                        return False

                    # 같은 위치 더블클릭
                    if not self._click_relative(screen, 'tower_click_2', delay_after=0.5):
                        print(f"ERROR: [{self.monitor_id}] Failed to double-click tower location")
                        keyboard.press_and_release('m')  # 맵 닫기
                        return False

                    # Y 키 입력으로 확인
                    keyboard.press_and_release('y')
                    print(f"INFO: [{self.monitor_id}] Pressed Y to confirm teleport")

                tower_teleport_wait_time = 2.5  # 적절한 시간으로 조정
                print(f"INFO: Waiting {tower_teleport_wait_time}s for tower teleport to complete...")
                time.sleep(tower_teleport_wait_time)

                print(f"INFO: Successfully initiated tower teleport")
                return True
            else:
                print(f"ERROR: [{self.monitor_id}] Unsupported arena waypoint index: {wp_index}")
                return False

        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Exception during arena WP{wp_index} movement: {e}")
            # 오류 시 맵/메뉴 닫기 시도
            try:
                keyboard.press_and_release('esc')
                if wp_index == 2:  # WP2는 맵을 열었을 수 있음
                    keyboard.press_and_release('m')
            except:
                pass
        except Exception as e:
            screen.wp1_step = 0  # 오류 시 리셋
            return False

    def _check_reached_wp(self, screen: ScreenMonitorInfo, wp_index: int) -> bool:
        """웨이포인트 도착 여부를 확인합니다"""
        print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Checking if reached Waypoint #{wp_index}")

        try:
            if wp_index == 1:
                # WP1: 아레나 내부에 있는지 확인
                if self._is_character_in_arena(screen):
                    print(f"INFO: [{self.monitor_id}] WP1 reached - Character is in arena")
                    return True
                else:
                    print(f"INFO: [{self.monitor_id}] WP1 not reached - Character not in arena")
                    return False

            elif wp_index == 2:
                # WP2: 타워 근처 도착 확인 (템플릿 또는 위치 기반)
                tower_template_path = template_paths.get_template(screen.screen_id, 'WAYPOINT_2')
                if tower_template_path and os.path.exists(tower_template_path):
                    screenshot = self.orchestrator.capture_screen_safely(screen.screen_id)
                    if image_utils.is_image_present(tower_template_path, screen.region, threshold=0.8,
                                                    screenshot_img=screenshot):
                        print(f"INFO: [{self.monitor_id}] WP2 reached - Tower location confirmed")
                        return True

                # 템플릿 없으면 이동 완료로 간주 (기존 로직 유지)
                print(f"INFO: [{self.monitor_id}] WP2 considered reached (no template check available)")
                return True

            elif wp_index == 3:
                # WP3: 이동 시퀀스 완료로 도착 간주
                print(f"INFO: [{self.monitor_id}] WP3 considered reached (movement sequence completed)")
                return True

            elif wp_index == 4:
                # WP4: 글라이더 시퀀스 완료 확인 (시퀀스 실행 성공 여부로 판단)
                print(f"INFO: [{self.monitor_id}] WP4 considered reached after glider sequence")
                return True

            elif wp_index == 5:
                # WP5: 최종 전투 지점 확인
                return self._is_at_combat_spot(screen)

            else:
                print(f"ERROR: [{self.monitor_id}] Unknown waypoint index: {wp_index}")
                return False

        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Exception during check waypoint {wp_index}: {e}")
            return False

    def _is_at_combat_spot(self, screen: ScreenMonitorInfo) -> bool:
        """최종 전투 지점 도착 여부를 최대 3번 확인합니다."""
        print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Checking if at combat spot")

        # 전투 지점 확인 템플릿 경로 가져오기
        template_path = template_paths.get_template(screen.screen_id, 'COMBAT_SPOT')

        if not template_path or not os.path.exists(template_path):
            print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: COMBAT_SPOT template not found")
            return False

        # 최대 3번 시도
        max_attempts = 3
        for attempt in range(max_attempts):
            screenshot = self.orchestrator.capture_screen_safely(screen.screen_id)
            if image_utils.is_image_present(
                    template_path=template_path,
                    region=screen.region,
                    threshold=self.confidence,
                    screenshot_img=screenshot
            ):
                print(f"INFO: [{self.monitor_id}] Combat spot reached confirmed on attempt {attempt + 1}")
                return True

            print(f"INFO: [{self.monitor_id}] Combat spot not detected on attempt {attempt + 1}/{max_attempts}")
            time.sleep(1.0)  # 1초 간격으로 재시도

        print(f"INFO: [{self.monitor_id}] Combat spot not confirmed after {max_attempts} attempts")
        return False

    def _move_to_party_shared_wp(self, screen: ScreenMonitorInfo, wp_index: int) -> bool:
        """파티 리더-팔로워 방식 웨이포인트(WP3, WP4)로 이동"""
        try:
            if wp_index == 3:
                # WP3 - 점프 시작점으로 이동 (WASD 이동)
                print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Moving to WP3 (Jump point)")

                with self.io_lock:
                    # 1단계: WASD 이동 (S5는 다른 타이밍)
                    if screen.screen_id == 'S5':
                        # S5 전용 타이밍
                        keyboard.press('a')
                        time.sleep(1.0)  #
                        keyboard.press('w')
                        time.sleep(5.0)  #
                        keyboard.release('a')
                        keyboard.release('w')
                        time.sleep(0.5)  #
                    else:
                        # S1~S4 기본 타이밍
                        keyboard.press('a')
                        time.sleep(1.3)
                        keyboard.press('w')
                        time.sleep(5.5)
                        keyboard.release('a')
                        keyboard.release('w')
                        time.sleep(0.5)

                    # 2단계: 줌아웃을 위한 변수 정의
                    center_x = screen.region[0] + screen.region[2] // 2
                    center_y = screen.region[1] + screen.region[3] // 2

                    if screen.screen_id == 'S5':
                        # S5: 휠다운
                        end_time = time.time() + 3.0
                        while time.time() < end_time:
                            pyautogui.scroll(-1)
                            time.sleep(0.1)
                    else:
                        # S1~S4: 드래그 - 변수 정의 추가
                        base_offset = 150  # S1 기준
                        screen_ratios = {
                            'S1': 1.0,
                            'S2': 1.1,
                            'S3': 1.0,
                            'S4': 1.0,
                        }

                        ratio = screen_ratios.get(screen.screen_id, 1.0)
                        offset = int(base_offset * ratio)
                        start_x = center_x + offset
                        start_y = center_y

                        keyboard.press('ctrl')
                        pyautogui.mouseDown(start_x, start_y, button='left')
                        pyautogui.dragTo(center_x, center_y, duration=0.5)
                        pyautogui.mouseUp(button='left')
                        keyboard.release('ctrl')

                    time.sleep(0.5)

                return True

            elif wp_index == 4:
                # WP4 - 글라이더 비행 시퀀스
                print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Starting WP4 (Glider sequence)")

                # YAML 파일에 정의된 글라이더 시퀀스 실행
                return self._execute_sequence("wp4_glider", stop_event=self.stop_event)

            else:
                print(f"ERROR: [{self.monitor_id}] Unsupported party waypoint index: {wp_index}")
                return False

        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Exception during party shared waypoint {wp_index}: {e}")
            traceback.print_exc()
            return False

    def _retry_field_return(self, screen: ScreenMonitorInfo, is_first_attempt: bool = False) -> bool:
        """필드 복귀 재시도: 단일 버튼 클릭 (첫 시도시에만 Y키 입력)"""
        try:
            print(
                f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Retrying field return (first attempt: {is_first_attempt})...")

            # 1. 단일 버튼 클릭
            if not self._click_relative(screen, 'field_return_button', delay_after=0.5):
                print(f"WARN: [{self.monitor_id}] Screen {screen.screen_id}: Failed to click field return button.")
                return False

            # 2. Y키 입력 (첫 시도일 때만)
            if is_first_attempt:
                time.sleep(0.3)  # 클릭 후 잠시 대기
                keyboard.press_and_release('y')
                print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Pressed Y key (first attempt).")

            return True

        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: Field return retry failed: {e}")
            return False
    # 1. 초기 대응 함수들
    def _initiate_recovery(self, screen: ScreenMonitorInfo) -> bool:
        """부활 버튼 클릭만 담당하는 초기 대응 함수"""
        print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Initiating recovery (clicking revive button)...")

        # 부활 버튼 템플릿 경로 가져오기
        revive_template_path = template_paths.get_template(screen.screen_id, 'REVIVE_BUTTON')
        if not revive_template_path or not os.path.exists(revive_template_path):
            print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: REVIVE_BUTTON template not found.")
            return False

        # 부활 버튼 위치 찾기
        screenshot = self.orchestrator.capture_screen_safely(screen.screen_id)
        revive_location = image_utils.return_ui_location(revive_template_path, screen.region, self.confidence,
                                                         screenshot)
        if not revive_location:
            print(f"ERROR: [{self.monitor_id}] Screen {screen.screen_id}: REVIVE_BUTTON not found on screen.")
            return False

        # 부활 버튼 클릭
        pyautogui.click(revive_location)
        print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Clicked REVIVE_BUTTON.")
        time.sleep(0.2)  # 클릭 후 약간의 대기

        return True

    def _initiate_flight(self, screen: ScreenMonitorInfo) -> bool:
        """도주 버튼 클릭만 담당하는 초기 대응 함수"""
        print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Initiating flight (clicking escape button)...")

        # 기존 도주 버튼 클릭 함수 호출 (이미 도주 버튼 클릭만 담당)
        return self._attempt_flight(screen=screen)

    def _execute_sequence(self, sequence_name: str, stop_event: threading.Event = None) -> bool:
        """YAML에 정의된 동작 시퀀스를 실행합니다."""
        try:
            # 매개변수가 없으면 인스턴스 변수 사용
            local_stop_event = stop_event if stop_event is not None else self.stop_event


            # 설정 폴더 경로 (프로젝트 루트 기준 상대 경로)
            config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
            yaml_path = os.path.join(config_dir, f"{sequence_name}.yaml")

            if not os.path.exists(yaml_path):
                print(f"ERROR: Sequence file not found: {yaml_path}")
                return False

            # YAML 파일 로드
            with open(yaml_path, 'r', encoding='utf-8') as f:
                sequence_data = yaml.safe_load(f)

            if not sequence_data:
                print(f"ERROR: Empty or invalid sequence data: {sequence_name}")
                return False

            # 첫 번째 키가 시퀀스 정의를 담고 있음
            sequence_key = next(iter(sequence_data))
            sequence = sequence_data[sequence_key]

            # 시퀀스의 각 단계(phase) 실행
            for phase in sequence:
                phase_name = phase.get('phase', 'unnamed')
                print(f"INFO: [{self.monitor_id}] Executing phase: {phase_name}")

                # 반복 실행이 필요한 경우
                repeat_count = phase.get('repeat', 1)
                interval = phase.get('interval', 0)

                for _ in range(repeat_count):
                    # 중지 신호 확인
                    if stop_event and stop_event.is_set():
                        print(f"INFO: [{self.monitor_id}] Sequence '{sequence_name}' interrupted by stop signal")
                        return False

                    # 단계 내 액션 실행
                    for action in phase.get('actions', []):
                        action_type = action.get('type', '')
                        key = action.get('key', '')
                        duration = action.get('duration', 0.1)

                        if action_type == 'key_press':
                            keyboard.press_and_release(key)
                        elif action_type == 'key_hold':
                            keyboard.press(key)
                        elif action_type == 'key_release':
                            keyboard.release(key)
                        elif action_type == 'wait':
                            pass  # duration으로만 대기

                        # 액션 후 지정된 시간만큼 대기
                        if duration > 0:
                            if stop_event and stop_event.wait(duration):
                                print(f"INFO: [{self.monitor_id}] Sequence interrupted during wait")
                                return False
                            else:
                                time.sleep(duration)

                    # 반복 간격 대기
                    if _ < repeat_count - 1 and interval > 0:
                        if stop_event and stop_event.wait(interval):
                            return False
                        else:
                            time.sleep(interval)

            print(f"INFO: [{self.monitor_id}] Sequence '{sequence_name}' completed successfully")
            return True

        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Failed to execute sequence '{sequence_name}': {e}")
            traceback.print_exc()
            # 안전을 위해 모든 키 해제
            keyboard.release('s')
            keyboard.release('w')
            keyboard.release('shift')
            keyboard.release('space')
            return False

    def _waypoint_navigation(self, stop_event: threading.Event, target_screen: ScreenMonitorInfo,
                             start_wp: int = 1, end_wp: int = None):
        """특정 화면에 대한 웨이포인트 네비게이션 로직을 처리합니다."""
        print(f"INFO: [{self.monitor_id}] Starting Waypoint Navigation for screen {target_screen.screen_id}...")

        # 전달된 화면 사용
        screen = target_screen

        # 웨이포인트 범위 설정
        if end_wp is None:
            end_wp = 5  # 또는 self._get_max_wp_num()

        self.current_wp = start_wp

        while self.current_wp <= end_wp and not stop_event.is_set():
            print(f"INFO: [{self.monitor_id}] --- Waypoint Loop: Target WP {self.current_wp}/{self.max_wp} ---")

            # 1. 웨이포인트로 이동 시도
            if not self._move_to_wp(screen, self.current_wp):
                print(
                    f"CRITICAL: [{self.monitor_id}] Failed to move to WP {self.current_wp}. Aborting waypoint navigation.")
                return  # 전체 네비게이션 종료

            # 2. 웨이포인트 도착 확인 (여러 번 시도)
            reached = False
            check_attempts = 0
            max_check_attempts = 10

            while not reached and check_attempts < max_check_attempts and not stop_event.is_set():
                if self._check_reached_wp(screen, self.current_wp):
                    print(f"INFO: [{self.monitor_id}] Successfully reached WP {self.current_wp}.")
                    reached = True
                    break

                check_attempts += 1
                print(
                    f"INFO: [{self.monitor_id}] WP {self.current_wp} not reached yet ({check_attempts}/{max_check_attempts}).")

                # 못 찾으면 조정 시도
                if not self._look_for_wp(screen, self.current_wp):
                    print(f"WARN: [{self.monitor_id}] Failed to look for WP {self.current_wp}.")

                # 잠시 대기 후 다시 확인
                if stop_event.wait(1.0):
                    return  # 중지 신호 받으면 종료

            if not reached:
                print(
                    f"WARN: [{self.monitor_id}] Could not confirm reaching WP {self.current_wp}. Aborting navigation.")
                return

            # 마지막 웨이포인트에 도달한 경우
            if self.current_wp == self.max_wp:
                print(f"INFO: [{self.monitor_id}] Reached final WP {self.max_wp}. Checking combat spot...")

                # 전투 지점 확인 (여러 번 시도)
                spot_reached = False
                spot_check_attempts = 0
                max_spot_checks = 10

                while not spot_reached and spot_check_attempts < max_spot_checks and not stop_event.is_set():
                    if self._is_at_combat_spot(screen):
                        print(f"INFO: [{self.monitor_id}] Successfully arrived at combat spot.")
                        spot_reached = True
                        break

                    spot_check_attempts += 1
                    print(
                        f"INFO: [{self.monitor_id}] Combat spot not reached ({spot_check_attempts}/{max_spot_checks}).")

                    # 위치 조정 시도
                    if not self._perform_combat_spot_adjustment(screen):
                        print(f"WARN: [{self.monitor_id}] Failed to adjust position.")

                    if stop_event.wait(1.0):
                        return

                if not spot_reached:
                    print(
                        f"WARN: [{self.monitor_id}] Could not confirm arriving at combat spot. Navigation may be incomplete.")

                return  # 마지막 웨이포인트 처리 후 종료

            # 다음 웨이포인트로
            self.current_wp += 1

        print(f"INFO: [{self.monitor_id}] Waypoint navigation completed.")

    def _look_for_wp(self, screen: ScreenMonitorInfo, wp_index: int) -> bool:
        """웨이포인트를 찾거나 경로를 조정하는 동작을 수행합니다."""
        print(
            f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Looking for/Adjusting path to Waypoint #{wp_index}...")

        try:
            # 웨이포인트 인덱스에 따른 조정 동작 분기 (WP1, WP2 제거)
            if wp_index in [1, 2, 3]:
                # WP1,2,3: UI/시간 기반 이동이므로 추가 조정 불필요
                print(f"INFO: [{self.monitor_id}] WP{wp_index} - No adjustment needed (sequence-based movement)")
                return True

            elif wp_index == 4:  # 글라이더 이륙 지점
                # 고도 및 방향 조정 (간단한 조정, 실제 글라이더 시퀀스는 _execute_sequence에서 처리)
                keyboard.press_and_release('space')  # 점프
                time.sleep(0.2)
                keyboard.press_and_release('w')  # 약간 전진

            else:  # 알 수 없는 웨이포인트
                print(f"WARN: [{self.monitor_id}] Unknown waypoint index for adjustment: {wp_index}")
                return False

            print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Adjusted position for Waypoint #{wp_index}")
            return True

        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Exception during waypoint adjustment: {e}")
            traceback.print_exc()
            return False

    def _get_max_wp_num(self) -> int:
        """전체 웨이포인트 개수를 반환합니다."""
        print(f"INFO: [{self.monitor_id}] Getting Max Waypoint Number...")
        return 5  # 현재 고정값, 추후 설정 또는 동적 계산 가능

    def _perform_combat_spot_adjustment(self, screen: ScreenMonitorInfo) -> bool:
        """최종 전투 지점 도착을 위한 위치 조정 동작을 수행합니다."""
        print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Adjusting position to reach Combat Spot...")

        try:
            # 1. 먼저 현재 위치가 대략적으로 전투 지점 근처인지 확인
            near_combat_spot = False

            # Combat_spot_near 템플릿 사용 (템플릿 경로가 정의되어 있다면)
            template_path = template_paths.get_template(screen.screen_id, 'COMBAT_SPOT_NEAR')
            if template_path and os.path.exists(template_path):
                screenshot = self.orchestrator.capture_screen_safely(screen.screen_id)
                near_combat_spot = image_utils.is_image_present(
                    template_path=template_path,
                    region=screen.region,
                    threshold=self.confidence,
                    screenshot_img=screenshot
                )
            # 2. 대략적인 위치 조정 (필요시)
            if not near_combat_spot:
                print(
                    f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Not near combat spot yet. Doing major adjustment...")

                # 주요 조정 (방향키로 위치 이동)
                keyboard.press_and_release('w')  # 앞으로 이동
                time.sleep(1.0)
                # 시야 회전
                keyboard.press_and_release('d')  # 오른쪽으로 회전
                time.sleep(0.5)
                keyboard.press_and_release('w')  # 다시 앞으로 이동
                time.sleep(0.5)

            # 3. 미세 조정 (항상 수행)
            print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Fine-tuning position...")

            # 현재 위치 기준으로 전투 위치 미세 조정 패턴
            # (실제 구현 시 필요에 따라 세밀한 조정 로직 추가)
            keyboard.press_and_release('a')  # 왼쪽으로 약간 회전
            time.sleep(0.2)
            keyboard.press_and_release('w')  # 약간 앞으로 이동
            time.sleep(0.1)
            keyboard.press_and_release('s')  # 약간 뒤로 이동 (원위치)
            time.sleep(0.1)
            keyboard.press_and_release('d')  # 오른쪽으로 약간 회전 (원위치)

            # 최종 위치 확인
            time.sleep(0.5)  # 조정 후 화면 안정화 대기

            print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Combat spot adjustment completed")
            return True

        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Exception during combat spot adjustment: {e}")
            traceback.print_exc()
            return False

    # === 메인 모니터링 루프 ===
    def run_loop(self, stop_event: threading.Event):
        """Orchestrator가 제어하는 메인 모니터링 루프."""
        print(f"INFO: Starting CombatMonitor {self.monitor_id} on {self.vd_name}...")
        if not self.screens:
            print(f"ERROR: [{self.monitor_id}] No screens added. Stopping monitor.")
            return

        # stop_event 저장
        self.stop_event = stop_event

        # 초기화
        self.death_count = 0
        try:
            self.max_wp = self._get_max_wp_num()
        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Error getting max waypoint number: {e}. Setting to 0.")
            self.max_wp = 0

        # 시작 위치 결정
        if not self._determine_initial_location(stop_event):
            print(f"INFO: [{self.monitor_id}] CombatMonitor stopped during initial location check.")
            return
        print(f"INFO: [{self.monitor_id}] Initial monitoring context: {self.location_flag.name}")

        # 각 화면의 상태를 NORMAL로 초기화
        for screen in self.screens:
            screen.current_state = ScreenState.NORMAL
            screen.last_state_change_time = time.time()
            screen.retry_count = 0

        # 메인 루프 시작
        while not stop_event.is_set():
            try:
                # 1. HOSTILE 상태 화면들 먼저 처리 (최우선)
                hostile_screens = [s for s in self.screens if s.current_state == ScreenState.HOSTILE]
                for screen in hostile_screens:
                    if stop_event.is_set(): break
                    self._handle_screen_state(screen, stop_event)

                # 2. 나머지 화면들 처리
                other_screens = [s for s in self.screens if s.current_state != ScreenState.HOSTILE]
                for screen in other_screens:
                    if stop_event.is_set(): break
                    self._handle_screen_state(screen, stop_event)

                # 루프 주기 조절
                if stop_event.wait(1.0): break  # 1초 대기하며 종료 신호 확인

            except Exception as e:
                # 메인 루프 내 예상치 못한 오류 처리
                print(f"ERROR: [{self.monitor_id}] Unhandled exception in main loop: {e}")
                traceback.print_exc()
                if stop_event.wait(5.0):  # 오류 발생 시 5초 대기하며 종료 신호 확인
                    break  # 종료 신호 받으면 루프 탈출

        # 루프 종료 시 stop 메서드 호출
        self.stop()

    def stop(self):
        """모니터를 중지하고 필요한 정리 작업을 수행합니다."""
        print(f"INFO: CombatMonitor {self.monitor_id} received stop signal. Cleaning up...")
        super().stop() # BaseMonitor의 stop 호출 (필요시)
        # 필요한 경우 추가적인 리소스 해제 로직

# === 독립 실행 테스트용 코드 ===
if __name__ == "__main__":
    print("INFO: Running CombatMonitor in standalone test mode...")
    print("INFO: 시작 대기중... 10초 후에 모니터링이 시작됩니다.")

    # 가상 데스크톱 전환을 위한 시작 전 딜레이 추가
    start_delay = 10  # 10초 딜레이
    for i in range(start_delay, 0, -1):
        print(f"INFO: {i}초 후 시작...")
        time.sleep(1)

    print("INFO: 모니터링을 시작합니다!")
    stop_event = threading.Event()

    # 1. 모니터 인스턴스 생성
    monitor_config = {'confidence': 0.85}
    monitor = CombatMonitor(monitor_id="SRM1_Test", config=monitor_config, vd_name="TestVD")

    # 2. 화면 정보 로드 및 추가 (Orchestrator 역할 시뮬레이션)
    try:
        # utils.screen_info 모듈 임포트를 위한 경로 설정 (환경에 따라 조정 필요)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        utils_dir = os.path.join(os.path.dirname(os.path.dirname(current_dir)), 'NightCrows', 'utils')
        if utils_dir not in sys.path:
             sys.path.insert(0, utils_dir)

        from screen_info import SCREEN_REGIONS # NightCrows/utils/screen_info.py

        if SCREEN_REGIONS and isinstance(SCREEN_REGIONS, dict):
            for screen_id in ['S1', 'S2', 'S3', 'S4', 'S5']:
                 if screen_id in SCREEN_REGIONS:
                     monitor.add_screen(screen_id=screen_id, region=SCREEN_REGIONS[screen_id])
                 else:
                     print(f"WARN: Screen ID '{screen_id}' not found in SCREEN_REGIONS.")
        else:
            print("ERROR: Could not load or invalid SCREEN_REGIONS from screen_info.py")
            sys.exit(1)
    except ImportError:
        print("ERROR: Could not import SCREEN_REGIONS from NightCrows/utils/screen_info.py.")
        print(f"Current sys.path: {sys.path}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Error loading screen info: {e}")
        sys.exit(1)

    if not monitor.screens:
         print("ERROR: No screens were added to the monitor. Exiting test.")
         sys.exit(1)

    # 3. 모니터 스레드 시작
    print(f"INFO: Starting monitor thread for {len(monitor.screens)} screens...")
    monitor_thread = threading.Thread(target=monitor.run_loop, args=(stop_event,), daemon=True)
    monitor_thread.start()

    # 4. 테스트 실행 및 종료 처리
    try:
        test_duration = 240 # 테스트 실행 시간 (초)
        print(f"INFO: Monitor running for {test_duration} seconds... Press Ctrl+C to stop early.")
        start_time = time.time()
        # 메인 스레드는 모니터 스레드가 끝나거나 시간이 다 되거나 Ctrl+C 입력 전까지 대기
        while monitor_thread.is_alive() and time.time() - start_time < test_duration:
            # KeyboardInterrupt 를 잡기 위해 짧게 sleep
            time.sleep(0.5)

        if monitor_thread.is_alive():
             print(f"\nINFO: Standalone test duration ({test_duration}s) elapsed.")
        else:
             print("\nINFO: Monitor thread finished early.")

    except KeyboardInterrupt:
        print("\nINFO: Ctrl+C detected. Stopping monitor...")
    finally:
        # 모니터 스레드 종료 신호 및 대기
        if monitor_thread.is_alive():
            print("INFO: Signaling monitor thread to stop...")
            stop_event.set()
            monitor_thread.join(timeout=10) # 최대 10초 대기
            if monitor_thread.is_alive():
                print("WARN: Monitor thread did not stop gracefully.")
        print("INFO: Standalone test finished.")


# **주요 TODO 사항:**
# - 웨이포인트 관련 함수들 구현 필요 (_move_to_wp, _check_reached_wp 등)
# - screen_info.py의 FIXED_UI_COORDS 실제 좌표값 측정 필요
# - S2-S5 템플릿 경로 추가 필요 (template_paths.py)