import schedule
import time
import requests
import os

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("CHANNEL_ACCESS_TOKEN")
SHEETY_ID = os.environ["SHEETY_ENDPOINT"]
MESSAGE_TEXT = '今日もお疲れさまでした！'

def fetch_user_ids():
    response = requests.get(SHEETY_ID)
    data = response.json()
    return [row['userId'] for row in data['userdata'] if row.get('userId')]

def push_message(user_id, text):
    headers = {
        'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}',
        'Content-Type': 'application/json'
    }
    payload = {
        'to': user_id,
        'messages': [{'type': 'text', 'text': text}]
    }
    res = requests.post('https://api.line.me/v2/bot/message/push', headers=headers, json=payload)
    print(f'Sent to {user_id}: {res.status_code}')

def job():
    print("Sending LINE message...")
    user_ids = fetch_user_ids()
    for user_id in user_ids:
        push_message(user_id, MESSAGE_TEXT)

# 22:00に通知
schedule.every().day.at("04:51").do(job)

# 実行ループ
while True:
    schedule.run_pending()
    time.sleep(60)
