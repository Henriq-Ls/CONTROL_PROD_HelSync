"""Núcleo compartilhado da aplicação desktop PySide6.

Este módulo concentra as regras que não pertencem diretamente a uma tela:
 banco SQLite, tarefas em segundo plano, cadastro de mídias e produção.
"""

from __future__ import annotations

import os
import json
import math
import re
import shutil
import sqlite3
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, Qt, Signal, Slot

from _LOGS_ import log
from _THREADS_.thread_segura import ThreadSegura
from _APP_.Cadastro.Cadastro.Microfone_PySide6 import RecordingCancelled
from _IAS_.ia_memory import init_memory_schema


PROJECT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_DIR / "_BANCOS_" / "Base_Dados.db"
DEFAULT_PRODUCTS_DIR = Path.home() / "Downloads" / "PRODUTOS"
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
VIDEO_EXTENSIONS = (".mp4", ".mov", ".avi", ".mkv")
MEDIA_EXTENSIONS = IMAGE_EXTENSIONS + VIDEO_EXTENSIONS
PASTA_AJUSTE_GERAL = "a_ajuste_geral"
PASTA_PREVIEWS = "previews"
PASTA_SEM_FUNDO = "b_sem_fundo"
PASTA_FUNDO_BRANCO = "c_fundo_branco"
PASTA_MEDIDAS = "d_medidas"
PASTA_FUNDO_CAPA = "E_fundo_capa"
PASTA_VIDEO_CONVERTIDO = "F_video_shopee"
PASTA_VIDEO_LEGADO = "e_video_shopee_convertido"

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))


def listar_imagens(
    pasta: str | Path,
    ordenacao: str = "Nome (A-Z)",
) -> list[str]:
    """Lista mídias conforme a ordenação escolhida no cadastro."""
    pasta = Path(pasta)
    if not pasta.exists():
        return []
    arquivos = [
        nome
        for nome in os.listdir(pasta)
        if nome.lower().endswith(MEDIA_EXTENSIONS)
    ]
    if ordenacao == "Nome (Z-A)":
        return sorted(arquivos, key=str.casefold, reverse=True)
    if ordenacao == "Data (mais antiga)":
        return sorted(
            arquivos,
            key=lambda nome: (pasta / nome).stat().st_mtime,
        )
    if ordenacao == "Data (mais recente)":
        return sorted(
            arquivos,
            key=lambda nome: (pasta / nome).stat().st_mtime,
            reverse=True,
        )
    return sorted(arquivos, key=str.casefold)


def gerar_referencia(nome: str) -> str:
    """Replica a regra de referência do módulo Functions.py."""
    palavras = [
        palavra
        for palavra in str(nome).strip().lower().replace("_", " ").split()
        if len(palavra) >= 2
    ]
    if len(palavras) == 1:
        return palavras[0][0] + palavras[0][1] + palavras[0][-1]
    if len(palavras) == 2:
        return palavras[0][0] + palavras[1][0] + palavras[1][-1]
    if len(palavras) >= 3:
        return palavras[0][0] + palavras[1][0] + palavras[2][0]
    return "pro"


def gerar_config_ref(
    tipo: str,
    qt_variacoes: int,
    tem_kit_tambem: str,
    qt_kit_tambem: int,
    qt_pecas_kit: int,
    tipo_var_kit: str,
    qt_kits: int,
) -> str:
    """Replica a configuração de produto usada pelo cadastro original."""
    resultado = f"TIPO:{tipo.upper()}"
    if tipo == "Único":
        resultado += f"|VAR={qt_variacoes}"
        if tem_kit_tambem == "Sim":
            resultado += f"|KIT=YES|PECAS={qt_kit_tambem}|QTS_KITS={qt_kits}"
        else:
            resultado += "|KIT=NO"
    elif tipo == "Kit":
        resultado += (
            f"|PECAS={qt_pecas_kit}|VAR={tipo_var_kit.upper()}"
            f"|QTS_KITS={qt_kits}"
        )
    return resultado


def parse_tipo_kit(config: str) -> dict[str, str]:
    valores: dict[str, str] = {}
    for parte in str(config).split("|"):
        if ":" in parte and "=" not in parte:
            chave, valor = parte.split(":", 1)
        elif "=" in parte:
            chave, valor = parte.split("=", 1)
        else:
            continue
        valores[chave.strip().upper()] = valor.strip()
    return valores


