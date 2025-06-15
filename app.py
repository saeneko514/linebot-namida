from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from datetime import datetime, timedelta
import os, requests

app = Flask(__name__)

# LINE設定
line_bot_api = LineBotApi(os.environ["LINE_CHANNEL_ACCESS_TOKEN"])
handler = WebhookHandler(os.environ["LINE_CHANNEL_SECRET"])

# エンドポイント
SHEETY_ID = os.environ["SHEETY_ID"]
USERDATA_URL = f"https://api.sheety.co/{SHEETY_ID}/lineUserData/userdata"
DIARY_ENDPOINT = f"https://api.sheety.co/{SHEETY_ID}/lineUserData/diary"

# 直近のメッセージ記録用（userId → (message, datetime)）
recent_messages = {}

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    message = event.message.text
    now = datetime.utcnow() + timedelta(hours=9)

    # 重複チェック
    last = recent_messages.get(user_id)
    if last:
        last_msg, last_time = last
        if message == last_msg and (now - last_time) < timedelta(seconds=30):
            print(f"重複メッセージのためスキップ: user={user_id}, msg={message}")
            return
    # メッセージ記録更新
    recent_messages[user_id] = (message, now)

    # ユーザープロフィール取得
    try:
        name = line_bot_api.get_profile(user_id).display_name
    except:
        name = "不明"

    # ユーザーデータ取得
    userdata = requests.get(USERDATA_URL).json().get("userdata", [])
    entry = next((u for u in userdata if u["userId"] == user_id), None)

    if entry is None:
        # 初回登録
        data = {
            "userdatum": {
                "name": name,
                "userId": user_id,
                "timestamp": now.strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        requests.post(USERDATA_URL, json=data)

        send_text(user_id, "ご登録ありがとうございます！次にこちらからアンケートに答えてください", event)
        return

    # 2回目以降 → 日記として保存
    diary_data = {
        "diary": {
            "name": name,
            "userId": user_id,
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "diary": message
        }
    }
    response = requests.post(DIARY_ENDPOINT, json=diary_data)
    print("POST diary status:", response.status_code)
    print("POST diary response:", response.text)
    send_text(user_id, "日記を保存しました。ありがとう！", event)

def send_text(user_id, text, event):
    try:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=text))
    except LineBotApiError:
        line_bot_api.push_message(user_id, TextSendMessage(text=text))

if __name__ == "__main__":
    app.run(debug=True, port=5000)
else:
    application = app
