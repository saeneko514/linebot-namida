from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from datetime import datetime, timedelta
import os
import requests

app = Flask(__name__)

# Health Check
@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200

# LINE webhook endpoint
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET'))
line_bot_api = LineBotApi(os.environ.get('LINE_CHANNEL_ACCESS_TOKEN'))

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id

    # プロフィール取得
    try:
        profile = line_bot_api.get_profile(user_id)
        user_name = profile.display_name
    except:
        user_name = "不明"

    # 時刻設定
    jst_now = datetime.utcnow() + timedelta(hours=9)
    now_str = jst_now.strftime('%Y-%m-%d %H:%M:%S')

    # Sheety からデータ取得
    SHEETY_ID = os.environ.get('SHEETY_ENDPOINT')
    SHEETY_ENDPOINT = f"https://api.sheety.co/{SHEETY_ID}/lineUserData/userdata"
    QUESTIONS_URL = f"https://api.sheety.co/{SHEETY_ID}/lineUserData/questions"

    userdata = requests.get(SHEETY_ENDPOINT).json().get("userdata", [])
    questions = requests.get(QUESTIONS_URL).json().get("questions", [])

    # 登録チェック
    entry = next((u for u in userdata if u["userId"] == user_id), None)
    print(entry)

    if entry is None:
        # 初回登録
        data = {
            "userdatum": {
                "name": user_name,
                "userId": user_id,
                "timestamp": now_str,
                "step": 1
            }
        }
        res = requests.post(SHEETY_ENDPOINT, json=data)
        message = ("登録ありがとうございます！あなたについて何点か教えてください"
                   if res.status_code in (200, 201)
                   else "登録に失敗しました。後で再度お試しください。")
        try:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=message))
        except LineBotApiError:
            line_bot_api.push_message(user_id, TextSendMessage(text=message))
        return

    # 2回目以降
    current_step = int(entry.get("step", 1))
    if current_step <= len(questions):
        # 回答を記録
        column = f"q{current_step}"
        entry[column] = event.message.text
        entry["step"] = current_step + 1
        update_url = f"{SHEETY_ENDPOINT}/{entry['id']}"
        requests.put(update_url, json={"userdata": entry})

        # 次の質問 or 完了メッセージ
        if current_step < len(questions):
            next_q = questions[current_step]["question"]
            try:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=next_q))
            except LineBotApiError:
                line_bot_api.push_message(user_id, TextSendMessage(text=next_q))
        else:
            finish = "全ての質問への回答ありがとうございました！"
            try:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=finish))
            except LineBotApiError:
                line_bot_api.push_message(user_id, TextSendMessage(text=finish))

# Gunicorn が使うエントリポイント
if __name__ != "__main__":
    application = app

if __name__ == "__main__":
    app.run(debug=True, port=5000)
