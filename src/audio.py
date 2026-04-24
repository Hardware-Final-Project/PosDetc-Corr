from gtts import gTTS

def gTTS_audio(text, filename="temp.mp3"):
    tts = gTTS(text=text, lang="zh-tw")
    tts.save(filename)
