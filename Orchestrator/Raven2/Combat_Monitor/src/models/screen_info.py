# Orchestrator/Raven2/Combat_Monitor/src/models/screen_info.py 수정 제안

from enum import Enum
from dataclasses import dataclass, field
from typing import Tuple, Dict, Any

class ScreenState(Enum):
    SLEEP = 0       # 잠금 상태 (정상)
    AWAKE = 1       # 깨어난 상태 (정상, 전투 가능)
    ABNORMAL = 2    # 상태이상 감지 (액션 필요)
    DEAD = 3        # 사망 감지 (액션 필요)

    # --- 새로운 상태 추가 ---
    RETREATING = 10          # 후퇴 동작 시작됨 (완료 확인 필요)
    SAFE_ZONE = 11           # 안전 지역 도착 확인됨 (물약 구매 또는 복귀 전)
    PURCHASING_POTIONS = 12  # 물약 구매 동작 시작됨 (완료 확인 필요)
    POTIONS_PURCHASED = 13   # 물약 구매 완료 확인됨 (복귀 전)
    RETURNING_TO_COMBAT = 14 # 사냥터 복귀 동작 시작됨 (완료 확인 필요)
    RECOVERING = 15          # 사망 후 부활/회복 동작 시작됨 (완료 확인 필요)
    # 필요에 따라 상태 추가/수정 가능 (예: COMBAT_READY 등)
    # --- 상태 추가 끝 ---

@dataclass
class CombatScreenInfo:
    window_id: str
    region: Tuple[int, int, int, int]
    ratio: float = 1.0

    # [수정] current_state 필드 제거 -> 프로퍼티로 대체
    # current_state: ScreenState = ScreenState.SLEEP

    # [신규] 공유 상태 딕셔너리 참조 (초기화 시 주입받음)
    _shared_state_ref: Dict[str, Any] = field(default_factory=dict, repr=False)

    retry_count: int = 0
    policy_step: int = 0
    policy_step_start_time: float = 0.0

    # [신규] current_state를 프로퍼티로 정의하여 공유 딕셔너리 접근
    @property
    def current_state(self):
        # 딕셔너리에 없으면 기본값 SLEEP 반환
        return self._shared_state_ref.get(self.window_id, ScreenState.SLEEP)

    @current_state.setter
    def current_state(self, new_state):
        # 딕셔너리에 값 쓰기 (모든 모니터가 즉시 알게 됨)
        self._shared_state_ref[self.window_id] = new_state