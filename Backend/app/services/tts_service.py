from gtts import gTTS
import uuid
import os

def text_to_speech(text: str) -> str:
    """
    Converts question text to audio file.
    Returns the path of the saved audio file.
    """
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    filename = f"question_{uuid.uuid4().hex}.mp3"
    filepath = os.path.join(upload_dir, filename)
    
    tts = gTTS(text=text, lang='en', slow=False)
    tts.save(filepath)
    
    return filepath