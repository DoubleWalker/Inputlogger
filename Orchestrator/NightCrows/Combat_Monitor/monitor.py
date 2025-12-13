# Orchestrator/NightCrows/Combat_Monitor/monitor.py
# 전체 리팩토링 버전 - 기능 동일, 가독성 및 유지보수성 개선

import pyautogui
import pytweening
import traceback
import cv2
import time
import threading
import os
import keyboard
import win32api
import win32con
import sys
import numpy as np
from dataclasses import dataclass, field
from typing import Tuple, List, Dict, Optional, Callable, Any
from Orchestrator.NightCrows.utils import image_utils
from Orchestrator.NightCrows.utils.screen_info import FIXED_UI_COORDS
from Orchestrator.src.core.io_scheduler import IOScheduler, Priority
from .config import srm_config, template_paths
from .config.srm_config import ScreenState
from enum import Enum, auto
from Orchestrator.NightCrows.System_Monitor.config.sm_config import SystemState


# ============================================================================
# Constants
# ============================================================================
class Location(Enum):
    """캐릭터의 주요 위치"""
    ARENA = auto()
    FIELD = auto()
    UNKNOWN = auto()


class CharacterState(Enum):
    """캐릭터의 주요 상태"""
    NORMAL = auto()
    HOSTILE_ENGAGE = auto()
    DEAD = auto()


# ============================================================================
# Data Classes
# ============================================================================
@dataclass
class ScreenMonitorInfo:
    """모니터링할 개별 화면의 정보"""
    screen_id: str
    region: Tuple[int, int, int, int]


    # [신규] 공유 상태 딕셔너리 참조
    _shared_state_ref: Dict[str, Any] = field(default_factory=dict, repr=False)

    retry_count: int = 0
    last_state_change_time: float = 0.0
    s1_completed: bool = False
    policy_step: int = 0
    policy_step_start_time: float = 0.0
    party_check_count: int = 0

    # [신규] 프로퍼티 정의
    @property
    def current_state(self):
        return self._shared_state_ref.get(self.screen_id, ScreenState.NORMAL)

    @current_state.setter
    def current_state(self, new_state):
        self._shared_state_ref[self.screen_id] = new_state


class BaseMonitor:
    """오케스트레이터와 호환되는 모니터의 기본 클래스"""

    def __init__(self, monitor_id="SRM1", config=None, vd_name="VD1",
                 orchestrator=None, io_scheduler=None, shared_states=None):  # <--- [추가]
        super().__init__()
        if io_scheduler is None:
            raise ValueError(f"[{self.monitor_id}] io_scheduler must be provided!")

        self.io_scheduler = io_scheduler
        self.orchestrator = orchestrator
        self.monitor_id = monitor_id
        self.config = config if isinstance(config, dict) else {}
        self.vd_name = vd_name
        self.shared_states = shared_states if shared_states is not None else {}

    def run_loop(self, stop_event: threading.Event):
        raise NotImplementedError("Subclasses should implement this method.")

    def stop(self):
        print(f"INFO: Stopping BaseMonitor for {self.monitor_id}")


