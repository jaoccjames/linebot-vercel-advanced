# tools/setup_rich_menu.py
"""
One-off helper to create and set a default Rich Menu.
Usage:
    export LINE_CHANNEL_ACCESS_TOKEN=xxx
    python tools/setup_rich_menu.py
"""

import os
import json
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi, MessagingApiBlob,
    RichMenuRequest, RichMenuArea, RichMenuBounds,
    RichMenuSwitchAction, PostbackAction, MessageAction
)

ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
if not ACCESS_TOKEN:
    raise SystemExit("Please set LINE_CHANNEL_ACCESS_TOKEN")

# Define a simple rich menu (2500x843)
rich_menu = RichMenuRequest(
    size={"width": 2500, "height": 843},
    selected=True,
    name="MainMenu",
    chatBarText="選單",
    areas=[
        RichMenuArea(
            bounds=RichMenuBounds(x=0, y=0, width=1250, height=843),
            action=PostbackAction(data="action=help", label="說明")
        ),
        RichMenuArea(
            bounds=RichMenuBounds(x=1250, y=0, width=1250, height=843),
            action=MessageAction(text="menu", label="功能")
        ),
    ]
)

configuration = Configuration(access_token=ACCESS_TOKEN)

with ApiClient(configuration) as api_client:
    api = MessagingApi(api_client)

    # Create rich menu
    result = api.create_rich_menu(rich_menu)
    rich_menu_id = result.rich_menu_id
    print("Created rich menu:", rich_menu_id)

    # Optionally upload an image (provide your own file path)
    image_path = os.getenv("RICH_MENU_IMAGE", "")
    if image_path and os.path.exists(image_path):
        blob = MessagingApiBlob(api_client)
        with open(image_path, "rb") as f:
            blob.set_rich_menu_image(rich_menu_id, "image/png", f)
        print("Uploaded image for rich menu.")

    # Set default rich menu
    api.set_default_rich_menu(rich_menu_id)
    print("Set as default rich menu.")
