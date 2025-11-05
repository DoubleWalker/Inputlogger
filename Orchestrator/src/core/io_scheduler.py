# Orchestrator/src/core/io_scheduler.py (수정됨)

import threading
import queue
import time  # time.time()을 위해 import 추가
import traceback  # 오류 로깅을 위해 import 추가
from enum import Enum


class Priority(Enum):
    URGENT = 0  # 피격, 사망
    HIGH = 1  # 재연결
    NORMAL = 2  # 물약, 이동
    LOW = 3  # 기타


class IOScheduler:
    def __init__(self):
        self.queue = queue.PriorityQueue()
        # ★★★ 이 lock이 "줄 세우기"의 핵심입니다 ★★★
        self.lock = threading.Lock()
        self.worker_thread = None
        self.stop_event = None

    def request(self, component: str, screen_id: str, action: callable, priority: Priority = Priority.NORMAL):
        """
        IO 작업을 요청합니다.
        action은 실행할 함수 또는 lambda여야 합니다.
        """
        # (priority.value, time.time(), ...)으로 우선순위 큐에 삽입
        self.queue.put((
            priority.value,
            time.time(),  # 동일 우선순위 시, 먼저 온 순서(Timestamp)
            component,
            screen_id,
            action  # <- 여기에 람다식이 통째로 전달됩니다.
        ))

    def start(self, stop_event):
        """워커 스레드 시작"""
        self.stop_event = stop_event
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)  # 데몬 스레드로 변경
        self.worker_thread.start()

    def _worker(self):
        """
        IO 실행 전용 워커 스레드.
        큐에서 작업을 하나씩 꺼내 lock을 잡고 순차적으로 실행합니다.
        """
        while not self.stop_event.is_set():
            try:
                # 1. 큐에서 작업 가져오기 (작업이 없으면 1초 대기)
                item = self.queue.get(timeout=1.0)
                priority_val, timestamp, component, screen_id, action_lambda = item

                # 2. ★★★ IO Lock 잡기 (이 순간 다른 IO는 모두 대기) ★★★
                with self.lock:
                    print(f"--- [IO START] ({component}/{screen_id}, P:{priority_val}) ---")

                    # 3. ★★★ 전달받은 람다(action) 실행 ★★★
                    try:
                        # 이 action_lambda()가 monitor.py에서 보낸
                        # lambda: self._initiate_flight(screen) 등을 실행합니다.
                        action_lambda()

                        print(f"--- [IO END]   ({component}/{screen_id}) ---")

                    except Exception as e:
                        # !!! 중요 !!!
                        # 람다 실행 중 에러가 나도 스케줄러는 죽지 않아야 합니다.
                        print(f"!!! ERROR: [IO] Action failed for {component}/{screen_id}: {e}")
                        traceback.print_exc()  # 상세 에러 로그 출력

                # 작업 큐 비우기 (필요시)
                self.queue.task_done()

            except queue.Empty:
                # 1초 동안 큐에 아무 작업도 없었음. (정상)
                continue
            except Exception as e:
                # 스케줄러 루프 자체의 심각한 오류
                print(f"!!! CRITICAL: [IO] Worker loop error: {e}")
                time.sleep(1)  # 루프 재시도 전 잠시 대기