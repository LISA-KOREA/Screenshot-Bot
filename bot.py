from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import fitz
import cv2
import os
import mimetypes

# Replace these values with your own
api_id = ""
api_hash = ""
bot_token = ""

app = Client("screenshot_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Function to take multiple screenshots of a document
def screenshot_document(file_path, max_pages=10):
    screenshots = []
    try:
        doc = fitz.open(file_path)
        for page_number in range(min(doc.page_count, max_pages)):
            page = doc.load_page(page_number)
            pix = page.get_pixmap()
            output_path = f"{file_path}_page_{page_number}.png"
            pix.save(output_path)
            screenshots.append(output_path)
        return screenshots
    except Exception as e:
        print(f"Failed to process document: {e}")
        return []

# Function to take multiple screenshots of a video at regular intervals
def screenshot_video(file_path, max_frames=10):
    screenshots = []
    try:
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            raise Exception("Could not open video file")
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        interval = max(1, total_frames // max_frames)
        
        for frame_number in range(0, total_frames, interval):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            success, frame = cap.read()
            if success:
                output_path = f"{file_path}_frame_{frame_number}.png"
                cv2.imwrite(output_path, frame)
                screenshots.append(output_path)
            if len(screenshots) >= max_frames:
                break
        
        cap.release()
        return screenshots
    except Exception as e:
        print(f"Failed to process video: {e}")
        return []

# Handler for the /start command
@app.on_message(filters.command("start"))
async def start(client, message):
    buttons = [
        [
            InlineKeyboardButton("📣 Join my channel 📣", url="https://t.me/NT_BOT_CHANNEL"),
            InlineKeyboardButton("👥 Support group 👥", url="https://t.me/NT_BOTS_SUPPORT"),
        ],
        [
            InlineKeyboardButton("👩‍💻 Developer 👩‍💻", url="https://t.me/LISA_FAN_LK"),
            InlineKeyboardButton("⛔️ Cancel ⛔️", callback_data="cancel"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await message.reply_text("Hello! I am your screenshot bot. Send me a document or video file, and I will generate screenshots for you.", reply_markup=reply_markup)

# Handler for the /help command
@app.on_message(filters.command("help"))
async def help(client, message):
    await message.reply_text("Usage:\n\n"
                             "1. Send a document (PDF, DOC, DOCX) to get screenshots of its pages.\n"
                             "2. Send a video file (MP4, WEBM, MKV, AVI, MOV, WMV) to get screenshots from the video.\n"
                             "3. I will process the file and upload the screenshots for you.")

# Handler for file messages
@app.on_message(filters.document | filters.video)
async def file_handler(client, message):
    file = message.document or message.video
    reply_message = await message.reply_text("Downloading file...")
    file_path = await app.download_media(file)
    
    if not file_path:
        await message.reply_text("Failed to download the file.")
        return
    
    mime_type, _ = mimetypes.guess_type(file_path)
    print(f"File MIME type: {mime_type}")
    
    if mime_type in ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
        await reply_message.edit_text("Processing document...")
        screenshots = screenshot_document(file_path)
    elif mime_type in ["video/mp4", "video/webm", "video/x-matroska", "video/avi", "video/quicktime", "video/x-msvideo", "video/x-ms-wmv"]:
        await reply_message.edit_text("Processing video...")
        screenshots = screenshot_video(file_path)
    else:
        await reply_message.edit_text(f"Unsupported file type: {mime_type}")
        os.remove(file_path)
        return

    os.remove(file_path)

    if screenshots:
        await reply_message.edit_text("Uploading screenshots...")
        for screenshot_path in screenshots:
            await app.send_photo(chat_id=message.chat.id, photo=screenshot_path)
            os.remove(screenshot_path)
        await reply_message.delete()
        await message.delete()
    else:
        await reply_message.edit_text("Failed to process the file.")

@app.on_callback_query(filters.regex("cancel"))
async def cancel(client, callback_query):
    await callback_query.message.delete()

# Run the bot
if __name__ == "__main__":
    app.run()
