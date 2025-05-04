import sys
import os
from pathlib import Path
import time

# --- 경로 설정 시작 ---
main_py_path = Path(__file__).resolve()
project_root = main_py_path.parent.parent.parent.parent
sys.path.insert(0, str(project_root))
# --- 경로 설정 끝 ---

# MailOpener 클래스 임포트
try:
    # opener.py 위치에 따라 경로 수정 필요
    from Orchestrator.Raven2.Mail_opener.src.core.opener import MailOpener
except ImportError as e:
    print(f"Error importing MailOpener: {e}")
    sys.exit(1)

if __name__ == "__main__":
    print("Starting MO2 (Raven2 Mail Opener)...")

    mo = MailOpener()

    template_base_path = Path(r"C:\Users\yjy16\template\RAVEN2\MO")

    # screen_configs: 사용자 opener.py의 __main__ 부분 파일 이름 반영
    screen_configs = [
        {'id': 'S1', 'mail_icon': 'mail_s1.png', 'notice_tab': 'notice_s1.png', 'envelope': 'env_s1.png', 'collect_all': 'open_s1.png', 'confirm': 'cf_s1.png'},
        {'id': 'S2', 'mail_icon': 'mail_s2.png', 'notice_tab': 'notice_s2.png', 'envelope': 'env_s2.png', 'collect_all': 'open_s2.png', 'confirm': 'cf_s2.png'},
        {'id': 'S3', 'mail_icon': 'mail_s3.png', 'notice_tab': 'notice_s3.png', 'envelope': 'env_s3.png', 'collect_all': 'open_s3.png', 'confirm': 'cf_s3.png'},
        {'id': 'S4', 'mail_icon': 'mail_s4.png', 'notice_tab': 'notice_s4.png', 'envelope': 'env_s4.png', 'collect_all': 'open_s4.png', 'confirm': 'cf_s4.png'},
        {'id': 'S5', 'mail_icon': 'mail_s5.png', 'notice_tab': 'notice_s5.png', 'envelope': 'env_s5.png', 'collect_all': 'open_s5.png', 'confirm': 'cf_s5.png'},
    ]

    for config in screen_configs:
        paths = {}
        all_exist = True
        required_keys = ['mail_icon', 'notice_tab', 'envelope', 'collect_all', 'confirm']
        for key in required_keys:
            if key not in config:
                print(f"Error: Key '{key}' missing in screen_configs for screen '{config['id']}'")
                all_exist = False
                break

            # 키 이름을 그대로 사용하여 파일 이름 가져오기
            path = template_base_path / config[key]
            paths[key] = str(path)
            if not path.exists():
                print(f"WARN: Template not found for {config['id']} - {key}: '{path}'")
                all_exist = False
                # break # 템플릿 없으면 추가하지 않으려면 주석 해제

        # if not all_exist:
        #     print(f"Skipping screen {config['id']} due to missing templates.")
        #     continue

        # add_screen 호출 시에도 config의 키 이름 그대로 사용
        mo.add_screen(
            screen_id=config['id'],
            mail_icon=paths['mail_icon'],
            # 순서 주의: opener.py add_screen 파라미터 순서와 일치 필요
            # def add_screen(self, screen_id: str, mail_icon: str, collect_all: str, notice_tab: str, envelope: str, confirm: str):
            collect_all=paths['collect_all'], # collect_all 먼저
            notice_tab=paths['notice_tab'],
            envelope=paths['envelope'],
            confirm=paths['confirm']
        )
        print(f"Added screen config for {config['id']}")

    countdown_time = 5
    print(f"--- MO2 will start in {countdown_time} seconds. Prepare RAVEN2 screens. ---")
    for i in range(countdown_time, 0, -1):
        print(f"{i}...")
        time.sleep(1)

    print("Running Raven2 mail opening process...")
    try:
        mo.run()
        print("MO2 process completed successfully.")
        sys.exit(0)
    except Exception as e:
        print(f"An error occurred during MO2 execution: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)