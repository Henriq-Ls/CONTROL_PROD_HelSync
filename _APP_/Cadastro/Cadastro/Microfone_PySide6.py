"""Captura e transcrição de voz usada pela interface PySide6."""

import audioop
import math
from collections import deque
from threading import Event
from time import monotonic
from typing import Callable

from _LOGS_ import log


class RecordingCancelled(RuntimeError):
    """Indica uma parada solicitada normalmente pelo usuário."""


def _verificar_cancelamento(
    cancel_event: Event | None,
    fase: str,
    inicio: float,
) -> None:
    """Interrompe a captura assim que o pedido de parada for observado."""
    if cancel_event is not None and cancel_event.is_set():
        duracao_ms = int((monotonic() - inicio) * 1000)
        log.aviso(
            "Microfone",
            "_verificar_cancelamento",
            f"cancelamento observado na fase '{fase}' "
            f"após {duracao_ms}ms",
        )
        raise RecordingCancelled("Gravação cancelada.")


def _ler_audio_cancelavel(
    recognizer,
    source,
    cancel_event: Event | None,
    inicio: float,
    timeout: float | None = None,
):
    """Captura até o usuário solicitar a parada, verificando-a por bloco."""
    import speech_recognition as sr

    stream = getattr(source, "stream", None)
    chunk_size = getattr(source, "CHUNK", None)
    if chunk_size is None and stream is not None:
        chunk_size = getattr(stream, "_frames_per_buffer", None)
    try:
        chunk_size = int(chunk_size)
    except (TypeError, ValueError):
        chunk_size = 1024
    if chunk_size <= 0:
        chunk_size = 1024

    sample_rate = getattr(source, "SAMPLE_RATE", None)
    if sample_rate is None and stream is not None:
        sample_rate = getattr(stream, "_rate", None)
    try:
        sample_rate = int(sample_rate)
    except (TypeError, ValueError):
        sample_rate = 16000
    if sample_rate <= 0:
        sample_rate = 16000

    sample_width = getattr(source, "SAMPLE_WIDTH", None)
    try:
        sample_width = int(sample_width)
    except (TypeError, ValueError):
        sample_width = 2
    if sample_width <= 0:
        sample_width = 2

    seconds_per_buffer = chunk_size / sample_rate
    elapsed_time = 0.0
    frames: deque[bytes] = deque()
    non_speaking_buffer_count = max(
        1,
        math.ceil(recognizer.non_speaking_duration / seconds_per_buffer),
    )
    timeout_text = "sem limite" if timeout is None else f"{timeout:.1f}s"

    log.info(
        "Microfone",
        "_ler_audio_cancelavel",
        f"captura em blocos iniciada; bloco={seconds_per_buffer:.3f}s; "
        f"timeout_inicial={timeout_text}; parada=botão",
    )

    while True:
        _verificar_cancelamento(cancel_event, "aguardando início da fala", inicio)
        if timeout is not None and elapsed_time > timeout:
            raise sr.WaitTimeoutError("tempo limite aguardando fala")

        # O MicrophoneStream do SpeechRecognition já desativa o overflow
        # internamente. Passar esse argumento novamente quebra versões em que
        # o wrapper expõe apenas read(size).
        buffer = source.stream.read(chunk_size)
        elapsed_time += seconds_per_buffer
        frames.append(buffer)
        if len(frames) > non_speaking_buffer_count:
            frames.popleft()

        if audioop.rms(buffer, source.SAMPLE_WIDTH) > recognizer.energy_threshold:
            log.info(
                "Microfone",
                "_ler_audio_cancelavel",
                f"fala detectada após {elapsed_time:.3f}s de espera",
            )
            break

    while True:
        if cancel_event is not None and cancel_event.is_set():
            log.info(
                "Microfone",
                "_ler_audio_cancelavel",
                "parada solicitada pelo usuário; finalizando o áudio "
                "capturado para transcrição",
            )
            break

        buffer = source.stream.read(chunk_size)
        elapsed_time += seconds_per_buffer
        frames.append(buffer)

    audio = sr.AudioData(
        b"".join(frames),
        sample_rate,
        sample_width,
    )
    log.info(
        "Microfone",
        "_ler_audio_cancelavel",
        f"captura de áudio concluída; duração={elapsed_time:.3f}s",
    )
    return audio


