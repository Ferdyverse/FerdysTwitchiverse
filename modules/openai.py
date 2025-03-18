import aiohttp
import os
import uuid
import asyncio
import config
import logging
from mutagen.mp3 import MP3

logger = logging.getLogger("uvicorn.error.open_ai")

async def generate_tts_audio(text, voice="nova"):
    """Generate a unique TTS audio file from text using OpenAI API."""
    os.makedirs(config.TTS_AUDIO_PATH, exist_ok=True)  # Ensure the directory exists
    file_name = f"tts_{uuid.uuid4().hex}.mp3"
    file_path = os.path.join(config.TTS_AUDIO_PATH, file_name)

    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {config.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "tts-1",
            "input": text,
            "voice": voice
        }

        async with session.post("https://api.openai.com/v1/audio/speech", json=data, headers=headers) as response:
            if response.status == 200:
                audio_data = await response.read()

                with open(file_path, "wb") as f:
                    f.write(audio_data)

                return file_name  # Return only the file name for web overlay playback
            else:
                error_message = await response.text()
                logger.error(f"❌ TTS API Error: {error_message}")
                return None

async def delete_tts_file(file_path, duration):
        """Delete the TTS audio file"""
        await asyncio.sleep(5)  # Safety sleep
        if os.path.exists(file_path):
            await asyncio.sleep(duration)
            os.remove(file_path)
            logger.info(f"🗑️ Deleted TTS file: {file_path}")

def get_mp3_duration(file_path):
    """Get the duration of an MP3 file in seconds."""
    try:
        audio = MP3(file_path)
        return audio.info.length  # Returns duration in seconds
    except Exception as e:
        print(f"❌ Error getting MP3 duration: {e}")
        return None
