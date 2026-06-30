import whisper
import os

# Load model once when server starts
print("Loading Whisper model...")
whisper_model = whisper.load_model("small")
print("Whisper model loaded!")

def speech_to_text(audio_path: str) -> str:
    """
    Converts interviewee's audio answer to text.
    Returns transcribed text for Sarah's evaluation.
    """
    result = whisper_model.transcribe(audio_path, language="en")
    return result["text"].strip()