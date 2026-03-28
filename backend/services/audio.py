"""
Audio transcription service.

Currently provides a mock transcription that simulates converting audio to text.
The transcribed text is then passed through the standard text parser.

To integrate real Whisper:
    1. pip install openai-whisper
    2. Replace mock_transcribe() with whisper.load_model("base").transcribe(audio_path)
"""

import tempfile
import os
from typing import Dict

# Ensure whisper can find ffmpeg binary when installed by winget.
# Adjust this path if your installation location differs.
FFMPEG_PATH = r"C:\Users\acers\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin"
if os.path.isdir(FFMPEG_PATH):
    os.environ["PATH"] = FFMPEG_PATH + os.pathsep + os.environ.get("PATH", "")

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

from services.parser import parse_text_input


def mock_transcribe(audio_bytes: bytes, filename: str = "audio.wav") -> str:
    """
    Mock audio-to-text transcription.

    In production, this would use OpenAI Whisper or a similar STT engine.
    For now, returns a realistic placeholder transcript based on the filename.
    """
    # Simulate different transcripts based on filename hints
    lower_name = filename.lower()
    if "rent" in lower_name:
        return "Pay 15000 rent on the first of next month"
    elif "salary" in lower_name:
        return "Received salary of 50000 today"
    elif "groceries" in lower_name or "grocery" in lower_name:
        return "Bought groceries for 3000 today"
    else:
        # Generic mock transcript
        return "paid 12500 for office supplies today"


def transcribe_audio(audio_bytes: bytes, filename: str = "audio.wav") -> str:
    """
    Transcribe audio bytes to text.
    Uses OpenAI Whisper if available, otherwise mock transcription.
    """
    if WHISPER_AVAILABLE:
        # Use real Whisper
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name

        try:
            model = whisper.load_model("base")
            result = model.transcribe(temp_path)
            transcript = result["text"].strip()
            print(f"Whisper transcript: '{transcript}'")
            if not transcript:
                raise RuntimeError("Whisper returned empty transcription")
            return transcript
        except Exception as e:
            print(f"Whisper failed: {e}")
            raise
        finally:
            os.unlink(temp_path)
    else:
        # Fallback to mock, only when whisper is unavailable.
        return mock_transcribe(audio_bytes, filename)


def parse_audio_input(audio_bytes: bytes, filename: str = "audio.wav") -> Dict:
    """
    Main audio processing entry point.
    1. Transcribe audio to text
    2. Parse the transcribed text using the standard NLP parser

    Returns the same dict structure as parser.parse_text_input(),
    plus the raw transcript.
    """
    # Step 1: Audio → Text
    transcript = transcribe_audio(audio_bytes, filename)

    # Step 2: Text → Structured data
    parsed = parse_text_input(transcript)

    # Slightly lower confidence for audio (transcription adds uncertainty)
    parsed["confidence_score"] = round(parsed["confidence_score"] * 0.85, 2)

    # Attach the raw transcript for transparency
    parsed["transcript"] = transcript

    return parsed
