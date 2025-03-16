import requests

TELEGRAM_BOT_TOKEN = "7323688717:AAE6fu2f8YYNFBAqnXqi36CaHo2FMxstuDA"
TELEGRAM_CHAT_ID = "641862693"

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    response = requests.post(url, json=payload)
    print(response.json())

# Test sending a message
send_to_telegram("Hello! This is a test message from my Telegram bot.")
