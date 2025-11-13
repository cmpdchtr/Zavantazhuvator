import asyncio
import logging
import os
import aiohttp
import yt_dlp
from pathlib import Path
from typing import Any

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram import F
from aiogram.types import FSInputFile, URLInputFile
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

# Check if using local Bot API server
bot_api_server = os.getenv("BOT_API_SERVER")
if bot_api_server:
    from aiogram.client.session.aiohttp import AiohttpSession
    session = AiohttpSession(api=bot_api_server)
    bot = Bot(token=token_str, session=session)
    logging.info(f"Using local Bot API server: {bot_api_server}")
    logging.info("File size limit: up to 2 GB")
else:
    bot = Bot(token=token_str)
    logging.info("Using official Telegram Bot API")
    logging.info("File size limit: 50 MB")

dp = Dispatcher()

# Cobalt API configuration
COBALT_API_URL = os.getenv("COBALT_API_URL", "https://co.wuk.sh")
COBALT_API_KEY = os.getenv("COBALT_API_KEY")  # Optional API key for authentication

# File size limits
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024 if bot_api_server else 50 * 1024 * 1024  # 2 GB or 50 MB

# Cache for JWT tokens
jwt_token_cache: dict[str, Any] = {}

async def get_jwt_token(api_url: str) -> str | None:
    """Get JWT token from Cobalt API if required"""
    # Check if we have a cached valid token
    if api_url in jwt_token_cache:
        cached = jwt_token_cache[api_url]
        # Simple expiry check (tokens usually last 2 hours)
        if cached.get("expires_at", 0) > asyncio.get_event_loop().time():
            return cached.get("token")
    
    # Try to get a new token without turnstile (some instances allow this)
    try:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{api_url}/session", headers=headers, json={}) as response:
                if response.status == 200:
                    data = await response.json()
                    token = data.get("token")
                    exp = data.get("exp", 7200)  # Default 2 hours
                    
                    if token:
                        jwt_token_cache[api_url] = {
                            "token": token,
                            "expires_at": asyncio.get_event_loop().time() + exp
                        }
                        return token
    except Exception as e:
        logging.debug(f"Could not get JWT token: {e}")
    
    return None

def is_youtube_url(url: str) -> bool:
    """Check if URL is from YouTube"""
    return "youtube.com" in url or "youtu.be" in url

