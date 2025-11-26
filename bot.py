import os
import mimetypes
import fitz
import cv2
import asyncio
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pymongo import MongoClient

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

mongo = MongoClient(MONGO_URI)
db = mongo["screenshot_bot"]
users = db["users"]

user_locks = {}

app = Client(
    "screenshot_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

@app.on_message(filters.command("setwm"))
async def set_wm(_, message):
    user_id = message.from_user.id
    args = message.text.split(" ", 1)

    if len(args) < 2:
        return await message.reply("Usage: `/setwm YourWatermarkText`")

    wm_text = args[1].strip()

    users.update_one(
        {"_id": user_id},
        {"$set": {"watermark": wm_text}},
        upsert=True
    )

    await message.reply(f"Watermark set to:\n`{wm_text}`")

def get_watermark(user_id, username):
    record = users.find_one({"_id": user_id})

    if record and "watermark" in record:
        return record["watermark"]

    default_wm = f"@{username}" if username else "Screenshot Bot"

    users.update_one(
        {"_id": user_id},
        {"$set": {"watermark": default_wm}},
        upsert=True
    )

    return default_wm

def add_watermark(image_path, text):
    img = cv2.imread(image_path)
    font = cv2.FONT_HERSHEY_SIMPLEX
    size = cv2.getTextSize(text, font, 1, 2)[0]
    x = img.shape[1] - size[0] - 25
    y = img.shape[0] - 25
    cv2.putText(img, text, (x, y), font, 1, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.imwrite(image_path, img)

async def update_progress(msg, current, total):
    percent = int((current / total) * 100)
    await msg.edit(f"Processing... {percent}%")

def screenshot_document(file_path, max_pages):
    screenshots = []
    try:
        doc = fitz.open(file_path)
        pages = min(doc.page_count, max_pages)
        for i in range(pages):
            page = doc.load_page(i)
            pix = page.get_pixmap()
            output = f"{file_path}_page_{i+1}.png"
            pix.save(output)
            screenshots.append(output)
        return screenshots
    except:
        return []

def screenshot_video(file_path, max_frames):
    screenshots = []
    try:
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            return []
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        interval = max(1, total // max_frames)
        for i in range(max_frames):
            frame = i * interval
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, img = cap.read()
            if not ok:
                continue
            output = f"{file_path}_frame_{i+1}.png"
            cv2.imwrite(output, img)
            screenshots.append(output)
        cap.release()
        return screenshots
    except:
        return []

@app.on_message(filters.command("start"))
async def start(_, message):
    await message.reply(
        "Send me any PDF or Video and I will generate screenshots.\n"
        "Use /setwm to set your watermark."
    )

@app.on_callback_query(filters.regex("count_"))
async def choose_count(_, query):
    user_id = query.from_user.id

    if user_locks.get(user_id, False):
        return await query.answer("Please wait, processing already running.", show_alert=True)

    count = int(query.data.split("_")[1])
    file = query.message.reply_to_message
    file_path = await file.download()

    user_locks[user_id] = True

    msg = await query.message.edit("Starting... 0%")

    mime, _ = mimetypes.guess_type(file_path)
    username = query.from_user.username
    watermark = get_watermark(user_id, username)

    if mime == "application/pdf":
        screenshots = screenshot_document(file_path, count)
    elif mime and mime.startswith("video"):
        screenshots = screenshot_video(file_path, count)
    else:
        user_locks[user_id] = False
        return await msg.edit("Unsupported file.")

    total = len(screenshots)

    for i, img in enumerate(screenshots, start=1):
        await update_progress(msg, i, total)
        add_watermark(img, watermark)

    await msg.edit("Uploading...")

    for img in screenshots:
        await app.send_photo(query.message.chat.id, img)
        os.remove(img)

    os.remove(file_path)
    user_locks[user_id] = False
    await msg.delete()

@app.on_message(filters.document | filters.video)
async def file_handler(_, message):
    user_id = message.from_user.id

    if user_locks.get(user_id, False):
        return await message.reply("You already have an active process.")

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("5", callback_data="count_5"),
            InlineKeyboardButton("10", callback_data="count_10"),
            InlineKeyboardButton("15", callback_data="count_15"),
            InlineKeyboardButton("20", callback_data="count_20"),
        ]
    ])

    await message.reply("Choose screenshot count:", reply_markup=buttons)

if __name__ == "__main__":
    print("Bot Running...")
    app.run()
