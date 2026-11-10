"""Ponto de entrada do hen-place-control.

A ordem deste bootstrap é importante:
    1. garantir o diretório do projeto no sys.path;
    2. ativar o faulthandler antes do PySide6;
    3. criar o logger da sessão;
    4. inicializar o AppData do usuário;
    5. registrar o capturador global de exceções;
    6. criar o QApplication e abrir a janela principal.
"""

from __future__ import annotations

import faulthandler
import os
import sys
import tempfile
import traceback


_DIR = os.path.dirname(os.path.abspath(__file__))
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)


faulthandler.enable()


from _LOGS_ import log
from _APPDATA_ import appdata


appdata.inicializar()


def _excepthook(tipo, valor, tb) -> None:
    """Registra exceções não tratadas antes do tratamento padrão do Python."""
    texto = "".join(traceback.format_exception(tipo, valor, tb))
    log.crash("main.py", "excepthook", texto)
    sys.__excepthook__(tipo, valor, tb)


sys.excepthook = _excepthook


if sys.platform == "win32":
    try:
        import ctypes as _ctypes

        _PVECTORED_HANDLER = _ctypes.WINFUNCTYPE(
            _ctypes.c_long,
            _ctypes.c_void_p,
        )

        @_PVECTORED_HANDLER
        def _veh_com_filter(exc_info):
            try:
                exc_rec = _ctypes.c_size_t.from_address(exc_info).value
                code = _ctypes.c_uint.from_address(exc_rec).value
                flags = _ctypes.c_uint.from_address(exc_rec + 4).value
                if code == 0x8001010D and not (flags & 0x1):
                    return -1
            except Exception:
                pass
            return 1

        _ctypes.windll.kernel32.AddVectoredExceptionHandler(
            1,
            _veh_com_filter,
        )
    except Exception as exc:
        log.aviso(
            "main.py",
            "veh_filter",
            f"filtro VEH não disponível: {exc}",
        )


from PySide6.QtCore import QLockFile, QtMsgType, qInstallMessageHandler
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from _CONFIGURA_ import (
    FONTE_NOME_UI,
    FONTE_TAMANHO_BASE,
    IMAGEM_ICO,
    TITULO_APP,
)
from _APP_.main_window import MainWindow


_LOCK_PATH = os.path.join(tempfile.gettempdir(), "hen-place-control.lock")
_lock_file = QLockFile(_LOCK_PATH)
_lock_file.setStaleLockTime(0)


def _qt_msg_handler(mode, context, message) -> None:
    """Encaminha mensagens relevantes do Qt para o log da sessão."""
    del context
    if "setPointSize" in message and "Point size <= 0" in message:
        return
    if mode == QtMsgType.QtWarningMsg:
        log.aviso("Qt", "msg_handler", message)
    elif mode in (QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
        log.erro("Qt", "msg_handler", message)


def main() -> int:
    if not _lock_file.tryLock(100):
        app_tmp = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.warning(
            None,
            "Já está aberto",
            "O aplicativo já está em execução.",
        )
        del app_tmp
        return 0

    log.info("main.py", "main", f"{TITULO_APP} iniciando...")
    qInstallMessageHandler(_qt_msg_handler)

    app = QApplication(sys.argv)
    app.setApplicationName(TITULO_APP)

    if FONTE_TAMANHO_BASE > 0:
        app.setFont(QFont(FONTE_NOME_UI, FONTE_TAMANHO_BASE))

    if os.path.isfile(IMAGEM_ICO):
        app.setWindowIcon(QIcon(IMAGEM_ICO))
        log.ok("main.py", "main", f"ícone carregado: {IMAGEM_ICO}")
    else:
        log.aviso("main.py", "main", f"ícone não encontrado: {IMAGEM_ICO}")

    log.ok("main.py", "main", "QApplication criada")
    window = MainWindow()
    window.show()
    log.ok("main.py", "main", "MainWindow exibida")

    code = app.exec()
    log.info("main.py", "main", f"aplicação encerrada com código {code}")
    return code


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        log.crash("main.py", "__main__", traceback.format_exc())
        raise