# ============================================================================
# Combat Monitor
# ============================================================================
class CombatMonitor(BaseMonitor):
    """
    여러 NightCrows 화면의 캐릭터 상태를 모니터링하고 자동 대응합니다.
    """

    # Constants
    MAX_RETRIES_LEADER = 5
    MAX_RETRIES_FOLLOWER = 10
    TIMEOUT_LEADER_GATHERING = 40.0
    TIMEOUT_FOLLOWER_RETURN = 30.0
    HOSTILE_SAMPLE_COUNT = 3
    HOSTILE_SAMPLE_INTERVAL = 0.1
    PARTY_CHECK_THRESHOLD = 3
    SAFE_STATES = [ScreenState.NORMAL, ScreenState.RETURNING, ScreenState.INITIALIZING]

    def __init__(self, monitor_id="SRM1", config=None, vd_name="VD1",
                 orchestrator=None, io_scheduler=None, shared_states=None):

        # 🔴 [수정] 부모 클래스(BaseMonitor)에 io_scheduler와 shared_states까지 전달하도록 수정
        super().__init__(monitor_id, config, vd_name, orchestrator, io_scheduler, shared_states)

        if io_scheduler is None:
            raise ValueError(f"[{self.monitor_id}] io_scheduler must be provided!")

        self.io_scheduler = io_scheduler
        self.location_flag: Location = Location.UNKNOWN
        self.death_count: int = 0
        self.current_wp: int = 0
        self.max_wp: int = 0
        self.stop_event = None
        self.screens: List[ScreenMonitorInfo] = []
        self.confidence = self.config.get('confidence', 0.85)

        # 템플릿 경로 초기화
        self.arena_template_path = getattr(template_paths, 'ARENA_TEMPLATE', None)
        self.dead_template_path = getattr(template_paths, 'DEAD_TEMPLATE', None)
        self.hostile_template_path = getattr(template_paths, 'HOSTILE_TEMPLATE', None)

        # 정책 핸들러 매핑 (타입 힌트 추가)
        self.policy_handlers: Dict[str, Callable[[ScreenMonitorInfo, dict], None]] = {
            'click': self._handle_click_operation,
            'key_press': self._handle_keypress_operation,
            'key_hold': self._handle_key_hold_operation,
            'wait_duration': self._handle_wait_duration,
            'wait': self._handle_wait_template,
            'execute_subroutine': self._handle_subroutine,
            'set_focus': self._handle_set_focus,
            'click_relative': self._handle_click_relative_operation,
            'key_press_raw': self._handle_key_press_raw_operation,
            'click_xy_operation': self._handle_click_xy_operation,
            'mouse_drag': self._handle_mouse_drag_operation,
            'mouse_scroll': self._handle_mouse_scroll_operation
        }

        self._verify_templates()

    # ========================================================================
    # Initialization & Setup
    # ========================================================================

    def _verify_templates(self):
        """필수 템플릿 검증"""
        if not all([self.arena_template_path, self.dead_template_path, self.hostile_template_path]):
            print(f"WARNING: [{self.monitor_id}] Essential templates missing in config.")

        print(f"INFO: [{self.monitor_id}] Verifying ALL registered template paths...")
        if not template_paths.verify_template_paths():
            print(f"ERROR: [{self.monitor_id}] Critical templates are missing.")
        else:
            print(f"INFO: [{self.monitor_id}] All registered template paths are valid.")

    def add_screen(self, screen_id: str, region: Tuple[int, int, int, int]):
        """모니터링할 화면 영역 등록"""
        if not isinstance(screen_id, str) or not screen_id:
            print(f"ERROR: [{self.monitor_id}] Invalid screen_id '{screen_id}'. Skipping.")
            return

        if not isinstance(region, tuple) or len(region) != 4:
            print(f"ERROR: [{self.monitor_id}] Invalid region for '{screen_id}'. Skipping.")
            return

        if any(s.screen_id == screen_id for s in self.screens):
            print(f"WARNING: [{self.monitor_id}] Screen '{screen_id}' already added. Skipping.")
            return

        screen = ScreenMonitorInfo(
            screen_id=screen_id,
            region=region,
            _shared_state_ref=self.shared_states  # <--- 전달
        )
        self.screens.append(screen)
        print(f"INFO: [{self.monitor_id}] Screen added: ID={screen_id}, Region={region}")

    # ========================================================================
    # Public API (Orchestrator 호출용)
    # ========================================================================

    def get_current_state(self, screen_id: str) -> Optional[ScreenState]:
        """화면의 현재 상태 조회 (Orchestrator용)"""
        screen = self._find_screen(screen_id)
        if not screen:
            print(f"WARN: [{self.monitor_id}] get_current_state: Screen {screen_id} not found.")
            return None
        return screen.current_state

    def force_reset_screen(self, screen_id: str):
        """화면 강제 리셋 (Orchestrator용)"""
        screen = self._find_screen(screen_id)
        if not screen:
            print(f"WARN: [{self.monitor_id}] force_reset_screen: Screen {screen_id} not found.")
            return

        print(f"INFO: [{self.monitor_id}] Screen {screen_id} forcibly reset by Orchestrator.")
        screen.policy_step = 0
        screen.policy_step_start_time = 0.0
        screen.retry_count = 0
        screen.s1_completed = False
        screen.party_check_count = 0
        self._change_state(screen, ScreenState.NORMAL)

    # ========================================================================
    # Template & Image Utilities
    # ========================================================================

    def _load_template(self, template_path: Optional[str]) -> Optional[cv2.typing.MatLike]:
        """템플릿 이미지 로드"""
        if not template_path or not isinstance(template_path, str):
            return None

        if not os.path.exists(template_path):
            print(f"ERROR: [{self.monitor_id}] Template not found: {template_path}")
            return None

        try:
            template = cv2.imread(template_path)
            if template is None:
                print(f"ERROR: [{self.monitor_id}] Failed to load template: {template_path}")
            return template
        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Exception loading template: {e}")
            return None

    def _get_template(self, screen: ScreenMonitorInfo, key: str,
                      fallback_attr: Optional[str] = None) -> Optional[cv2.typing.MatLike]:
        """템플릿 경로 조회 및 로드 통합"""
        path = template_paths.get_template(screen.screen_id, key)
        if not path and fallback_attr:
            path = getattr(template_paths, fallback_attr, None)
        return self._load_template(path) if path else None

    def _check_template_present(self, screen: ScreenMonitorInfo, template_key: str) -> bool:
        """템플릿 존재 여부 확인"""
        template_path = template_paths.get_template(screen.screen_id, template_key)
        if not template_path:
            template_path = getattr(template_paths, template_key, None)

        if not template_path or not os.path.exists(template_path):
            print(f"WARN: [{self.monitor_id}] Template not found for key '{template_key}'")
            return False

        screenshot = self.orchestrator.capture_screen_safely(screen.screen_id)
        if screenshot is None:
            return False

        return image_utils.is_image_present(template_path, screen.region,
                                            self.confidence, screenshot)

    # ========================================================================
    # Character State Detection
    # ========================================================================

    def _get_character_state_on_screen(self, screen: ScreenMonitorInfo) -> CharacterState:
        """화면의 캐릭터 상태 확인"""
        if not screen or not screen.region:
            print(f"ERROR: [{self.monitor_id}] Invalid screen for state check.")
            return CharacterState.NORMAL

        screenshot = self._capture_screenshot_safe(screen)
        if screenshot is None:
            return CharacterState.NORMAL

        try:
            # DEAD 체크
            if self._check_dead_state(screen, screenshot):
                return CharacterState.DEAD

            # HOSTILE 체크 (연속 샘플링)
            if self._check_hostile_state(screen):
                return CharacterState.HOSTILE_ENGAGE

            return CharacterState.NORMAL

        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] State check error (Screen: {screen.screen_id}): {e}")
            traceback.print_exc()
            return CharacterState.NORMAL

    def _capture_screenshot_safe(self, screen: ScreenMonitorInfo) -> Optional[np.ndarray]:
        """안전한 스크린샷 캡처"""
        try:
            screenshot = self.orchestrator.capture_screen_safely(screen.screen_id)
            if screenshot is None:
                print(f"ERROR: [{self.monitor_id}] Screenshot failed (Screen: {screen.screen_id}).")
            return screenshot
        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Screenshot exception (Screen: {screen.screen_id}): {e}")
            return None

    def _check_dead_state(self, screen: ScreenMonitorInfo, screenshot: np.ndarray) -> bool:
        """사망 상태 확인"""
        dead_template = self._get_template(screen, 'DEAD', 'dead_template_path')
        if dead_template is None:
            return False
        return image_utils.compare_images(screenshot, dead_template, threshold=self.confidence)

    def _check_hostile_state(self, screen: ScreenMonitorInfo) -> bool:
        """적대 상태 확인 (연속 샘플링)"""
        hostile_template_path = (template_paths.get_template(screen.screen_id, 'HOSTILE')
                                 or self.hostile_template_path)

        if not hostile_template_path:
            return False

        hostile_template = self._load_template(hostile_template_path)
        if hostile_template is None:
            return False

        for sample_idx in range(self.HOSTILE_SAMPLE_COUNT):
            try:
                screenshot = self._capture_screenshot_safe(screen)
                if screenshot is None:
                    continue

                if image_utils.compare_images(screenshot, hostile_template,
                                              threshold=self.confidence):
                    print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: "
                          f"HOSTILE detected on sample {sample_idx + 1}/{self.HOSTILE_SAMPLE_COUNT}")
                    return True

            except Exception as e:
                print(f"ERROR: [{self.monitor_id}] HOSTILE sampling error {sample_idx + 1}: {e}")

            if sample_idx < self.HOSTILE_SAMPLE_COUNT - 1:
                time.sleep(self.HOSTILE_SAMPLE_INTERVAL)

        return False

    def _is_character_in_arena(self, screen: ScreenMonitorInfo) -> bool:
        """아레나 내부 확인"""
        if not screen or not screen.region:
            print(f"ERROR: [{self.monitor_id}] Invalid screen for arena check.")
            return False

        arena_template = self._get_template(screen, 'ARENA', 'arena_template_path')
        if arena_template is None:
            return False

        try:
            screenshot = self._capture_screenshot_safe(screen)
            if screenshot is None:
                return False
            return image_utils.compare_images(screenshot, arena_template,
                                              threshold=self.confidence)
        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Arena check exception: {e}")
            return False

    # ========================================================================
    # State Management
    # ========================================================================

    def _change_state(self, screen: ScreenMonitorInfo, new_state: ScreenState):
        """화면 상태 변경 및 S1 긴급 귀환 처리"""
        if screen.current_state == new_state:
            return

        old_state = screen.current_state
        screen.current_state = new_state
        screen.last_state_change_time = time.time()
        screen.retry_count = 0

        # S1 긴급 귀환 로직
        if (new_state == ScreenState.HOSTILE and
                screen.screen_id != 'S1' and
                self.location_flag == Location.FIELD):
            self._handle_s1_emergency_return()

        if old_state != new_state:
            print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: "
                  f"State changed: {old_state.name} -> {new_state.name}")

    def _handle_s1_emergency_return(self):
        """S1 긴급 귀환 처리 (FIELD 컨텍스트)"""
        s1_screen = self._find_screen('S1')
        if not s1_screen or s1_screen.current_state not in self.SAFE_STATES:
            return

        print(f"INFO: [{self.monitor_id}] S1 emergency return triggered (FIELD context).")

        is_sleeping = self._check_s1_sleeping_state(s1_screen)
        target_state = (ScreenState.S1_EMERGENCY_FLEE if is_sleeping
                        else ScreenState.HOSTILE)

        self._change_state(s1_screen, target_state)

    def _check_s1_sleeping_state(self, s1_screen: ScreenMonitorInfo) -> bool:
        """S1 절전 상태 확인"""
        sleep_template_path = template_paths.get_template(s1_screen.screen_id, 'SLEEP')

        if not sleep_template_path or not os.path.exists(sleep_template_path):
            print(f"WARN: [{self.monitor_id}] 'SLEEP' template not defined for S1. Assuming AWAKE.")
            return False

        try:
            screenshot = self._capture_screenshot_safe(s1_screen)
            sleep_template = self._load_template(sleep_template_path)

            if screenshot is not None and sleep_template is not None:
                if image_utils.compare_images(screenshot, sleep_template,
                                              threshold=self.confidence):
                    print(f"INFO: [{self.monitor_id}] S1 is visually SLEEPING.")
                    return True
                print(f"INFO: [{self.monitor_id}] S1 is visually AWAKE.")
                return False

            print(f"WARN: [{self.monitor_id}] Could not verify S1 sleep state. Assuming AWAKE.")
            return False

        except Exception as e:
            print(f"WARN: [{self.monitor_id}] Error checking S1 sleep state: {e}. Assuming AWAKE.")
            return False

    def _notify_s1_completion(self):
        """S1 파티 수집 완료 알림"""
        print(f"INFO: [{self.monitor_id}] S1 party gathering completed! Notifying waiting screens...")
        for screen in self.screens:
            if screen.screen_id != 'S1' and screen.current_state == ScreenState.RETURNING:
                screen.s1_completed = True
                print(f"INFO: [{self.monitor_id}] Notified {screen.screen_id}")

    # ========================================================================
    # Policy Execution Engine
    # ========================================================================

    def _execute_policy_step(self, screen: ScreenMonitorInfo):
        """범용 정책 실행기"""
        policy = srm_config.get_state_policy(screen.current_state, screen.screen_id)
        action_type = policy.get('action_type')

        # time_based_wait 처리
        if action_type == 'time_based_wait':
            return self._handle_time_based_wait(screen, policy)

        # sequence 아니면 종료
        if action_type != 'sequence':
            return

        # INITIALIZING 특수 처리
        if not self._check_initialization_ready(screen):
            return

        # 현재 액션 가져오기
        actions = policy.get('sequence_config', {}).get('actions', [])
        if screen.policy_step >= len(actions):
            return self._complete_sequence(screen, policy)

        current_action = actions[screen.policy_step]

        # Context 체크
        if not self._check_context_match(current_action):
            self._skip_to_next_step(screen)
            return

        # Operation 실행
        self._execute_operation(screen, current_action)

    def _handle_time_based_wait(self, screen: ScreenMonitorInfo, policy: dict):
        """시간 기반 대기 처리"""
        expected_duration = policy.get('expected_duration', 10.0)
        elapsed = time.time() - screen.last_state_change_time

        if elapsed >= expected_duration:
            print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: "
                  f"'{screen.current_state.name}' duration ({expected_duration}s) complete.")

            next_state_key = policy.get('transitions', {}).get('duration_complete', 'NORMAL')
            next_state = (next_state_key if isinstance(next_state_key, ScreenState)
                          else ScreenState.NORMAL)
            self._change_state(screen, next_state)

    def _check_initialization_ready(self, screen: ScreenMonitorInfo) -> bool:
        """INITIALIZING 상태 대기 로직 (S2-S5)"""
        # 1. 이미 초기화가 끝났으면 통과
        if screen.current_state != ScreenState.INITIALIZING:
            return True

        # 2. S1(리더)은 스스로 판단하고 진행
        if screen.screen_id == 'S1':
            return True

        # 3. 위치 정보가 이미 확보되었다면 통과
        if self.location_flag != Location.UNKNOWN:
            print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: "
                  f"Location confirmed ({self.location_flag.name}). Moving to NORMAL.")
            self._change_state(screen, ScreenState.NORMAL)
            screen.policy_step = 0
            return False  # 이번 틱 종료, 다음 틱부터 NORMAL 로직 수행

        # ---------------------------------------------------------
        # [스마트 판단] S1 상태를 보고 대기 여부 결정
        # ---------------------------------------------------------
        s1_screen = self._find_screen('S1')

        # S1이 아직 등록되지 않았으면 기다림
        if not s1_screen:
            print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Waiting for S1 to register...")
            return False

        # ✅ [핵심 수정] S1이 정상이 아닌 경우 (SM이 작업 중이거나, 위험 상태)
        # 공유 메모리 덕분에 S1의 상태가 SystemState인지 바로 알 수 있음
        is_s1_busy_with_system = isinstance(s1_screen.current_state, SystemState)

        # S1이 SRM 차원에서 위험한 상태 (죽음, 적대 등)
        unsafe_states = [ScreenState.DEAD, ScreenState.HOSTILE, ScreenState.S1_EMERGENCY_FLEE]
        is_s1_unsafe = s1_screen.current_state in unsafe_states

        # S1이 제정신이 아니라면(시스템 복구 중이거나 위험함), 우린 걍 각자도생(NORMAL) 한다.
        if is_s1_busy_with_system or is_s1_unsafe:
            print(f"WARN: [{self.monitor_id}] S1 is unavailable ({s1_screen.current_state}). "
                  f"Forcing {screen.screen_id} to NORMAL (Break Dependency).")
            self._change_state(screen, ScreenState.NORMAL)
            screen.policy_step = 0
            return False

        # ---------------------------------------------------------
        # S1도 INITIALIZING 중이라면 타임아웃 체크 (너무 오래 걸리면 포기)
        if s1_screen.current_state == ScreenState.INITIALIZING:
            elapsed = time.time() - s1_screen.last_state_change_time  # [이전 수정 반영]

            if elapsed > 60.0:
                print(f"WARN: [{self.monitor_id}] S1 initialization timed out ({elapsed:.0f}s). "
                      f"Forcing {screen.screen_id} to NORMAL.")
                self._change_state(screen, ScreenState.NORMAL)
                screen.policy_step = 0
                return False

        print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: "
              f"Waiting for S1 to determine location...")
        return False

    def _complete_sequence(self, screen: ScreenMonitorInfo, policy: dict):
        """시퀀스 완료 처리"""
        print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: "
              f"Sequence '{screen.current_state.name}' completed.")

        # S1 INITIALIZING 성공 시 ARENA 설정
        if screen.current_state == ScreenState.INITIALIZING and screen.screen_id == 'S1':
            self.location_flag = Location.ARENA
            print(f"INFO: [{self.monitor_id}] Initial Location (S1 Success): "
                  f"{self.location_flag.name}")

        next_state_key = policy.get('transitions', {}).get('sequence_complete', 'NORMAL')
        next_state = (next_state_key if isinstance(next_state_key, ScreenState)
                      else ScreenState.NORMAL)

        self._change_state(screen, next_state)
        screen.policy_step = 0
        screen.policy_step_start_time = 0.0

    def _check_context_match(self, action: dict) -> bool:
        """액션의 context 요구사항 확인"""
        required_context_str = action.get('context')
        if not required_context_str:
            return True

        required_context = getattr(Location, required_context_str, Location.UNKNOWN)
        if self.location_flag != required_context:
            print(f"INFO: [{self.monitor_id}] Action skipped "
                  f"(Context mismatch: {self.location_flag.name} != {required_context_str})")
            return False

        return True

    def _skip_to_next_step(self, screen: ScreenMonitorInfo):
        """다음 스텝으로 건너뛰기"""
        screen.policy_step += 1
        screen.policy_step_start_time = time.time()

    def _execute_operation(self, screen: ScreenMonitorInfo, action: dict):
        """액션의 operation 실행"""
        operation = action.get('operation')
        handler = self.policy_handlers.get(operation)

        if handler:
            handler(screen, action)
        else:
            print(f"WARN: [{self.monitor_id}] Unknown operation '{operation}'")

    # ========================================================================
    # Policy Operation Handlers
    # ========================================================================
    def _handle_key_press_raw_operation(self, screen: ScreenMonitorInfo, action: dict):
        """key_press_raw operation 처리 (press 또는 release만)"""
        self.io_scheduler.request(
            component=self.monitor_id,
            screen_id=screen.screen_id,
            action=lambda: self._do_key_press_raw_action(screen, action),
            priority=Priority.NORMAL
        )
        self._advance_step(screen, action.get('operation'))

    def _handle_mouse_drag_operation(self, screen: ScreenMonitorInfo, action: dict):
        """mouse_drag operation 처리"""
        self.io_scheduler.request(
            component=self.monitor_id,
            screen_id=screen.screen_id,
            action=lambda: self._do_mouse_drag_action(screen, action),
            priority=Priority.NORMAL
        )
        self._advance_step(screen, action.get('operation'))

    def _handle_mouse_scroll_operation(self, screen: ScreenMonitorInfo, action: dict):
        """mouse_scroll operation 처리 핸들러"""
        self.io_scheduler.request(
            component=self.monitor_id,
            screen_id=screen.screen_id,
            action=lambda: self._do_mouse_scroll_action(screen, action),
            priority=Priority.NORMAL
        )
        self._advance_step(screen, action.get('operation'))

    def _handle_key_hold_operation(self, screen: ScreenMonitorInfo, action: dict):
        """key_hold operation 처리"""
        self.io_scheduler.request(
            component=self.monitor_id,
            screen_id=screen.screen_id,
            action=lambda: self._do_key_hold_action(screen, action),
            priority=Priority.NORMAL
        )
        self._advance_step(screen, action.get('operation'))

    def _handle_click_operation(self, screen: ScreenMonitorInfo, action: dict):
        """click operation 처리"""
        self.io_scheduler.request(
            component=self.monitor_id,
            screen_id=screen.screen_id,
            action=lambda: self._do_click_action(screen, action),
            priority=Priority.NORMAL
        )
        self._advance_step(screen, action.get('operation'))

    def _handle_keypress_operation(self, screen: ScreenMonitorInfo, action: dict):
        """key_press operation 처리"""
        self.io_scheduler.request(
            component=self.monitor_id,
            screen_id=screen.screen_id,
            action=lambda: self._do_keypress_action(screen, action),
            priority=Priority.NORMAL
        )
        self._advance_step(screen, action.get('operation'))

    def _handle_set_focus(self, screen: ScreenMonitorInfo, action: dict):
        """set_focus operation 처리"""
        self.io_scheduler.request(
            component=self.monitor_id,
            screen_id=screen.screen_id,
            action=lambda: self._do_set_focus(screen),
            priority=Priority.NORMAL
        )
        self._advance_step(screen, action.get('operation'))

    def _handle_click_relative_operation(self, screen: ScreenMonitorInfo, action: dict):
        """click_relative operation 처리"""
        self.io_scheduler.request(
            component=self.monitor_id,
            screen_id=screen.screen_id,
            action=lambda: self._do_click_relative_action(screen, action),
            priority=Priority.NORMAL
        )
        self._advance_step(screen, action.get('operation'))


    def _handle_subroutine(self, screen: ScreenMonitorInfo, action: dict):
            """execute_subroutine operation 처리"""
            subroutine_name = action.get('name')

            if subroutine_name == '_do_flight':
                # (기존 코드 유지)
                self.io_scheduler.request(
                    component=self.monitor_id,
                    screen_id=screen.screen_id,
                    action=lambda: self._do_flight(screen),
                    priority=Priority.NORMAL
                )
                self._advance_step(screen, action.get('operation'))

            elif subroutine_name == '_do_wp3_movement':
                # ★ [신규] WP3 이동 시퀀스 처리 (CRITICAL 우선순위)
                print(f"INFO: [{self.monitor_id}] Requesting Atomic WP3 Macro for {screen.screen_id}")
                self.io_scheduler.request(
                    component=self.monitor_id,
                    screen_id=screen.screen_id,
                    action=lambda: self._do_wp3_movement(screen),
                    priority=Priority.URGENT  # ★ 절대 방해받지 않음
                )
                self._advance_step(screen, action.get('operation'))

            else:
                print(f"ERROR: [{self.monitor_id}] Unknown subroutine '{subroutine_name}'")

        # [신규 메서드 추가] _do_wp3_movement
    def _do_wp3_movement(self, screen: ScreenMonitorInfo):
            """
            WP3 시퀀스를 원자적(Atomic)으로 실행하는 매크로 함수.
            스케줄러 안에서 실행되므로, 이 함수가 끝날 때까지 다른 IO는 차단됨.
            """
            from .config.srm_config_wp_sequences import get_wp_sequence

            # 1. 시퀀스 데이터 로드
            sequence = get_wp_sequence(screen.screen_id, 'wp3', 'ARENA')
            if not sequence:
                print(f"WARN: [{self.monitor_id}] No WP3 sequence found for {screen.screen_id}")
                return

            print(
                f"INFO: [{self.monitor_id}] Starting Atomic WP3 Sequence ({len(sequence)} ops) for {screen.screen_id}")

            try:
                # 2. 포커스 확보 (필수)

                # 3. 시퀀스 순차 실행 (tester.py와 동일한 방식)
                for i, op in enumerate(sequence):
                    op_type = op.get('operation')

                    # 각 동작을 _do_... 메서드에 직접 위임 (스케줄러 거치지 않음!)
                    if op_type == 'mouse_drag':
                        self._do_mouse_drag_action(screen, op)
                    elif op_type == 'key_press_raw':
                        self._do_key_press_raw_action(screen, op)
                    elif op_type == 'key_hold':
                        self._do_key_hold_action(screen, op)
                    elif op_type == 'click_relative':
                        self._do_click_relative_action(screen, op)
                    elif op_type == 'key_press':
                        self._do_keypress_action(screen, op)
                    elif op_type == 'wait_duration':
                        # wait_duration은 _do 메서드가 없으므로 직접 처리
                        time.sleep(op.get('duration', 0.1))

                    # 디버깅용 (필요시 주석 해제)
                    # print(f"   [{i+1}/{len(sequence)}] {op_type} done.")

                print(f"INFO: [{self.monitor_id}] Atomic WP3 Sequence Completed.")

            except Exception as e:
                print(f"ERROR: [{self.monitor_id}] WP3 Sequence Failed: {e}")
                traceback.print_exc()

    def _handle_wait_duration(self, screen: ScreenMonitorInfo, action: dict):
        """wait_duration operation 처리"""
        if screen.policy_step_start_time == 0.0 and action.get('initial') == True:
            screen.policy_step_start_time = time.time()

        elapsed = time.time() - screen.policy_step_start_time
        duration = action.get('duration', 5.0)

        if elapsed >= duration:
            print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: "
                  f"wait_duration {duration}s complete.")
            self._advance_step(screen, 'wait_duration')

    def _handle_wait_template(self, screen: ScreenMonitorInfo, action: dict):
        """wait (템플릿 대기) operation 처리"""
        template_key = action.get('template')

        # 🔥 step 시작 시간 초기화 확인
        if screen.policy_step_start_time == 0.0:
            screen.policy_step_start_time = time.time()

        if self._check_template_present(screen, template_key):
            print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: "
                  f"wait '{template_key}' complete.")
            self._advance_step(screen, 'wait')
            return

        # 타임아웃 체크
        step_timeout = action.get('timeout')
        if not step_timeout:
            return

        elapsed_on_step = time.time() - screen.policy_step_start_time
        if elapsed_on_step <= step_timeout:
            return

        # 타임아웃 발생
        print(f"WARN: [{self.monitor_id}] wait '{template_key}' timed out after {elapsed_on_step:.1f}s")

        on_timeout_action = action.get('on_timeout')
        if on_timeout_action == 'fail_sequence':
            self._handle_sequence_timeout(screen, action)

    def _handle_sequence_timeout(self, screen: ScreenMonitorInfo, action: dict):
        """시퀀스 타임아웃 처리"""
        # S1 INITIALIZING 타임아웃 시 FIELD 설정
        if screen.current_state == ScreenState.INITIALIZING and screen.screen_id == 'S1':
            self.location_flag = Location.FIELD
            print(f"INFO: [{self.monitor_id}] Initial Location (S1 Timeout): "
                  f"{self.location_flag.name}")

        policy = srm_config.get_state_policy(screen.current_state)
        next_state_key = policy.get('transitions', {}).get('sequence_failed', 'NORMAL')
        next_state = (next_state_key if isinstance(next_state_key, ScreenState)
                      else ScreenState.NORMAL)

        self._change_state(screen, next_state)
        screen.policy_step = 0
        screen.policy_step_start_time = 0.0

    def _handle_click_xy_operation(self, screen: ScreenMonitorInfo, action: dict):
        """click_xy operation 처리 (x, y 좌표 직접 클릭)"""
        self.io_scheduler.request(
            component=self.monitor_id,
            screen_id=screen.screen_id,
            action=lambda: self._do_click_xy_action(screen, action),
            priority=Priority.NORMAL
        )

    def _advance_step(self, screen: ScreenMonitorInfo, operation: str):
        """다음 스텝으로 진행"""
        print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: "
              f"Step {screen.policy_step} ({operation}) requested.")
        screen.policy_step += 1
        screen.policy_step_start_time = time.time()

    # ========================================================================
    # IO Actions (스케줄러가 실행)
    # ========================================================================
    def _do_key_press_raw_action(self, screen: ScreenMonitorInfo, action: dict):
        """key_press_raw 액션 실행 (press 또는 release만 수행)"""
        key = action.get('key')
        event = action.get('event')  # 'press' 또는 'release'

        if not key:
            print(f"ERROR: [{self.monitor_id}] key_press_raw operation missing 'key'")
            return

        if not event or event not in ['press', 'release']:
            print(f"ERROR: [{self.monitor_id}] key_press_raw operation missing or invalid 'event'")
            return

        if event == 'press':
            keyboard.press(key)
        else:  # release
            keyboard.release(key)

        self._apply_delay(action)

    def _do_key_hold_action(self, screen: ScreenMonitorInfo, action: dict):
        """key_hold 액션 실행 (press → duration → release)"""
        if not self._click_relative(screen, 'safe_click_point', delay_after=0.3):
            print(f"ERROR: [{self.monitor_id}] Failed to click safe_click_point for {screen.screen_id}")
            return

        key = action.get('key')
        duration = action.get('duration', 0.0)

        if not key:
            print(f"ERROR: [{self.monitor_id}] key_hold operation missing 'key'")
            return

        # Press
        keyboard.press(key)

        # Hold
        if duration > 0:
            time.sleep(duration)

        # Release
        keyboard.release(key)

        self._apply_delay(action)

    def _do_click_action(self, screen: ScreenMonitorInfo, action: dict):
        """click 액션 실행"""
        template_key = action.get('template')
        if not template_key:
            print(f"ERROR: [{self.monitor_id}] click operation missing 'template' key")
            return

        template_path = template_paths.get_template(screen.screen_id, template_key)
        if not template_path:
            template_path = getattr(template_paths, template_key, None)

        if not template_path or not os.path.exists(template_path):
            print(f"ERROR: [{self.monitor_id}] Template not found for '{template_key}'")
            return

        screenshot = self._capture_screenshot_safe(screen)
        location = image_utils.return_ui_location(template_path, screen.region,
                                                  self.confidence, screenshot)

        if location:
            pyautogui.click(location)
        else:
            print(f"WARN: [{self.monitor_id}] Failed to find template '{template_key}'")

        self._apply_delay(action)

    def _do_mouse_drag_action(self, screen: ScreenMonitorInfo, action: dict):
        """
        마우스 드래그 실행 (moveTo -> dragTo) + Tweening 적용
        """
        from_x = action.get('from_x')
        from_y = action.get('from_y')
        to_x = action.get('to_x')
        to_y = action.get('to_y')
        duration = action.get('duration', 0.5)
        button = action.get('button', 'left')

        if None in [from_x, from_y, to_x, to_y]:
            print(f"ERROR: [{self.monitor_id}] mouse_drag missing coordinates")
            return

        # 스크린 절대 좌표 계산
        region_x, region_y, _, _ = screen.region
        abs_start_x = region_x + from_x
        abs_start_y = region_y + from_y
        abs_end_x = region_x + to_x
        abs_end_y = region_y + to_y

        try:
            # 1. 시작 지점으로 이동
            pyautogui.moveTo(abs_start_x, abs_start_y)

            # 2. 드래그 실행 (Tweening 적용!)
            # tester.py에서 성공했던 그 느낌 그대로
            pyautogui.dragTo(abs_end_x, abs_end_y, duration=duration, button=button, tween=pyautogui.easeOutQuad)

        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Drag failed: {e}")

        self._apply_delay(action)

    def _do_keypress_action(self, screen: ScreenMonitorInfo, action: dict):
        """key_press 액션 실행"""
        if not self._click_relative(screen, 'safe_click_point', delay_after=0.3):
            print(f"ERROR: [{self.monitor_id}] Failed to click safe_click_point for {screen.screen_id}")
            return

        key = action.get('key')
        if key:
            keyboard.press_and_release(key)
        else:
            print(f"ERROR: [{self.monitor_id}] key_press operation missing 'key'")

        self._apply_delay(action)

    def _do_mouse_scroll_action(self, screen: ScreenMonitorInfo, action: dict):
        """실제 마우스 스크롤 실행"""
        amount = action.get('amount', 0)
        if amount == 0: return

        # 1. 화면 중앙 좌표 계산
        region_x, region_y, region_w, region_h = screen.region
        center_x = region_x + (region_w // 2)
        center_y = region_y + (region_h // 2)

        # 2. 마우스를 화면 중앙으로 이동 후 스크롤 (pyautogui 지원 기능)
        # (마우스가 엉뚱한 곳에 있으면 스크롤이 안 먹힐 수 있으므로 중앙 이동 필수)
        pyautogui.scroll(amount, x=center_x, y=center_y)

        self._apply_delay(action)

    def _do_set_focus(self, screen: ScreenMonitorInfo):
        """set_focus 액션 실행"""
        if not image_utils.set_focus(screen.screen_id, delay_after=0.5):
            print(f"ERROR: [{self.monitor_id}] Failed to set focus on {screen.screen_id}")

    def _do_click_relative_action(self, screen: ScreenMonitorInfo, action: dict):
        """click_relative 액션 실행"""
        key = action.get('key')
        if key:
            self._click_relative(screen, key, delay_after=0.0)
        else:
            print(f"ERROR: [{self.monitor_id}] click_relative operation missing 'key'")

        self._apply_delay(action)

    def _do_click_xy_action(self, screen: ScreenMonitorInfo, action: dict):
        """click_xy 액션 실행"""
        x = action.get('x')
        y = action.get('y')

        if x is None or y is None:
            print(f"ERROR: [{self.monitor_id}] click_xy operation missing 'x' or 'y'")
            return

        self._click_relative(screen, (x, y), delay_after=0.0)
        self._apply_delay(action)

    def _apply_delay(self, action: dict):
        """액션의 delay_after 적용"""
        delay = action.get('delay_after', 0)
        if delay > 0:
            time.sleep(delay)

    def _do_flight(self, screen: ScreenMonitorInfo):
        """도주 버튼 클릭 실행 (상태에 따라 깨우기 동작 분기)"""
        try:
            if screen.current_state == ScreenState.S1_EMERGENCY_FLEE:
                print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: S1 Emergency Flee. Waking up screen...")
                if not self._wake_screen(screen):
                    return

                # ✅ 개선 1: 화면 깨운 후 0.8초 대기 (UI 렌더링 완료 기다림)
                print(f"INFO: [{self.monitor_id}] Waiting for UI to render after wake-up...")
                time.sleep(0.8)
            else:
                pass

            flight_template_path = template_paths.get_template(screen.screen_id, 'FLIGHT_BUTTON')
            if not flight_template_path or not os.path.exists(flight_template_path):
                print(f"WARN: [{self.monitor_id}] Flight template not found. Using fixed coordinates...")
                self._click_relative(screen, 'flight_button', delay_after=0.2)
                return

            # ✅ 개선 2: 최대 5회(2.5초) 동안 템플릿 등장 대기
            max_wait_attempts = 5
            wait_interval = 0.5
            center_coords = None

            print(f"INFO: [{self.monitor_id}] Waiting for FLIGHT_BUTTON template to appear...")
            for attempt in range(max_wait_attempts):
                screenshot = self._capture_screenshot_safe(screen)
                if screenshot is None:
                    time.sleep(wait_interval)
                    continue

                center_coords = image_utils.return_ui_location(
                    template_path=flight_template_path,
                    region=screen.region,
                    threshold=self.confidence,
                    screenshot_img=screenshot
                )

                if center_coords:
                    print(f"INFO: [{self.monitor_id}] FLIGHT_BUTTON found on attempt {attempt + 1}/{max_wait_attempts}")
                    break

                if attempt < max_wait_attempts - 1:
                    time.sleep(wait_interval)

            if center_coords:
                pyautogui.click(center_coords)
                print(f"INFO: [{self.monitor_id}] Flight via template matching at {center_coords}.")
            else:
                print(
                    f"WARN: [{self.monitor_id}] Template matching failed after {max_wait_attempts} attempts. Using fixed coordinates...")
                if self._click_relative(screen, 'flight_button', delay_after=0.2):
                    print(f"INFO: [{self.monitor_id}] Flight via fixed coordinates.")
                    # ✅ 개선 3: 고정 좌표도 이중 클릭 (씹힘 방지)
                    time.sleep(0.2)
                    self._click_relative(screen, 'flight_button', delay_after=0.2)
                else:
                    print(f"ERROR: [{self.monitor_id}] Both template and fixed coords failed.")

        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Exception in _do_flight: {e}")
            traceback.print_exc()

    def _wake_screen(self, screen: ScreenMonitorInfo) -> bool:
        """화면 활성화 (포커스 + ESC)"""
        if not self._click_relative(screen, 'safe_click_point', delay_after=0.2):
            print(f"WARN: [{self.monitor_id}] safe_click_point failed. Clicking center.")
            try:
                region_x, region_y, region_w, region_h = screen.region
                center_x = region_x + (region_w // 2)
                center_y = region_y + (region_h // 2)
                pyautogui.click(center_x, center_y)
                time.sleep(0.1)
            except Exception as e:
                print(f"ERROR: [{self.monitor_id}] Failed to click center: {e}")
                return False

        keyboard.press_and_release('esc')
        time.sleep(0.3)
        return True

    def _click_relative(self, screen: ScreenMonitorInfo, coord_key: str,
                        delay_after: float = 0.5, random_offset: int = 2) -> bool:
        """상대 좌표 클릭 (드래그 방지용 안전 클릭 적용)"""
        if not screen or not screen.region or not hasattr(screen, 'screen_id'):
            print(f"ERROR: [{self.monitor_id}] Invalid screen for relative click.")
            return False

        screen_coords = FIXED_UI_COORDS.get(screen.screen_id)
        if not screen_coords:
            print(f"ERROR: [{self.monitor_id}] Coordinates not found for '{screen.screen_id}'.")
            return False

        relative_coord = screen_coords.get(coord_key)
        if not relative_coord or not isinstance(relative_coord, tuple) or len(relative_coord) != 2:
            print(f"ERROR: [{self.monitor_id}] Invalid coordinate '{coord_key}' for '{screen.screen_id}'.")
            return False

        region_x, region_y, _, _ = screen.region
        try:
            # 좌표 계산 (int 변환 필수)
            click_x = int(region_x + relative_coord[0])
            click_y = int(region_y + relative_coord[1])
        except ValueError:
            print(f"ERROR: [{self.monitor_id}] Invalid coordinate values for '{coord_key}'.")
            return False

        try:
            # ✅ [수정] 안전한 클릭 시퀀스 (Ghost Drag 방지)

            # 1. 좌표로 이동
            pyautogui.moveTo(click_x, click_y)

            # 2. 누르기 (Press)
            pyautogui.mouseDown()

            # 3. 확실하게 눌린 상태 유지 (OS가 인식할 시간 부여)
            time.sleep(0.1)

            # 4. 떼기 (Release)
            pyautogui.mouseUp()

            # 5. 떼고 나서도 아주 잠깐 대기 (OS가 '드래그 끝' 인식할 시간 부여)
            time.sleep(0.05)

            if delay_after > 0:
                time.sleep(delay_after)
            return True

        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Failed to click '{coord_key}': {e}")
            return False
    # ========================================================================
    # State Handlers
    # ========================================================================

    def _handle_screen_state(self, screen: ScreenMonitorInfo, stop_event: threading.Event):
        """현재 화면 상태에 따라 처리"""

        # 1. [공유 상태 읽기]
        state = screen.current_state

        # 2. [교통 정리] 내 담당 상태(ScreenState)가 아니면 무시
        if not isinstance(state, ScreenState):
            # SM이 작업 중 (SystemState) -> 무시
            return

        # 3. [정상 로직]
        if state == ScreenState.NORMAL:
            self._handle_normal_state(screen)
        elif state in [ScreenState.DEAD, ScreenState.INITIALIZING, ScreenState.RECOVERING,
                       ScreenState.HOSTILE, ScreenState.FLEEING, ScreenState.S1_EMERGENCY_FLEE,
                       ScreenState.BUYING_POTIONS, ScreenState.RESUME_COMBAT
                       ]:
            self._execute_policy_step(screen)
        elif state == ScreenState.RETURNING:
            self._handle_returning_state(screen)

    def _handle_normal_state(self, screen: ScreenMonitorInfo):
        """NORMAL 상태 처리 - 이상 감지"""
        character_state = self._get_character_state_on_screen(screen)

        if character_state == CharacterState.DEAD:
            self._change_state(screen, ScreenState.DEAD)
        elif character_state == CharacterState.HOSTILE_ENGAGE:
            self._change_state(screen, ScreenState.HOSTILE)

    def _handle_returning_state(self, screen: ScreenMonitorInfo):
        """RETURNING 상태 처리 (FIELD/ARENA 분기)"""
        if self.location_flag == Location.FIELD:
            self._handle_field_return(screen)
        elif self.location_flag == Location.ARENA:
            self._execute_policy_step(screen)

    def _handle_field_return(self, screen: ScreenMonitorInfo):
        """필드 복귀 처리 (파티 수집)"""
        elapsed = time.time() - screen.last_state_change_time

        if screen.screen_id == 'S1':
            self._handle_s1_party_gathering(screen, elapsed)
        else:
            self._handle_follower_return(screen, elapsed)

    def _handle_s1_party_gathering(self, screen: ScreenMonitorInfo, elapsed: float):
        """S1 파티 수집 처리"""
        # 파티원 확인
        if self._check_returned_well_s1(screen):
            screen.party_check_count += 1

        # 성공 조건
        if screen.party_check_count >= self.PARTY_CHECK_THRESHOLD:
            print(f"INFO: [{self.monitor_id}] S1: Party gathering completed.")
            screen.party_check_count = 0
            self._change_state(screen, ScreenState.RESUME_COMBAT)
            self._notify_s1_completion()
            return

        # 실패 조건
        if screen.retry_count >= self.MAX_RETRIES_LEADER:
            print(f"WARN: [{self.monitor_id}] S1: Max retry attempts reached.")
            screen.party_check_count = 0
            self._change_state(screen, ScreenState.RESUME_COMBAT)
            self._notify_s1_completion()
            return

        if elapsed > self.TIMEOUT_LEADER_GATHERING:
            print(f"WARN: [{self.monitor_id}] S1: Total timeout. Giving up.")
            screen.party_check_count = 0
            self._change_state(screen, ScreenState.RESUME_COMBAT)
            self._notify_s1_completion()
            return

        # 재시도
        if elapsed >= (screen.retry_count * 2.0):
            screen.retry_count += 1
            print(
                f"INFO: [{self.monitor_id}] S1: Retrying party gathering ({screen.retry_count}/{self.MAX_RETRIES_LEADER})...")
            self.io_scheduler.request(
                component=self.monitor_id,
                screen_id=screen.screen_id,
                action=lambda: self._retry_field_return(screen, is_first_attempt=(screen.retry_count == 1)),
                priority=Priority.NORMAL
            )

    def _handle_follower_return(self, screen: ScreenMonitorInfo, elapsed: float):
        """팔로워 복귀 처리"""
        # S1 완료 대기
        if not screen.s1_completed:
            print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Waiting for S1 completion...")
            return

        # S1 확인
        if self._check_returned_well_others(screen):
            screen.party_check_count += 1

        # 성공 조건
        if screen.party_check_count >= self.PARTY_CHECK_THRESHOLD:
            print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Successfully returned to party.")
            screen.party_check_count = 0
            self._change_state(screen, ScreenState.RESUME_COMBAT)
            return

        # 실패 조건
        if screen.retry_count >= self.MAX_RETRIES_FOLLOWER:
            print(f"WARN: [{self.monitor_id}] Screen {screen.screen_id}: Max retry attempts reached.")
            screen.party_check_count = 0
            self._change_state(screen, ScreenState.RESUME_COMBAT)
            return

        if elapsed > self.TIMEOUT_FOLLOWER_RETURN:
            print(f"WARN: [{self.monitor_id}] Screen {screen.screen_id}: Total timeout.")
            screen.party_check_count = 0
            self._change_state(screen, ScreenState.RESUME_COMBAT)
            return

        # 재시도
        if elapsed >= (screen.retry_count * 2.0):
            screen.retry_count += 1
            print(
                f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Retrying field return ({screen.retry_count}/{self.MAX_RETRIES_FOLLOWER})...")
            self.io_scheduler.request(
                component=self.monitor_id,
                screen_id=screen.screen_id,
                action=lambda: self._retry_field_return(screen, is_first_attempt=(screen.retry_count == 0)),
                priority=Priority.NORMAL
            )

    # ========================================================================
    # Party Check Utilities
    # ========================================================================

    def _check_single_party_template(self, screen: ScreenMonitorInfo,
                                     template_path: str, threshold: float = 0.15) -> bool:
        """단일 파티 템플릿 체크 (Non-Blocking)"""
        if not template_path or not os.path.exists(template_path):
            return False

        try:
            template = cv2.imread(template_path)
            if template is None:
                print(f"ERROR: [{self.monitor_id}] Failed to load PARTY_UI template: {template_path}")
                return False

            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            screenshot = self._capture_screenshot_safe(screen)

            if screenshot is None:
                return False

            screen_gray = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
            match_result = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_SQDIFF_NORMED)
            min_val, _, _, _ = cv2.minMaxLoc(match_result)

            if min_val < threshold:
                print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: "
                      f"Party UI found (template: {os.path.basename(template_path)}, match: {min_val:.4f})")
                return True

            return False

        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Exception in _check_single_party_template: {e}")
            return False

    def _check_returned_well_s1(self, screen: ScreenMonitorInfo) -> bool:
        """S1용: S2~S5 중 하나라도 매칭되면 True"""
        for member_id in ['S2', 'S3', 'S4', 'S5']:
            template_path = template_paths.get_template('S1', member_id)
            if template_path and self._check_single_party_template(screen, template_path):
                print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Found party member {member_id}")
                return True
        return False

    def _check_returned_well_others(self, screen: ScreenMonitorInfo) -> bool:
        """S2~S5용: S1 파티 템플릿만 체크"""
        s1_template_path = template_paths.get_template('S1', 'PARTY_UI')
        if s1_template_path and self._check_single_party_template(screen, s1_template_path):
            print(f"INFO: [{self.monitor_id}] Screen {screen.screen_id}: Found S1")
            return True
        return False

    def _retry_field_return(self, screen: ScreenMonitorInfo, is_first_attempt: bool = False) -> bool:
        """필드 복귀 재시도"""
        try:
            if not self._click_relative(screen, 'field_return_button', delay_after=0.5):
                print(f"WARN: [{self.monitor_id}] Failed to click field return button.")
                return False

            if is_first_attempt:
                time.sleep(0.3)
                keyboard.press_and_release('y')
                print(f"INFO: [{self.monitor_id}] Pressed Y key (first attempt).")

            return True

        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Field return retry failed: {e}")
            return False

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def _find_screen(self, screen_id: str) -> Optional[ScreenMonitorInfo]:
        """화면 ID로 화면 객체 찾기"""
        return next((s for s in self.screens if s.screen_id == screen_id), None)

    def _get_max_wp_num(self) -> int:
        """전체 웨이포인트 개수 반환"""
        return 5

    def win32_click(self, x, y):
        """Win32 API 클릭"""
        win32api.SetCursorPos((x, y))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)

    # ========================================================================
    # Main Loop
    # ========================================================================

    def run_loop(self, stop_event: threading.Event):
        """메인 모니터링 루프"""
        print(f"INFO: Starting CombatMonitor {self.monitor_id} on {self.vd_name}...")

        if not self.screens:
            print(f"ERROR: [{self.monitor_id}] No screens added. Stopping monitor.")
            return

        self.stop_event = stop_event
        self.death_count = 0

        try:
            self.max_wp = self._get_max_wp_num()
        except Exception as e:
            print(f"ERROR: [{self.monitor_id}] Error getting max waypoint number: {e}")
            self.max_wp = 0

        self.location_flag = Location.UNKNOWN
        print(f"INFO: [{self.monitor_id}] Initial monitoring context: UNKNOWN")

        # 초기 상태 설정
        for screen in self.screens:
            screen.current_state = ScreenState.INITIALIZING
            screen.last_state_change_time = time.time()
            screen.retry_count = 0
            screen.policy_step = 0
            screen.policy_step_start_time = 0.0

        # 메인 루프
        while not stop_event.is_set():
            try:
                # HOSTILE 우선 처리
                hostile_screens = [s for s in self.screens if s.current_state == ScreenState.HOSTILE]
                for screen in hostile_screens:
                    if stop_event.is_set():
                        break
                    self._handle_screen_state(screen, stop_event)

                # 나머지 처리
                other_screens = [s for s in self.screens if s.current_state != ScreenState.HOSTILE]
                for screen in other_screens:
                    if stop_event.is_set():
                        break
                    self._handle_screen_state(screen, stop_event)

                if stop_event.wait(1.0):
                    break

            except Exception as e:
                print(f"ERROR: [{self.monitor_id}] Unhandled exception in main loop: {e}")
                traceback.print_exc()
                if stop_event.wait(5.0):
                    break

        self.stop()

    def stop(self):
        """모니터 중지 및 정리"""
        print(f"INFO: CombatMonitor {self.monitor_id} received stop signal. Cleaning up...")
        super().stop()


# ============================================================================
# Standalone Test
# ============================================================================
if __name__ == "__main__":
    print("INFO: Running CombatMonitor in standalone test mode...")
    print("INFO: 시작 대기중... 10초 후에 모니터링이 시작됩니다.")

    start_delay = 10
    for i in range(start_delay, 0, -1):
        print(f"INFO: {i}초 후 시작...")
        time.sleep(1)

    print("INFO: 모니터링을 시작합니다!")
    stop_event = threading.Event()

    monitor_config = {'confidence': 0.85}
    monitor = CombatMonitor(monitor_id="SRM1_Test", config=monitor_config, vd_name="TestVD")

    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        utils_dir = os.path.join(os.path.dirname(os.path.dirname(current_dir)), 'NightCrows', 'utils')
        if utils_dir not in sys.path:
            sys.path.insert(0, utils_dir)

        from screen_info import SCREEN_REGIONS

        if SCREEN_REGIONS and isinstance(SCREEN_REGIONS, dict):
            for screen_id in ['S1', 'S2', 'S3', 'S4', 'S5']:
                if screen_id in SCREEN_REGIONS:
                    monitor.add_screen(screen_id=screen_id, region=SCREEN_REGIONS[screen_id])
                else:
                    print(f"WARN: Screen ID '{screen_id}' not found in SCREEN_REGIONS.")
        else:
            print("ERROR: Could not load SCREEN_REGIONS")
            sys.exit(1)

    except ImportError:
        print("ERROR: Could not import SCREEN_REGIONS")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Error loading screen info: {e}")
        sys.exit(1)

    if not monitor.screens:
        print("ERROR: No screens were added. Exiting test.")
        sys.exit(1)

    print(f"INFO: Starting monitor thread for {len(monitor.screens)} screens...")
    monitor_thread = threading.Thread(target=monitor.run_loop, args=(stop_event,), daemon=True)
    monitor_thread.start()

    try:
        test_duration = 240
        print(f"INFO: Monitor running for {test_duration} seconds... Press Ctrl+C to stop early.")
        start_time = time.time()

        while monitor_thread.is_alive() and time.time() - start_time < test_duration:
            time.sleep(0.5)

        if monitor_thread.is_alive():
            print(f"\nINFO: Standalone test duration ({test_duration}s) elapsed.")
        else:
            print("\nINFO: Monitor thread finished early.")

    except KeyboardInterrupt:
        print("\nINFO: Ctrl+C detected. Stopping monitor...")
    finally:
        if monitor_thread.is_alive():
            print("INFO: Signaling monitor thread to stop...")
            stop_event.set()
            monitor_thread.join(timeout=10)
            if monitor_thread.is_alive():
                print("WARN: Monitor thread did not stop gracefully.")
        print("INFO: Standalone test finished.")