async def download_youtube_video(url: str, status_message: types.Message) -> Path | None:
    """Download YouTube video using yt-dlp"""
    downloads_dir = Path("downloads")
    downloads_dir.mkdir(exist_ok=True)
    
    max_file_size = MAX_FILE_SIZE
    
    # Try downloading with quality limit
    ydl_opts: dict[str, Any] = {
        'format': (
            'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/'
            'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        ),
        'outtmpl': str(downloads_dir / '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'merge_output_format': 'mp4',
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore
        info = ydl.extract_info(url, download=True)
        video_filename = Path(ydl.prepare_filename(info))
    
    # Check file size
    file_size = video_filename.stat().st_size
    
    # If too large, try lower quality
    if file_size > max_file_size:
        video_filename.unlink()
        await status_message.edit_text("📉 Файл занадто великий, завантажую у 480p...")
        
        ydl_opts['format'] = (
            'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/'
            'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]'
        )
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore
            info = ydl.extract_info(url, download=True)
            video_filename = Path(ydl.prepare_filename(info))
        
        file_size = video_filename.stat().st_size
        
        # If still too large, inform user
        if file_size > max_file_size:
            video_filename.unlink()
            limit_text = "2 ГБ" if bot_api_server else "50 МБ"
            await status_message.edit_text(
                f"❌ Відео занадто велике ({file_size / (1024 * 1024):.1f} МБ).\n\n"
                f"Ліміт Telegram: {limit_text}. Спробуйте коротше відео."
            )
            return None
    
    return video_filename

async def download_with_cobalt(url: str) -> dict[str, Any]:
    """Download video using Cobalt API"""
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    # Add authentication if available
    if COBALT_API_KEY:
        headers["Authorization"] = f"Api-Key {COBALT_API_KEY}"
    else:
        # Try to get JWT token
        jwt_token = await get_jwt_token(COBALT_API_URL)
        if jwt_token:
            headers["Authorization"] = f"Bearer {jwt_token}"
    
    payload = {
        "url": url,
        "videoQuality": "max",
        "filenameStyle": "basic",
        "downloadMode": "auto"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{COBALT_API_URL}/", headers=headers, json=payload) as response:
            response_text = await response.text()
            
            if response.status != 200:
                logging.error(f"Cobalt API error {response.status}: {response_text}")
                raise Exception(f"Cobalt API error: {response.status} - {response_text[:200]}")
            
            try:
                return await response.json()
            except Exception as e:
                logging.error(f"Failed to parse JSON response: {response_text}")
                raise Exception(f"Invalid JSON response from Cobalt API")

# /start handler
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    file_limit = "2 ГБ 🚀" if bot_api_server else "50 МБ"
    api_status = "Локальний Bot API Server" if bot_api_server else "Офіційний Telegram API"
    
    welcome_text = (
        "🎬 Zavantazhuvator — твій універсальний відео помічник!\n\n"
        "Завантажуй відео з YouTube, TikTok, Instagram, Twitter, Reddit та багатьох інших платформ "
        "у найкращій якості за лічені секунди!\n\n"
        "✨ Можливості:\n"
        "• Підтримка 20+ популярних платформ\n"
        "• YouTube: до 1080p з оригінальним аудіо (yt-dlp)\n"
        "• Інші платформи: до 4K/8K (Cobalt API)\n"
        "• Блискавична швидкість завантаження\n"
        "• Оригінальна аудіодоріжка без перекладу\n\n"
        f"📊 Статус: {api_status}\n"
        f"📦 Ліміт файлів: {file_limit}\n\n"
        "Просто надішли посилання на відео!\n\n"
        "🤫 Більше крутих ботів у @cmpdchtr_bots"
    )
    await message.answer(welcome_text)

# Universal video handler - detects URLs and downloads using Cobalt or yt-dlp
@dp.message(F.text.regexp(r'https?://'))
async def video_handler(message: types.Message):
    if message.text is None:
        return
    
    url = message.text.strip()
    
    # Check if it's YouTube - use yt-dlp
    if is_youtube_url(url):
        status_message = await message.answer("⚡ Завантажую YouTube відео...")
        
        try:
            video_path = await download_youtube_video(url, status_message)
            
            if video_path and video_path.exists():
                await status_message.edit_text("📤 Відправляю відео...")
                video_file = FSInputFile(video_path)
                await message.answer_video(video=video_file)
                await status_message.delete()
                
                # Clean up
                video_path.unlink()
        except Exception as e:
            logging.error(f"Error downloading YouTube video: {e}")
            await status_message.edit_text(
                f"❌ Помилка при завантаженні YouTube відео: {str(e)}\n\n"
                f"Спробуйте інше посилання."
            )
        return
    
    # For other platforms, use Cobalt API
    status_message = await message.answer("⚡ Завантажую відео через Cobalt API...")
    
    try:
        # Get download info from Cobalt API
        result = await download_with_cobalt(url)
        status = result.get("status")
        
        if status == "error":
            error_code = result.get("error", {}).get("code", "unknown")
            await status_message.edit_text(f"❌ Помилка: {error_code}\n\nПеревірте посилання та спробуйте ще раз.")
            return
        
        if status == "picker":
            # Multiple items (like Instagram carousel or TikTok slideshow)
            picker_items = result.get("picker", [])
            await status_message.edit_text(f"� Знайдено {len(picker_items)} елементів. Завантажую...")
            
            for item in picker_items[:10]:  # Limit to 10 items
                item_url = item.get("url")
                if item_url:
                    try:
                        if item.get("type") == "photo":
                            await message.answer_photo(photo=item_url)
                        else:
                            await message.answer_video(video=URLInputFile(item_url))
                    except Exception as e:
                        logging.error(f"Error sending picker item: {e}")
                        continue
            
            await status_message.delete()
            return
        
        if status in ["tunnel", "redirect"]:
            # Single video/audio file
            download_url = result.get("url")
            filename = result.get("filename", "video.mp4")
            
            if not download_url:
                await status_message.edit_text("❌ Не вдалося отримати посилання на завантаження.")
                return
            
            # Download file through server to bypass Cloudflare protection
            file_path = None
            try:
                await status_message.edit_text("📥 Завантажую файл...")
                
                downloads_dir = Path("downloads")
                downloads_dir.mkdir(exist_ok=True)
                file_path = downloads_dir / filename
                
                # Download file with proper headers
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "*/*",
                    "Referer": COBALT_API_URL
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(download_url, headers=headers) as response:
                        if response.status != 200:
                            raise Exception(f"Failed to download: HTTP {response.status}")
                        
                        # Check file size
                        content_length = response.headers.get("Content-Length")
                        if content_length:
                            file_size = int(content_length)
                            
                            if file_size > MAX_FILE_SIZE:
                                limit_text = "2 ГБ" if bot_api_server else "50 МБ"
                                await status_message.edit_text(
                                    f"⚠️ Відео занадто велике ({file_size / (1024 * 1024):.1f} МБ).\n\n"
                                    f"Ліміт Telegram: {limit_text}. Ось пряме посилання:\n"
                                    f"📥 [Завантажити відео]({download_url})",
                                    parse_mode="Markdown",
                                    disable_web_page_preview=True
                                )
                                return
                        
                        # Download file
                        with open(file_path, "wb") as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                
                # Send video
                await status_message.edit_text("📤 Відправляю відео...")
                video_file = FSInputFile(file_path)
                await message.answer_video(video=video_file)
                await status_message.delete()
                
                # Clean up
                if file_path.exists():
                    file_path.unlink()
                    
            except Exception as e:
                logging.error(f"Error downloading/sending video: {e}")
                await status_message.edit_text(
                    f"❌ Помилка при завантаженні.\n\n"
                    f"Спробуйте пряме посилання:\n"
                    f"📥 [Завантажити відео]({download_url})",
                    parse_mode="Markdown",
                    disable_web_page_preview=True
                )
                # Clean up on error
                if file_path and file_path.exists():
                    file_path.unlink()
            return
        
        # Unsupported status
        await status_message.edit_text(f"❌ Непідтримуваний тип відповіді: {status}")
        
    except Exception as e:
        logging.error(f"Error downloading video: {e}")
        await status_message.edit_text(
            f"❌ Помилка при завантаженні: {str(e)}\n\n"
            f"Можливо, платформа не підтримується або посилання неправильне."
        )

# Reacting to all other messages
@dp.message(F.text)
async def other_handler(message: types.Message):
    await message.answer(
        "❌ Надішліть посилання на відео з підтримуваних платформ:\n\n"
        "YouTube, TikTok, Instagram, Twitter/X, Reddit, Twitch, Vimeo, "
        "Facebook, Dailymotion, Vine, Tumblr, Bilibili та інші!"
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())