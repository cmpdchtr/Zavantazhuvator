import asyncio
import logging
import os
import yt_dlp
from pathlib import Path
from typing import Any

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram import F
from aiogram.types import FSInputFile
from dotenv import load_dotenv

# Enable logging
logging.basicConfig(level=logging.INFO)

# Load environment variables from .env file
load_dotenv()

# Initialize bot and dispatcher
token = os.getenv("BOT_TOKEN")
if token is None:
    raise RuntimeError("BOT_TOKEN environment variable is not set")
token_str: str = token
bot = Bot(token=token_str)
dp = Dispatcher()

# /start handler
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привіт! Я допоможу тобі завантажувати відео/аудіо з різних платформ, таких як YouTube, Tiktok та інші. Просто введи посилання, щоб розпочати.")

# Reacting to messages with YouTube links
@dp.message(F.text.contains("youtube.com") | F.text.contains("youtu.be"))
async def youtube_handler(message: types.Message):
    if message.text is None:
        return
    
    url = message.text.strip()
    await message.answer("⏳ Завантажую відео, будь ласка, зачекайте...")
    
    try:
        downloads_dir = Path("downloads")
        downloads_dir.mkdir(exist_ok=True)
        
        # Configuring yt-dlp for downloading in the best quality
        ydl_opts: dict[str, Any] = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': str(downloads_dir / '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'merge_output_format': 'mp4',
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore
            info = ydl.extract_info(url, download=True)
            video_title = info.get('title', 'video')
            video_filename = ydl.prepare_filename(info)
        
        # Sending the video to the user
        video_file = FSInputFile(video_filename)
        await message.answer_video(
            video=video_file,
            caption=f"✅ {video_title}"
        )
        
        # Deleting the file after sending
        os.remove(video_filename)
        
    except Exception as e:
        logging.error(f"Error downloading video: {e}")
        await message.answer(f"❌ Помилка при завантаженні відео: {str(e)}\n\nСпробуйте інше посилання або повторіть спробу пізніше.")

# Reacting to all other messages
@dp.message(F.text)
async def other_handler(message: types.Message):
    await message.answer("❌ Надішліть посилання на YouTube відео.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())