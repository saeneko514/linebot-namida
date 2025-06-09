from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ['LINE_CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['LINE_CHANNEL_SECRET'])
ADMIN_USER_ID = 'U8ccba01578d82755c5bc76117b020dd7'


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
    text = event.message.text
    reply = TextSendMessage(text=f"あなたのメッセージ: {text}")
    line_bot_api.reply_message(event.reply_token, reply)


if __name__ == "__main__":
    app.run()


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id

    # ユーザーへの返信（IDは送らない）
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="メッセージありがとうございます！")
    )

    # 管理者にユーザーIDとメッセージ内容を送る
    admin_message = f"新しいメッセージが来ました。ユーザーID: {user_id}\n内容: {event.message.text}"
    line_bot_api.push_message(ADMIN_USER_ID, TextSendMessage(text=admin_message))
