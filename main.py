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
    status_message = await message.answer("⏳ Завантажую відео, будь ласка, зачекайте...")
    
    try:
        downloads_dir = Path("downloads")
        downloads_dir.mkdir(exist_ok=True)
        
        max_file_size = 50 * 1024 * 1024  # 50 MB - Telegram limit
        video_filename = None
        
        # Try downloading in best quality with original audio
        ydl_opts: dict[str, Any] = {
            'format': (
                'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/'
                'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            ),
            'outtmpl': str(downloads_dir / '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore
            info = ydl.extract_info(url, download=True)
            video_title = info.get('title', 'video')
            video_filename = ydl.prepare_filename(info)
        
        # Check file size
        file_size = os.path.getsize(video_filename)
        
        # If file is still too large, try 480p
        if file_size > max_file_size:
            os.remove(video_filename)
            await status_message.edit_text("📉 Файл занадто великий, завантажую у 480p...")
            
            ydl_opts['format'] = (
                'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/'
                'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]/'
                'bestvideo[ext=mp4]+bestaudio[ext=m4a]'
            )
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore
                info = ydl.extract_info(url, download=True)
                video_filename = ydl.prepare_filename(info)
            
            file_size = os.path.getsize(video_filename)
            
            # If still too large, inform user
            if file_size > max_file_size:
                os.remove(video_filename)
                await status_message.edit_text(
                    f"❌ Відео занадто велике ({file_size / (1024 * 1024):.1f} МБ).\n\n"
                    f"Telegram Bot API має ліміт 50 МБ. Спробуйте коротше відео."
                )
                return
        
        # Send the video
        video_file = FSInputFile(video_filename)
        await message.answer_video(
            video=video_file,
        )
        
        # Deleting the status message
        await status_message.delete()
        
        # Deleting the file after sending
        if video_filename and os.path.exists(video_filename):
            os.remove(video_filename)
        
    except Exception as e:
        logging.error(f"Error downloading video: {e}")
        await message.answer(f"❌ Помилка при завантаженні відео: {str(e)}\n\nСпробуйте інше посилання або повторіть спробу пізніше.")

# Reacting to messages with TikTok links
@dp.message(F.text.contains("tiktok.com") | F.text.contains("vm.tiktok.com"))
async def tiktok_handler(message: types.Message):
    if message.text is None:
        return
    
    url = message.text.strip()
    status_message = await message.answer("⏳ Завантажую TikTok відео, будь ласка, зачекайте...")
    
    try:
        downloads_dir = Path("downloads")
        downloads_dir.mkdir(exist_ok=True)
        
        max_file_size = 50 * 1024 * 1024  # 50 MB - Telegram limit
        video_filename = None
        
        # Configuring yt-dlp for TikTok downloads
        ydl_opts: dict[str, Any] = {
            'format': 'best[filesize<?50M]/best',
            'outtmpl': str(downloads_dir / '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore
            info = ydl.extract_info(url, download=True)
            video_title = info.get('title', 'tiktok_video')
            video_filename = ydl.prepare_filename(info)
        
        # Check file size
        file_size = os.path.getsize(video_filename)
        
        # If file is too large, inform user
        if file_size > max_file_size:
            os.remove(video_filename)
            await status_message.edit_text(
                f"❌ Відео занадто велике ({file_size / (1024 * 1024):.1f} МБ).\n\n"
                f"Telegram Bot API має ліміт 50 МБ."
            )
            return
        
        # Send the video
        video_file = FSInputFile(video_filename)
        await message.answer_video(
            video=video_file,
        )
        
        # Deleting the status message
        await status_message.delete()
        
        # Deleting the file after sending
        if video_filename and os.path.exists(video_filename):
            os.remove(video_filename)
        
    except Exception as e:
        logging.error(f"Error downloading TikTok video: {e}")
        await message.answer(f"❌ Помилка при завантаженні TikTok відео: {str(e)}\n\nСпробуйте інше посилання або повторіть спробу пізніше.")

# Reacting to all other messages
@dp.message(F.text)
async def other_handler(message: types.Message):
    await message.answer("❌ Надішліть посилання на YouTube або TikTok відео.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())