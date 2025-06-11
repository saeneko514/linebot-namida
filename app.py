# from flask import Flask, request, abort
# from linebot import LineBotApi, WebhookHandler
# from linebot.exceptions import InvalidSignatureError
# from linebot.models import MessageEvent, TextMessage, TextSendMessage
# from datetime import datetime, timedelta
# import os
# import requests

# app = Flask(__name__)

# LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
# LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')

# line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
# handler = WebhookHandler(LINE_CHANNEL_SECRET)


# SHEETY_ID = os.environ.get('SHEETY_ENDPOINT')
# SHEETY_ENDPOINT = f"https://api.sheety.co/{SHEETY_ID}/lineUserData/sheet1"


# @app.route("/callback", methods=['POST'])
# def callback():
#     signature = request.headers['X-Line-Signature']
#     body = request.get_data(as_text=True)

#     try:
#         handler.handle(body, signature)
#     except InvalidSignatureError:
#         abort(400)

#     return 'OK'


# @handler.add(MessageEvent, message=TextMessage)
# def handle_message(event):
#     user_id = event.source.user_id

#     try:
#         # LINEのプロフィール情報を取得
#         profile = line_bot_api.get_profile(user_id)
#         user_name = profile.display_name
#     except:
#         user_name = "不明"

#     # 日本時間に調整（UTC+9）
#     jst_now = datetime.utcnow() + timedelta(hours=9)
#     now_str = jst_now.strftime('%Y-%m-%d %H:%M:%S')

    
#     # ① 過去に登録があるかチェック（GET）
#     response_get = requests.get(SHEETY_ENDPOINT)
#     user_data = response_get.json().get("sheet1", [])

#     is_first_time = not any(entry["userId"] == user_id for entry in user_data)

#     # ② 毎回ログとしてPOST（記録は常に行う）
#     data = {
#         "sheet1": {
#             "name": user_name,
#             "userId": user_id,
#             "timestamp": now_str
#         }
#     }
#     response_post = requests.post(SHEETY_ENDPOINT, json=data)
#     print("送信データ:", data)
#     print("レスポンスコード:", response_post.status_code)
#     print("レスポンス内容:", response_post.text)

#     # ③ 初回のみ返信
#     if is_first_time:
#         reply_text = "登録ありがとうございます！"
#         line_bot_api.reply_message(
#             event.reply_token,
#             TextSendMessage(text=reply_text)
#         )
