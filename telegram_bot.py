import requests

# Telegram Bot Settings
TELEGRAM_BOT_TOKEN = '7885273126:AAEpr5Dy9bUXYE3kf9lEH1ww2bXsByE9y5c'
TELEGRAM_CHAT_ID = '6101168212'

def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        requests.post(url, data=data, timeout=5)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")
