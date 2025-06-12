from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import requests
from datetime import datetime, timedelta

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ.get('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET'))

SHEETY_ID = os.environ.get('SHEETY_ENDPOINT')
SHEETY_ENDPOINT = f"https://api.sheety.co/{SHEETY_ID}/lineUserData/userdata"
GAS_API_URL = os.environ.get('GAS_API_URL')  

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text

    # Sheetyからuserdata取得
    userdata = requests.get(SHEETY_ENDPOINT).json().get("userdata", [])
    entry = next((u for u in userdata if u["userId"] == user_id), None)

    if entry is None:
        # 初回登録処理
        jst_now = datetime.utcnow() + timedelta(hours=9)
        now_str = jst_now.strftime('%Y-%m-%d %H:%M:%S')

        # プロフィール取得（失敗時は不明）
        try:
            profile = line_bot_api.get_profile(user_id)
            user_name = profile.display_name
        except:
            user_name = "不明"

        data = {
            "userdatum": {
                "name": user_name,
                "userId": user_id,
                "timestamp": now_str,
                "step": 1
            }
        }
        res = requests.post(SHEETY_ENDPOINT, json=data)

        if res.status_code in (200, 201):
            # 初回登録完了メッセージを送信
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="登録ありがとうございます！質問を始めます。"))
            # 次のメッセージからはGASに転送するためここでreturn
            return
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="登録に失敗しました。後で再度お試しください。"))
            return

    # 2回目以降はGASに処理を転送
    payload = {
        "events": [
            {
                "replyToken": event.reply_token,
                "source": {"userId": user_id},
                "message": {"text": text},
                "type": "message"
            }
        ]
    }
    headers = {'Content-Type': 'application/json'}
    gas_res = requests.post(GAS_API_URL, json=payload, headers=headers)

    if gas_res.status_code != 200:
        # GASが何らかの理由でエラーのときのフォールバック
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="エラーが発生しました。もう一度お試しください。"))

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, port=port)
