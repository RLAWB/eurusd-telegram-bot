import os
import requests

# Use GitHub Secrets
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_test_message():
    if not TELEGRAM_TOKEN:
        print("❌ TELEGRAM_TOKEN is missing")
        return

    if not CHAT_ID:
        print("❌ CHAT_ID is missing")
        return

    message = "✅ GitHub Actions Telegram test working!"

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message
        }
    )

    print("Status Code:", response.status_code)
    print("Response:", response.text)

if __name__ == "__main__":
    send_test_message()
