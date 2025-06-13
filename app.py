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
SHEETY_ID = os.environ["SHEETY_ENDPOINT"]
USERDATA_URL = f"https://api.sheety.co/{SHEETY_ID}/lineUserData/userdata"
QUESTIONS_URL = f"https://api.sheety.co/{SHEETY_ID}/lineUserData/questions"

@app.route("/", methods=["GET"])
def health(): return jsonify({"status": "ok"}), 200

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try: handler.handle(body, signature)
    except InvalidSignatureError: abort(400)
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    message = event.message.text
    now = (datetime.utcnow() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
    try: name = line_bot_api.get_profile(user_id).display_name
    except: name = "不明"

    userdata = requests.get(USERDATA_URL).json().get("userdata", [])
    questions = requests.get(QUESTIONS_URL).json().get("questions", [])
    entry = next((u for u in userdata if u["userId"] == user_id), None)
    total_q = len(questions)

    if entry is None:
        # 初回登録（q1に保存）
        data = {
            "userdatum": {
                "name": name, "userId": user_id, "timestamp": now,
                "step": 1, "q1": message
            }
        }
        requests.post(USERDATA_URL, json=data)
        if len(questions) >= 2:
            send_text(user_id, questions[1]["question"], event)
        else:
            send_text(user_id, "ご登録ありがとうございました！", event)
        return

    step = int(entry.get("step", 1)) 
    if step >= total_q:
        # すでに全て回答済みなら終了
        return
    
    q_key = f"q{step + 1}"
    entry[q_key] = message
    entry["step"] = step + 1
    update_url = f"{USERDATA_URL}/{entry['id']}"
    requests.put(update_url, json={"userdatum": entry})

    # 次の質問 or 完了
    if entry["step"] < total_q:
        send_text(user_id, questions[entry["step"]]["question"], event)
    else:
        send_text(user_id, "全ての質問へのご回答ありがとうございました！", event)

def send_text(user_id, text, event):
    try:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=text))
    except LineBotApiError:
        line_bot_api.push_message(user_id, TextSendMessage(text=text))

# エントリポイント
if __name__ != "__main__":
    application = app
else:
    app.run(debug=True, port=5000)
