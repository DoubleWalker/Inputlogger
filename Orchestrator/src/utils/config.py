# orchestrator/src/utils/config.py

from dataclasses import dataclass
from typing import Tuple

@dataclass
class TaskbarConfig:
   region: Tuple[int, int, int, int]  # x, y, width, height 좌표
   game1_icon: str  # 게임1 작업표시줄 아이콘 경로
   game2_icon: str  # 게임2 작업표시줄 아이콘 경로
   confidence_threshold: float = 0.85

# 실제 값들은 외부에서 주입
TASKBAR_CONFIG = TaskbarConfig(
   region=(0, 1040, 1920, 40),
   game1_icon=r"C:\Users\yjy16\template\NightCrows\NC.png",
   game2_icon=r"C:\Users\yjy16\template\RAVEN2\raven2.png",
)