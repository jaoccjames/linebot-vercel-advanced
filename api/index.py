# api/index.py
import os
import logging
from flask import Flask, request, abort, jsonify

# 可在本地使用 .env；在 Vercel 請用 Project → Environment Variables
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

# ── 讀環境變數 ────────────────────────────────────────────────────────────────
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")

# 在沒有設定金鑰時，/api 能健康檢查，但 /api/webhook 會明確拒絕
HAS_CREDS = bool(CHANNEL_ACCESS_TOKEN and CHANNEL_SECRET)

# SDK 設定，Messaging API 會在使用時建立連線
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)

# 重要：避免與 Vercel 的入口名稱 "handler" 衝突，改名為 line_handler
line_handler = WebhookHandler(CHANNEL_SECRET or "placeholder-secret")


# ── 路由 ─────────────────────────────────────────────────────────────────────
@app.get("/")
@app.get("/api")  # 兼容 Vercel 可能保留 /api 前綴的情況
def health():
    return "OK", 200

# ✅ Webhook：同時支援 GET（給 LINE Verify）與 POST（正式事件）
@app.route("/webhook", methods=["GET", "POST"])
@app.route("/api/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        # LINE Developers → Verify 只要 200 就會通過
        return "OK", 200

    # 以下是 POST 的實際事件處理
    if not HAS_CREDS:
        return jsonify(error="Missing LINE_CHANNEL_ACCESS_TOKEN or LINE_CHANNEL_SECRET"), 500

    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.warning("Invalid signature.")
        abort(400)

    return "OK", 200


# ── 事件處理 ─────────────────────────────────────────────────────────────────
@line_handler.add(MessageEvent, message=TextMessageContent)
def on_text(event: MessageEvent):
    text = (event.message.text or "").strip()

    # Flex 選單
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
                    {
                        "type": "button",
                        "style": "primary",
                        "action": {"type": "postback", "label": "說明 / Help", "data": "action=help"},
                    },
                    {
                        "type": "button",
                        "style": "secondary",
                        "action": {
                            "type": "uri",
                            "label": "LINE Bot Docs",
                            "uri": "https://developers.line.biz/en/docs/messaging-api/overview/",
                        },
                    },
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

    # 一般回聲
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
                # v3 參數名稱為 snake_case（非 packageId/stickerId）
                messages=[StickerMessage(package_id="11537", sticker_id="52002734")],
            )
        )


@line_handler.add(MessageEvent, message=ImageMessageContent)
def on_image(event: MessageEvent):
    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text="收到圖片啦 📷")])
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
                    reply_token=event.reply_token, messages=[TextMessage(text=f"Postback 收到：{data}")]
                )
            )

# 注意：在 Vercel（Serverless）環境切勿使用 app.run()
