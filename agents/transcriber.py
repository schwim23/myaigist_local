import os
import tempfile
import uuid
import requests
from pathlib import Path
from typing import Optional

class Transcriber:
    """Agent responsible for audio transcription (Whisper.cpp) and text-to-speech (Piper)"""

    def __init__(self):
        """Initialize the Transcriber with Whisper and Piper endpoints"""
        try:
            self.whisper_host = os.getenv('WHISPER_HOST', 'http://localhost:9000')
            self.piper_host = os.getenv('PIPER_HOST', 'http://localhost:10200')
            self.audio_dir = Path('static/audio')
            self.audio_dir.mkdir(exist_ok=True)
            
            # Supported audio and video formats for transcription
            self.supported_formats = [
                # Audio formats
                '.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.wma', '.mpga',
                # Video formats (audio will be extracted)
                '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv', '.m4v', '.3gp', '.mpeg', '.mpg'
            ]


            print(f"✅ Transcriber initialized (Whisper: {self.whisper_host}, Piper: {self.piper_host})")
            
        except Exception as e:
            print(f"❌ Error initializing Transcriber: {e}")
            raise
    
    def transcribe_audio(self, media_file_path: str) -> str:
        """
        Transcribe audio or video file using Whisper.cpp
        
        Args:
            media_file_path (str): Path to the audio or video file
            
        Returns:
            str: Transcribed text
        """
        try:
            print(f"🎬 Transcribing media file: {media_file_path}")
            
            if not os.path.exists(media_file_path):
                raise FileNotFoundError(f"Media file not found: {media_file_path}")
            
            # Check file size (reasonable limit for processing)
            file_size = os.path.getsize(media_file_path)
            if file_size > 25 * 1024 * 1024:  # 25MB
                raise ValueError("Media file too large. Maximum size is 25MB.")
            
            # Check if file extension is supported
            file_ext = Path(media_file_path).suffix.lower()
            if file_ext not in self.supported_formats:
                print(f"⚠️  Unsupported format {file_ext}, attempting transcription anyway...")
            
            # Determine if it's audio or video
            video_formats = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv', '.m4v', '.3gp', '.mpeg', '.mpg']
            is_video = file_ext in video_formats
            
            if is_video:
                print(f"🎥 Processing video file: {file_ext} (audio will be extracted)")
            else:
                print(f"🎵 Processing audio file: {file_ext}")
            
            # Check if we need to convert the format for Whisper
            whisper_supported_formats = ['.flac', '.m4a', '.mp3', '.mp4', '.mpeg', '.mpga', '.oga', '.ogg', '.wav', '.webm']
            
            # Use Whisper.cpp HTTP API for transcription
            with open(media_file_path, 'rb') as media_file:
                files = {'audio_file': (Path(media_file_path).name, media_file, 'audio/*')}
                params = {
                    'task': 'transcribe',
                    'language': 'en',
                    'output': 'txt'
                }

                response = requests.post(
                    f"{self.whisper_host}/asr",
                    files=files,
                    params=params,
                    timeout=300  # 5 minute timeout for large files
                )
                response.raise_for_status()

                transcribed_text = response.text.strip()
            
            media_type = "video" if is_video else "audio"
            print(f"✅ Successfully transcribed {media_type}: {len(transcribed_text)} characters")
            return transcribed_text.strip()
            
        except Exception as e:
            error_msg = f"Error transcribing media: {str(e)}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
    
    def text_to_speech(self, text: str, voice: str = "nova") -> Optional[str]:
        """
        Convert text to speech using Piper TTS
        
        Args:
            text (str): Text to convert to speech
            voice (str): Voice to use (alloy, echo, fable, onyx, nova, shimmer)
            
        Returns:
            Optional[str]: URL path to generated audio file, or None if failed
        """
        try:
            if not text or len(text.strip()) == 0:
                print("⚠️  No text provided for TTS")
                return None
            
            # Limit text length for TTS (reasonable limit for processing)
            if len(text) > 4000:
                text = text[:4000] + "..."
                print("⚠️  Text truncated for TTS (4000 char limit)")
            
            print(f"🔊 Generating speech for {len(text)} characters")
            
            # Generate unique filename
            audio_id = str(uuid.uuid4())
            audio_filename = f"speech_{audio_id}.wav"
            audio_path = self.audio_dir / audio_filename

            # Generate speech using Piper
            piper_voice = os.getenv('PIPER_VOICE', 'en_US-lessac-medium')
            response = requests.post(
                f"{self.piper_host}/api/tts",
                json={
                    'text': text,
                    'voice': piper_voice
                },
                timeout=60
            )
            response.raise_for_status()

            # Save audio file
            with open(audio_path, 'wb') as f:
                f.write(response.content)
            
            # Return URL path for the frontend
            audio_url = f"/static/audio/{audio_filename}"
            print(f"✅ Generated speech audio: {audio_url}")
            return audio_url
            
        except Exception as e:
            print(f"❌ Error generating speech: {e}")
            return None
    
    def transcribe(self, media_file) -> str:
        """
        Transcribe uploaded audio/video file object (Flask file upload)
        
        Args:
            media_file: Flask uploaded file object (audio or video)
            
        Returns:
            str: Transcribed text
        """
        try:
            # Save uploaded file temporarily
            temp_dir = tempfile.gettempdir()
            temp_filename = f"temp_media_{uuid.uuid4()}{Path(media_file.filename).suffix}"
            temp_path = os.path.join(temp_dir, temp_filename)
            
            print(f"🎬 Processing uploaded media file: {media_file.filename}")
            
            # Save the uploaded file
            media_file.save(temp_path)
            
            try:
                # Transcribe the temporary file
                result = self.transcribe_audio(temp_path)
                return result
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
        except Exception as e:
            error_msg = f"Error transcribing uploaded file: {str(e)}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
    
    def cleanup_old_files(self, max_age_hours: int = 24):
        """
        Clean up old audio files to save disk space
        
        Args:
            max_age_hours (int): Maximum age of files to keep in hours
        """
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            cleaned_count = 0
            for audio_file in self.audio_dir.glob("*.mp3"):
                file_age = current_time - audio_file.stat().st_mtime
                if file_age > max_age_seconds:
                    audio_file.unlink()
                    cleaned_count += 1
            
            if cleaned_count > 0:
                print(f"🧹 Cleaned up {cleaned_count} old audio files")
                
        except Exception as e:
            print(f"⚠️  Error cleaning up audio files: {e}")
    
    def get_supported_formats(self) -> list:
        """Get list of supported audio and video formats"""
        return self.supported_formats.copy()
    
    def get_audio_formats(self) -> list:
        """Get list of supported audio formats only"""
        audio_formats = ['.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.wma', '.mpga']
        return audio_formats
    
    def get_video_formats(self) -> list:
        """Get list of supported video formats only"""
        video_formats = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv', '.m4v', '.3gp', '.mpeg', '.mpg']
        return video_formats
    
    def is_media_file(self, filename: str) -> bool:
        """Check if a filename is a supported media file"""
        if not filename:
            return False
        file_ext = Path(filename).suffix.lower()
        return file_ext in self.supported_formats
    
    def get_available_voices(self) -> list:
        """Get list of available TTS voices"""
        return ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]