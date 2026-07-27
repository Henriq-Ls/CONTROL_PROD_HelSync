# 📁 _FERRAMENTAS_/Falar_Descrever.py

ffmpeg_path = r"_FERRAMENTAS_\ffmpeg\bin\ffmpeg.exe"

def Falar_Funtion(st):
    import subprocess
    import tempfile
    import speech_recognition as sr
    from streamlit_mic_recorder import mic_recorder
    if "texto_area" not in st.session_state:
        st.session_state["texto_area"] = ""

    # MICROFONE
    audio = mic_recorder(
            start_prompt="🎤 Como pode ser usado:",
            stop_prompt="⏹ Parar",
            just_once=True,
            key="mic_1",width=True
        )

    if audio:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
            f.write(audio["bytes"])
            webm_path = f.name

        wav_path = webm_path.replace(".webm", ".wav")

        subprocess.run([
            ffmpeg_path, "-y", "-i", webm_path, wav_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            try:
                texto = recognizer.recognize_google(audio_data, language="pt-BR")
                atual = st.session_state["texto_area"]
                st.session_state["texto_area"] = (atual + " " + texto).strip()
            except sr.UnknownValueError:
                st.warning("Nao entendi o audio.")
            except sr.RequestError:
                st.error("Erro no reconhecimento.")

    # RESULTADO
    st.text_area("Como pode ser usado:", key="texto_area", height=259,label_visibility='collapsed')

    return st.session_state["texto_area"]

def Falar_Descrever(st):
    import subprocess
    import tempfile
    import speech_recognition as sr
    from streamlit_mic_recorder import mic_recorder
    if "texto_area2" not in st.session_state:
        st.session_state["texto_area2"] = ""

    # MICROFONE
    audio = mic_recorder(
        start_prompt="🎤 Falar Descrição:",
        stop_prompt="⏹ Parar",
        just_once=True,
        key="mic_2",width=True
    )

    if audio:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
            f.write(audio["bytes"])
            webm_path = f.name

        wav_path = webm_path.replace(".webm", ".wav")

        subprocess.run([
            ffmpeg_path, "-y", "-i", webm_path, wav_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            try:
                texto = recognizer.recognize_google(audio_data, language="pt-BR")
                atual = st.session_state["texto_area2"]
                st.session_state["texto_area2"] = (atual + " " + texto).strip()
            except sr.UnknownValueError:
                st.warning("Nao entendi o audio.")
            except sr.RequestError:
                st.error("Erro no reconhecimento.")

    # RESULTADO
    st.text_area("📝 Descrição:", key="texto_area2", height=259,label_visibility='collapsed')

    return st.session_state["texto_area2"]
