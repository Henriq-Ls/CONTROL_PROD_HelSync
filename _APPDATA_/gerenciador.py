# _APPDATA_/gerenciador.py
"""
GerenciadorAppData — Singleton Facade do AppData

Ponto ÚNICO de acesso a tudo que vive em PASTA_APPDATA (definida em _CONFIGURA_).
Nenhum módulo deve montar caminhos de AppData na mão — todos consultam esta classe.

Uso:
    from _APPDATA_ import appdata
    appdata.inicializar()
    print(appdata.pasta_raiz)
"""

import os
import json
import datetime
from pathlib import Path


MIDIA_CATEGORIAS = {
    "logo": {
        "rotulo": "Logo para imagens",
        "extensoes": (".png", ".jpg", ".jpeg", ".webp"),
        "multiplo": True,
    },
    "fundo_capa": {
        "rotulo": "Fundo de capa",
        "extensoes": (".png", ".jpg", ".jpeg", ".webp"),
        "multiplo": True,
    },
    "fundo_medida": {
        "rotulo": "Fundo de medida",
        "extensoes": (".png", ".jpg", ".jpeg", ".webp"),
        "multiplo": True,
    },
    "fundo_branco": {
        "rotulo": "Fundo branco",
        "extensoes": (".png", ".jpg", ".jpeg", ".webp"),
        "multiplo": False,
    },
    "logo_video": {
        "rotulo": "Logo para vídeo",
        "extensoes": (".png", ".jpg", ".jpeg", ".webp"),
        "multiplo": False,
    },
    "qr_video": {
        "rotulo": "QR Code para vídeo",
        "extensoes": (".png", ".jpg", ".jpeg", ".webp"),
        "multiplo": False,
    },
    "musica": {
        "rotulo": "Música para vídeo",
        "extensoes": (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"),
        "multiplo": True,
    },
}


# Import tardio para evitar dependência circular na inicialização
def _log():
    from _LOGS_ import log as _l
    return _l


class GerenciadorAppData:
    """Singleton — instância única durante toda a vida do processo."""
    _inst: "GerenciadorAppData | None" = None

    @classmethod
    def instancia(cls) -> "GerenciadorAppData":
        if cls._inst is None:
            cls._inst = cls()
        return cls._inst

    def __init__(self):
        from _CONFIGURA_ import PASTA_APPDATA
        self._raiz = PASTA_APPDATA
        self._inicializado = False

    # ── Inicialização ────────────────────────────────────────────────────────

    def inicializar(self):
        """
        Garante toda a estrutura de pastas e arquivos padrão.
        Deve ser chamado UMA vez no startup, antes de qualquer acesso.
        """
        if self._inicializado:
            return

        os.makedirs(self._raiz,          exist_ok=True)
        os.makedirs(self.pasta_logs,     exist_ok=True)
        os.makedirs(self.pasta_config,   exist_ok=True)
        os.makedirs(self.pasta_cache,    exist_ok=True)
        os.makedirs(self.pasta_projetos, exist_ok=True)
        os.makedirs(self.pasta_midias,   exist_ok=True)
        for categoria in MIDIA_CATEGORIAS:
            os.makedirs(self.pasta_midia_categoria(categoria), exist_ok=True)

        self._garantir_config_padrao()
        self._inicializado = True
        _log().ok("AppData", "inicializar", f"pasta_raiz={self._raiz}")

    # ── Caminhos canônicos ────────────────────────────────────────────────────
    # Sempre use estas properties — nunca monte caminhos na mão fora daqui

    @property
    def pasta_raiz(self) -> str:
        return self._raiz

    @property
    def pasta_logs(self) -> str:
        return os.path.join(self._raiz, "logs")

    @property
    def pasta_config(self) -> str:
        return os.path.join(self._raiz, "config")

    @property
    def pasta_cache(self) -> str:
        return os.path.join(self._raiz, "cache")

    @property
    def pasta_projetos(self) -> str:
        return os.path.join(self._raiz, "projetos")

    @property
    def pasta_midias(self) -> str:
        return os.path.join(self._raiz, "midias")

    def pasta_midia_categoria(self, categoria: str) -> str:
        if categoria not in MIDIA_CATEGORIAS:
            raise ValueError(f"Categoria de mídia inválida: {categoria}")
        return os.path.join(self.pasta_midias, categoria)

    def listar_midias(self, categoria: str) -> list[str]:
        """Lista apenas arquivos compatíveis com a categoria do AppData."""
        pasta = Path(self.pasta_midia_categoria(categoria))
        extensoes = MIDIA_CATEGORIAS[categoria]["extensoes"]
        if not pasta.is_dir():
            return []
        return sorted(
            caminho.name
            for caminho in pasta.iterdir()
            if caminho.is_file() and caminho.suffix.casefold() in extensoes
        )

    @property
    def arq_config(self) -> str:
        return os.path.join(self.pasta_config, "config.json")

    @property
    def arq_sessao(self) -> str:
        return os.path.join(self.pasta_config, "sessao.json")

    # ── Config ────────────────────────────────────────────────────────────────

    def ler_config(self) -> dict:
        """Lê config.json. Retorna {} em caso de falha."""
        try:
            with open(self.arq_config, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            _log().aviso("AppData", "ler_config", f"falha ao ler config.json: {e}")
            return {}

    def salvar_config(self, dados: dict) -> bool:
        """Salva dict no config.json e informa se a gravação foi concluída."""
        try:
            with open(self.arq_config, "w", encoding="utf-8") as f:
                json.dump(dados, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            _log().erro("AppData", "salvar_config", f"falha ao salvar config.json: {e}")
            return False

    def ler_config_ia(self) -> dict:
        """Lê o formulário persistido de configurações da IA."""
        self.inicializar()
        dados = self.ler_config()
        configuracao = dados.get("ia")
        return dict(configuracao) if isinstance(configuracao, dict) else {}

    def salvar_config_ia(self, configuracao: dict) -> None:
        """Salva o formulário completo da IA dentro de config.json."""
        self.inicializar()
        dados = self.ler_config()
        dados["ia"] = dict(configuracao)
        self.salvar_config(dados)

    def restaurar_padrao(self):
        """Apaga config.json e recria com valores padrão de fábrica."""
        if os.path.exists(self.arq_config):
            os.remove(self.arq_config)
        self._garantir_config_padrao()
        _log().ok("AppData", "restaurar_padrao", "config restaurado ao padrão")

    # ── Sessão (geometria, estado da janela) ──────────────────────────────────

    def ler_sessao(self) -> dict:
        """Lê sessao.json. Retorna {} em caso de falha."""
        try:
            with open(self.arq_sessao, "r", encoding="utf-8") as f:
                dados = json.load(f)
            _log().ok("AppData", "ler_sessao", f"sessão restaurada: {list(dados.keys())}")
            return dados
        except Exception:
            _log().info("AppData", "ler_sessao", "sessao.json ausente — usando padrão")
            return {}

    def salvar_sessao(self, dados: dict):
        """Persiste dados de sessão em sessao.json."""
        try:
            with open(self.arq_sessao, "w", encoding="utf-8") as f:
                json.dump(dados, f, indent=2, ensure_ascii=False)
            _log().ok("AppData", "salvar_sessao", f"sessão salva: {list(dados.keys())}")
        except Exception as e:
            _log().erro("AppData", "salvar_sessao", f"falha ao salvar sessao.json: {e}")

    # ── Internos ──────────────────────────────────────────────────────────────

    def _garantir_config_padrao(self):
        if not os.path.exists(self.arq_config):
            from _CONFIGURA_ import VERSAO_APP, TEMA_QT
            padrao = {
                "tema":    TEMA_QT,
                "versao":  VERSAO_APP,
                "criado":  datetime.datetime.now().isoformat(),
            }
            self.salvar_config(padrao)
