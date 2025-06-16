from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.models import QuickReply, QuickReplyButton, MessageAction, TextSendMessage
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

# 直近のイベントIDを記録（再送防止用）
recent_message_ids = set()

#感情の選択肢
emotion_buttons = [
    QuickReplyButton(action=MessageAction(label="喜び", text="喜び")),
    QuickReplyButton(action=MessageAction(label="悲しみ", text="悲しみ")),
    QuickReplyButton(action=MessageAction(label="怒り", text="怒り")),
    QuickReplyButton(action=MessageAction(label="驚き", text="驚き")),
    QuickReplyButton(action=MessageAction(label="恐れ", text="恐れ")),
    QuickReplyButton(action=MessageAction(label="安心", text="安心")),
]

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
    event_id = event.message.id
    if event_id in recent_message_ids:
        print(f"重複イベントのためスキップ: event_id={event_id}")
        return
    recent_message_ids.add(event_id)

    user_id = event.source.user_id
    message = event.message.text
    now = datetime.utcnow() + timedelta(hours=9)

    # ユーザープロフィール取得
    try:
        name = line_bot_api.get_profile(user_id).display_name
    except:
        name = "不明"

    # ユーザーデータ取得
    try:
        userdata = requests.get(USERDATA_URL).json().get("userdata", [])
    except Exception as e:
        print("ユーザーデータ取得エラー:", e)
        send_text(user_id, "サーバーエラーが発生しました。", event)
        return

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
        try:
            requests.post(USERDATA_URL, json=data)
        except Exception as e:
            print("初回登録エラー:", e)
        send_text(user_id, "ご登録ありがとうございます！\n"
        "次にこちらからアンケートに答えてください\n"
                  "https://namisapo3.love", event)
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
    try:
        response = requests.post(DIARY_ENDPOINT, json=diary_data)
        print("POST diary status:", response.status_code)
        print("POST diary response:", response.text)
        send_text(
            user_id, 
            "５行日記で書いた出来事で\n"
            "あなたが感じた感情の種類を\n"
            "特定してください。",
            event,
            quick_reply_items=emotion_buttons
        )
    except Exception as e:
        print("日記保存エラー:", e)
        send_text(user_id, "日記の保存中にエラーが発生しました。", event)

def send_text(user_id, text, event, quick_reply_items=None):
    try:
        if quick_reply_items:
            message = TextSendMessage(
                text=text,
                quick_reply=QuickReply(items=quick_reply_items)
            )
        else:
            message = TextSendMessage(text=text)

        line_bot_api.reply_message(event.reply_token, message)
    except LineBotApiError:
        line_bot_api.push_message(user_id, TextSendMessage(text=text))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
else:
    application = app
