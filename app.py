from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

line_bot_api = LineBotApi('f5wyS1nU1GG2Tob2zmEGMaQQnWYpN+FBpUsw2rgK5FN2P/ZfnmWnsthJm7wLKH0cLEq/khxpEQwCxl55MgeVa/A83qlVDTbiZdi2yVSNtCAJzC42A6PAqkYELgXWX9cQ8n04zJa+aT2SIdrSFWfSygdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('bf92425416b56cce6a3964cada5e18ac')

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
    reply_text = f"あなたは「{event.message.text}」と書きましたね！"
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

if __name__ == "__main__":
    app.run(port=5000)
