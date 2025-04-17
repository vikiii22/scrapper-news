import subprocess
import requests
import os
from dotenv import load_dotenv

load_dotenv()  # Carga las variables del .env

def run_script(script_path):
    print(f"Ejecutando {script_path} ...")
    result = subprocess.run(["python", script_path], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("Errores:", result.stderr)

def send_telegram_message(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": message}
    requests.post(url, data=data)

def send_telegram_file(token, chat_id, file_path, caption=None):
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    with open(file_path, "rb") as f:
        files = {"document": f}
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
        requests.post(url, data=data, files=files)

if __name__ == "__main__":
    run_script("scrapper-data-besoccer.py")
    run_script("scrapper-teams-analysis.py")
    run_script("quiniela_analysis.py")
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    send_telegram_file(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, "quiniela_results.txt", caption="Análisis de quiniela adjunto.")