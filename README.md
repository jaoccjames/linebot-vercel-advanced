# LINE Bot on Vercel — Advanced

## What’s inside
- `api/index.py` — Flask app with handlers for Text, Sticker, Image, Postback + a Flex "menu"
- `tools/setup_rich_menu.py` — one-off helper to create & set a default Rich Menu
- `flex_samples/menu.json` — editable Flex JSON
- `requirements.txt`, `.gitignore`, `pyproject.toml`

## Deploy 
1) Push this folder to GitHub → Import to Vercel (Project → New).
2) Set Environment Variables:
   - `LINE_CHANNEL_SECRET`
   - `LINE_CHANNEL_ACCESS_TOKEN`
3) Set Webhook URL on LINE Console:
   `https://<project>.vercel.app/api/webhook`

## Local quick test
```bash
pip install -r requirements.txt
export LINE_CHANNEL_SECRET=xxx
export LINE_CHANNEL_ACCESS_TOKEN=yyy
flask --app api/index.py run
# or
npm i -g vercel && vercel dev
```

## Rich Menu (optional)
```bash
export LINE_CHANNEL_ACCESS_TOKEN=yyy
# (optional) export RICH_MENU_IMAGE=/path/to/your.png
python tools/setup_rich_menu.py
```
