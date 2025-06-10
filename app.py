from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import requests

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)


SHEETY_ID = os.environ.get('SHEETY_ENDPOINT')
SHEETY_ENDPOINT = f"https://api.sheety.co/{SHEETY_ID}/lineUserData/sheet1"


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
        # LINEのプロフィール情報を取得
        profile = line_bot_api.get_profile(user_id)
        user_name = profile.display_name
    except:
        user_name = "不明"

    # SheetyへPOST
    data = {
        "sheet1": {
            "name": user_name,
            "userId": user_id
        }
    }

    response = requests.post(SHEETY_ENDPOINT, json=data)

        
    # 応答メッセージ
    if response.status_code in [200, 201]:
        reply_text = "登録ありがとうございます！"
    else:
        reply_text = "登録に失敗しました。"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run()
