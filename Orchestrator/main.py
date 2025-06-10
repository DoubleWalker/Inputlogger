import sys
from pathlib import Path

# 프로젝트 루트 경로 설정
current_dir = Path(__file__).parent
project_root = current_dir.parent if current_dir.name == 'src' else current_dir.parent.parent
sys.path.insert(0, str(project_root))

# 이제 절대 경로로 임포트
from Orchestrator.src.core.orchestrator import Orchestrator

if __name__ == "__main__":
    print("Starting Orchestrator System...")
    print(f"Project Root (estimated): {current_dir}")

    # 타임 슬라이스 시간 설정 (분 단위)
    vd1_minutes = 3
    vd2_minutes = 3

    orchestrator = None
    try:
        orchestrator = Orchestrator(vd1_slice_min=vd1_minutes, vd2_slice_min=vd2_minutes)
        orchestrator.run_orchestration_loop()
    except Exception as e:
        print(f"An error occurred during Orchestrator execution: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if orchestrator:
             orchestrator.shutdown() # 예외 발생 시에도 종료 시도
        print("Orchestrator System finished.")