def init_database() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS A_ENTRADA(
                PRODUTO TEXT PRIMARY KEY NOT NULL,
                REFERENCIA TEXT,
                DIRETORIO TEXT,
                DESCRITION TEXT,
                SERVENTIA TEXT,
                ACOMPANHA TEXT,
                ACABAMENTO TEXT,
                KIT TEXT,
                OBS TEXT
            );
            CREATE TABLE IF NOT EXISTS VENDAS(
                ID TEXT NOT NULL,
                DATA TEXT,
                NOME_PRODUTO TEXT,
                KIT TEXT,
                PLATAFORMAS_POSTADO TEXT,
                PLATAFORMA_VENDA TEXT,
                CLIENTE_NOME TEXT,
                CLIENTE_CPF TEXT,
                CLIENTE_TELEFONE TEXT,
                ENDERECO TEXT,
                VALOR_VENDA REAL,
                CUSTO_PRODUTO REAL,
                TAXA_PLATAFORMA REAL,
                LUCRO REAL,
                QUANTIDADE INTEGER,
                OBSERVACOES TEXT
            );
            CREATE TABLE IF NOT EXISTS MARKET_PLACE(
                ID TEXT NOT NULL,
                IMAGEM TEXT,
                DATA TEXT,
                NOME_PRODUTO TEXT,
                KIT TEXT,
                PLATAFORMAS_POSTADO TEXT,
                PLATAFORMA_VENDA TEXT,
                CLIENTE_NOME TEXT,
                CLIENTE_CPF TEXT,
                CLIENTE_TELEFONE TEXT,
                ENDERECO TEXT,
                VALOR_VENDA REAL,
                CUSTO_PRODUTO REAL,
                TAXA_PLATAFORMA REAL,
                LUCRO REAL,
                QUANTIDADE INTEGER,
                TITULO TEXT,
                DESCRITION TEXT
            );
            """
        )
    init_memory_schema(DB_PATH)


def ler_entradas() -> list[tuple]:
    init_database()
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute("SELECT * FROM A_ENTRADA ORDER BY rowid").fetchall()


def salvar_entrada(
    produto: str,
    referencia: str,
    diretorio: str,
    descricao: str,
    serventia: str,
    acompanha: str,
    acabamento: str,
    kit: str,
) -> None:
    init_database()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO A_ENTRADA
            (PRODUTO, REFERENCIA, DIRETORIO, DESCRITION, SERVENTIA,
             ACOMPANHA, ACABAMENTO, KIT)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                produto,
                referencia,
                diretorio,
                descricao,
                serventia,
                acompanha,
                acabamento,
                kit,
            ),
        )


def apagar_entrada(produto: str) -> None:
    init_database()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM A_ENTRADA WHERE PRODUTO = ?", (produto,))


class TaskWorker(QObject):
    """Executa uma função pesada em uma thread e devolve progresso à tela."""

    progress = Signal(str)
    finished = Signal(object)
    failed = Signal(str)

    cancelled = Signal(str)

    def __init__(self, function: Callable, *args, **kwargs):
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs

    def run(self) -> None:
        nome_funcao = getattr(self.function, "__name__", "tarefa")
        log.info(
            "TaskWorker",
            "run",
            f"iniciando tarefa: {nome_funcao}",
        )
        try:
            resultado = self.function(
                *self.args,
                progress=self.progress.emit,
                **self.kwargs,
            )
            log.ok(
                "TaskWorker",
                "run",
                f"tarefa concluída: {nome_funcao}",
            )
            self.finished.emit(resultado)
        except RecordingCancelled as exc:
            log.aviso(
                "TaskWorker",
                "run",
                f"tarefa cancelada normalmente: {nome_funcao}; motivo={exc}",
            )
            self.cancelled.emit(str(exc))
        except RecordingCancelled as exc:
            log.aviso(
                "TaskWorker",
                "run",
                f"tarefa cancelada normalmente: {nome_funcao}; motivo={exc}",
            )
            self.cancelled.emit(str(exc))
        except RecordingCancelled as exc:
            log.aviso(
                "TaskWorker",
                "run",
                f"tarefa cancelada normalmente: {nome_funcao}; motivo={exc}",
            )
            self.cancelled.emit(str(exc))
        except Exception:
            erro = traceback.format_exc()
            log.erro("TaskWorker", "run", erro)
            self.failed.emit(erro)


class _TaskCallbackRelay(QObject):
    """Entrega callbacks da tarefa na thread principal da interface."""

    def __init__(
        self,
        on_done: Callable[[object], None] | None,
        on_error: Callable[[str], None] | None,
        on_cancel: Callable[[str], None] | None,
        parent=None,
    ):
        super().__init__(parent)
        self._on_done = on_done
        self._on_error = on_error
        self._on_cancel = on_cancel

    @Slot(object)
    def handle_done(self, result: object) -> None:
        try:
            if self._on_done:
                self._on_done(result)
        finally:
            self.deleteLater()

    @Slot(str)
    def handle_error(self, error: str) -> None:
        try:
            if self._on_error:
                self._on_error(error)
        finally:
            self.deleteLater()

    @Slot(str)
    def handle_cancel(self, message: str) -> None:
        try:
            if self._on_cancel:
                self._on_cancel(message)
        finally:
            self.deleteLater()

class BackgroundMixin:
    """Executa processamento pesado sem travar a janela."""

    def __init__(self) -> None:
        self._threads: list[ThreadSegura] = []

    def start_task(
        self,
        function: Callable,
        *args,
        on_done: Callable[[object], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        on_cancel: Callable[[str], None] | None = None,
        **kwargs,
    ) -> None:
        nome_funcao = getattr(function, "__name__", "tarefa")
        nome_thread = f"{nome_funcao}_{id(self)}_{len(self._threads) + 1}"
        log.info(
            "BackgroundMixin",
            "start_task",
            f"preparando worker: função={nome_funcao}; thread={nome_thread}",
        )
        thread = ThreadSegura(nome=nome_thread, parent=self)
        worker = TaskWorker(function, *args, **kwargs)
        worker.moveToThread(thread)
        setattr(thread, "_task_worker", worker)
        relay = _TaskCallbackRelay(on_done, on_error, on_cancel, parent=self)
        setattr(thread, "_task_callback_relay", relay)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.cancelled.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        worker.cancelled.connect(worker.deleteLater)
        if on_done:
            worker.finished.connect(
                relay.handle_done,
                Qt.ConnectionType.QueuedConnection,
            )
        if on_error:
            worker.failed.connect(
                relay.handle_error,
                Qt.ConnectionType.QueuedConnection,
            )
        if on_cancel:
            worker.cancelled.connect(
                relay.handle_cancel,
                Qt.ConnectionType.QueuedConnection,
            )
        worker.progress.connect(
            self.show_log,
            Qt.ConnectionType.QueuedConnection,
        )
        thread.finished.connect(self._ao_finalizar_thread)
        self._threads.append(thread)
        thread.start()
        log.info(
            "BackgroundMixin",
            "start_task",
            f"thread iniciada e worker conectado: {nome_thread}",
        )

    def _ao_finalizar_thread(self) -> None:
        """Remove da lista as threads que já terminaram."""
        self._threads[:] = [thread for thread in self._threads if thread.isRunning()]

    def show_log(self, message: str) -> None:
        log.info("BackgroundMixin", "progress", str(message))


def reconhecer_microfone(
    progress: Callable[[str], None] | None = None,
) -> str:
    """Grava uma fala curta e converte para texto em português.

    Os imports são tardios para que a aplicação continue abrindo mesmo quando
    o computador ainda não tem o suporte de microfone configurado.
    """
    try:
        import speech_recognition as sr
    except ImportError as exc:
        raise RuntimeError(
            "O reconhecimento por microfone precisa do pacote "
            "SpeechRecognition e de um mecanismo de áudio instalado."
        ) from exc

    recognizer = sr.Recognizer()
    try:
        # Não dependa do "dispositivo padrão" do Windows. Em algumas
        # instalações ele não existe, mesmo havendo microfones disponíveis,
        # e o SpeechRecognition lança "No Default Input Device Available".
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
            except (OSError, IOError):
                pass

            if device_index is None:
                for index in range(audio_probe.get_device_count()):
                    info = audio_probe.get_device_info_by_index(index)
                    if int(info.get("maxInputChannels", 0)) > 0:
                        device_index = index
                        device_name = str(info.get("name", ""))
                        break
        finally:
            audio_probe.terminate()

        if device_index is None:
            raise RuntimeError(
                "Nenhum microfone de entrada foi encontrado no Windows. "
                "Conecte ou habilite um microfone e tente novamente."
            )

        if progress:
            progress(f"Microfone selecionado: {device_name}")

        with sr.Microphone(device_index=device_index) as source:
            if progress:
                progress("Ajustando o microfone...")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            if progress:
                progress("Fale agora...")
            audio = recognizer.listen(
                source,
                timeout=10,
                phrase_time_limit=120,
            )
    except sr.WaitTimeoutError as exc:
        raise RuntimeError("Nenhuma fala foi capturada pelo microfone.") from exc
    except RuntimeError:
        raise
    except (AssertionError, AttributeError, OSError, IOError) as exc:
        raise RuntimeError(
            "Não foi possível acessar o microfone. "
            "Verifique as permissões do Windows, o dispositivo de entrada "
            f"e a instalação do PyAudio. Detalhe: {exc}"
        ) from exc

    try:
        if progress:
            progress("Convertendo fala em texto...")
        return recognizer.recognize_google(audio, language="pt-BR")
    except sr.UnknownValueError as exc:
        raise RuntimeError("Não foi possível entender o áudio.") from exc
    except sr.RequestError as exc:
        raise RuntimeError(
            "O serviço de reconhecimento de voz não respondeu."
        ) from exc


def copiar_cadastro(
    pasta_origem: str,
    pasta_destino: str,
    arquivos: list[str],
    dados: list[tuple[str, str, str, str, str]],
    progress: Callable[[str], None] | None = None,
    nomes_destino: list[str] | None = None,
) -> str:
    """Grava produtos.txt e copia as mídias com os nomes do cadastro."""
    origem = Path(pasta_origem)
    destino = Path(pasta_destino)
    destino.mkdir(parents=True, exist_ok=True)
    caminho_txt = destino / "produtos.txt"
    nomes_destino = nomes_destino or []
    ordem_imagens: list[str] = []
    videos_copiados: list[str] = []

    with caminho_txt.open("w", encoding="utf-8") as arquivo_txt:
        for index, (nome, altura, largura, espessura, peso) in enumerate(dados):
            nome_final = (
                nomes_destino[index]
                if index < len(nomes_destino) and nomes_destino[index]
                else nome
            )
            arquivo_txt.write(f"{altura}x{largura}x{espessura},{peso}\n")
            origem_file = origem / nome
            destino_file = destino / nome_final
            if origem_file.exists():
                shutil.copy2(origem_file, destino_file)
                ordem_imagens.append(nome_final)

        for nome in arquivos:
            if nome.lower().endswith(VIDEO_EXTENSIONS):
                origem_file = origem / nome
                destino_file = destino / nome
                if origem_file.exists():
                    shutil.copy2(origem_file, destino_file)
                    videos_copiados.append(nome)

    (destino / ".ordem_midias.json").write_text(
        json.dumps(
            ordem_imagens + videos_copiados,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    if progress:
        progress(f"Arquivo criado: {caminho_txt}")
        progress(f"Mídias copiadas para: {destino}")
    return str(caminho_txt)


def gerar_pastas_iniciais(
    pasta_destino: str,
    proporcao: str,
    progress: Callable[[str], None] | None = None,
) -> None:
    """Mantém a criação de Proportion_Ajustada e Ajuste_Geral."""
    from Tratar_midias.a__Ajuste_Proportion_IMG import Proporcao_IMG
    from Tratar_midias.b__Ajuste_Geral_IMG import Ajuste_IMG

    destino = Path(pasta_destino)
    proportion = destino / "Proportion_Ajustada"
    ajuste = destino / "Ajuste_Geral"
    if not proportion.exists():
        if progress:
            progress("Gerando Proportion_Ajustada...")
        Proporcao_IMG(
            str(destino),
            str(proportion),
            tuple(map(int, proporcao.split(":"))),
        )
        Ajuste_IMG(str(proportion), str(ajuste))


def salvar_cadastro_task(
    pasta_origem: str,
    pasta_destino: str,
    arquivos: list[str],
    dados: list[tuple[str, str, str, str, str]],
    produto: str,
    descricao: str,
    serventia: str,
    acompanha: str,
    acabamento: str,
    tipo: str,
    qt_variacoes: int,
    tem_kit_tambem: str,
    qt_kit_tambem: int,
    qt_pecas_kit: int,
    tipo_var_kit: str,
    qt_kits: int,
    proporcao: str,
    progress: Callable[[str], None] | None = None,
    nomes_destino: list[str] | None = None,
) -> str:
    ref_kit = gerar_config_ref(
        tipo,
        qt_variacoes,
        tem_kit_tambem,
        qt_kit_tambem,
        qt_pecas_kit,
        tipo_var_kit,
        qt_kits,
    )
    salvar_entrada(
        produto.title(),
        gerar_referencia(produto).lower(),
        pasta_destino,
        descricao,
        serventia,
        acompanha,
        acabamento,
        ref_kit,
    )
    copiar_cadastro(
        pasta_origem,
        pasta_destino,
        arquivos,
        dados,
        progress=progress,
        nomes_destino=nomes_destino,
    )
    gerar_pastas_iniciais(pasta_destino, proporcao, progress)
    if progress:
        progress("Cadastro concluído.")
    return pasta_destino


def _primeiro_arquivo(pasta: Path, prefixos: tuple[str, ...]) -> Path | None:
    if not pasta.exists():
        return None
    candidatos = sorted(
        caminho
        for caminho in pasta.iterdir()
        if caminho.is_file()
        and caminho.suffix.lower() in IMAGE_EXTENSIONS
        and caminho.name.lower().startswith(prefixos)
    )
    return candidatos[0] if candidatos else None


def gerar_previews_qt(
    pasta: str,
    referencia: str,
    progress: Callable[[str], None] | None = None,
    imagens_ordem: list[str] | None = None,
    imagem_capa: str | None = None,
    imagem_medida: str | None = None,
) -> tuple[Path, Path, Path, Path]:
    """Gera os previews usando os módulos de mídia existentes."""
    from _FERRAMENTAS_.Previews import preview_produto_com_fundo

    produto_dir = Path(pasta)
    logos_dir = PROJECT_DIR / "Midias"
    logos_dir.mkdir(exist_ok=True)
    logo = _primeiro_arquivo(logos_dir, ("logo",))
    fundo_medida = _primeiro_arquivo(logos_dir, ("medida",))
    fundo_capa = _primeiro_arquivo(logos_dir, ("capa",))
    por_nome = {
        caminho.name.casefold(): caminho
        for caminho in produto_dir.iterdir()
        if caminho.is_file() and caminho.suffix.lower() in IMAGE_EXTENSIONS
    }
    imagens = []
    if imagens_ordem:
        imagens.extend(
            por_nome[nome.casefold()]
            for nome in imagens_ordem
            if nome.casefold() in por_nome
        )
    imagens.extend(
        caminho
        for caminho in sorted(por_nome.values(), key=lambda item: item.name.casefold())
        if caminho not in imagens
    )
    if not imagens or not fundo_capa or not fundo_medida:
        raise FileNotFoundError(
            "É necessário ter imagens do produto e arquivos logo*, capa* e "
            "medida* na pasta Midias."
        )

    previews = produto_dir / "PREVIEWS"
    previews.mkdir(exist_ok=True)
    capa = por_nome.get(str(imagem_capa or "").casefold(), imagens[0])
    medida = por_nome.get(str(imagem_medida or "").casefold(), imagens[-1])
    for prefixo, fundo, imagem_atual in (
        ("CAPA", fundo_capa, capa),
        ("MEDIDA", fundo_medida, medida),
    ):
        caminho = previews / f"{prefixo}_{referencia}_{fundo.stem}.png"
        if not caminho.exists():
            resultado = preview_produto_com_fundo(
                imagem_atual,
                fundo,
                sombra_altura=0.18,
            )
            if resultado:
                resultado.save(caminho, "PNG")
                if progress:
                    progress(f"Preview salvo: {caminho.name}")
    return logos_dir, logo or Path(), fundo_capa, fundo_medida


def _ler_ordem_midias_producao(pasta: Path) -> tuple[list[str], list[str]]:
    """Carrega a ordem salva pelo Cadastro e separa imagens de vídeos."""
    manifesto = pasta / ".ordem_midias.json"
    if not manifesto.exists():
        raise FileNotFoundError(
            f"Manifesto de mídias não encontrado: {manifesto.name}. "
            "Salve novamente o Cadastro antes de iniciar a Produção."
        )

    try:
        valores = json.loads(manifesto.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError) as exc:
        raise ValueError(
            f"Não foi possível ler {manifesto.name}: {exc}"
        ) from exc

    if not isinstance(valores, list):
        raise ValueError(f"{manifesto.name} precisa conter uma lista de mídias.")

    arquivos_por_nome: dict[str, Path] = {}
    imagens_por_stem: dict[str, list[Path]] = {}
    for caminho in pasta.iterdir():
        if not caminho.is_file():
            continue
        arquivos_por_nome[caminho.name.casefold()] = caminho
        if caminho.suffix.lower() in IMAGE_EXTENSIONS:
            imagens_por_stem.setdefault(caminho.stem.casefold(), []).append(caminho)

    usados: set[str] = set()
    ordenados: list[str] = []
    ausentes: list[str] = []
    for valor in valores:
        nome = Path(str(valor)).name
        extensao = Path(nome).suffix.lower()
        if extensao in IMAGE_EXTENSIONS:
            candidatos = imagens_por_stem.get(Path(nome).stem.casefold(), [])
            extensao_preferida = extensao
            encontrado = (
                min(
                    candidatos,
                    key=lambda candidato: (
                        candidato.suffix.lower() != extensao_preferida,
                        IMAGE_EXTENSIONS.index(candidato.suffix.lower()),
                        candidato.name.casefold(),
                    ),
                )
                if candidatos
                else None
            )
        else:
            encontrado = arquivos_por_nome.get(nome.casefold())
        if encontrado is None:
            nome_ausente = (
                f"{Path(nome).stem} (pasta: {pasta})"
                if extensao in IMAGE_EXTENSIONS
                else f"{nome} (pasta: {pasta})"
            )
            ausentes.append(nome_ausente)
            continue
        if encontrado.name.casefold() not in usados:
            ordenados.append(encontrado.name)
            usados.add(encontrado.name.casefold())

    if ausentes:
        nomes = ", ".join(ausentes[:5])
        extra = "..." if len(ausentes) > 5 else ""
        raise FileNotFoundError(
            f"O manifesto aponta para mídia ausente: {nomes}{extra}"
        )

    imagens = [
        nome for nome in ordenados
        if Path(nome).suffix.lower() in IMAGE_EXTENSIONS
    ]
    videos = [
        nome for nome in ordenados
        if Path(nome).suffix.lower() in VIDEO_EXTENSIONS
    ]
    if not imagens:
        raise ValueError("O manifesto não contém imagens para produzir.")
    return imagens, videos


def _ler_linhas_produtos_txt(
    pasta: Path,
    imagens: list[str],
) -> list[tuple[str, str]]:
    """Lê o TXT somente para conferir o pacote salvo pelo Cadastro."""
    caminho_txt = pasta / "produtos.txt"
    if not caminho_txt.exists():
        raise FileNotFoundError(
            "produtos.txt não encontrado na pasta do produto. "
            "Salve novamente o Cadastro antes da Produção."
        )

    linhas: list[tuple[str, str]] = []
    for numero, linha in enumerate(
        caminho_txt.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        texto = linha.strip()
        if not texto:
            continue
        partes = texto.split(",", 1)
        medidas = partes[0].strip().lower().replace("×", "x")
        peso = partes[1].strip() if len(partes) > 1 else ""
        if not medidas:
            raise ValueError(
                f"produtos.txt: linha {numero} não possui medidas."
            )
        linhas.append((medidas, peso))

    if len(linhas) != len(imagens):
        raise ValueError(
            "O pacote do Cadastro está inconsistente: "
            f"produtos.txt tem {len(linhas)} linha(s), mas o manifesto tem "
            f"{len(imagens)} imagem(ns)."
        )
    return linhas


def _partes_nome_producao(nome: str) -> tuple[str, str, str]:
    """Extrai grupo, medidas e peso de um nome final do Cadastro."""
    partes = Path(nome).stem.split("_")
    if len(partes) < 3:
        raise ValueError(
            f"Nome de imagem fora do padrão do Cadastro: {Path(nome).name}"
        )

    medidas = partes[-2].lower().replace("×", "x")
    if not re.fullmatch(
        r"\d+(?:\.\d+)?x\d+(?:\.\d+)?(?:x\d+(?:\.\d+)?)?",
        medidas,
    ):
        raise ValueError(
            f"Medidas ausentes ou inválidas no nome: {Path(nome).name}"
        )

    peso = partes[-1].lower()
    if len(partes) >= 4 and re.fullmatch(r"\d+", partes[-3]):
        grupo = "_".join(partes[:-3])
    else:
        grupo = "_".join(partes[:-2])
    if not grupo:
        raise ValueError(f"Grupo ausente no nome: {Path(nome).name}")
    return grupo, medidas, peso


def _normalizar_peso(valor: str) -> str:
    """Compara peso do TXT e do nome sem tratar unidade como associação."""
    texto = str(valor).strip().lower().replace(",", ".")
    texto = texto.replace("kg", "").replace("gm", "").replace("g", "")
    try:
        return str(float(texto or "0")).rstrip("0").rstrip(".")
    except ValueError:
        return texto


def _validar_nomes_e_txt(
    imagens: list[str],
    linhas_txt: list[tuple[str, str]],
) -> None:
    """Confere que o nome final preserva as medidas do cartão do Cadastro."""
    erros: list[str] = []
    for nome, (medidas_txt, peso_txt) in zip(imagens, linhas_txt):
        _grupo, medidas_nome, peso_nome = _partes_nome_producao(nome)
        if medidas_nome != medidas_txt:
            erros.append(
                f"{nome}: nome={medidas_nome}, TXT={medidas_txt}"
            )
        if _normalizar_peso(peso_nome) != _normalizar_peso(peso_txt):
            erros.append(
                f"{nome}: peso no nome={peso_nome}, TXT={peso_txt or '0'}"
            )
    if erros:
        detalhes = "\n".join(f"• {erro}" for erro in erros[:8])
        extra = "\n• ..." if len(erros) > 8 else ""
        raise ValueError(
            "As medidas do Cadastro não conferem com os nomes finais:\n"
            f"{detalhes}{extra}\n"
            "Revise os grupos e salve o Cadastro novamente."
        )


def _separar_imagens_por_papel(
    imagens: list[str],
) -> tuple[list[str], list[str], list[str]]:
    """Aplica a regra nova: primeira é capa, última é medida."""
    grupos: dict[str, list[str]] = {}
    for nome in imagens:
        grupo, _medidas, _peso = _partes_nome_producao(nome)
        grupos.setdefault(grupo, []).append(nome)

    capas_e_variacoes: list[str] = []
    medidas: list[str] = []
    resumo: list[str] = []
    for grupo, nomes in grupos.items():
        capas_e_variacoes.extend(nomes[:-1] or nomes[:1])
        medidas.append(nomes[-1])
        resumo.append(
            f"{grupo}: capa={nomes[0]}, "
            f"medida={nomes[-1]}, variações={max(0, len(nomes) - 2)}"
        )
    return capas_e_variacoes, medidas, resumo


def _copiar_selecionadas(
    origem: Path,
    destino: Path,
    nomes: list[str],
    *,
    preferir_png: bool = False,
) -> None:
    """Copia somente as imagens pertencentes ao papel calculado."""
    destino.mkdir(parents=True, exist_ok=True)
    por_stem: dict[str, list[Path]] = {}
    if origem.is_dir():
        for caminho in origem.iterdir():
            if caminho.is_file() and caminho.suffix.lower() in IMAGE_EXTENSIONS:
                por_stem.setdefault(caminho.stem.casefold(), []).append(caminho)

    for nome in nomes:
        stem = Path(nome).stem
        candidatos = por_stem.get(stem.casefold(), [])
        if not candidatos:
            raise FileNotFoundError(
                f"Imagem esperada com stem '{stem}' não encontrada na pasta {origem}."
            )
        extensao_preferida = (
            ".png" if preferir_png else Path(nome).suffix.lower()
        )
        arquivo = min(
            candidatos,
            key=lambda candidato: (
                candidato.suffix.lower() != extensao_preferida,
                IMAGE_EXTENSIONS.index(candidato.suffix.lower()),
                candidato.name.casefold(),
            ),
        )
        shutil.copy2(arquivo, destino / arquivo.name)


def _formas_de_venda(
    tipo_kit_config: str,
    selecionadas: list[str] | str | None,
) -> list[str]:
    """Normaliza as formas comerciais permitidas pelo Cadastro."""
    config = parse_tipo_kit(tipo_kit_config)
    tipo = config.get("TIPO", "").upper()
    tem_kit = config.get("KIT", "NO").upper() == "YES"
    pecas = config.get("PECAS", "")
    permitidas: list[str] = []
    if tipo == "ÚNICO":
        permitidas.append("Peça única")
        if tem_kit and pecas:
            permitidas.append(f"Kit: {pecas}")
    elif tipo == "KIT" and pecas:
        permitidas.append(f"Kit: {pecas}")

    if isinstance(selecionadas, str):
        solicitadas = [selecionadas] if selecionadas else []
    else:
        solicitadas = [str(valor) for valor in (selecionadas or [])]
    escolhidas = [valor for valor in solicitadas if valor in permitidas]
    if solicitadas and not escolhidas:
        raise ValueError(
            "As formas de venda selecionadas não correspondem à configuração "
            f"do Cadastro. Permitidas: {', '.join(permitidas) or 'nenhuma'}."
        )
    return escolhidas or permitidas


def executar_producao(
    produto_row: tuple,
    sombra_altura: float,
    volume_musica: float,
    ordem: str,
    tipo_medidas: str,
    kit_opcoes: list[str] | str | None,
    progress: Callable[[str], None] | None = None,
) -> str:
    """Executa as mesmas etapas de produção da interface original."""

    def log(texto: str) -> None:
        if progress:
            progress(texto)

    produto = str(produto_row[0]).upper()
    referencia = str(produto_row[1])
    pasta = Path(str(produto_row[2]))
    tipo_kit_config = str(produto_row[7])
    if not pasta.exists():
        raise FileNotFoundError(f"Pasta do produto não encontrada: {pasta}")

    imagens_ordem, videos_manifesto = _ler_ordem_midias_producao(pasta)
    linhas_txt = _ler_linhas_produtos_txt(pasta, imagens_ordem)
    _validar_nomes_e_txt(imagens_ordem, linhas_txt)
    amostras, imagens_medida, resumo_grupos = _separar_imagens_por_papel(
        imagens_ordem
    )
    formas_venda = _formas_de_venda(tipo_kit_config, kit_opcoes)

    log(f"Iniciando produção de {produto}")
    log(
        f"Cadastro validado: {len(imagens_ordem)} imagem(ns), "
        f"{len(videos_manifesto)} vídeo(s), "
        f"{len(resumo_grupos)} grupo(s)."
    )
    for resumo in resumo_grupos:
        log(f"  {resumo}")
    log(f"Formas de venda: {', '.join(formas_venda)}")
    logos_dir, logo_path, capa_path, medida_path = gerar_previews_qt(
        str(pasta),
        referencia,
        progress,
        imagens_ordem=imagens_ordem,
        imagem_capa=amostras[0] if amostras else imagens_ordem[0],
        imagem_medida=imagens_medida[-1],
    )
    qrcode_path = logos_dir / "qr_code_zap.jpg"
    musica_path = logos_dir / "Simple.mp3"
    video_path = logos_dir / "video.png"

    ajuste_geral = pasta / "Ajuste_Geral"
    sem_fundo = pasta / "a_Sem_Fundo"
    fundo_capa = pasta / "b_Fundo_Capa"
    fundo_banco = pasta / "Fundo_Banco"
    fundo_medida = pasta / "b_Fundo_Medida"
    amostra_sem_logo = pasta / "c_Amostra_SEM_LOGO"
    imagem_med = pasta / "Imag_med"
    medida_sem_logo = pasta / "c_Medida_SEM_LOGO"
    amostra_com_logo = pasta / "d_Amostra_COM_LOGO"
    medida_com_logo = pasta / "d_Medida_COM_LOGO"

    from Tratar_midias.c__Remove_Refina_IMG import Remove_IMG
    from Tratar_midias.d__Trocar_Fundo_IMG import Trocar_fundo
    from Tratar_midias.e__Colocar_Logos_Ref import Adicionar_logo_completa
    from Tratar_midias.f__Medidas_Graficos import Colocar_medidas

    if not sem_fundo.exists() or not any(sem_fundo.iterdir()):
        log("Gerando pasta sem fundo...")
        Remove_IMG(str(ajuste_geral), str(sem_fundo))
    if not fundo_capa.exists() or not any(fundo_capa.iterdir()):
        log("Gerando fundo de capa...")
        Trocar_fundo(str(sem_fundo), str(fundo_capa), str(capa_path), sombra_altura)
    if not fundo_banco.exists() or not any(fundo_banco.iterdir()):
        log("Gerando fundo branco...")
        Trocar_fundo(
            str(sem_fundo),
            str(fundo_banco),
            str(logos_dir / "fumdo_branco.jpeg"),
            sombra_altura,
        )
    if not fundo_medida.exists() or not any(fundo_medida.iterdir()):
        log("Gerando fundo de medida...")
        Trocar_fundo(
            str(sem_fundo),
            str(fundo_medida),
            str(medida_path),
            sombra_altura,
        )
    if not amostra_sem_logo.exists() or not all(
        (amostra_sem_logo / nome).exists() for nome in amostras
    ):
        log("Separando capas e variações pelos grupos do Cadastro...")
        _copiar_selecionadas(fundo_capa, amostra_sem_logo, amostras)
    if not imagem_med.exists() or not all(
        (imagem_med / nome).exists() for nome in imagens_medida
    ):
        log("Separando imagens de medidas pelos grupos do Cadastro...")
        _copiar_selecionadas(fundo_medida, imagem_med, imagens_medida)
    if not medida_sem_logo.exists() or not all(
        (medida_sem_logo / Path(nome).stem).with_suffix(".jpg").exists()
        for nome in imagens_medida
    ):
        log("Desenhando medidas...")
        Colocar_medidas(
            str(imagem_med),
            str(medida_sem_logo),
            tipo_kit_config,
            tipo_medidas,
        )
    if not amostra_com_logo.exists() or not any(amostra_com_logo.iterdir()):
        log("Adicionando logo às amostras...")
        Adicionar_logo_completa(
            str(amostra_sem_logo),
            str(amostra_com_logo),
            str(logo_path) if logo_path else None,
            "@henriqls",
            "",
            "Sim",
        )
    if not medida_com_logo.exists() or not any(medida_com_logo.iterdir()):
        log("Adicionando logo às medidas...")
        Adicionar_logo_completa(
            str(medida_sem_logo),
            str(medida_com_logo),
            str(logo_path) if logo_path else None,
            "@henriqls",
            "",
            "Sim",
        )

        init_database()
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM VENDAS")
            for arquivo in sorted(medida_com_logo.iterdir()):
                if arquivo.suffix.lower() in IMAGE_EXTENSIONS:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO VENDAS
                        (ID, DATA, NOME_PRODUTO, KIT, OBSERVACOES)
                        VALUES (?, date('now'), ?, ?, ?)
                        """,
                        (
                            arquivo.stem,
                            produto,
                            tipo_kit_config,
                            str(arquivo),
                        ),
                    )

    videos = [pasta / nome for nome in videos_manifesto]
    video_dir = pasta / "Video_shopee_convertido"
    video_output = video_dir / f"video_{referencia}.mp4"
    if not video_output.exists() and videos:
        from Tratar_midias.v__Converter_video import Converte_Video_Completo

        log("Convertendo vídeo...")
        Converte_Video_Completo(
            ref=referencia,
            input_video=str(videos[0]),
            pasta_video=str(video_dir),
            logo_path=str(video_path),
            som=volume_musica,
            qrcode_path=str(qrcode_path),
            musica_path=str(musica_path),
            link_url="henriqls.shop",
            max_size_mb=30,
            max_duration=59,
        )
    elif not videos:
        log("Nenhum vídeo encontrado; etapa de vídeo ignorada.")

    (pasta / "formas_venda.json").write_text(
        json.dumps(
            {
                "produto": produto,
                "configuracao_cadastro": tipo_kit_config,
                "formas": formas_venda,
                "grupos": resumo_grupos,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    log("Produção concluída.")
    return str(pasta)


def ler_proporcao(produto: str) -> str:
    """Lê a proporção salva no Cadastro sem depender da ordem das colunas."""
    produto_id = str(produto or "").strip()
    if not produto_id:
        return ""
    init_database()
    with sqlite3.connect(DB_PATH) as conn:
        colunas = {
            str(linha[1])
            for linha in conn.execute("PRAGMA table_info(A_ENTRADA)")
        }
        if "PROPORCAO" not in colunas:
            return ""
        linha = conn.execute(
            "SELECT PROPORCAO FROM A_ENTRADA WHERE PRODUTO = ?",
            (produto_id,),
        ).fetchone()
    return str(linha[0] or "").strip() if linha else ""


def listar_produtos_vendas() -> list[str]:
    """Lista apenas produtos permanentes usados nas telas do Marketplace."""
    init_database()
    with sqlite3.connect(DB_PATH) as conn:
        tabelas = {
            str(row[0])
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        if "PRODUTOS_ATIVOS" not in tabelas:
            return []
        rows = conn.execute(
            """
            SELECT PRODUTO
            FROM PRODUTOS_ATIVOS
            WHERE PRODUTO IS NOT NULL AND TRIM(PRODUTO) <> ''
            ORDER BY rowid DESC
            """
        ).fetchall()
    return [str(row[0]).strip() for row in rows if str(row[0] or "").strip()]


def carregar_itens_anuncio_marketplace(produto: str) -> dict[str, object]:
    """Carrega IDs atuais e legados sem alterar o banco."""
    nome_produto = str(produto or "").strip()
    if not nome_produto:
        return {"title": "", "description": "", "items": []}
    produto_key = nome_produto.casefold()

    caminho = Path(DB_PATH).expanduser()
    if not caminho.is_file():
        raise FileNotFoundError(f"O banco existente não foi encontrado: {caminho}")
    uri = f"{caminho.resolve().as_uri()}?mode=ro"
    with sqlite3.connect(uri, uri=True, timeout=5.0) as conn:
        conn.row_factory = sqlite3.Row
        from _APP_.product_lifecycle import (
            esquema_instalado,
            listar_precos_anuncio,
            listar_textos_marketplace,
        )

        tabelas = {
            str(row[0])
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        registros: list[dict[str, object]] = []
        if "VENDAS" in tabelas:
            vendas = conn.execute(
                """
                SELECT ID, DATA, NOME_PRODUTO, KIT, OBSERVACOES,
                       PLATAFORMAS_POSTADO, VALOR_VENDA, CUSTO_PRODUTO
                FROM VENDAS
                ORDER BY rowid DESC
                """
            ).fetchall()
            registros.extend(
                dict(venda)
                for venda in vendas
                if str(venda["NOME_PRODUTO"] or "").strip().casefold()
                == produto_key
            )

        ids_vendas = {
            str(registro["ID"] or "").strip()
            for registro in registros
            if str(registro["ID"] or "").strip()
        }
        if "MARKET_PLACE" in tabelas:
            registros_legados = conn.execute(
                """
                SELECT ID, DATA, NOME_PRODUTO, KIT, IMAGEM AS OBSERVACOES,
                       PLATAFORMAS_POSTADO, VALOR_VENDA, CUSTO_PRODUTO
                FROM MARKET_PLACE
                ORDER BY rowid DESC
                """
            ).fetchall()
            for registro in registros_legados:
                if (
                    str(registro["NOME_PRODUTO"] or "").strip().casefold()
                    != produto_key
                ):
                    continue
                item_id = str(registro["ID"] or "").strip()
                if item_id and item_id not in ids_vendas:
                    ids_vendas.add(item_id)
                    registros.append(dict(registro))

        items: list[dict[str, object]] = []
        seen_ids: set[str] = set()
        title = ""
        description = ""
        has_marketplace_records = False
        has_legacy_records = False
        for venda in registros:
            if (
                str(venda["NOME_PRODUTO"] or "").strip().casefold()
                != nome_produto.casefold()
            ):
                continue
            item_id = str(venda["ID"] or "").strip()
            if not item_id or item_id in seen_ids:
                continue
            seen_ids.add(item_id)

            market_rows = []
            if "MARKET_PLACE" in tabelas:
                market_rows = conn.execute(
                    f"""
                    SELECT NOME_PRODUTO, IMAGEM, DATA, KIT, PLATAFORMAS_POSTADO,
                           VALOR_VENDA, CUSTO_PRODUTO, TITULO, DESCRITION,
                           CASE WHEN {_MARKETPLACE_UNSOLD_SQL}
                                THEN 1 ELSE 0 END AS DISPONIVEL
                    FROM MARKET_PLACE
                    WHERE ID = ?
                    ORDER BY DISPONIVEL DESC, rowid DESC
                    """,
                    (item_id,),
                ).fetchall()
            product_market_rows = [
                market_row
                for market_row in market_rows
                if str(market_row["NOME_PRODUTO"] or "").strip().casefold()
                == nome_produto.casefold()
            ]
            if product_market_rows:
                has_marketplace_records = True
                has_legacy_records = True
            market = (
                product_market_rows[0] if product_market_rows else None
            )
            market_stock = sum(
                int(market_row["DISPONIVEL"] or 0)
                for market_row in product_market_rows
                if str(market_row["NOME_PRODUTO"] or "").strip().casefold()
                == nome_produto.casefold()
            )

            stored_title = str(market["TITULO"] or "").strip() if market else ""
            stored_description = (
                str(market["DESCRITION"] or "").strip() if market else ""
            )
            if not title and stored_title:
                title = stored_title
            if not description and stored_description:
                description = stored_description

            def prefer_venda(column: str, fallback: object) -> object:
                value = venda[column]
                if value is None or value == "":
                    return fallback
                if (
                    column in {"VALOR_VENDA", "CUSTO_PRODUTO"}
                    and float(value) <= 0
                    and fallback
                ):
                    return fallback
                return value

            items.append(
                {
                    "id": item_id,
                    "date": str(
                        venda["DATA"]
                        or (market["DATA"] if market else "")
                        or ""
                    ),
                    "kit": str(
                        venda["KIT"]
                        or (market["KIT"] if market else "")
                        or ""
                    ),
                    "image": str(
                        venda["OBSERVACOES"]
                        or (market["IMAGEM"] if market else "")
                        or ""
                    ),
                    "platforms": str(
                        prefer_venda(
                            "PLATAFORMAS_POSTADO",
                            market["PLATAFORMAS_POSTADO"] if market else "",
                        )
                        or ""
                    ),
                    "sale_price": float(
                        prefer_venda(
                            "VALOR_VENDA",
                            market["VALOR_VENDA"] if market else 0,
                        )
                        or 0
                    ),
                    "cost": float(
                        prefer_venda(
                            "CUSTO_PRODUTO",
                            market["CUSTO_PRODUTO"] if market else 0,
                        )
                        or 0
                    ),
                    "stock": market_stock,
                    "quantity": (
                        market_stock if product_market_rows else 1
                    ),
                }
            )

        listings: list[dict[str, object]] = []
        if esquema_instalado(conn):
            listings = [
                dict(item)
                for item in listar_textos_marketplace(
                    nome_produto,
                    conexao=conn,
                )
            ]
            price_map = listar_precos_anuncio(nome_produto, conexao=conn)
            active_listings = [
                item for item in listings if bool(item.get("active"))
            ]
            if active_listings:
                title = str(active_listings[0].get("title") or title)
                description = str(
                    active_listings[0].get("description") or description
                )
                has_marketplace_records = True
            for item in items:
                prices = price_map.get(str(item["id"]), {})
                item["platform_prices"] = prices
                if prices:
                    item["sale_price"] = next(iter(prices.values()))

    return {
        "title": title,
        "description": description,
        "items": items,
        "has_marketplace_records": has_marketplace_records,
        "has_legacy_records": has_legacy_records,
        "listings": listings,
    }


def salvar_itens_anuncio_marketplace(
    produto: str,
    titulo: str | None,
    descricao: str | None,
    itens: list[dict[str, object]],
) -> int:
    """Grava os dados de venda e anúncio sem apagar unidades já vendidas."""
    nome_produto = str(produto or "").strip()
    titulo = str(titulo).strip() if titulo is not None else None
    descricao = str(descricao).strip() if descricao is not None else None
    titulo = titulo or None
    descricao = descricao or None
    if not nome_produto:
        raise ValueError("Selecione um produto.")
    if not itens:
        raise ValueError("Não há IDs de produção para salvar.")

    from _APP_.product_lifecycle import (
        listar_marketplaces,
        salvar_ofertas_marketplace,
    )

    plataformas_validas = {
        str(item["name"])
        for item in listar_marketplaces()
        if bool(item["active"])
    }
    normalizados: list[dict[str, object]] = []
    vistos: set[str] = set()
    for item in itens:
        item_id = str(item.get("id") or "").strip()
        if not item_id or item_id in vistos:
            raise ValueError("A lista contém um ID vazio ou repetido.")
        vistos.add(item_id)

        ofertas_brutas = item.get("offers") or []
        if ofertas_brutas:
            ofertas = [
                {
                    "marketplace": str(oferta.get("marketplace") or "").strip(),
                    "sale_price": float(oferta.get("sale_price") or 0),
                }
                for oferta in ofertas_brutas
                if str(oferta.get("marketplace") or "").strip()
            ]
        else:
            plataformas_entrada = [
                str(plataforma).strip()
                for plataforma in item.get("platforms", [])
                if str(plataforma).strip()
            ]
            preco_base = float(item.get("sale_price", 0))
            ofertas = [
                {"marketplace": plataforma, "sale_price": preco_base}
                for plataforma in plataformas_entrada
            ]
        plataformas = list(
            dict.fromkeys(str(oferta["marketplace"]) for oferta in ofertas)
        )
        if not plataformas or any(
            plataforma not in plataformas_validas
            for plataforma in plataformas
        ):
            raise ValueError(
                f"Selecione ao menos um marketplace válido para o ID {item_id}."
            )
        try:
            cost = float(item.get("cost", 0))
            quantity = int(item.get("quantity", 0))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Preço, custo ou quantidade inválidos no ID {item_id}.") from exc
        precos = [float(oferta["sale_price"]) for oferta in ofertas]
        if (
            not math.isfinite(cost)
            or cost <= 0
            or quantity < 0
            or not precos
            or any(not math.isfinite(preco) or preco <= 0 for preco in precos)
        ):
            raise ValueError(
                f"Informe preço e custo maiores que zero e quantidade não "
                f"negativa "
                f"para o ID {item_id}."
            )
        sale_price = min(precos)
        normalizados.append(
            {
                "id": item_id,
                "platforms": ", ".join(dict.fromkeys(plataformas)),
                "offers": ofertas,
                "sale_price": sale_price,
                "cost": cost,
                "quantity": quantity,
            }
        )

    init_database()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN IMMEDIATE")
        data_atual = conn.execute("SELECT date('now')").fetchone()[0]
        tabelas_existentes = {
            str(row[0])
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        if "ANUNCIOS" in tabelas_existentes:
            conn.execute(
                "UPDATE ANUNCIOS SET ATIVO = 0 "
                "WHERE PRODUTO = ? COLLATE NOCASE",
                (nome_produto,),
            )
        for item in normalizados:
            item_id = str(item["id"])
            vendas_por_id = conn.execute(
                """
                SELECT rowid, NOME_PRODUTO, DATA, KIT, OBSERVACOES
                FROM VENDAS
                WHERE ID = ?
                ORDER BY rowid
                """,
                (item_id,),
            ).fetchall()
            vendas_do_produto = [
                row
                for row in vendas_por_id
                if str(row["NOME_PRODUTO"] or "").strip().casefold()
                == nome_produto.casefold()
            ]
            rows_marketplace = conn.execute(
                """
                SELECT rowid, NOME_PRODUTO, DATA, KIT, IMAGEM,
                       TITULO, DESCRITION,
                       CASE WHEN (CLIENTE_NOME IS NULL
                                  OR TRIM(CLIENTE_NOME) = '')
                                  AND (CLIENTE_CPF IS NULL
                                       OR TRIM(CLIENTE_CPF) = '')
                                  AND (CLIENTE_TELEFONE IS NULL
                                       OR TRIM(CLIENTE_TELEFONE) = '')
                                  AND (ENDERECO IS NULL
                                       OR TRIM(ENDERECO) = '')
                                  AND (PLATAFORMA_VENDA IS NULL
                                       OR TRIM(PLATAFORMA_VENDA) = '')
                                  AND COALESCE(CAST(TAXA_PLATAFORMA AS REAL), 0) = 0
                                  AND COALESCE(CAST(LUCRO AS REAL), 0) = 0
                            THEN 1 ELSE 0 END AS DISPONIVEL
                FROM MARKET_PLACE
                WHERE ID = ?
                ORDER BY rowid
                """,
                (item_id,),
            ).fetchall()
            marketplace_do_produto = [
                row
                for row in rows_marketplace
                if str(row["NOME_PRODUTO"] or "").strip().casefold()
                == nome_produto.casefold()
            ]
            if not vendas_do_produto and not marketplace_do_produto:
                raise ValueError(
                    f"O ID {item_id} não foi encontrado para este produto "
                    "em VENDAS nem em MARKET_PLACE."
                )
            venda = vendas_do_produto[0] if vendas_do_produto else None
            registro_marketplace = (
                marketplace_do_produto[0] if marketplace_do_produto else None
            )

            plataformas = str(item["platforms"])
            for venda_row in vendas_do_produto:
                conn.execute(
                    """
                    UPDATE VENDAS
                    SET PLATAFORMAS_POSTADO = ?, VALOR_VENDA = ?,
                        CUSTO_PRODUTO = ?
                    WHERE rowid = ?
                    """,
                    (
                        plataformas,
                        float(item["sale_price"]),
                        float(item["cost"]),
                        venda_row["rowid"],
                    ),
                )

            disponiveis = [
                row
                for row in rows_marketplace
                if str(row["NOME_PRODUTO"] or "").strip().casefold()
                == nome_produto.casefold()
                and int(row["DISPONIVEL"] or 0) == 1
            ]
            quantidade = int(item["quantity"])
            if len(disponiveis) > quantidade:
                raise ValueError(
                    f"O ID {item_id} já tem {len(disponiveis)} unidade(s) "
                    "disponível(is). Este formulário não reduz estoque para "
                    "preservar os registros existentes."
                )

            data = str(
                (venda["DATA"] if venda else None)
                or (
                    registro_marketplace["DATA"]
                    if registro_marketplace
                    else None
                )
                or data_atual
            )
            kit = str(
                (venda["KIT"] if venda else None)
                or (
                    registro_marketplace["KIT"]
                    if registro_marketplace
                    else ""
                )
                or ""
            )
            imagem = str(
                (venda["OBSERVACOES"] if venda else None)
                or (
                    registro_marketplace["IMAGEM"]
                    if registro_marketplace
                    else ""
                )
                or ""
            )
            for row in disponiveis:
                conn.execute(
                    """
                    UPDATE MARKET_PLACE
                    SET IMAGEM = ?, DATA = ?, KIT = ?,
                        PLATAFORMAS_POSTADO = ?, VALOR_VENDA = ?,
                        CUSTO_PRODUTO = ?, QUANTIDADE = 1,
                        TITULO = COALESCE(?, TITULO),
                        DESCRITION = COALESCE(?, DESCRITION)
                    WHERE rowid = ?
                    """,
                    (
                        imagem,
                        data,
                        kit,
                        plataformas,
                        float(item["sale_price"]),
                        float(item["cost"]),
                        titulo,
                        descricao,
                        row["rowid"],
                    ),
                )

            faltantes = quantidade - len(disponiveis)
            for _ in range(faltantes):
                conn.execute(
                    """
                    INSERT INTO MARKET_PLACE
                    (ID, IMAGEM, DATA, NOME_PRODUTO, KIT,
                     PLATAFORMAS_POSTADO, VALOR_VENDA, CUSTO_PRODUTO,
                     TAXA_PLATAFORMA, QUANTIDADE, TITULO, DESCRITION)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 1, ?, ?)
                    """,
                    (
                        item_id,
                        imagem,
                        data,
                        nome_produto,
                        kit,
                        plataformas,
                        float(item["sale_price"]),
                        float(item["cost"]),
                        titulo or "",
                        descricao or "",
                    ),
                )

        if "ANUNCIOS" in tabelas_existentes:
            salvar_ofertas_marketplace(
                conn,
                nome_produto,
                titulo or "",
                descricao or "",
                normalizados,
            )

    return len(normalizados)


def salvar_textos_anuncio_marketplace(
    produto: str,
    titulo: str,
    descricao: str,
    marketplace: str | None = None,
) -> int:
    """Atualiza somente o texto do anúncio, sem alterar estoque ou vendas."""
    nome_produto = str(produto or "").strip()
    titulo = str(titulo or "").strip()
    descricao = str(descricao or "").strip()
    if not nome_produto:
        raise ValueError("Selecione um produto.")
    if not titulo:
        raise ValueError("O título do anúncio não pode ficar vazio.")

    init_database()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN IMMEDIATE")
        vendas = conn.execute(
            "SELECT DISTINCT ID, NOME_PRODUTO FROM VENDAS"
        ).fetchall()
        ids_produto = {
            str(row["ID"] or "").strip()
            for row in vendas
            if str(row["ID"] or "").strip()
            and str(row["NOME_PRODUTO"] or "").strip().casefold()
            == nome_produto.casefold()
        }
        if not ids_produto:
            raise ValueError(
                "Este produto ainda não possui IDs de produção salvos."
            )

        placeholders = ", ".join("?" for _ in ids_produto)
        registros = conn.execute(
            f"""
            SELECT rowid, ID, NOME_PRODUTO
            FROM MARKET_PLACE
            WHERE ID IN ({placeholders})
            """,
            tuple(sorted(ids_produto)),
        ).fetchall()
        registros_produto = [
            row
            for row in registros
            if str(row["NOME_PRODUTO"] or "").strip().casefold()
            == nome_produto.casefold()
        ]
        if not registros_produto:
            raise ValueError(
                "Este produto ainda não tem configuração comercial salva. "
                "Salve primeiro em Montar anúncio."
            )

        from _APP_.product_lifecycle import (
            esquema_instalado,
            salvar_textos_marketplace,
        )

        if esquema_instalado(conn):
            atualizados = salvar_textos_marketplace(
                conn,
                nome_produto,
                titulo,
                descricao,
                marketplace,
            )
            if atualizados == 0:
                conn.executemany(
                    """
                    UPDATE MARKET_PLACE
                    SET TITULO = ?, DESCRITION = ?
                    WHERE rowid = ?
                    """,
                    (
                        (titulo, descricao, row["rowid"])
                        for row in registros_produto
                    ),
                )
        else:
            conn.executemany(
                """
                UPDATE MARKET_PLACE
                SET TITULO = ?, DESCRITION = ?
                WHERE rowid = ?
                """,
                (
                    (titulo, descricao, row["rowid"])
                    for row in registros_produto
                ),
            )

    return len({str(row["ID"] or "").strip() for row in registros_produto})


_MARKETPLACE_UNSOLD_SQL = """
    (CLIENTE_NOME IS NULL OR TRIM(CLIENTE_NOME) = '')
    AND (CLIENTE_CPF IS NULL OR TRIM(CLIENTE_CPF) = '')
    AND (CLIENTE_TELEFONE IS NULL OR TRIM(CLIENTE_TELEFONE) = '')
    AND (ENDERECO IS NULL OR TRIM(ENDERECO) = '')
    AND (PLATAFORMA_VENDA IS NULL OR TRIM(PLATAFORMA_VENDA) = '')
    AND COALESCE(CAST(TAXA_PLATAFORMA AS REAL), 0) = 0
    AND COALESCE(CAST(LUCRO AS REAL), 0) = 0
"""


def listar_unidades_disponiveis_para_venda() -> list[dict[str, object]]:
    """Lista IDs com unidades ainda não atribuídas a uma venda."""
    caminho = Path(DB_PATH).expanduser()
    if not caminho.is_file():
        raise FileNotFoundError(
            f"O banco de estoque não foi encontrado: {caminho}"
        )

    uri = f"{caminho.resolve().as_uri()}?mode=ro"
    with sqlite3.connect(uri, uri=True, timeout=5.0) as conn:
        conn.row_factory = sqlite3.Row
        tabelas = {
            str(row[0])
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        if "MARKET_PLACE" not in tabelas:
            raise RuntimeError(
                f"A tabela MARKET_PLACE não existe no banco: {caminho}"
            )
        rows = conn.execute(
            f"""
            SELECT ID, NOME_PRODUTO, MAX(IMAGEM) AS IMAGEM,
                   MAX(KIT) AS KIT,
                   MAX(PLATAFORMAS_POSTADO) AS PLATAFORMAS_POSTADO,
                   MAX(CAST(VALOR_VENDA AS REAL)) AS VALOR_VENDA,
                   MAX(CAST(CUSTO_PRODUTO AS REAL)) AS CUSTO_PRODUTO,
                   COUNT(*) AS ESTOQUE,
                   MAX(estoque.rowid) AS ORDEM_CADASTRO
            FROM MARKET_PLACE AS estoque
            WHERE {_MARKETPLACE_UNSOLD_SQL}
            GROUP BY estoque.ID, estoque.NOME_PRODUTO
            HAVING COUNT(*) > 0
            ORDER BY ORDEM_CADASTRO DESC, MAX(estoque.rowid) DESC, estoque.ID
            """
        ).fetchall()
        from _APP_.product_lifecycle import (
            esquema_instalado,
            listar_precos_anuncio,
        )

        resultado = [dict(row) for row in rows]
        if esquema_instalado(conn):
            for item in resultado:
                nome_produto = str(item.get("NOME_PRODUTO") or "")
                mapa_precos = listar_precos_anuncio(
                    nome_produto,
                    conexao=conn,
                )
                item["PRECOS_MARKETPLACE"] = mapa_precos.get(
                    str(item.get("ID") or ""),
                    {},
                )
                item["TEM_ANUNCIOS_NORMALIZADOS"] = bool(
                    listar_textos_marketplace(
                        nome_produto,
                        conexao=conn,
                    )
                )
    return resultado


def registrar_venda_marketplace(
    item_id: str,
    produto: str,
    quantidade: int,
    cliente_nome: str,
    cliente_cpf: str = "",
    cliente_telefone: str = "",
    endereco: str = "",
    plataforma_venda: str = "",
    taxa_por_unidade: float = 0,
) -> int:
    """Marca unidades disponíveis como vendidas numa transação SQLite."""
    item_id = str(item_id or "").strip()
    produto = str(produto or "").strip()
    cliente_nome = str(cliente_nome or "").strip()
    plataforma_venda = str(plataforma_venda or "").strip()
    try:
        quantidade_num = float(quantidade)
        taxa = float(taxa_por_unidade)
    except (TypeError, ValueError) as exc:
        raise ValueError("Quantidade ou taxa da plataforma inválida.") from exc

    if not item_id or not produto:
        raise ValueError("Selecione um ID de produto com estoque disponível.")
    if not cliente_nome:
        raise ValueError("Informe o nome do cliente.")
    if not quantidade_num.is_integer() or quantidade_num < 1:
        raise ValueError("A quantidade deve ser um número inteiro positivo.")
    from _APP_.product_lifecycle import (
        esquema_instalado,
        listar_marketplaces,
        listar_textos_marketplace,
        obter_preco_para_venda,
    )

    plataformas_ativas = {
        str(item["name"])
        for item in listar_marketplaces()
        if bool(item["active"])
    }
    if plataforma_venda not in plataformas_ativas:
        raise ValueError("Selecione uma plataforma de venda válida.")
    if not math.isfinite(taxa) or taxa < 0:
        raise ValueError("A taxa por unidade deve ser um valor válido e positivo.")

    quantidade = int(quantidade_num)
    cpf = str(cliente_cpf or "").strip()
    telefone = str(cliente_telefone or "").strip()
    endereco = str(endereco or "").strip()

    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN IMMEDIATE")
        unidades = conn.execute(
            f"""
            SELECT rowid AS ITEM_ROWID, VALOR_VENDA, CUSTO_PRODUTO
            FROM MARKET_PLACE
            WHERE ID = ?
              AND LOWER(TRIM(NOME_PRODUTO)) = LOWER(TRIM(?))
              AND {_MARKETPLACE_UNSOLD_SQL}
            ORDER BY rowid
            LIMIT ?
            """,
            (item_id, produto, quantidade),
        ).fetchall()
        if len(unidades) != quantidade:
            raise ValueError(
                "O estoque disponível mudou. Atualize a lista e tente "
                "registrar a venda novamente."
            )

        for unidade in unidades:
            preco = float(unidade["VALOR_VENDA"] or 0)
            custo = float(unidade["CUSTO_PRODUTO"] or 0)
            if esquema_instalado(conn):
                listings = listar_textos_marketplace(
                    produto,
                    conexao=conn,
                )
                if any(bool(item.get("active")) for item in listings):
                    preco_canal = obter_preco_para_venda(
                        conn,
                        produto,
                        item_id,
                        plataforma_venda,
                    )
                    if preco_canal is None:
                        raise ValueError(
                            f"Não há anúncio ativo de {produto} em "
                            f"{plataforma_venda} para o ID {item_id}."
                        )
                    preco = preco_canal
            if not math.isfinite(preco) or preco <= 0:
                raise ValueError(
                    f"O ID {item_id} não tem preço de venda válido. "
                    "Configure-o na aba Anúncio."
                )
            if not math.isfinite(custo) or custo < 0:
                raise ValueError(f"O ID {item_id} tem um custo inválido.")

            cursor = conn.execute(
                f"""
                UPDATE MARKET_PLACE
                SET CLIENTE_NOME = ?,
                    CLIENTE_CPF = ?,
                    CLIENTE_TELEFONE = ?,
                    ENDERECO = ?,
                    PLATAFORMA_VENDA = ?,
                    VALOR_VENDA = ?,
                    TAXA_PLATAFORMA = ?,
                    LUCRO = ?
                WHERE rowid = ?
                  AND {_MARKETPLACE_UNSOLD_SQL}
                """,
                (
                    cliente_nome,
                    cpf,
                    telefone,
                    endereco,
                    plataforma_venda,
                    preco,
                    taxa,
                    round(preco - custo - taxa, 2),
                    int(unidade["ITEM_ROWID"]),
                ),
            )
            if cursor.rowcount != 1:
                raise ValueError(
                    "Uma unidade foi alterada durante o registro. "
                    "Nenhuma alteração foi gravada; atualize e tente de novo."
                )
    return quantidade


def listar_vendas_marketplace_realizadas() -> list[dict[str, object]]:
    """Lista unidades vendidas; cada linha de MARKET_PLACE representa uma unidade."""
    init_database()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT ID, NOME_PRODUTO, KIT, CLIENTE_NOME, CLIENTE_CPF,
                   CLIENTE_TELEFONE, ENDERECO, PLATAFORMA_VENDA,
                   VALOR_VENDA, CUSTO_PRODUTO, TAXA_PLATAFORMA, LUCRO
            FROM MARKET_PLACE
            WHERE CLIENTE_NOME IS NOT NULL
              AND TRIM(CLIENTE_NOME) <> ''
            ORDER BY rowid DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def _copiar_cadastro_com_nomes(
    pasta_origem: str,
    pasta_destino: str,
    arquivos: list[str],
    dados: list[tuple[str, str, str, str, str]],
    nomes_destino: list[str] | None = None,
    progress: Callable[[str], None] | None = None,
) -> str:
    """Copia imagens com nomes da Produção e mantém vídeos na pasta raiz."""
    origem = Path(pasta_origem)
    destino = Path(pasta_destino)
    destino.mkdir(parents=True, exist_ok=True)
    caminho_txt = destino / "produtos.txt"
    nomes_destino = nomes_destino or []
    ordem_imagens: list[str] = []

    with caminho_txt.open("w", encoding="utf-8") as arquivo_txt:
        for index, (nome, altura, largura, espessura, peso) in enumerate(dados):
            nome_final = (
                nomes_destino[index]
                if index < len(nomes_destino) and nomes_destino[index]
                else nome
            )
            arquivo_txt.write(f"{altura}x{largura}x{espessura},{peso}\n")
            origem_file = origem / nome
            destino_file = destino / nome_final
            if origem_file.exists():
                shutil.copy2(origem_file, destino_file)
                ordem_imagens.append(nome_final)

        videos_copiados: list[str] = []
        for nome in arquivos:
            if nome.lower().endswith(VIDEO_EXTENSIONS):
                origem_file = origem / nome
                destino_file = destino / nome
                if origem_file.exists():
                    shutil.copy2(origem_file, destino_file)
                    videos_copiados.append(nome)

    (destino / ".ordem_midias.json").write_text(
        json.dumps(
            ordem_imagens + videos_copiados,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    if progress:
        progress(f"Arquivo criado: {caminho_txt}")
        progress(f"Mídias copiadas para: {destino}")
    return str(caminho_txt)


def salvar_cadastro_task(
    pasta_origem: str,
    pasta_destino: str,
    arquivos: list[str],
    dados: list[tuple[str, str, str, str, str]],
    produto: str,
    descricao: str,
    serventia: str,
    acompanha: str,
    acabamento: str,
    tipo: str,
    qt_variacoes: int,
    tem_kit_tambem: str,
    qt_kit_tambem: int,
    qt_pecas_kit: int,
    tipo_var_kit: str,
    qt_kits: int,
    proporcao: str,
    progress: Callable[[str], None] | None = None,
    nomes_destino: list[str] | None = None,
) -> str:
    """Salva o cadastro ativo com as imagens já preparadas para Produção."""
    ref_kit = gerar_config_ref(
        tipo,
        qt_variacoes,
        tem_kit_tambem,
        qt_kit_tambem,
        qt_pecas_kit,
        tipo_var_kit,
        qt_kits,
    )
    salvar_entrada(
        produto.title(),
        gerar_referencia(produto).lower(),
        pasta_destino,
        descricao,
        serventia,
        acompanha,
        acabamento,
        ref_kit,
    )
    _copiar_cadastro_com_nomes(
        pasta_origem,
        pasta_destino,
        arquivos,
        dados,
        nomes_destino,
        progress,
    )
    gerar_pastas_iniciais(pasta_destino, proporcao, progress)
    if progress:
        progress("Cadastro concluído.")
    return pasta_destino


# Estas são as definições efetivas do módulo. O arquivo mantém cópias históricas
# acima, mas a janela importa os símbolos finais durante a inicialização.
class TaskWorker(QObject):
    """Executa tarefas fora da UI e separa cancelamento de falhas."""

    progress = Signal(str)
    finished = Signal(object)
    failed = Signal(str)
    cancelled = Signal(str)

    def __init__(self, function: Callable, *args, **kwargs):
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs

    def run(self) -> None:
        nome_funcao = getattr(self.function, "__name__", "tarefa")
        log.info("TaskWorker", "run", f"iniciando tarefa: {nome_funcao}")
        try:
            resultado = self.function(
                *self.args,
                progress=self.progress.emit,
                **self.kwargs,
            )
            log.ok("TaskWorker", "run", f"tarefa concluída: {nome_funcao}")
            self.finished.emit(resultado)
        except RecordingCancelled as exc:
            log.aviso(
                "TaskWorker",
                "run",
                f"tarefa cancelada normalmente: {nome_funcao}; motivo={exc}",
            )
            self.cancelled.emit(str(exc))
        except Exception:
            erro = traceback.format_exc()
            log.erro("TaskWorker", "run", erro)
            self.failed.emit(erro)


class BackgroundMixin:
    """Executa processamento pesado e entrega callbacks na thread principal."""

    def __init__(self) -> None:
        self._threads: list[ThreadSegura] = []

    def start_task(
        self,
        function: Callable,
        *args,
        on_done: Callable[[object], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        on_cancel: Callable[[str], None] | None = None,
        **kwargs,
    ) -> None:
        nome_funcao = getattr(function, "__name__", "tarefa")
        nome_thread = f"{nome_funcao}_{id(self)}_{len(self._threads) + 1}"
        thread = ThreadSegura(nome=nome_thread, parent=self)
        worker = TaskWorker(function, *args, **kwargs)
        worker.moveToThread(thread)
        setattr(thread, "_task_worker", worker)
        relay = _TaskCallbackRelay(
            on_done,
            on_error,
            on_cancel,
            parent=self,
        )
        setattr(thread, "_task_callback_relay", relay)
        thread.started.connect(worker.run)
        worker.progress.connect(
            self.show_log,
            Qt.ConnectionType.QueuedConnection,
        )
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.cancelled.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        worker.cancelled.connect(worker.deleteLater)
        if on_done:
            worker.finished.connect(
                relay.handle_done,
                Qt.ConnectionType.QueuedConnection,
            )
        if on_error:
            worker.failed.connect(
                relay.handle_error,
                Qt.ConnectionType.QueuedConnection,
            )
        if on_cancel:
            worker.cancelled.connect(
                relay.handle_cancel,
                Qt.ConnectionType.QueuedConnection,
            )
        thread.finished.connect(self._ao_finalizar_thread)
        self._threads.append(thread)
        thread.start()

    def _ao_finalizar_thread(self) -> None:
        self._threads[:] = [
            thread for thread in self._threads if thread.isRunning()
        ]

    def show_log(self, message: str) -> None:
        """Mantém progresso técnico somente no arquivo de log."""
        log.info("BackgroundMixin", "progress", str(message))


def reconhecer_microfone(
    progress: Callable[[str], None] | None = None,
) -> str:
    """Captura voz usando um dispositivo de entrada real do Windows.

    O Streamlit capturava o áudio pelo navegador. No PySide6, o
    SpeechRecognition precisa do PyAudio e do índice de um dispositivo de
    entrada; por isso não dependemos somente do dispositivo padrão do sistema.
    """
    try:
        import speech_recognition as sr
    except ImportError as exc:
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
            except (OSError, IOError):
                pass

            if device_index is None:
                for index in range(audio_probe.get_device_count()):
                    info = audio_probe.get_device_info_by_index(index)
                    if int(info.get("maxInputChannels", 0)) > 0:
                        device_index = index
                        device_name = str(info.get("name", ""))
                        break
        finally:
            audio_probe.terminate()

        if device_index is None:
            raise RuntimeError(
                "Nenhum microfone de entrada foi encontrado no Windows. "
                "Conecte ou habilite um microfone e tente novamente."
            )

        if progress:
            progress(f"Microfone selecionado: {device_name}")

        with sr.Microphone(device_index=device_index) as source:
            if progress:
                progress("Ajustando o microfone...")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            if progress:
                progress("Fale agora...")
            audio = recognizer.listen(
                source,
                timeout=10,
                phrase_time_limit=120,
            )
    except sr.WaitTimeoutError as exc:
        raise RuntimeError("Nenhuma fala foi capturada pelo microfone.") from exc
    except RuntimeError:
        raise
    except (AssertionError, AttributeError, OSError, IOError) as exc:
        raise RuntimeError(
            "Não foi possível acessar o microfone. "
            "Verifique as permissões do Windows, o dispositivo de entrada "
            f"e a instalação do PyAudio. Detalhe: {exc}"
        ) from exc

    try:
        if progress:
            progress("Convertendo fala em texto...")
        return recognizer.recognize_google(audio, language="pt-BR")
    except sr.UnknownValueError as exc:
        raise RuntimeError("Não foi possível entender o áudio.") from exc
    except sr.RequestError as exc:
        raise RuntimeError(
            "O serviço de reconhecimento de voz não respondeu."
        ) from exc


def encontrar_arquivo_txt(pasta: str | Path) -> Path | None:
    """Encontra o primeiro arquivo TXT da pasta, sem exigir nome específico."""
    diretorio = Path(pasta)
    if not diretorio.exists() or not diretorio.is_dir():
        return None
    arquivos = sorted(
        (
            caminho
            for caminho in diretorio.iterdir()
            if caminho.is_file() and caminho.suffix.lower() == ".txt"
        ),
        key=lambda caminho: caminho.name.casefold(),
    )
    return arquivos[0] if arquivos else None


def ler_medidas_txt(
    pasta: str | Path,
) -> tuple[Path | None, list[tuple[str, str, str, str]]]:
    """Lê medidas no formato ``altura x largura x espessura,peso``.

    O nome do arquivo não participa da decisão: qualquer TXT da pasta pode
    fornecer as medidas. Linhas vazias ou incompatíveis são ignoradas para que
    um TXT de anotações não impeça o preenchimento manual.
    """
    arquivo_txt = encontrar_arquivo_txt(pasta)
    if arquivo_txt is None:
        return None, []

    try:
        linhas = arquivo_txt.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError):
        return arquivo_txt, []

    medidas: list[tuple[str, str, str, str]] = []
    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
        partes = linha.split(",", 1)
        dimensoes = partes[0].strip()
        peso = partes[1].strip() if len(partes) > 1 else ""
        valores = [
            valor.strip()
            for valor in dimensoes.replace("×", "x").replace("X", "x").split("x")
        ]
        if len(valores) < 3 or not all(valores[:3]):
            continue
        medidas.append((valores[0], valores[1], valores[2], peso))

    return arquivo_txt, medidas

"""Núcleo compartilhado da aplicação desktop PySide6.

Este módulo concentra as regras que não pertencem diretamente a uma tela:
 banco SQLite, tarefas em segundo plano, cadastro de mídias e produção.
"""

import os
import shutil
import sqlite3
import sys
import traceback
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, Qt, Signal

from _LOGS_ import log
from _THREADS_.thread_segura import ThreadSegura


PROJECT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_DIR / "_BANCOS_" / "Base_Dados.db"
DEFAULT_PRODUCTS_DIR = Path.home() / "Downloads" / "PRODUTOS"
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
VIDEO_EXTENSIONS = (".mp4", ".mov", ".avi", ".mkv")
MEDIA_EXTENSIONS = IMAGE_EXTENSIONS + VIDEO_EXTENSIONS

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))


def listar_imagens(
    pasta: str | Path,
    ordenacao: str = "Nome (A-Z)",
) -> list[str]:
    """Lista mídias conforme a ordenação escolhida no cadastro."""
    pasta = Path(pasta)
    if not pasta.exists():
        return []
    arquivos = [
        nome
        for nome in os.listdir(pasta)
        if nome.lower().endswith(MEDIA_EXTENSIONS)
    ]
    if ordenacao == "Nome (Z-A)":
        return sorted(arquivos, key=str.casefold, reverse=True)
    if ordenacao == "Data (mais antiga)":
        return sorted(arquivos, key=lambda nome: (pasta / nome).stat().st_mtime)
    if ordenacao == "Data (mais recente)":
        return sorted(
            arquivos,
            key=lambda nome: (pasta / nome).stat().st_mtime,
            reverse=True,
        )
    return sorted(arquivos, key=str.casefold)


def gerar_referencia(nome: str) -> str:
    """Replica a regra de referência do módulo Functions.py."""
    palavras = [
        palavra
        for palavra in str(nome).strip().lower().replace("_", " ").split()
        if len(palavra) >= 2
    ]
    if len(palavras) == 1:
        return palavras[0][0] + palavras[0][1] + palavras[0][-1]
    if len(palavras) == 2:
        return palavras[0][0] + palavras[1][0] + palavras[1][-1]
    if len(palavras) >= 3:
        return palavras[0][0] + palavras[1][0] + palavras[2][0]
    return "pro"


def gerar_config_ref(
    tipo: str,
    qt_variacoes: int,
    tem_kit_tambem: str,
    qt_kit_tambem: int,
    qt_pecas_kit: int,
    tipo_var_kit: str,
    qt_kits: int,
) -> str:
    """Replica a configuração de produto usada pelo cadastro original."""
    resultado = f"TIPO:{tipo.upper()}"
    if tipo == "Único":
        resultado += f"|VAR={qt_variacoes}"
        if tem_kit_tambem == "Sim":
            resultado += f"|KIT=YES|PECAS={qt_kit_tambem}|QTS_KITS={qt_kits}"
        else:
            resultado += "|KIT=NO"
    elif tipo == "Kit":
        resultado += (
            f"|PECAS={qt_pecas_kit}|VAR={tipo_var_kit.upper()}"
            f"|QTS_KITS={qt_kits}"
        )
    return resultado


def parse_tipo_kit(config: str) -> dict[str, str]:
    valores: dict[str, str] = {}
    for parte in str(config).split("|"):
        if ":" in parte and "=" not in parte:
            chave, valor = parte.split(":", 1)
        elif "=" in parte:
            chave, valor = parte.split("=", 1)
        else:
            continue
        valores[chave.strip().upper()] = valor.strip()
    return valores


def init_database() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS A_ENTRADA(
                PRODUTO TEXT PRIMARY KEY NOT NULL,
                REFERENCIA TEXT,
                DIRETORIO TEXT,
                DESCRITION TEXT,
                SERVENTIA TEXT,
                ACOMPANHA TEXT,
                ACABAMENTO TEXT,
                KIT TEXT,
                OBS TEXT
            );
            CREATE TABLE IF NOT EXISTS VENDAS(
                ID TEXT NOT NULL,
                DATA TEXT,
                NOME_PRODUTO TEXT,
                KIT TEXT,
                PLATAFORMAS_POSTADO TEXT,
                PLATAFORMA_VENDA TEXT,
                CLIENTE_NOME TEXT,
                CLIENTE_CPF TEXT,
                CLIENTE_TELEFONE TEXT,
                ENDERECO TEXT,
                VALOR_VENDA REAL,
                CUSTO_PRODUTO REAL,
                TAXA_PLATAFORMA REAL,
                LUCRO REAL,
                QUANTIDADE INTEGER,
                OBSERVACOES TEXT
            );
            CREATE TABLE IF NOT EXISTS MARKET_PLACE(
                ID TEXT NOT NULL,
                IMAGEM TEXT,
                DATA TEXT,
                NOME_PRODUTO TEXT,
                KIT TEXT,
                PLATAFORMAS_POSTADO TEXT,
                PLATAFORMA_VENDA TEXT,
                CLIENTE_NOME TEXT,
                CLIENTE_CPF TEXT,
                CLIENTE_TELEFONE TEXT,
                ENDERECO TEXT,
                VALOR_VENDA REAL,
                CUSTO_PRODUTO REAL,
                TAXA_PLATAFORMA REAL,
                LUCRO REAL,
                QUANTIDADE INTEGER,
                TITULO TEXT,
                DESCRITION TEXT
            );
            """
        )
    init_memory_schema(DB_PATH)


def ler_entradas() -> list[tuple]:
    init_database()
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute("SELECT * FROM A_ENTRADA ORDER BY rowid").fetchall()


def salvar_entrada(
    produto: str,
    referencia: str,
    diretorio: str,
    descricao: str,
    serventia: str,
    acompanha: str,
    acabamento: str,
    kit: str,
) -> None:
    init_database()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO A_ENTRADA
            (PRODUTO, REFERENCIA, DIRETORIO, DESCRITION, SERVENTIA,
             ACOMPANHA, ACABAMENTO, KIT)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                produto,
                referencia,
                diretorio,
                descricao,
                serventia,
                acompanha,
                acabamento,
                kit,
            ),
        )


def apagar_entrada(produto: str) -> None:
    init_database()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM A_ENTRADA WHERE PRODUTO = ?", (produto,))


class TaskWorker(QObject):
    """Executa uma função pesada em uma thread e devolve progresso à tela."""

    progress = Signal(str)
    finished = Signal(object)
    failed = Signal(str)
    cancelled = Signal(str)

    def __init__(self, function: Callable, *args, **kwargs):
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs

    def run(self) -> None:
        nome_funcao = getattr(self.function, "__name__", "tarefa")
        log.info(
            "TaskWorker",
            "run",
            f"iniciando tarefa: {nome_funcao}",
        )
        try:
            resultado = self.function(
                *self.args,
                progress=self.progress.emit,
                **self.kwargs,
            )
            log.ok(
                "TaskWorker",
                "run",
                f"tarefa concluída: {nome_funcao}",
            )
            self.finished.emit(resultado)
        except RecordingCancelled as exc:
            log.aviso(
                "TaskWorker",
                "run",
                f"tarefa cancelada normalmente: {nome_funcao}; motivo={exc}",
            )
            self.cancelled.emit(str(exc))
        except Exception:
            erro = traceback.format_exc()
            log.erro("TaskWorker", "run", erro)
            self.failed.emit(erro)


class BackgroundMixin:
    """Executa processamento pesado sem travar a janela."""

    def __init__(self) -> None:
        self._threads: list[ThreadSegura] = []

    def start_task(
        self,
        function: Callable,
        *args,
        on_done: Callable[[object], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        on_cancel: Callable[[str], None] | None = None,
        **kwargs,
    ) -> None:
        nome_funcao = getattr(function, "__name__", "tarefa")
        nome_thread = f"{nome_funcao}_{id(self)}_{len(self._threads) + 1}"
        log.info(
            "BackgroundMixin",
            "start_task",
            f"preparando worker: função={nome_funcao}; thread={nome_thread}",
        )
        thread = ThreadSegura(nome=nome_thread, parent=self)
        worker = TaskWorker(function, *args, **kwargs)
        worker.moveToThread(thread)
        setattr(thread, "_task_worker", worker)
        relay = _TaskCallbackRelay(on_done, on_error, on_cancel, parent=self)
        setattr(thread, "_task_callback_relay", relay)
        thread.started.connect(worker.run)
        worker.progress.connect(
            self.show_log,
            Qt.ConnectionType.QueuedConnection,
        )
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.cancelled.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        worker.cancelled.connect(worker.deleteLater)
        if on_done:
            worker.finished.connect(
                relay.handle_done,
                Qt.ConnectionType.QueuedConnection,
            )
        if on_error:
            worker.failed.connect(
                relay.handle_error,
                Qt.ConnectionType.QueuedConnection,
            )
        if on_cancel:
            worker.cancelled.connect(
                relay.handle_cancel,
                Qt.ConnectionType.QueuedConnection,
            )
        thread.finished.connect(self._ao_finalizar_thread)
        self._threads.append(thread)
        thread.start()
        log.info(
            "BackgroundMixin",
            "start_task",
            f"thread iniciada e worker conectado: {nome_thread}",
        )

    def _ao_finalizar_thread(self) -> None:
        """Remove da lista as threads que já terminaram."""
        self._threads[:] = [thread for thread in self._threads if thread.isRunning()]

    def show_log(self, message: str) -> None:
        log.info("BackgroundMixin", "show_log", str(message))


def reconhecer_microfone(
    progress: Callable[[str], None] | None = None,
) -> str:
    """Grava uma fala curta e converte para texto em português.

    Os imports são tardios para que a aplicação continue abrindo mesmo quando
    o computador ainda não tem o suporte de microfone configurado.
    """
    try:
        import speech_recognition as sr
    except ImportError as exc:
        raise RuntimeError(
            "O reconhecimento por microfone precisa do pacote "
            "SpeechRecognition e de um mecanismo de áudio instalado."
        ) from exc

    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            if progress:
                progress("Ajustando o microfone...")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            if progress:
                progress("Fale agora...")
            audio = recognizer.listen(
                source,
                timeout=10,
                phrase_time_limit=120,
            )
    except sr.WaitTimeoutError as exc:
        raise RuntimeError("Nenhuma fala foi capturada pelo microfone.") from exc
    except (AttributeError, OSError) as exc:
        raise RuntimeError(
            "Não foi possível acessar o microfone. "
            "Verifique o dispositivo e o suporte de áudio."
        ) from exc

    try:
        if progress:
            progress("Convertendo fala em texto...")
        return recognizer.recognize_google(audio, language="pt-BR")
    except sr.UnknownValueError as exc:
        raise RuntimeError("Não foi possível entender o áudio.") from exc
    except sr.RequestError as exc:
        raise RuntimeError(
            "O serviço de reconhecimento de voz não respondeu."
        ) from exc


def copiar_cadastro(
    pasta_origem: str,
    pasta_destino: str,
    arquivos: list[str],
    dados: list[tuple[str, str, str, str, str]],
    progress: Callable[[str], None] | None = None,
    nomes_destino: list[str] | None = None,
) -> str:
    """Grava produtos.txt e copia as mídias com os nomes do cadastro."""
    origem = Path(pasta_origem)
    destino = Path(pasta_destino)
    destino.mkdir(parents=True, exist_ok=True)
    caminho_txt = destino / "produtos.txt"
    nomes_destino = nomes_destino or []
    ordem_imagens: list[str] = []
    videos_copiados: list[str] = []

    with caminho_txt.open("w", encoding="utf-8") as arquivo_txt:
        for index, (nome, altura, largura, espessura, peso) in enumerate(dados):
            nome_final = (
                nomes_destino[index]
                if index < len(nomes_destino) and nomes_destino[index]
                else nome
            )
            arquivo_txt.write(f"{altura}x{largura}x{espessura},{peso}\n")
            origem_file = origem / nome
            destino_file = destino / nome_final
            if origem_file.exists():
                shutil.copy2(origem_file, destino_file)
                ordem_imagens.append(nome_final)

        for nome in arquivos:
            if nome.lower().endswith(VIDEO_EXTENSIONS):
                origem_file = origem / nome
                destino_file = destino / nome
                if origem_file.exists():
                    shutil.copy2(origem_file, destino_file)
                    videos_copiados.append(nome)

    (destino / ".ordem_midias.json").write_text(
        json.dumps(
            ordem_imagens + videos_copiados,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    if progress:
        progress(f"Arquivo criado: {caminho_txt}")
        progress(f"Mídias copiadas para: {destino}")
    return str(caminho_txt)


def gerar_pastas_iniciais(
    pasta_destino: str,
    proporcao: str,
    progress: Callable[[str], None] | None = None,
) -> None:
    """Mantém a criação de Proportion_Ajustada e Ajuste_Geral."""
    from Tratar_midias.a__Ajuste_Proportion_IMG import Proporcao_IMG
    from Tratar_midias.b__Ajuste_Geral_IMG import Ajuste_IMG

    destino = Path(pasta_destino)
    proportion = destino / "Proportion_Ajustada"
    ajuste = destino / "Ajuste_Geral"
    if not proportion.exists():
        if progress:
            progress("Gerando Proportion_Ajustada...")
        Proporcao_IMG(
            str(destino),
            str(proportion),
            tuple(map(int, proporcao.split(":"))),
        )
        Ajuste_IMG(str(proportion), str(ajuste))


def salvar_cadastro_task(
    pasta_origem: str,
    pasta_destino: str,
    arquivos: list[str],
    dados: list[tuple[str, str, str, str, str]],
    produto: str,
    descricao: str,
    serventia: str,
    acompanha: str,
    acabamento: str,
    tipo: str,
    qt_variacoes: int,
    tem_kit_tambem: str,
    qt_kit_tambem: int,
    qt_pecas_kit: int,
    tipo_var_kit: str,
    qt_kits: int,
    proporcao: str,
    progress: Callable[[str], None] | None = None,
    nomes_destino: list[str] | None = None,
) -> str:
    ref_kit = gerar_config_ref(
        tipo,
        qt_variacoes,
        tem_kit_tambem,
        qt_kit_tambem,
        qt_pecas_kit,
        tipo_var_kit,
        qt_kits,
    )
    salvar_entrada(
        produto.title(),
        gerar_referencia(produto).lower(),
        pasta_destino,
        descricao,
        serventia,
        acompanha,
        acabamento,
        ref_kit,
    )
    copiar_cadastro(
        pasta_origem,
        pasta_destino,
        arquivos,
        dados,
        progress,
        nomes_destino,
    )
    gerar_pastas_iniciais(pasta_destino, proporcao, progress)
    if progress:
        progress("Cadastro concluído.")
    return pasta_destino


def _primeiro_arquivo(pasta: Path, prefixos: tuple[str, ...]) -> Path | None:
    if not pasta.exists():
        return None
    candidatos = sorted(
        caminho
        for caminho in pasta.iterdir()
        if caminho.is_file()
        and caminho.suffix.lower() in IMAGE_EXTENSIONS
        and caminho.name.lower().startswith(prefixos)
    )
    return candidatos[0] if candidatos else None


def gerar_previews_qt(
    pasta: str,
    referencia: str,
    progress: Callable[[str], None] | None = None,
    imagens_ordem: list[str] | None = None,
    imagem_capa: str | None = None,
    imagem_medida: str | None = None,
) -> tuple[Path, Path, Path, Path]:
    """Gera os previews usando os módulos de mídia existentes."""
    from _FERRAMENTAS_.Previews import preview_produto_com_fundo

    produto_dir = Path(pasta)
    logos_dir = PROJECT_DIR / "Midias"
    logos_dir.mkdir(exist_ok=True)
    logo = _primeiro_arquivo(logos_dir, ("logo",))
    fundo_medida = _primeiro_arquivo(logos_dir, ("medida",))
    fundo_capa = _primeiro_arquivo(logos_dir, ("capa",))
    por_nome = {
        caminho.name.casefold(): caminho
        for caminho in produto_dir.iterdir()
        if caminho.is_file() and caminho.suffix.lower() in IMAGE_EXTENSIONS
    }
    imagens = []
    if imagens_ordem:
        imagens.extend(
            por_nome[nome.casefold()]
            for nome in imagens_ordem
            if nome.casefold() in por_nome
        )
    imagens.extend(
        caminho
        for caminho in sorted(
            por_nome.values(),
            key=lambda item: item.name.casefold(),
        )
        if caminho not in imagens
    )
    if not imagens or not fundo_capa or not fundo_medida:
        raise FileNotFoundError(
            "É necessário ter imagens do produto e arquivos logo*, capa* e "
            "medida* na pasta Midias."
        )

    previews = produto_dir / "PREVIEWS"
    previews.mkdir(exist_ok=True)
    capa = por_nome.get(str(imagem_capa or "").casefold(), imagens[0])
    medida = por_nome.get(str(imagem_medida or "").casefold(), imagens[-1])
    for prefixo, fundo, imagem_atual in (
        ("CAPA", fundo_capa, capa),
        ("MEDIDA", fundo_medida, medida),
    ):
        caminho = previews / f"{prefixo}_{referencia}_{fundo.stem}.png"
        if not caminho.exists():
            resultado = preview_produto_com_fundo(
                imagem_atual,
                fundo,
                sombra_altura=0.18,
            )
            if resultado:
                resultado.save(caminho, "PNG")
                if progress:
                    progress(f"Preview salvo: {caminho.name}")
    return logos_dir, logo or Path(), fundo_capa, fundo_medida


def executar_producao(
    produto_row: tuple,
    sombra_altura: float,
    volume_musica: float,
    ordem: str,
    tipo_medidas: str,
    kit_opcoes: list[str] | str | None,
    progress: Callable[[str], None] | None = None,
) -> str:
    """Executa as mesmas etapas de produção da interface original."""

    def log(texto: str) -> None:
        if progress:
            progress(texto)

    produto = str(produto_row[0]).upper()
    referencia = str(produto_row[1])
    pasta = Path(str(produto_row[2]))
    tipo_kit_config = str(produto_row[7])
    if not pasta.exists():
        raise FileNotFoundError(f"Pasta do produto não encontrada: {pasta}")

    imagens_ordem, videos_manifesto = _ler_ordem_midias_producao(pasta)
    linhas_txt = _ler_linhas_produtos_txt(pasta, imagens_ordem)
    _validar_nomes_e_txt(imagens_ordem, linhas_txt)
    amostras, imagens_medida, resumo_grupos = _separar_imagens_por_papel(
        imagens_ordem
    )
    formas_venda = _formas_de_venda(tipo_kit_config, kit_opcoes)

    log(f"Iniciando produção de {produto}")
    log(
        f"Cadastro validado: {len(imagens_ordem)} imagem(ns), "
        f"{len(videos_manifesto)} vídeo(s), "
        f"{len(resumo_grupos)} grupo(s)."
    )
    for resumo in resumo_grupos:
        log(f"  {resumo}")
    log(f"Formas de venda: {', '.join(formas_venda)}")
    logos_dir, logo_path, capa_path, medida_path = gerar_previews_qt(
        str(pasta),
        referencia,
        progress,
        imagens_ordem=imagens_ordem,
        imagem_capa=amostras[0] if amostras else imagens_ordem[0],
        imagem_medida=imagens_medida[-1],
    )
    qrcode_path = logos_dir / "qr_code_zap.jpg"
    musica_path = logos_dir / "Simple.mp3"
    video_path = logos_dir / "video.png"

    ajuste_geral = pasta / "Ajuste_Geral"
    sem_fundo = pasta / "a_Sem_Fundo"
    fundo_capa = pasta / "b_Fundo_Capa"
    fundo_banco = pasta / "Fundo_Banco"
    fundo_medida = pasta / "b_Fundo_Medida"
    amostra_sem_logo = pasta / "c_Amostra_SEM_LOGO"
    imagem_med = pasta / "Imag_med"
    medida_sem_logo = pasta / "c_Medida_SEM_LOGO"
    amostra_com_logo = pasta / "d_Amostra_COM_LOGO"
    medida_com_logo = pasta / "d_Medida_COM_LOGO"

    from Tratar_midias.c__Remove_Refina_IMG import Remove_IMG
    from Tratar_midias.d__Trocar_Fundo_IMG import Trocar_fundo
    from Tratar_midias.e__Colocar_Logos_Ref import Adicionar_logo_completa
    from Tratar_midias.f__Medidas_Graficos import Colocar_medidas

    if not sem_fundo.exists() or not any(sem_fundo.iterdir()):
        log("Gerando pasta sem fundo...")
        Remove_IMG(str(ajuste_geral), str(sem_fundo))
    if not fundo_capa.exists() or not any(fundo_capa.iterdir()):
        log("Gerando fundo de capa...")
        Trocar_fundo(str(sem_fundo), str(fundo_capa), str(capa_path), sombra_altura)
    if not fundo_banco.exists() or not any(fundo_banco.iterdir()):
        log("Gerando fundo branco...")
        Trocar_fundo(
            str(sem_fundo),
            str(fundo_banco),
            str(logos_dir / "fumdo_branco.jpeg"),
            sombra_altura,
        )
    if not fundo_medida.exists() or not any(fundo_medida.iterdir()):
        log("Gerando fundo de medida...")
        Trocar_fundo(
            str(sem_fundo),
            str(fundo_medida),
            str(medida_path),
            sombra_altura,
        )
    if not amostra_sem_logo.exists() or not all(
        (amostra_sem_logo / nome).exists() for nome in amostras
    ):
        log("Separando capas e variações pelos grupos do Cadastro...")
        _copiar_selecionadas(fundo_capa, amostra_sem_logo, amostras)
    if not imagem_med.exists() or not all(
        (imagem_med / nome).exists() for nome in imagens_medida
    ):
        log("Separando imagens de medidas pelos grupos do Cadastro...")
        _copiar_selecionadas(fundo_medida, imagem_med, imagens_medida)
    if not medida_sem_logo.exists() or not all(
        (medida_sem_logo / Path(nome).stem).with_suffix(".jpg").exists()
        for nome in imagens_medida
    ):
        log("Desenhando medidas...")
        Colocar_medidas(
            str(imagem_med),
            str(medida_sem_logo),
            tipo_kit_config,
            tipo_medidas,
        )
    if not amostra_com_logo.exists() or not any(amostra_com_logo.iterdir()):
        log("Adicionando logo às amostras...")
        Adicionar_logo_completa(
            str(amostra_sem_logo),
            str(amostra_com_logo),
            str(logo_path) if logo_path else None,
            "@henriqls",
            "",
            "Sim",
        )
    if not medida_com_logo.exists() or not any(medida_com_logo.iterdir()):
        log("Adicionando logo às medidas...")
        Adicionar_logo_completa(
            str(medida_sem_logo),
            str(medida_com_logo),
            str(logo_path) if logo_path else None,
            "@henriqls",
            "",
            "Sim",
        )

        init_database()
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM VENDAS")
            for arquivo in sorted(medida_com_logo.iterdir()):
                if arquivo.suffix.lower() in IMAGE_EXTENSIONS:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO VENDAS
                        (ID, DATA, NOME_PRODUTO, KIT, OBSERVACOES)
                        VALUES (?, date('now'), ?, ?, ?)
                        """,
                        (
                            arquivo.stem,
                            produto,
                            tipo_kit_config,
                            str(arquivo),
                        ),
                    )

    videos = [pasta / nome for nome in videos_manifesto]
    video_dir = pasta / "Video_shopee_convertido"
    video_output = video_dir / f"video_{referencia}.mp4"
    if not video_output.exists() and videos:
        from Tratar_midias.v__Converter_video import Converte_Video_Completo

        log("Convertendo vídeo...")
        Converte_Video_Completo(
            ref=referencia,
            input_video=str(videos[0]),
            pasta_video=str(video_dir),
            logo_path=str(video_path),
            som=volume_musica,
            qrcode_path=str(qrcode_path),
            musica_path=str(musica_path),
            link_url="henriqls.shop",
            max_size_mb=30,
            max_duration=59,
        )
    elif not videos:
        log("Nenhum vídeo encontrado; etapa de vídeo ignorada.")

    (pasta / "formas_venda.json").write_text(
        json.dumps(
            {
                "produto": produto,
                "configuracao_cadastro": tipo_kit_config,
                "formas": formas_venda,
                "grupos": resumo_grupos,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    log("Produção concluída.")
    return str(pasta)

"""Núcleo compartilhado da aplicação desktop PySide6.

Este módulo concentra as regras que não pertencem diretamente a uma tela:
 banco SQLite, tarefas em segundo plano, cadastro de mídias e produção.
"""

import os
import shutil
import sqlite3
import sys
import traceback
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, Qt, Signal

from _LOGS_ import log
from _THREADS_.thread_segura import ThreadSegura


PROJECT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_DIR / "_BANCOS_" / "Base_Dados.db"
DEFAULT_PRODUCTS_DIR = Path.home() / "Downloads" / "PRODUTOS"
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
VIDEO_EXTENSIONS = (".mp4", ".mov", ".avi", ".mkv")
MEDIA_EXTENSIONS = IMAGE_EXTENSIONS + VIDEO_EXTENSIONS

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))


def listar_imagens(
    pasta: str | Path,
    ordenacao: str = "Nome (A-Z)",
) -> list[str]:
    """Lista mídias conforme a ordenação escolhida no cadastro."""
    pasta = Path(pasta)
    if not pasta.exists():
        return []
    arquivos = [
        nome
        for nome in os.listdir(pasta)
        if nome.lower().endswith(MEDIA_EXTENSIONS)
    ]
    if ordenacao == "Nome (Z-A)":
        return sorted(arquivos, key=str.casefold, reverse=True)
    if ordenacao == "Data (mais antiga)":
        return sorted(arquivos, key=lambda nome: (pasta / nome).stat().st_mtime)
    if ordenacao == "Data (mais recente)":
        return sorted(
            arquivos,
            key=lambda nome: (pasta / nome).stat().st_mtime,
            reverse=True,
        )
    return sorted(arquivos, key=str.casefold)


def gerar_referencia(nome: str) -> str:
    """Replica a regra de referência do módulo Functions.py."""
    palavras = [
        palavra
        for palavra in str(nome).strip().lower().replace("_", " ").split()
        if len(palavra) >= 2
    ]
    if len(palavras) == 1:
        return palavras[0][0] + palavras[0][1] + palavras[0][-1]
    if len(palavras) == 2:
        return palavras[0][0] + palavras[1][0] + palavras[1][-1]
    if len(palavras) >= 3:
        return palavras[0][0] + palavras[1][0] + palavras[2][0]
    return "pro"


def gerar_config_ref(
    tipo: str,
    qt_variacoes: int,
    tem_kit_tambem: str,
    qt_kit_tambem: int,
    qt_pecas_kit: int,
    tipo_var_kit: str,
    qt_kits: int,
) -> str:
    """Replica a configuração de produto usada pelo cadastro original."""
    resultado = f"TIPO:{tipo.upper()}"
    if tipo == "Único":
        resultado += f"|VAR={qt_variacoes}"
        if tem_kit_tambem == "Sim":
            resultado += f"|KIT=YES|PECAS={qt_kit_tambem}|QTS_KITS={qt_kits}"
        else:
            resultado += "|KIT=NO"
    elif tipo == "Kit":
        resultado += (
            f"|PECAS={qt_pecas_kit}|VAR={tipo_var_kit.upper()}"
            f"|QTS_KITS={qt_kits}"
        )
    return resultado


def parse_tipo_kit(config: str) -> dict[str, str]:
    valores: dict[str, str] = {}
    for parte in str(config).split("|"):
        if ":" in parte and "=" not in parte:
            chave, valor = parte.split(":", 1)
        elif "=" in parte:
            chave, valor = parte.split("=", 1)
        else:
            continue
        valores[chave.strip().upper()] = valor.strip()
    return valores


def init_database() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS A_ENTRADA(
                PRODUTO TEXT PRIMARY KEY NOT NULL,
                REFERENCIA TEXT,
                DIRETORIO TEXT,
                DESCRITION TEXT,
                SERVENTIA TEXT,
                ACOMPANHA TEXT,
                ACABAMENTO TEXT,
                KIT TEXT,
                OBS TEXT
            );
            CREATE TABLE IF NOT EXISTS VENDAS(
                ID TEXT NOT NULL,
                DATA TEXT,
                NOME_PRODUTO TEXT,
                KIT TEXT,
                PLATAFORMAS_POSTADO TEXT,
                PLATAFORMA_VENDA TEXT,
                CLIENTE_NOME TEXT,
                CLIENTE_CPF TEXT,
                CLIENTE_TELEFONE TEXT,
                ENDERECO TEXT,
                VALOR_VENDA REAL,
                CUSTO_PRODUTO REAL,
                TAXA_PLATAFORMA REAL,
                LUCRO REAL,
                QUANTIDADE INTEGER,
                OBSERVACOES TEXT
            );
            CREATE TABLE IF NOT EXISTS MARKET_PLACE(
                ID TEXT NOT NULL,
                IMAGEM TEXT,
                DATA TEXT,
                NOME_PRODUTO TEXT,
                KIT TEXT,
                PLATAFORMAS_POSTADO TEXT,
                PLATAFORMA_VENDA TEXT,
                CLIENTE_NOME TEXT,
                CLIENTE_CPF TEXT,
                CLIENTE_TELEFONE TEXT,
                ENDERECO TEXT,
                VALOR_VENDA REAL,
                CUSTO_PRODUTO REAL,
                TAXA_PLATAFORMA REAL,
                LUCRO REAL,
                QUANTIDADE INTEGER,
                TITULO TEXT,
                DESCRITION TEXT
            );
            """
        )
    init_memory_schema(DB_PATH)


def ler_entradas() -> list[tuple]:
    init_database()
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute("SELECT * FROM A_ENTRADA ORDER BY rowid").fetchall()


def salvar_entrada(
    produto: str,
    referencia: str,
    diretorio: str,
    descricao: str,
    serventia: str,
    acompanha: str,
    acabamento: str,
    kit: str,
) -> None:
    init_database()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO A_ENTRADA
            (PRODUTO, REFERENCIA, DIRETORIO, DESCRITION, SERVENTIA,
             ACOMPANHA, ACABAMENTO, KIT)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                produto,
                referencia,
                diretorio,
                descricao,
                serventia,
                acompanha,
                acabamento,
                kit,
            ),
        )


def apagar_entrada(produto: str) -> None:
    init_database()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM A_ENTRADA WHERE PRODUTO = ?", (produto,))


class TaskWorker(QObject):
    """Executa uma função pesada em uma thread e devolve progresso à tela."""

    progress = Signal(str)
    finished = Signal(object)
    failed = Signal(str)

    cancelled = Signal(str)

    def __init__(self, function: Callable, *args, **kwargs):
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs

    def run(self) -> None:
        nome_funcao = getattr(self.function, "__name__", "tarefa")
        log.info(
            "TaskWorker",
            "run",
            f"iniciando tarefa: {nome_funcao}",
        )
        try:
            resultado = self.function(
                *self.args,
                progress=self.progress.emit,
                **self.kwargs,
            )
            log.ok(
                "TaskWorker",
                "run",
                f"tarefa concluída: {nome_funcao}",
            )
            self.finished.emit(resultado)
        except RecordingCancelled as exc:
            log.aviso(
                "TaskWorker",
                "run",
                f"tarefa cancelada normalmente: {nome_funcao}; motivo={exc}",
            )
            self.cancelled.emit(str(exc))
        except Exception:
            erro = traceback.format_exc()
            log.erro("TaskWorker", "run", erro)
            self.failed.emit(erro)


class BackgroundMixin:
    """Executa processamento pesado sem travar a janela."""

    def __init__(self) -> None:
        self._threads: list[ThreadSegura] = []

    def start_task(
        self,
        function: Callable,
        *args,
        on_done: Callable[[object], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        on_cancel: Callable[[str], None] | None = None,
        **kwargs,
    ) -> None:
        nome_funcao = getattr(function, "__name__", "tarefa")
        nome_thread = f"{nome_funcao}_{id(self)}_{len(self._threads) + 1}"
        thread = ThreadSegura(nome=nome_thread, parent=self)
        worker = TaskWorker(function, *args, **kwargs)
        worker.moveToThread(thread)
        setattr(thread, "_task_worker", worker)
        relay = _TaskCallbackRelay(on_done, on_error, on_cancel, parent=self)
        setattr(thread, "_task_callback_relay", relay)
        thread.started.connect(worker.run)
        worker.progress.connect(
            self.show_log,
            Qt.ConnectionType.QueuedConnection,
        )
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.cancelled.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        worker.cancelled.connect(worker.deleteLater)
        if on_done:
            worker.finished.connect(
                relay.handle_done,
                Qt.ConnectionType.QueuedConnection,
            )
        if on_error:
            worker.failed.connect(
                relay.handle_error,
                Qt.ConnectionType.QueuedConnection,
            )
        if on_cancel:
            worker.cancelled.connect(
                relay.handle_cancel,
                Qt.ConnectionType.QueuedConnection,
            )
        thread.finished.connect(self._ao_finalizar_thread)
        self._threads.append(thread)
        thread.start()

    def _ao_finalizar_thread(self) -> None:
        """Remove da lista as threads que já terminaram."""
        self._threads[:] = [thread for thread in self._threads if thread.isRunning()]

    def show_log(self, message: str) -> None:
        log.info("BackgroundMixin", "progress", str(message))


def reconhecer_microfone(
    progress: Callable[[str], None] | None = None,
) -> str:
    """Grava uma fala curta e converte para texto em português.

    Os imports são tardios para que a aplicação continue abrindo mesmo quando
    o computador ainda não tem o suporte de microfone configurado.
    """
    try:
        import speech_recognition as sr
    except ImportError as exc:
        raise RuntimeError(
            "O reconhecimento por microfone precisa do pacote "
            "SpeechRecognition e de um mecanismo de áudio instalado."
        ) from exc

    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            if progress:
                progress("Ajustando o microfone...")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            if progress:
                progress("Fale agora...")
            audio = recognizer.listen(
                source,
                timeout=10,
                phrase_time_limit=120,
            )
    except sr.WaitTimeoutError as exc:
        raise RuntimeError("Nenhuma fala foi capturada pelo microfone.") from exc
    except (AttributeError, OSError) as exc:
        raise RuntimeError(
            "Não foi possível acessar o microfone. "
            "Verifique o dispositivo e o suporte de áudio."
        ) from exc

    try:
        if progress:
            progress("Convertendo fala em texto...")
        return recognizer.recognize_google(audio, language="pt-BR")
    except sr.UnknownValueError as exc:
        raise RuntimeError("Não foi possível entender o áudio.") from exc
    except sr.RequestError as exc:
        raise RuntimeError(
            "O serviço de reconhecimento de voz não respondeu."
        ) from exc


def copiar_cadastro(
    pasta_origem: str,
    pasta_destino: str,
    arquivos: list[str],
    dados: list[tuple[str, str, str, str, str]],
    progress: Callable[[str], None] | None = None,
    nomes_destino: list[str] | None = None,
) -> str:
    """Grava produtos.txt e copia as mídias com os nomes do cadastro."""
    origem = Path(pasta_origem)
    destino = Path(pasta_destino)
    destino.mkdir(parents=True, exist_ok=True)
    caminho_txt = destino / "produtos.txt"
    nomes_destino = nomes_destino or []
    ordem_imagens: list[str] = []
    videos_copiados: list[str] = []

    with caminho_txt.open("w", encoding="utf-8") as arquivo_txt:
        for index, (nome, altura, largura, espessura, peso) in enumerate(dados):
            nome_final = (
                nomes_destino[index]
                if index < len(nomes_destino) and nomes_destino[index]
                else nome
            )
            arquivo_txt.write(f"{altura}x{largura}x{espessura},{peso}\n")
            origem_file = origem / nome
            destino_file = destino / nome_final
            if origem_file.exists():
                shutil.copy2(origem_file, destino_file)
                ordem_imagens.append(nome_final)

        for nome in arquivos:
            if nome.lower().endswith(VIDEO_EXTENSIONS):
                origem_file = origem / nome
                destino_file = destino / nome
                if origem_file.exists():
                    shutil.copy2(origem_file, destino_file)
                    videos_copiados.append(nome)

    (destino / ".ordem_midias.json").write_text(
        json.dumps(
            ordem_imagens + videos_copiados,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    if progress:
        progress(f"Arquivo criado: {caminho_txt}")
        progress(f"Mídias copiadas para: {destino}")
    return str(caminho_txt)


def gerar_pastas_iniciais(
    pasta_destino: str,
    proporcao: str,
    progress: Callable[[str], None] | None = None,
) -> None:
    """Mantém a criação de Proportion_Ajustada e Ajuste_Geral."""
    from Tratar_midias.a__Ajuste_Proportion_IMG import Proporcao_IMG
    from Tratar_midias.b__Ajuste_Geral_IMG import Ajuste_IMG

    destino = Path(pasta_destino)
    proportion = destino / "Proportion_Ajustada"
    ajuste = destino / "Ajuste_Geral"
    if not proportion.exists():
        if progress:
            progress("Gerando Proportion_Ajustada...")
        Proporcao_IMG(
            str(destino),
            str(proportion),
            tuple(map(int, proporcao.split(":"))),
        )
        Ajuste_IMG(str(proportion), str(ajuste))


def salvar_cadastro_task(
    pasta_origem: str,
    pasta_destino: str,
    arquivos: list[str],
    dados: list[tuple[str, str, str, str, str]],
    produto: str,
    descricao: str,
    serventia: str,
    acompanha: str,
    acabamento: str,
    tipo: str,
    qt_variacoes: int,
    tem_kit_tambem: str,
    qt_kit_tambem: int,
    qt_pecas_kit: int,
    tipo_var_kit: str,
    qt_kits: int,
    proporcao: str,
    progress: Callable[[str], None] | None = None,
    nomes_destino: list[str] | None = None,
) -> str:
    ref_kit = gerar_config_ref(
        tipo,
        qt_variacoes,
        tem_kit_tambem,
        qt_kit_tambem,
        qt_pecas_kit,
        tipo_var_kit,
        qt_kits,
    )
    salvar_entrada(
        produto.title(),
        gerar_referencia(produto).lower(),
        pasta_destino,
        descricao,
        serventia,
        acompanha,
        acabamento,
        ref_kit,
    )
    copiar_cadastro(
        pasta_origem,
        pasta_destino,
        arquivos,
        dados,
        progress=progress,
        nomes_destino=nomes_destino,
    )
    gerar_pastas_iniciais(pasta_destino, proporcao, progress)
    if progress:
        progress("Cadastro concluído.")
    return pasta_destino


def _primeiro_arquivo(pasta: Path, prefixos: tuple[str, ...]) -> Path | None:
    if not pasta.exists():
        return None
    candidatos = sorted(
        caminho
        for caminho in pasta.iterdir()
        if caminho.is_file()
        and caminho.suffix.lower() in IMAGE_EXTENSIONS
        and caminho.name.lower().startswith(prefixos)
    )
    return candidatos[0] if candidatos else None


def gerar_previews_qt(
    pasta: str,
    referencia: str,
    progress: Callable[[str], None] | None = None,
) -> tuple[Path, Path, Path, Path]:
    """Gera os previews usando os módulos de mídia existentes."""
    from _FERRAMENTAS_.Previews import preview_produto_com_fundo

    produto_dir = Path(pasta)
    logos_dir = PROJECT_DIR / "Midias"
    logos_dir.mkdir(exist_ok=True)
    logo = _primeiro_arquivo(logos_dir, ("logo",))
    fundo_medida = _primeiro_arquivo(logos_dir, ("medida",))
    fundo_capa = _primeiro_arquivo(logos_dir, ("capa",))
    imagens = sorted(
        caminho
        for caminho in produto_dir.iterdir()
        if caminho.is_file() and caminho.suffix.lower() in IMAGE_EXTENSIONS
    )
    if not imagens or not fundo_capa or not fundo_medida:
        raise FileNotFoundError(
            "É necessário ter imagens do produto e arquivos logo*, capa* e "
            "medida* na pasta Midias."
        )

    previews = produto_dir / "PREVIEWS"
    previews.mkdir(exist_ok=True)
    imagem_atual = imagens[-1]
    for prefixo, fundo in (("CAPA", fundo_capa), ("MEDIDA", fundo_medida)):
        caminho = previews / f"{prefixo}_{referencia}_{fundo.stem}.png"
        if not caminho.exists():
            resultado = preview_produto_com_fundo(
                imagem_atual,
                fundo,
                sombra_altura=0.18,
            )
            if resultado:
                resultado.save(caminho, "PNG")
                if progress:
                    progress(f"Preview salvo: {caminho.name}")
    return logos_dir, logo or Path(), fundo_capa, fundo_medida


def executar_producao(
    produto_row: tuple,
    sombra_altura: float,
    volume_musica: float,
    ordem: str,
    tipo_medidas: str,
    kit_opcoes: list[str] | str | None,
    progress: Callable[[str], None] | None = None,
) -> str:
    """Executa as mesmas etapas de produção da interface original."""

    def log(texto: str) -> None:
        if progress:
            progress(texto)

    produto = str(produto_row[0]).upper()
    referencia = str(produto_row[1])
    pasta = Path(str(produto_row[2]))
    tipo_kit_config = str(produto_row[7])
    if not pasta.exists():
        raise FileNotFoundError(f"Pasta do produto não encontrada: {pasta}")

    log(f"Iniciando produção de {produto}")
    logos_dir, logo_path, capa_path, medida_path = gerar_previews_qt(
        str(pasta),
        referencia,
        progress,
    )
    qrcode_path = logos_dir / "qr_code_zap.jpg"
    musica_path = logos_dir / "Simple.mp3"
    video_path = logos_dir / "video.png"

    ajuste_geral = pasta / "Ajuste_Geral"
    sem_fundo = pasta / "a_Sem_Fundo"
    fundo_capa = pasta / "b_Fundo_Capa"
    fundo_banco = pasta / "Fundo_Banco"
    fundo_medida = pasta / "b_Fundo_Medida"
    amostra_sem_logo = pasta / "c_Amostra_SEM_LOGO"
    imagem_med = pasta / "Imag_med"
    medida_sem_logo = pasta / "c_Medida_SEM_LOGO"
    amostra_com_logo = pasta / "d_Amostra_COM_LOGO"
    medida_com_logo = pasta / "d_Medida_COM_LOGO"

    from Tratar_midias.c__Remove_Refina_IMG import Remove_IMG
    from Tratar_midias.d__Trocar_Fundo_IMG import Trocar_fundo
    from Tratar_midias.e__Colocar_Logos_Ref import Adicionar_logo_completa
    from Tratar_midias.e__Renomeie_IMG import renomear_por_config
    from Tratar_midias.f__Medidas_Graficos import Colocar_medidas

    if not sem_fundo.exists() or not any(sem_fundo.iterdir()):
        log("Gerando pasta sem fundo...")
        Remove_IMG(str(ajuste_geral), str(sem_fundo))
    if not fundo_capa.exists() or not any(fundo_capa.iterdir()):
        log("Gerando fundo de capa...")
        Trocar_fundo(str(sem_fundo), str(fundo_capa), str(capa_path), sombra_altura)
    if not fundo_banco.exists() or not any(fundo_banco.iterdir()):
        log("Gerando fundo branco...")
        Trocar_fundo(
            str(sem_fundo),
            str(fundo_banco),
            str(logos_dir / "fumdo_branco.jpeg"),
            sombra_altura,
        )
    if not fundo_medida.exists() or not any(fundo_medida.iterdir()):
        log("Gerando fundo de medida...")
        Trocar_fundo(
            str(sem_fundo),
            str(fundo_medida),
            str(medida_path),
            sombra_altura,
        )
    if not amostra_sem_logo.exists() or not any(amostra_sem_logo.iterdir()):
        log("Renomeando amostras...")
        renomear_por_config(
            None,
            str(fundo_capa),
            str(pasta),
            tipo_kit_config,
            referencia,
            ordem,
        )
        renomear_por_config(
            None,
            str(fundo_banco),
            str(pasta),
            tipo_kit_config,
            referencia,
            ordem,
        )
        renomear_por_config(
            None,
            str(fundo_medida),
            str(pasta),
            tipo_kit_config,
            referencia,
            ordem,
        )
    if not medida_sem_logo.exists() or not any(medida_sem_logo.iterdir()):
        log("Desenhando medidas...")
        Colocar_medidas(
            str(imagem_med),
            str(medida_sem_logo),
            tipo_kit_config,
            tipo_medidas,
        )
    if not amostra_com_logo.exists() or not any(amostra_com_logo.iterdir()):
        log("Adicionando logo às amostras...")
        Adicionar_logo_completa(
            str(amostra_sem_logo),
            str(amostra_com_logo),
            str(logo_path) if logo_path else None,
            "@henriqls",
            "",
            "Sim",
        )
    if not medida_com_logo.exists() or not any(medida_com_logo.iterdir()):
        log("Adicionando logo às medidas...")
        Adicionar_logo_completa(
            str(medida_sem_logo),
            str(medida_com_logo),
            str(logo_path) if logo_path else None,
            "@henriqls",
            "",
            "Sim",
        )

        init_database()
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM VENDAS")
            for arquivo in sorted(medida_com_logo.iterdir()):
                if arquivo.suffix.lower() in IMAGE_EXTENSIONS:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO VENDAS
                        (ID, DATA, NOME_PRODUTO, KIT, OBSERVACOES)
                        VALUES (?, date('now'), ?, ?, ?)
                        """,
                        (
                            arquivo.stem,
                            produto,
                            tipo_kit_config,
                            str(arquivo),
                        ),
                    )

    videos = [
        caminho
        for caminho in pasta.iterdir()
        if caminho.is_file() and caminho.suffix.lower() in VIDEO_EXTENSIONS
    ]
    video_dir = pasta / "Video_shopee_convertido"
    video_output = video_dir / f"video_{referencia}.mp4"
    if not video_output.exists() and videos:
        from Tratar_midias.v__Converter_video import Converte_Video_Completo

        log("Convertendo vídeo...")
        Converte_Video_Completo(
            ref=referencia,
            input_video=str(videos[0]),
            pasta_video=str(video_dir),
            logo_path=str(video_path),
            som=volume_musica,
            qrcode_path=str(qrcode_path),
            musica_path=str(musica_path),
            link_url="henriqls.shop",
            max_size_mb=30,
            max_duration=59,
        )
    elif not videos:
        log("Nenhum vídeo encontrado; etapa de vídeo ignorada.")

    log("Produção concluída.")
    return str(pasta)

"""Núcleo compartilhado da aplicação desktop PySide6.

Este módulo concentra as regras que não pertencem diretamente a uma tela:
 banco SQLite, tarefas em segundo plano, cadastro de mídias e produção.
"""

import os
import shutil
import sqlite3
import sys
import traceback
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, Qt, Signal

from _LOGS_ import log
from _THREADS_.thread_segura import ThreadSegura


PROJECT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_DIR / "_BANCOS_" / "Base_Dados.db"
DEFAULT_PRODUCTS_DIR = Path.home() / "Downloads" / "PRODUTOS"
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
VIDEO_EXTENSIONS = (".mp4", ".mov", ".avi", ".mkv")
MEDIA_EXTENSIONS = IMAGE_EXTENSIONS + VIDEO_EXTENSIONS

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))


def listar_imagens(
    pasta: str | Path,
    ordenacao: str = "Nome (A-Z)",
) -> list[str]:
    """Lista mídias conforme a ordenação escolhida no cadastro."""
    pasta = Path(pasta)
    if not pasta.exists():
        return []
    arquivos = [
        nome
        for nome in os.listdir(pasta)
        if nome.lower().endswith(MEDIA_EXTENSIONS)
    ]
    if ordenacao == "Nome (Z-A)":
        return sorted(arquivos, key=str.casefold, reverse=True)
    if ordenacao == "Data (mais antiga)":
        return sorted(arquivos, key=lambda nome: (pasta / nome).stat().st_mtime)
    if ordenacao == "Data (mais recente)":
        return sorted(
            arquivos,
            key=lambda nome: (pasta / nome).stat().st_mtime,
            reverse=True,
        )
    return sorted(arquivos, key=str.casefold)


def gerar_referencia(nome: str) -> str:
    """Replica a regra de referência do módulo Functions.py."""
    palavras = [
        palavra
        for palavra in str(nome).strip().lower().replace("_", " ").split()
        if len(palavra) >= 2
    ]
    if len(palavras) == 1:
        return palavras[0][0] + palavras[0][1] + palavras[0][-1]
    if len(palavras) == 2:
        return palavras[0][0] + palavras[1][0] + palavras[1][-1]
    if len(palavras) >= 3:
        return palavras[0][0] + palavras[1][0] + palavras[2][0]
    return "pro"


def gerar_config_ref(
    tipo: str,
    qt_variacoes: int,
    tem_kit_tambem: str,
    qt_kit_tambem: int,
    qt_pecas_kit: int,
    tipo_var_kit: str,
    qt_kits: int,
) -> str:
    """Replica a configuração de produto usada pelo cadastro original."""
    resultado = f"TIPO:{tipo.upper()}"
    if tipo == "Único":
        resultado += f"|VAR={qt_variacoes}"
        if tem_kit_tambem == "Sim":
            resultado += f"|KIT=YES|PECAS={qt_kit_tambem}|QTS_KITS={qt_kits}"
        else:
            resultado += "|KIT=NO"
    elif tipo == "Kit":
        resultado += (
            f"|PECAS={qt_pecas_kit}|VAR={tipo_var_kit.upper()}"
            f"|QTS_KITS={qt_kits}"
        )
    return resultado


def parse_tipo_kit(config: str) -> dict[str, str]:
    valores: dict[str, str] = {}
    for parte in str(config).split("|"):
        if ":" in parte and "=" not in parte:
            chave, valor = parte.split(":", 1)
        elif "=" in parte:
            chave, valor = parte.split("=", 1)
        else:
            continue
        valores[chave.strip().upper()] = valor.strip()
    return valores


def init_database() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS A_ENTRADA(
                PRODUTO TEXT PRIMARY KEY NOT NULL,
                REFERENCIA TEXT,
                DIRETORIO TEXT,
                DESCRITION TEXT,
                SERVENTIA TEXT,
                ACOMPANHA TEXT,
                ACABAMENTO TEXT,
                KIT TEXT,
                OBS TEXT
            );
            CREATE TABLE IF NOT EXISTS VENDAS(
                ID TEXT NOT NULL,
                DATA TEXT,
                NOME_PRODUTO TEXT,
                KIT TEXT,
                PLATAFORMAS_POSTADO TEXT,
                PLATAFORMA_VENDA TEXT,
                CLIENTE_NOME TEXT,
                CLIENTE_CPF TEXT,
                CLIENTE_TELEFONE TEXT,
                ENDERECO TEXT,
                VALOR_VENDA REAL,
                CUSTO_PRODUTO REAL,
                TAXA_PLATAFORMA REAL,
                LUCRO REAL,
                QUANTIDADE INTEGER,
                OBSERVACOES TEXT
            );
            CREATE TABLE IF NOT EXISTS MARKET_PLACE(
                ID TEXT NOT NULL,
                IMAGEM TEXT,
                DATA TEXT,
                NOME_PRODUTO TEXT,
                KIT TEXT,
                PLATAFORMAS_POSTADO TEXT,
                PLATAFORMA_VENDA TEXT,
                CLIENTE_NOME TEXT,
                CLIENTE_CPF TEXT,
                CLIENTE_TELEFONE TEXT,
                ENDERECO TEXT,
                VALOR_VENDA REAL,
                CUSTO_PRODUTO REAL,
                TAXA_PLATAFORMA REAL,
                LUCRO REAL,
                QUANTIDADE INTEGER,
                TITULO TEXT,
                DESCRITION TEXT
            );
            """
        )
    init_memory_schema(DB_PATH)


def ler_entradas() -> list[tuple]:
    init_database()
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute("SELECT * FROM A_ENTRADA ORDER BY rowid").fetchall()


def salvar_entrada(
    produto: str,
    referencia: str,
    diretorio: str,
    descricao: str,
    serventia: str,
    acompanha: str,
    acabamento: str,
    kit: str,
) -> None:
    init_database()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO A_ENTRADA
            (PRODUTO, REFERENCIA, DIRETORIO, DESCRITION, SERVENTIA,
             ACOMPANHA, ACABAMENTO, KIT)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                produto,
                referencia,
                diretorio,
                descricao,
                serventia,
                acompanha,
                acabamento,
                kit,
            ),
        )


def apagar_entrada(produto: str) -> None:
    init_database()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM A_ENTRADA WHERE PRODUTO = ?", (produto,))


class TaskWorker(QObject):
    """Executa uma função pesada em uma thread e devolve progresso à tela."""

    progress = Signal(str)
    finished = Signal(object)
    failed = Signal(str)

    cancelled = Signal(str)

    def __init__(self, function: Callable, *args, **kwargs):
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs

    def run(self) -> None:
        nome_funcao = getattr(self.function, "__name__", "tarefa")
        log.info(
            "TaskWorker",
            "run",
            f"iniciando tarefa: {nome_funcao}",
        )
        try:
            resultado = self.function(
                *self.args,
                progress=self.progress.emit,
                **self.kwargs,
            )
            log.ok(
                "TaskWorker",
                "run",
                f"tarefa concluída: {nome_funcao}",
            )
            self.finished.emit(resultado)
        except RecordingCancelled as exc:
            log.aviso(
                "TaskWorker",
                "run",
                f"tarefa cancelada normalmente: {nome_funcao}; motivo={exc}",
            )
            self.cancelled.emit(str(exc))
        except Exception:
            erro = traceback.format_exc()
            log.erro("TaskWorker", "run", erro)
            self.failed.emit(erro)


class BackgroundMixin:
    """Executa processamento pesado sem travar a janela."""

    def __init__(self) -> None:
        self._threads: list[ThreadSegura] = []

    def start_task(
        self,
        function: Callable,
        *args,
        on_done: Callable[[object], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        on_cancel: Callable[[str], None] | None = None,
        **kwargs,
    ) -> None:
        nome_funcao = getattr(function, "__name__", "tarefa")
        nome_thread = f"{nome_funcao}_{id(self)}_{len(self._threads) + 1}"
        thread = ThreadSegura(nome=nome_thread, parent=self)
        worker = TaskWorker(function, *args, **kwargs)
        worker.moveToThread(thread)
        setattr(thread, "_task_worker", worker)
        relay = _TaskCallbackRelay(on_done, on_error, on_cancel, parent=self)
        setattr(thread, "_task_callback_relay", relay)
        thread.started.connect(worker.run)
        worker.progress.connect(
            self.show_log,
            Qt.ConnectionType.QueuedConnection,
        )
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.cancelled.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        worker.cancelled.connect(worker.deleteLater)
        if on_done:
            worker.finished.connect(
                relay.handle_done,
                Qt.ConnectionType.QueuedConnection,
            )
        if on_error:
            worker.failed.connect(
                relay.handle_error,
                Qt.ConnectionType.QueuedConnection,
            )
        if on_cancel:
            worker.cancelled.connect(
                relay.handle_cancel,
                Qt.ConnectionType.QueuedConnection,
            )
        thread.finished.connect(self._ao_finalizar_thread)
        self._threads.append(thread)
        thread.start()

    def _ao_finalizar_thread(self) -> None:
        """Remove da lista as threads que já terminaram."""
        self._threads[:] = [thread for thread in self._threads if thread.isRunning()]

    def show_log(self, message: str) -> None:
        log.info("BackgroundMixin", "progress", str(message))


def reconhecer_microfone(
    progress: Callable[[str], None] | None = None,
) -> str:
    """Grava uma fala curta e converte para texto em português.

    Os imports são tardios para que a aplicação continue abrindo mesmo quando
    o computador ainda não tem o suporte de microfone configurado.
    """
    try:
        import speech_recognition as sr
    except ImportError as exc:
        raise RuntimeError(
            "O reconhecimento por microfone precisa do pacote "
            "SpeechRecognition e de um mecanismo de áudio instalado."
        ) from exc

    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            if progress:
                progress("Ajustando o microfone...")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            if progress:
                progress("Fale agora...")
            audio = recognizer.listen(
                source,
                timeout=10,
                phrase_time_limit=120,
            )
    except sr.WaitTimeoutError as exc:
        raise RuntimeError("Nenhuma fala foi capturada pelo microfone.") from exc
    except (AttributeError, OSError) as exc:
        raise RuntimeError(
            "Não foi possível acessar o microfone. "
            "Verifique o dispositivo e o suporte de áudio."
        ) from exc

    try:
        if progress:
            progress("Convertendo fala em texto...")
        return recognizer.recognize_google(audio, language="pt-BR")
    except sr.UnknownValueError as exc:
        raise RuntimeError("Não foi possível entender o áudio.") from exc
    except sr.RequestError as exc:
        raise RuntimeError(
            "O serviço de reconhecimento de voz não respondeu."
        ) from exc


def copiar_cadastro(
    pasta_origem: str,
    pasta_destino: str,
    arquivos: list[str],
    dados: list[tuple[str, str, str, str, str]],
    progress: Callable[[str], None] | None = None,
    nomes_destino: list[str] | None = None,
) -> str:
    """Grava produtos.txt e copia as mídias com os nomes do cadastro."""
    origem = Path(pasta_origem)
    destino = Path(pasta_destino)
    destino.mkdir(parents=True, exist_ok=True)
    caminho_txt = destino / "produtos.txt"
    nomes_destino = nomes_destino or []
    ordem_imagens: list[str] = []
    videos_copiados: list[str] = []

    with caminho_txt.open("w", encoding="utf-8") as arquivo_txt:
        for index, (nome, altura, largura, espessura, peso) in enumerate(dados):
            nome_final = (
                nomes_destino[index]
                if index < len(nomes_destino) and nomes_destino[index]
                else nome
            )
            arquivo_txt.write(f"{altura}x{largura}x{espessura},{peso}\n")
            origem_file = origem / nome
            destino_file = destino / nome_final
            if origem_file.exists():
                shutil.copy2(origem_file, destino_file)
                ordem_imagens.append(nome_final)

        for nome in arquivos:
            if nome.lower().endswith(VIDEO_EXTENSIONS):
                origem_file = origem / nome
                destino_file = destino / nome
                if origem_file.exists():
                    shutil.copy2(origem_file, destino_file)
                    videos_copiados.append(nome)

    (destino / ".ordem_midias.json").write_text(
        json.dumps(
            ordem_imagens + videos_copiados,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    if progress:
        progress(f"Arquivo criado: {caminho_txt}")
        progress(f"Mídias copiadas para: {destino}")
    return str(caminho_txt)


def gerar_pastas_iniciais(
    pasta_destino: str,
    proporcao: str,
    progress: Callable[[str], None] | None = None,
) -> None:
    """Gera PNGs com proporção escolhida sem reduzir os pixels do produto."""
    from Tratar_midias.a__Ajuste_Proportion_IMG import Proporcao_IMG
    from Tratar_midias.b__Ajuste_Geral_IMG import Ajuste_IMG

    destino = Path(pasta_destino)
    ajuste = destino / PASTA_AJUSTE_GERAL
    imagens_origem = sorted(
        arquivo
        for arquivo in destino.iterdir()
        if arquivo.is_file() and arquivo.suffix.lower() in IMAGE_EXTENSIONS
    )
    if not imagens_origem:
        if progress:
            progress(
                f"AVISO: não há imagens originais para gerar {PASTA_AJUSTE_GERAL}."
            )
        return

    if progress:
        progress(
            f"Gerando {PASTA_AJUSTE_GERAL} em PNG, "
            "preservando a resolução original..."
        )
    with tempfile.TemporaryDirectory(
        prefix="hen-place-cadastro-"
    ) as pasta_temporaria:
        Proporcao_IMG(
            str(destino),
            pasta_temporaria,
            tuple(map(int, proporcao.split(":"))),
            preservar_resolucao=True,
        )
        Ajuste_IMG(
            pasta_temporaria,
            str(ajuste),
            salvar_png=True,
        )

    faltantes = [
        imagem.stem
        for imagem in imagens_origem
        if not (ajuste / f"{imagem.stem}.png").is_file()
    ]
    if faltantes and progress:
        progress(
            f"AVISO: {PASTA_AJUSTE_GERAL} não recebeu PNGs para: "
            + ", ".join(faltantes)
        )
    elif progress:
        progress(f"Cadastro concluído. PNGs prontos em: {ajuste}")


def salvar_cadastro_task(
    pasta_origem: str,
    pasta_destino: str,
    arquivos: list[str],
    dados: list[tuple[str, str, str, str, str]],
    produto: str,
    descricao: str,
    serventia: str,
    acompanha: str,
    acabamento: str,
    tipo: str,
    qt_variacoes: int,
    tem_kit_tambem: str,
    qt_kit_tambem: int,
    qt_pecas_kit: int,
    tipo_var_kit: str,
    qt_kits: int,
    proporcao: str,
    progress: Callable[[str], None] | None = None,
    nomes_destino: list[str] | None = None,
) -> str:
    ref_kit = gerar_config_ref(
        tipo,
        qt_variacoes,
        tem_kit_tambem,
        qt_kit_tambem,
        qt_pecas_kit,
        tipo_var_kit,
        qt_kits,
    )
    salvar_entrada(
        produto.title(),
        gerar_referencia(produto).lower(),
        pasta_destino,
        descricao,
        serventia,
        acompanha,
        acabamento,
        ref_kit,
    )
    copiar_cadastro(
        pasta_origem,
        pasta_destino,
        arquivos,
        dados,
        progress=progress,
        nomes_destino=nomes_destino,
    )
    gerar_pastas_iniciais(pasta_destino, proporcao, progress)
    if progress:
        progress("Cadastro concluído.")
    return pasta_destino


def _primeiro_arquivo(pasta: Path, prefixos: tuple[str, ...]) -> Path | None:
    if not pasta.exists():
        return None
    candidatos = sorted(
        caminho
        for caminho in pasta.iterdir()
        if caminho.is_file()
        and caminho.suffix.lower() in IMAGE_EXTENSIONS
        and caminho.name.lower().startswith(prefixos)
    )
    return candidatos[0] if candidatos else None


def gerar_previews_qt(
    pasta: str,
    referencia: str,
    progress: Callable[[str], None] | None = None,
) -> tuple[Path, Path, Path, Path]:
    """Gera os previews usando os módulos de mídia existentes."""
    from _FERRAMENTAS_.Previews import preview_produto_com_fundo

    produto_dir = Path(pasta)
    logos_dir = PROJECT_DIR / "Midias"
    logos_dir.mkdir(exist_ok=True)
    logo = _primeiro_arquivo(logos_dir, ("logo",))
    fundo_medida = _primeiro_arquivo(logos_dir, ("medida",))
    fundo_capa = _primeiro_arquivo(logos_dir, ("capa",))
    imagens = sorted(
        caminho
        for caminho in produto_dir.iterdir()
        if caminho.is_file() and caminho.suffix.lower() in IMAGE_EXTENSIONS
    )
    if not imagens or not fundo_capa or not fundo_medida:
        raise FileNotFoundError(
            "É necessário ter imagens do produto e arquivos logo*, capa* e "
            "medida* na pasta Midias."
        )

    previews = produto_dir / "PREVIEWS"
    previews.mkdir(exist_ok=True)
    imagem_atual = imagens[-1]
    for prefixo, fundo in (("CAPA", fundo_capa), ("MEDIDA", fundo_medida)):
        caminho = previews / f"{prefixo}_{referencia}_{fundo.stem}.png"
        if not caminho.exists():
            resultado = preview_produto_com_fundo(
                imagem_atual,
                fundo,
                sombra_altura=0.18,
            )
            if resultado:
                resultado.save(caminho, "PNG")
                if progress:
                    progress(f"Preview salvo: {caminho.name}")
    return logos_dir, logo or Path(), fundo_capa, fundo_medida


def executar_producao(
    produto_row: tuple,
    sombra_altura: float,
    volume_musica: float,
    ordem: str,
    tipo_medidas: str,
    kit_opcoes: list[str] | str | None,
    progress: Callable[[str], None] | None = None,
) -> str:
    """Executa as mesmas etapas de produção da interface original."""

    def log(texto: str) -> None:
        if progress:
            progress(texto)

    produto = str(produto_row[0]).upper()
    referencia = str(produto_row[1])
    pasta = Path(str(produto_row[2]))
    tipo_kit_config = str(produto_row[7])
    if not pasta.exists():
        raise FileNotFoundError(f"Pasta do produto não encontrada: {pasta}")

    log(f"Iniciando produção de {produto}")
    logos_dir, logo_path, capa_path, medida_path = gerar_previews_qt(
        str(pasta),
        referencia,
        progress,
    )
    qrcode_path = logos_dir / "qr_code_zap.jpg"
    musica_path = logos_dir / "Simple.mp3"
    video_path = logos_dir / "video.png"

    ajuste_geral = pasta / "Ajuste_Geral"
    sem_fundo = pasta / "a_Sem_Fundo"
    fundo_capa = pasta / "b_Fundo_Capa"
    fundo_banco = pasta / "Fundo_Banco"
    fundo_medida = pasta / "b_Fundo_Medida"
    amostra_sem_logo = pasta / "c_Amostra_SEM_LOGO"
    imagem_med = pasta / "Imag_med"
    medida_sem_logo = pasta / "c_Medida_SEM_LOGO"
    amostra_com_logo = pasta / "d_Amostra_COM_LOGO"
    medida_com_logo = pasta / "d_Medida_COM_LOGO"

    from Tratar_midias.c__Remove_Refina_IMG import Remove_IMG
    from Tratar_midias.d__Trocar_Fundo_IMG import Trocar_fundo
    from Tratar_midias.e__Colocar_Logos_Ref import Adicionar_logo_completa
    from Tratar_midias.e__Renomeie_IMG import renomear_por_config
    from Tratar_midias.f__Medidas_Graficos import Colocar_medidas

    if not sem_fundo.exists() or not any(sem_fundo.iterdir()):
        log("Gerando pasta sem fundo...")
        Remove_IMG(str(ajuste_geral), str(sem_fundo))
    if not fundo_capa.exists() or not any(fundo_capa.iterdir()):
        log("Gerando fundo de capa...")
        Trocar_fundo(str(sem_fundo), str(fundo_capa), str(capa_path), sombra_altura)
    if not fundo_banco.exists() or not any(fundo_banco.iterdir()):
        log("Gerando fundo branco...")
        Trocar_fundo(
            str(sem_fundo),
            str(fundo_banco),
            str(logos_dir / "fumdo_branco.jpeg"),
            sombra_altura,
        )
    if not fundo_medida.exists() or not any(fundo_medida.iterdir()):
        log("Gerando fundo de medida...")
        Trocar_fundo(
            str(sem_fundo),
            str(fundo_medida),
            str(medida_path),
            sombra_altura,
        )
    if not amostra_sem_logo.exists() or not any(amostra_sem_logo.iterdir()):
        log("Renomeando amostras...")
        renomear_por_config(
            None,
            str(fundo_capa),
            str(pasta),
            tipo_kit_config,
            referencia,
            ordem,
        )
        renomear_por_config(
            None,
            str(fundo_banco),
            str(pasta),
            tipo_kit_config,
            referencia,
            ordem,
        )
        renomear_por_config(
            None,
            str(fundo_medida),
            str(pasta),
            tipo_kit_config,
            referencia,
            ordem,
        )
    if not medida_sem_logo.exists() or not any(medida_sem_logo.iterdir()):
        log("Desenhando medidas...")
        Colocar_medidas(
            str(imagem_med),
            str(medida_sem_logo),
            tipo_kit_config,
            tipo_medidas,
        )
    if not amostra_com_logo.exists() or not any(amostra_com_logo.iterdir()):
        log("Adicionando logo às amostras...")
        Adicionar_logo_completa(
            str(amostra_sem_logo),
            str(amostra_com_logo),
            str(logo_path) if logo_path else None,
            "@henriqls",
            "",
            "Sim",
        )
    if not medida_com_logo.exists() or not any(medida_com_logo.iterdir()):
        log("Adicionando logo às medidas...")
        Adicionar_logo_completa(
            str(medida_sem_logo),
            str(medida_com_logo),
            str(logo_path) if logo_path else None,
            "@henriqls",
            "",
            "Sim",
        )

        init_database()
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM VENDAS")
            for arquivo in sorted(medida_com_logo.iterdir()):
                if arquivo.suffix.lower() in IMAGE_EXTENSIONS:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO VENDAS
                        (ID, DATA, NOME_PRODUTO, KIT, OBSERVACOES)
                        VALUES (?, date('now'), ?, ?, ?)
                        """,
                        (
                            arquivo.stem,
                            produto,
                            tipo_kit_config,
                            str(arquivo),
                        ),
                    )

    videos = [
        caminho
        for caminho in pasta.iterdir()
        if caminho.is_file() and caminho.suffix.lower() in VIDEO_EXTENSIONS
    ]
    video_dir = pasta / "Video_shopee_convertido"
    video_output = video_dir / f"video_{referencia}.mp4"
    if not video_output.exists() and videos:
        from Tratar_midias.v__Converter_video import Converte_Video_Completo

        log("Convertendo vídeo...")
        Converte_Video_Completo(
            ref=referencia,
            input_video=str(videos[0]),
            pasta_video=str(video_dir),
            logo_path=str(video_path),
            som=volume_musica,
            qrcode_path=str(qrcode_path),
            musica_path=str(musica_path),
            link_url="henriqls.shop",
            max_size_mb=30,
            max_duration=59,
        )
    elif not videos:
        log("Nenhum vídeo encontrado; etapa de vídeo ignorada.")

    log("Produção concluída.")
    return str(pasta)