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
        return "Paid 5000 for miscellaneous expenses today"


def transcribe_audio(audio_bytes: bytes, filename: str = "audio.wav") -> str:
    """
    Transcribe audio bytes to text.
    Uses mock transcription — swap implementation for real Whisper.
    """
    # Future: save to temp file, run Whisper, delete temp file
    # whisper_model = whisper.load_model("base")
    # result = whisper_model.transcribe(temp_path)
    # return result["text"]
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
