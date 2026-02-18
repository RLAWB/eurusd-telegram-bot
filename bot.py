import requests

# 🔹 REPLACE THESE WITH YOUR REAL VALUES
TELEGRAM_TOKEN = "YOUR_BOT_TOKEN_HERE"
CHAT_ID = "YOUR_CHAT_ID_HERE"

def send_test_message():
    message = "✅ GitHub Actions test message working!"

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
