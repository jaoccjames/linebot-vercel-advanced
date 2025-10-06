# api/index.py
import os
import logging
from flask import Flask, request, abort

# 本地可用 .env；在 Vercel 上請用 Project → Environment Variables
try:
    from dotenv import load_dotenv
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
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    ReplyMessageRequest, PushMessageRequest,
    TextMessage, StickerMessage, FlexMessage
)
from linebot.v3.webhook import WebhookHandler

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# ── 讀環境變數 ────────────────────────────────────────────────────────────────
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

# 若尚未設定，/api 仍回 OK（健康檢查），但 /api/webhook 會提示缺少設定
HAS_CREDS = bool(CHANNEL_ACCESS_TOKEN and CHANNEL_SECRET)

# LINE SDK 初始化（延後：只有在有變數時才建 configuration）
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN) if HAS_CREDS else None

# 為了讓下面的 @handler.add 裝飾器在匯入階段可用，給一個可用的 Handler
# （若還沒設好密鑰，用空字串占位；實際處理時我們會先檢查 HAS_CREDS）
handler = WebhookHandler(CHANNEL_SECRET or "")

# ── 健康檢查（對應 Vercel 的 /api 路徑）──────────────────────────────────────
@app.get("/")
def health():
    return "OK", 200

# ── LINE Webhook ────────────────────────────────────────────────────────────
@app.post("/webhook")
def webhook():
    # 若環境變數尚未配置，明確回應提示；避免整個 Function 500
    if not HAS_CREDS or configuration is None:
        return (
            "Missing LINE credentials. Please set LINE_CHANNEL_SECRET and "
            "LINE_CHANNEL_ACCESS_TOKEN in Vercel → Project → Settings → Environment Variables.",
            500,
        )

    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    app.logger.info("Webhook body: %s", body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        # 簽章不符（多半是 secret 錯或 URL 被測試工具改動了 body）
        abort(400)

    return "OK", 200

# ── Message handlers ────────────────────────────────────────────────────────
@handler.add(MessageEvent, message=TextMessageContent)
def on_text(event: MessageEvent):
    text = (event.message.text or "").strip()

    # 顯示 Flex 選單
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

    # 默認回聲
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

# 注意：在 Vercel（Serverless）環境切勿使用 app.run()