def reconhecer_microfone(
    progress: Callable[[str], None] | None = None,
    cancel_event: Event | None = None,
) -> str:
    """Captura voz de um dispositivo de entrada e converte para pt-BR."""
    inicio = monotonic()
    log.info(
        "Microfone",
        "reconhecer_microfone",
        "iniciando captura de voz; cancelamento cooperativo habilitado",
    )
    try:
        import speech_recognition as sr
    except ImportError as exc:
        log.erro(
            "Microfone",
            "reconhecer_microfone",
            "SpeechRecognition/PyAudio não está disponível",
        )
        raise RuntimeError(
            "O reconhecimento por microfone precisa do pacote "
            "SpeechRecognition e do PyAudio instalados."
        ) from exc

    recognizer = sr.Recognizer()
    try:
        pyaudio_module = sr.Microphone.get_pyaudio()
        audio_probe = pyaudio_module.PyAudio()
        try:
            device_index: int | None = None
            device_name = ""

            try:
                default_device = audio_probe.get_default_input_device_info()
                if int(default_device.get("maxInputChannels", 0)) > 0:
                    device_index = int(default_device["index"])
                    device_name = str(default_device.get("name", ""))
                    log.info(
                        "Microfone",
                        "reconhecer_microfone",
                        f"dispositivo padrão encontrado: índice={device_index}, "
                        f"nome={device_name}",
                    )
            except (OSError, IOError) as exc:
                log.aviso(
                    "Microfone",
                    "reconhecer_microfone",
                    f"dispositivo padrão indisponível: {exc}",
                )

            if device_index is None:
                for index in range(audio_probe.get_device_count()):
                    info = audio_probe.get_device_info_by_index(index)
                    if int(info.get("maxInputChannels", 0)) > 0:
                        device_index = index
                        device_name = str(info.get("name", ""))
                        log.info(
                            "Microfone",
                            "reconhecer_microfone",
                            f"primeiro dispositivo de entrada encontrado: "
                            f"índice={device_index}, nome={device_name}",
                        )
                        break
        finally:
            audio_probe.terminate()

        if device_index is None:
            log.erro(
                "Microfone",
                "reconhecer_microfone",
                "nenhum dispositivo de entrada encontrado",
            )
            raise RuntimeError(
                "Nenhum microfone de entrada foi encontrado no Windows. "
                "Conecte ou habilite um microfone e tente novamente."
            )

        if progress:
            progress(f"Microfone selecionado: {device_name}")

        log.info(
            "Microfone",
            "reconhecer_microfone",
            f"abrindo dispositivo de entrada: índice={device_index}",
        )
        with sr.Microphone(device_index=device_index) as source:
            _verificar_cancelamento(cancel_event, "antes da calibração", inicio)
            if progress:
                progress("Ajustando o microfone...")
            log.info(
                "Microfone",
                "reconhecer_microfone",
                "calibrando ruído ambiente por 0,5 segundo",
            )
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            _verificar_cancelamento(cancel_event, "após a calibração", inicio)
            if progress:
                progress(
                    "Gravando; clique novamente para parar e transcrever."
                )
            log.info(
                "Microfone",
                "reconhecer_microfone",
                "aguardando fala do usuário",
            )
            audio = _ler_audio_cancelavel(
                recognizer,
                source,
                cancel_event,
                inicio,
                timeout=None,
            )
    except sr.WaitTimeoutError as exc:
        log.erro(
            "Microfone",
            "reconhecer_microfone",
            "nenhuma fala foi capturada dentro do tempo permitido",
        )
        raise RuntimeError("Nenhuma fala foi capturada pelo microfone.") from exc
    except RuntimeError:
        raise
    except (AssertionError, AttributeError, OSError, IOError) as exc:
        log.erro(
            "Microfone",
            "reconhecer_microfone",
            f"falha ao acessar o dispositivo: {exc}",
        )
        raise RuntimeError(
            "Não foi possível acessar o microfone. "
            "Verifique as permissões do Windows, o dispositivo de entrada "
            f"e a instalação do PyAudio. Detalhe: {exc}"
        ) from exc

    try:
        if progress:
            progress("Convertendo fala em texto...")
        log.info(
            "Microfone",
            "reconhecer_microfone",
            "enviando áudio para transcrição pt-BR",
        )
        texto = recognizer.recognize_google(audio, language="pt-BR")
        log.ok(
            "Microfone",
            "reconhecer_microfone",
            f"transcrição concluída ({len(texto)} caracteres)",
        )
        return texto
    except sr.UnknownValueError as exc:
        log.erro(
            "Microfone",
            "reconhecer_microfone",
            "o áudio foi capturado, mas não foi compreendido",
        )
        raise RuntimeError("Não foi possível entender o áudio.") from exc
    except sr.RequestError as exc:
        log.erro(
            "Microfone",
            "reconhecer_microfone",
            f"serviço de reconhecimento não respondeu: {exc}",
        )
        raise RuntimeError(
            "O serviço de reconhecimento de voz não respondeu."
        ) from exc