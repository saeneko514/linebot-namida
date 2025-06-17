from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.models import QuickReply, QuickReplyButton, MessageAction
from datetime import datetime, timedelta
import os, requests

app = Flask(__name__)
user_state = {}

# LINE設定
line_bot_api = LineBotApi(os.environ["LINE_CHANNEL_ACCESS_TOKEN"])
handler = WebhookHandler(os.environ["LINE_CHANNEL_SECRET"])

# エンドポイント
SHEETY_ID = os.environ["SHEETY_ID"]
USERDATA_URL = f"https://api.sheety.co/{SHEETY_ID}/lineUserData/userdata"
DIARY_ENDPOINT = f"https://api.sheety.co/{SHEETY_ID}/lineUserData/diary"

# 直近のイベントIDを記録（再送防止用）
recent_message_ids = set()

# 感情の選択肢
emotion_buttons = [
    QuickReplyButton(action=MessageAction(label="怖かった", text="怖かった")),
    QuickReplyButton(action=MessageAction(label="怒った", text="怒った")),
    QuickReplyButton(action=MessageAction(label="悲しかった", text="悲しかった")),
    QuickReplyButton(action=MessageAction(label="寂しかった", text="寂しかった")),
    QuickReplyButton(action=MessageAction(label="無価値観", text="無価値観")),
    QuickReplyButton(action=MessageAction(label="その他", text="その他")),
    QuickReplyButton(action=MessageAction(label="わからない", text="わからない")),
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
                "timestamp": now.strftime("%Y-%m-%d")
            }
        }
        try:
            requests.post(USERDATA_URL, json=data)
        except Exception as e:
            print("初回登録エラー:", e)
        send_text(user_id, "ご登録ありがとうございます！\n次にこちらからアンケートに答えてください\nhttps://namisapo3.love", event)
        return

    # ステップ3: スコア入力を待っている状態か？
    if user_id in user_state and user_state[user_id].get("awaiting_score"):
        try:
            score = int(message)
            if 0 <= score <= 100:
                diary_data = {
                    "diary": {
                        "name": name,
                        "userId": user_id,
                        "timestamp": now.strftime("%Y-%m-%d"),
                        "diary": user_state[user_id]["last_diary"],
                        "emotion": "無価値観",
                        "score": score
                    }
                }
                requests.post(DIARY_ENDPOINT, json=diary_data)
                send_text(user_id, "ありがとうございました。\nゆっくり休んでくださいね。", event)
                user_state.pop(user_id, None)
            else:
                send_text(user_id, "0〜100の数値で入力してください。", event)
            return
        except:
            send_text(user_id, "数値で入力してください（例：70）", event)
            return

    # ステップ2: 感情の選択
    emotion_texts = [btn.action.text for btn in emotion_buttons]
    if message in emotion_texts:
        if message == "無価値観":
            if user_id not in user_state:
                user_state[user_id] = {}
            user_state[user_id]["emotion"] = message
            user_state[user_id]["awaiting_score"] = True
            send_text(user_id, "今日の自己肯定感を100点満点で教えてください。", event)
        else:
            diary_data = {
                "diary": {
                    "name": name,
                    "userId": user_id,
                    "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "diary": user_state.get(user_id, {}).get("last_diary", ""),
                    "emotion": message
                }
            }
            try:
                requests.post(DIARY_ENDPOINT, json=diary_data)
                send_text(user_id, "ありがとうございました。\nゆっくり休んでくださいね。", event)
                user_state.pop(user_id, None)
            except:
                send_text(user_id, "保存中にエラーが発生しました。", event)
        return

    # ステップ1: 日記の入力
    try:
        user_state[user_id] = {"last_diary": message}
        send_text(
            user_id,
            "５行日記で書いた出来事で\nあなたが感じた感情の種類を\n特定してください。",
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
