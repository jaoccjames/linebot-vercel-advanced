# api/index.py
import os
import logging
from flask import Flask, request, abort, jsonify

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    StickerMessageContent,
    ImageMessageContent,
    PostbackEvent,
)
from linebot.v3.webhook import WebhookHandler
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    StickerMessage,
    FlexMessage,
)

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
HAS_CREDS = bool(CHANNEL_ACCESS_TOKEN and CHANNEL_SECRET)

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)

# 避免與 Vercel 預設入口名稱 "handler" 衝突
line_handler = WebhookHandler(CHANNEL_SECRET or "placeholder-secret")


def _handle_line_post():
    """統一處理 LINE 平台的 POST 請求"""
    if not HAS_CREDS:
        return jsonify(error="Missing LINE_CHANNEL_ACCESS_TOKEN or LINE_CHANNEL_SECRET"), 500

    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        # 沒帶/錯誤簽章 → 400（LINE Verify 不會打 POST，所以不影響）
        abort(400)

    return "OK", 200


# ================= 路由：完整相容（/、/api、/webhook、/api/webhook） =================

# 根路徑：瀏覽器/健檢可用
@app.route("/", methods=["GET", "HEAD"], strict_slashes=False)
def root_ok():
    return "OK", 200

# 將 /api 當 webhook 入口（建議 Webhook 設這個）
@app.route("/api", methods=["GET", "HEAD", "POST"], strict_slashes=False)
def api_entry():
    if request.method in ("GET", "HEAD"):
        # 給瀏覽器與 LINE 後台 Verify 用
        return "OK", 200
    return _handle_line_post()

# 若你堅持用 /api/webhook，也支援
@app.route("/api/webhook", methods=["GET", "HEAD", "POST"], strict_slashes=False)
def api_webhook_entry():
    if request.method in ("GET", "HEAD"):
        return "OK", 200
    return _handle_line_post()

# 若有其他服務打到 /webhook（少見），一樣支援
@app.route("/webhook", methods=["GET", "HEAD", "POST"], strict_slashes=False)
def webhook_entry():
    if request.method in ("GET", "HEAD"):
        return "OK", 200
    return _handle_line_post()


# ================= 事件處理 =================

@line_handler.add(MessageEvent, message=TextMessageContent)
def on_text(event: MessageEvent):
    text = (event.message.text or "").strip()

    if text.lower() in {"menu", "選單"}:
        flex_contents = {
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": "https://picsum.photos/1024/512",
                "size": "full",
                "aspectRatio": "2:1",
                "aspectMode": "cover",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {"type": "text", "text": "LINE Bot 範例選單", "weight": "bold", "size": "lg"},
                    {"type": "text", "text": "試試看下面的按鈕或直接跟我說話～", "wrap": True},
                ],
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {"type": "button", "style": "primary",
                     "action": {"type": "postback", "label": "說明 / Help", "data": "action=help"}},
                    {"type": "button", "style": "secondary",
                     "action": {"type": "uri", "label": "LINE Bot Docs",
                                "uri": "https://developers.line.biz/en/docs/messaging-api/overview/"}},
                ],
            },
        }
        with ApiClient(configuration) as api_client:
            MessagingApi(api_client).reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[FlexMessage(alt_text="範例選單", contents=flex_contents)],
                )
            )
        return

    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=text)])
        )


@line_handler.add(MessageEvent, message=StickerMessageContent)
def on_sticker(event: MessageEvent):
    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[StickerMessage(package_id="11537", sticker_id="52002734")],
            )
        )


@line_handler.add(MessageEvent, message=ImageMessageContent)
def on_image(event: MessageEvent):
    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="收到圖片啦 📷")]
            )
        )


@line_handler.add(PostbackEvent)
def on_postback(event: PostbackEvent):
    data = (event.postback.data or "").strip()
    with ApiClient(configuration) as api_client:
        if "action=help" in data:
            MessagingApi(api_client).reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="這是說明：輸入 menu 來看 Flex，或隨便講話我會回聲～")],
                )
            )
        else:
            MessagingApi(api_client).reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=f"Postback 收到：{data}")],
                )
            )

# 別加 app.run()（Serverless 不需要）
