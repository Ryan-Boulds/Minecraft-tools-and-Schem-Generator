import librosa
import numpy as np
from tkinter import filedialog, messagebox

def load_audio_data(app):
    path = filedialog.askopenfilename(
        filetypes=[("Audio Files", "*.mp3 *.wav *.ogg")]
    )
    if not path:
        return
    
    try:
        # 1. Force use of soundfile or audioread if default fails
        # librosa.load can sometimes fail on mp3 if ffmpeg isn't in PATH
        y, sr = librosa.load(path, sr=2000) 
        
        if y is None or len(y) == 0:
            raise ValueError("Audio data is empty or could not be decoded.")

        duration = librosa.get_duration(y=y, sr=sr)
        
        # 2. Normalize safely
        max_val = np.max(np.abs(y))
        if max_val > 0:
            y = y / max_val
        
        # 3. Update app state
        app.audio_path = path
        app.audio_waveform = y
        app.audio_duration = duration
        
        # 4. Thread-safe UI refresh
        if hasattr(app, "_refresh_builder") and app._refresh_builder is not None:
            # Wrap in after() to ensure it runs on the main GUI thread
            app.main_app.root.after(0, app._refresh_builder)
            
    except Exception as e:
        # Clear state on failure so the timeline doesn't try to draw old/broken data
        app.audio_path = None
        app.audio_waveform = None
        messagebox.showerror("Audio Error", f"Failed to load audio: {e}\n\nTip: Ensure ffmpeg is installed for MP3 support.")