# api/index.py
import os
import logging
from flask import Flask, request, abort

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from linebot.v3.webhook import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    StickerMessageContent,
    ImageMessageContent,
    PostbackEvent,
)
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    ReplyMessageRequest, PushMessageRequest,
    TextMessage, StickerMessage, FlexMessage
)

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    raise RuntimeError("Missing credentials: set LINE_CHANNEL_ACCESS_TOKEN and LINE_CHANNEL_SECRET")

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

@app.get("/")
def health():
    return "OK", 200

@app.post("/webhook")
def webhook():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    app.logger.info("Webhook body: %s", body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK", 200

# --- Message handlers ---

@handler.add(MessageEvent, message=TextMessageContent)
def on_text(event: MessageEvent):
    text = event.message.text.strip()

    # Example: send Flex for "menu"
    if text.lower() in ("menu", "選單"):
        flex = {
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": "https://picsum.photos/600/400",
                "size": "full",
                "aspectRatio": "2:1",
                "aspectMode": "cover"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {"type": "text", "text": "範例選單", "weight": "bold", "size": "xl"},
                    {"type": "text", "text": "點按下方按鈕試試", "size": "sm", "color": "#888888"}
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "action": {"type": "postback", "label": "查看說明", "data": "action=help"}
                    },
                    {
                        "type": "button",
                        "style": "secondary",
                        "action": {"type": "message", "label": "回聲測試", "text": "echo hello"}
                    }
                ]
            }
        }
        with ApiClient(configuration) as api_client:
            MessagingApi(api_client).reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[FlexMessage(altText="範例選單", contents=flex)]
                )
            )
        return

    # Default echo
    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=f"你說：{text}")]
            )
        )

@handler.add(MessageEvent, message=StickerMessageContent)
def on_sticker(event: MessageEvent):
    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[StickerMessage(packageId="11537", stickerId="52002734")]
            )
        )

@handler.add(MessageEvent, message=ImageMessageContent)
def on_image(event: MessageEvent):
    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="收到圖片啦 📷")]
            )
        )

@handler.add(PostbackEvent)
def on_postback(event: PostbackEvent):
    data = event.postback.data or ""
    with ApiClient(configuration) as api_client:
        if "action=help" in data:
            MessagingApi(api_client).reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="這是說明：輸入 menu 來看 Flex，或隨便講話我會回聲～")]
                )
            )
        else:
            MessagingApi(api_client).reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=f"Postback 收到：{data}")]
                )
            )
