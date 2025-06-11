from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from datetime import datetime, timedelta
import os
import requests

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)


SHEETY_ID = os.environ.get('SHEETY_ENDPOINT')
SHEETY_ENDPOINT = f"https://api.sheety.co/{SHEETY_ID}/lineUserData/userdata"
QUESTIONS_URL = f"https://api.sheety.co/{SHEETY_ID}/lineUserData/questions"


@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id

    try:
        profile = line_bot_api.get_profile(user_id)
        user_name = profile.display_name
    except:
        user_name = "不明"

    jst_now = datetime.utcnow() + timedelta(hours=9)
    now_str = jst_now.strftime('%Y-%m-%d %H:%M:%S')

    # ユーザーデータと質問を取得
    response_get = requests.get(SHEETY_ENDPOINT)
    userdata = response_get.json().get("userdata", [])
    questions = requests.get(QUESTIONS_URL).json().get("questions", [])

    # ユーザーが登録済みかチェック
    entry = next((u for u in userdata if u["userId"] == user_id), None)

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
        
        # POST実行
        res = requests.post(SHEETY_ENDPOINT, json=data)
            
        print("POST status:", res.status_code)
        print("POST response:", res.text)
        if res.status_code in (200, 201):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="登録ありがとうございます！あなたについて何点か教えてください")
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="登録に失敗しました。後で再度お試しください。")
            )
        return

    # 初回以降の処理
    current_step = int(entry.get("step", 1))

    if current_step <= len(questions):
        # 質問中
        column_name = f"q{current_step}"
        entry[column_name] = event.message.text
        entry["step"] = current_step + 1

        update_url = f"{SHEETY_ENDPOINT}/{entry['id']}"
        requests.put(update_url, json={"userdata": entry})

        # 次の質問があれば送信
        if current_step < len(questions):
            next_question = questions[current_step]["question"]
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=next_question)
            )
        else:
            # 最終質問への回答時は完了メッセージを送る
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="全ての質問への回答ありがとうございました！")
            )

if __name__ == "__main__":
    app.run(debug=True, port=5000)
