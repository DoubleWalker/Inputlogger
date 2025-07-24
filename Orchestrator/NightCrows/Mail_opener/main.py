import sys
import os
from pathlib import Path
import time

# --- 경로 설정 시작 ---
# 이 main.py 파일의 위치를 기준으로 프로젝트 루트 경로 계산
# C:\Users\yjy16\PycharmProjects\Inputlogger\Orchestrator\NightCrows\Mail_opener\main.py
main_py_path = Path(__file__).resolve()
# Mail_opener 폴더
mail_opener_dir = main_py_path.parent
# NightCrows 폴더
nightcrows_dir = mail_opener_dir.parent
# Orchestrator 폴더
orchestrator_dir = nightcrows_dir.parent
# 프로젝트 루트 (Inputlogger 폴더)
project_root = orchestrator_dir.parent

# sys.path에 프로젝트 루트와 Orchestrator 폴더 추가 (다른 모듈 임포트를 위해)
sys.path.insert(0, str(project_root))
# sys.path.insert(0, str(orchestrator_dir)) # Orchestrator 내부 모듈 직접 접근 필요시
# sys.path.insert(0, str(nightcrows_dir))   # NightCrows 내부 모듈 직접 접근 필요시

# --- 경로 설정 끝 ---
from Orchestrator.NightCrows.utils.screen_utils import TaskScreenPreparer

# 경로 설정 후 MailOpener 클래스 임포트
# opener.py의 위치: Orchestrator/NightCrows/Mail_opener/src/core/opener.py
try:
    # 프로젝트 루트부터의 전체 경로를 사용
    from Orchestrator.NightCrows.Mail_opener.src.core.opener import MailOpener
except ImportError as e:
    print(f"Error importing MailOpener: {e}")
    print(f"Current sys.path: {sys.path}")
    print("Please check the folder structure and import path.")
    sys.exit(1) # 오류 발생 시 종료


if __name__ == "__main__":
    print("Starting MO1 (NightCrows Mail Opener)...")

    # 화면 준비 과정 추가
    preparer = TaskScreenPreparer()
    preparer.prepare_all_screens()

    # MailOpener 객체 생성
    mo = MailOpener()

    # 템플릿 파일 기본 경로 (프로젝트 루트 기준)
    template_base_path = Path(r"C:\Users\yjy16\template\NightCrows\MO")

    # 화면 설정 (screen_info.py를 여기서 직접 임포트해서 사용하거나,
    # MailOpener 클래스 내부에서 처리하도록 수정 필요)
    # 우선 기존처럼 경로 직접 지정 (screen_info 사용 부분은 opener.py 수정 필요)
    screen_configs = [
        {'id': 'S1', 'mail': 'mail_s1.png', 'open': 'open_s1.png'},
        {'id': 'S2', 'mail': 'mail_s2.png', 'open': 'open_s2.png'},
        {'id': 'S3', 'mail': 'mail_s3.png', 'open': 'open_s3.png'},
        {'id': 'S4', 'mail': 'mail_s4.png', 'open': 'open_s4.png'},
        {'id': 'S5', 'mail': 'mail_s5.png', 'open': 'open_s5.png'},
    ]

    for config in screen_configs:
        mail_icon_path = template_base_path / config['mail']
        collect_all_path = template_base_path / config['open']

        if not mail_icon_path.exists():
            print(f"Warning: Mail icon template not found for {config['id']} at {mail_icon_path}")
        if not collect_all_path.exists():
            print(f"Warning: Collect all template not found for {config['id']} at {collect_all_path}")

        # MailOpener는 screen_id만 받도록 수정하거나, 여기서 region 정보를 직접 넘겨야 함
        # 우선 기존 add_screen 인터페이스 유지
        mo.add_screen(
            screen_id=config['id'],
            mail_icon=str(mail_icon_path),
            collect_all=str(collect_all_path)
        )
        print(f"Added screen config for {config['id']}")

    # 5초 카운트다운 (사용자 준비 시간)
    countdown_time = 5
    print(f"--- MO1 will start in {countdown_time} seconds. Prepare NightCrows screens. ---")
    for i in range(countdown_time, 0, -1):
        print(f"{i}...")
        time.sleep(1)

    # 메일 열기 실행
    print("Running mail opening process...")
    try:
        mo.run()
        print("MO1 process completed successfully.")
        sys.exit(0) # 정상 종료
    except Exception as e:
        print(f"An error occurred during MO1 execution: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) # 비정상 종료