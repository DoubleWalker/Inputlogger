# Orchestrator/Raven2/Combat_Monitor/src/models/screen_info.py 수정 제안

from enum import Enum
from dataclasses import dataclass
from typing import Tuple

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
    ratio: float = 1.0  # 기본값 1.0으로 설정
    current_state: ScreenState = ScreenState.SLEEP # 초기 상태는 SLEEP 유지
    retry_count: int = 0
    # ⬇️ SRM1의 '엔진' 구동을 위해 이 두 필드 추가 ⬇️
    policy_step: int = 0
    policy_step_start_time: float = 0.0