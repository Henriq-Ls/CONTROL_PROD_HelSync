"""Memoria persistente da IA armazenada fora do banco comercial.

Conversas de produtos e rascunhos do Cadastro ficam no AppData, separados do
banco comercial. O rascunho pode ser promovido quando o produto for salvo.
"""

from __future__ import annotations

import json
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from _APPDATA_ import appdata


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _raiz_memoria() -> Path:
    raiz = Path(appdata.pasta_raiz) / "IAs"
    raiz.mkdir(parents=True, exist_ok=True)
    (raiz / "produtos").mkdir(exist_ok=True)
    return raiz


def _raiz_chat_ia() -> Path:
    """Raiz das conversas temporarias e operacionais da IA."""
    raiz = Path(appdata.pasta_raiz) / "IAs" / "Chat_IA"
    (raiz / "RASCUNHOS").mkdir(parents=True, exist_ok=True)
    (raiz / "GLOBAIS").mkdir(exist_ok=True)
    return raiz


def _componente_seguro(valor: str) -> str:
    limpo = re.sub(r"[^A-Za-z0-9._-]+", "_", str(valor).strip())
    return limpo.strip("._")[:120] or "sem-identificador"


def _id_pasta(produto_id: str) -> str:
    texto = str(produto_id).strip()
    if ":" in texto:
        prefixo, restante = texto.split(":", 1)
        if prefixo == "produto":
            texto = restante
    return _componente_seguro(texto)


def _pasta_produto(produto_id: str, *, criar: bool = True) -> Path:
    pasta = _raiz_memoria() / "produtos" / _id_pasta(produto_id)
    if criar:
        pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def _pasta_conversa(
    produto_id: str,
    conversa_id: str,
    escopo: str,
    *,
    criar: bool = True,
) -> Path:
    pasta = (
        _pasta_produto(produto_id, criar=criar)
        / "conversas"
        / _componente_seguro(conversa_id)
        / _componente_seguro(escopo or "Cadastro")
    )
    if criar:
        pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def _escrever_json_atomico(caminho: Path, dados: Mapping[str, Any]) -> None:
    temporario = caminho.with_suffix(caminho.suffix + ".tmp")
    temporario.write_text(
        json.dumps(dict(dados), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporario.replace(caminho)


def _ler_json(caminho: Path) -> dict[str, Any]:
    if not caminho.exists():
        return {}
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return {}
    return dict(dados) if isinstance(dados, Mapping) else {}


def _caminho_rascunho_ativo() -> Path:
    return _raiz_chat_ia() / "rascunho_ativo.json"


def obter_rascunho_ativo() -> str:
    """Retorna o rascunho ainda nao promovido associado a esta instalacao."""
    caminho = _caminho_rascunho_ativo()
    dados = _ler_json(caminho)
    identificador = str(dados.get("rascunho_id") or "").strip()
    if not identificador:
        return ""
    pasta = caminho_rascunho(identificador)
    if not pasta.is_dir():
        limpar_rascunho_ativo(identificador)
        return ""
    contexto = _ler_json(pasta / "contexto.json")
    if contexto.get("promovido_para"):
        limpar_rascunho_ativo(identificador)
        return ""
    return identificador


def definir_rascunho_ativo(rascunho_id: str) -> None:
    caminho = _caminho_rascunho_ativo()
    identificador = str(rascunho_id or "").strip()
    if not identificador:
        caminho.unlink(missing_ok=True)
        return
    _escrever_json_atomico(caminho, {"rascunho_id": identificador})


def limpar_rascunho_ativo(rascunho_id: str = "") -> None:
    caminho = _caminho_rascunho_ativo()
    if not caminho.exists():
        return
    if rascunho_id:
        atual = _ler_json(caminho)
        if str(atual.get("rascunho_id") or "") != str(rascunho_id):
            return
    caminho.unlink(missing_ok=True)


def _pasta_conversa_global(escopo: str, *, criar: bool = True) -> Path:
    pasta = _raiz_chat_ia() / "GLOBAIS" / _componente_seguro(escopo or "Geral")
    if criar:
        pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def abrir_conversa_global(escopo: str) -> str:
    """Abre a conversa persistente do escopo global, sem produto associado."""
    pasta = _pasta_conversa_global(escopo)
    caminho_meta = pasta / "meta.json"
    meta = _ler_json(caminho_meta)
    conversa_id = str(meta.get("conversa_id") or "").strip()
    if not conversa_id:
        conversa_id = uuid.uuid4().hex
        _escrever_json_atomico(
            caminho_meta,
            {
                "conversa_id": conversa_id,
                "escopo": str(escopo or "Geral"),
                "criada_em": _agora(),
            },
        )
    return conversa_id


def salvar_mensagem_global(
    escopo: str,
    papel: str,
    conteudo: str,
    *,
    provedor: str = "",
    modelo: str = "",
    status: str = "concluida",
) -> str | None:
    """Acrescenta uma mensagem a memoria global isolada por aba."""
    texto = str(conteudo).strip()
    if not texto:
        return None
    conversa_id = abrir_conversa_global(escopo)
    caminho = _pasta_conversa_global(escopo) / "conversa.jsonl"
    mensagem = {
        "mensagem_id": uuid.uuid4().hex,
        "conversa_id": conversa_id,
        "escopo": str(escopo or "Geral"),
        "papel": str(papel or "user"),
        "conteudo": texto,
        "provedor": str(provedor or ""),
        "modelo": str(modelo or ""),
        "status": str(status or "concluida"),
        "criada_em": _agora(),
    }
    with caminho.open("a", encoding="utf-8") as arquivo:
        arquivo.write(json.dumps(mensagem, ensure_ascii=False) + "\n")
    return str(caminho)


def carregar_mensagens_globais(
    escopo: str,
    limite: int = 20,
) -> list[dict[str, str]]:
    """Carrega somente a conversa global da aba solicitada."""
    caminho = _pasta_conversa_global(escopo, criar=False) / "conversa.jsonl"
    if not caminho.exists():
        return []
    try:
        linhas = caminho.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    mensagens: list[dict[str, str]] = []
    for linha in linhas:
        try:
            item = json.loads(linha)
        except (TypeError, ValueError):
            continue
        if not isinstance(item, dict):
            continue
        mensagens.append(
            {
                "role": str(item.get("papel") or ""),
                "content": str(item.get("conteudo") or ""),
                "provider": str(item.get("provedor") or ""),
                "model": str(item.get("modelo") or ""),
                "status": str(item.get("status") or ""),
                "created_at": str(item.get("criada_em") or ""),
            }
        )
    limite_seguro = max(1, min(int(limite), 100))
    return mensagens[-limite_seguro:]


def apagar_conversa_global(escopo: str) -> bool:
    """Limpa, mediante acao explicita, apenas o historico global desta aba."""
    pasta = _pasta_conversa_global(escopo, criar=False)
    caminho = pasta / "conversa.jsonl"
    if not caminho.exists():
        return False
    caminho.unlink()
    (pasta / "meta.json").unlink(missing_ok=True)
    return True


def _conversas_existentes(produto_id: str) -> list[Path]:
    pasta = _pasta_produto(produto_id, criar=False) / "conversas"
    if not pasta.exists():
        return []
    return [item for item in pasta.iterdir() if item.is_dir()]


def _ultima_conversa(produto_id: str) -> str:
    conversas = _conversas_existentes(produto_id)
    if not conversas:
        return ""
    mais_nova = max(conversas, key=lambda item: item.stat().st_mtime)
    return mais_nova.name


def abrir_conversa(
    produto_id: str,
    snapshot: Mapping[str, Any] | None = None,
) -> str:
    """Retorna a conversa do produto ou cria uma somente para produto salvo."""
    produto_id = str(produto_id).strip()
    if not produto_id:
        return ""

    existente = _ultima_conversa(produto_id)
    if existente:
        return existente

    conversa_id = uuid.uuid4().hex
    produto_pasta = _pasta_produto(produto_id)
    conversa_pasta = produto_pasta / "conversas" / conversa_id
    conversa_pasta.mkdir(parents=True, exist_ok=True)
    _escrever_json_atomico(
        conversa_pasta / "meta.json",
        {
            "produto_id": produto_id,
            "conversa_id": conversa_id,
            "criada_em": _agora(),
        },
    )
    if snapshot:
        _escrever_json_atomico(produto_pasta / "identidade.json", snapshot)
    return conversa_id


def init_memory_schema(db_path: str | Path | None = None) -> None:
    """Prepara pastas de memoria sem apagar historicos ou rascunhos."""
    del db_path
    _raiz_memoria()
    _raiz_chat_ia()


def iniciar_rascunho(
    rascunho_id: str = "",
    snapshot: Mapping[str, Any] | None = None,
    *,
    escopo: str = "Cadastro",
) -> str:
    """Cria ou abre um rascunho persistente no AppData."""
    identificador = _componente_seguro(rascunho_id) if rascunho_id else uuid.uuid4().hex
    pasta = _raiz_chat_ia() / "RASCUNHOS" / identificador
    pasta.mkdir(parents=True, exist_ok=True)
    meta_caminho = pasta / "contexto.json"
    meta = _ler_json(meta_caminho)
    if meta.get("promovido_para"):
        raise ValueError("Este rascunho ja foi associado a um produto salvo.")
    meta.update(
        {
            "rascunho_id": identificador,
            "escopo": str(escopo or "Cadastro"),
            "atualizado_em": _agora(),
        }
    )
    if snapshot:
        meta["snapshot"] = dict(snapshot)
    _escrever_json_atomico(meta_caminho, meta)
    definir_rascunho_ativo(identificador)
    return identificador


def caminho_rascunho(rascunho_id: str) -> Path:
    """Retorna o caminho da pasta persistente de um rascunho."""
    return _raiz_chat_ia() / "RASCUNHOS" / _componente_seguro(rascunho_id)


def salvar_contexto_rascunho(
    rascunho_id: str,
    snapshot: Mapping[str, Any],
    *,
    escopo: str = "Cadastro",
) -> str:
    """Atualiza o snapshot sem apagar o historico de mensagens."""
    identificador = iniciar_rascunho(rascunho_id, snapshot, escopo=escopo)
    return str(caminho_rascunho(identificador) / "contexto.json")


def salvar_rascunho_mensagem(
    rascunho_id: str,
    escopo: str,
    papel: str,
    conteudo: str,
    *,
    provedor: str = "",
    modelo: str = "",
    status: str = "concluida",
    metadados: Mapping[str, Any] | None = None,
) -> str | None:
    """Persiste uma mensagem temporaria e retorna o arquivo usado."""
    texto = str(conteudo).strip()
    if not rascunho_id or not texto:
        return None
    identificador = iniciar_rascunho(rascunho_id, escopo=escopo)
    caminho = caminho_rascunho(identificador) / "conversa.jsonl"
    mensagem: dict[str, Any] = {
        "mensagem_id": uuid.uuid4().hex,
        "papel": str(papel or "user"),
        "conteudo": texto,
        "escopo": str(escopo or "Cadastro"),
        "provedor": str(provedor or ""),
        "modelo": str(modelo or ""),
        "status": str(status or "concluida"),
        "criada_em": _agora(),
    }
    if metadados:
        mensagem["metadados"] = dict(metadados)
    with caminho.open("a", encoding="utf-8") as arquivo:
        arquivo.write(json.dumps(mensagem, ensure_ascii=False) + "\n")
    return str(caminho)


def carregar_rascunho_mensagens(
    rascunho_id: str,
    escopo: str,
    limite: int = 100,
) -> list[dict[str, str]]:
    """Carrega mensagens do rascunho filtradas pelo escopo da aba."""
    if not rascunho_id:
        return []
    caminho = caminho_rascunho(rascunho_id) / "conversa.jsonl"
    if not caminho.exists():
        return []
    try:
        linhas = caminho.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    mensagens: list[dict[str, str]] = []
    escopo_alvo = str(escopo or "Cadastro")
    for linha in linhas:
        try:
            item = json.loads(linha)
        except (TypeError, ValueError):
            continue
        if not isinstance(item, dict):
            continue
        if str(item.get("escopo") or "Cadastro") != escopo_alvo:
            continue
        mensagens.append(
            {
                "role": str(item.get("papel") or ""),
                "content": str(item.get("conteudo") or ""),
                "provider": str(item.get("provedor") or ""),
                "model": str(item.get("modelo") or ""),
                "status": str(item.get("status") or ""),
                "created_at": str(item.get("criada_em") or ""),
            }
        )
    return mensagens[-max(1, min(int(limite), 500)) :]


def apagar_rascunho(rascunho_id: str) -> bool:
    """Apaga somente o rascunho explicitamente solicitado."""
    pasta = caminho_rascunho(rascunho_id)
    if not pasta.exists():
        return False
    for caminho in pasta.iterdir():
        if caminho.is_file():
            caminho.unlink()
    pasta.rmdir()
    limpar_rascunho_ativo(rascunho_id)
    return True


def salvar_produto(
    produto_id: str,
    snapshot: Mapping[str, Any],
    db_path: str | Path | None = None,
    *,
    conversa_id: str = "",
) -> None:
    """Salva identidade e contexto somente de produto cadastrado."""
    if not produto_id or not conversa_id:
        return

    dados = dict(snapshot)
    dados["produto_id"] = str(dados.get("produto_id") or produto_id)
    dados["memoria_id"] = str(produto_id)
    dados["memoria_tipo"] = "produto"
    dados["conversa_id"] = conversa_id
    dados["atualizado_em"] = _agora()
    produto_pasta = _pasta_produto(produto_id)
    _escrever_json_atomico(produto_pasta / "identidade.json", dados)
    pasta = _pasta_conversa(produto_id, conversa_id, str(dados.get("escopo") or "Cadastro"))
    _escrever_json_atomico(pasta / "contexto.json", dados)


def obter_produto(
    produto_id: str,
    db_path: str | Path | None = None,
) -> dict[str, Any] | None:
    """Carrega a identidade persistente de um produto."""
    caminho = _pasta_produto(produto_id, criar=False) / "identidade.json"
    if not caminho.exists():
        return None
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return None


def salvar_mensagem(
    produto_id: str,
    escopo: str,
    papel: str,
    conteudo: str,
    *,
    provedor: str = "",
    modelo: str = "",
    status: str = "concluida",
    conversa_id: str = "",
    db_path: str | Path | None = None,
) -> int | None:
    """Acrescenta uma mensagem da conversa persistente do produto."""
    texto = str(conteudo).strip()
    if not produto_id or not conversa_id or not texto:
        return None

    caminho = _pasta_conversa(produto_id, conversa_id, escopo) / "conversa.jsonl"
    mensagem = {
        "mensagem_id": uuid.uuid4().hex,
        "papel": str(papel or "user"),
        "conteudo": texto,
        "provedor": str(provedor or ""),
        "modelo": str(modelo or ""),
        "status": str(status or "concluida"),
        "criada_em": _agora(),
    }
    with caminho.open("a", encoding="utf-8") as arquivo:
        arquivo.write(json.dumps(mensagem, ensure_ascii=False) + "\n")
    return 1


def apagar_historico_produto(produto_id: str) -> bool:
    """Apaga todo o historico conversacional do produto, preservando identidade."""
    if not str(produto_id or "").strip():
        return False
    pasta = _pasta_produto(produto_id, criar=False) / "conversas"
    if not pasta.exists():
        return False
    shutil.rmtree(pasta)
    return True


def apagar_historico_conversa(
    produto_id: str,
    conversa_id: str,
    escopo: str,
) -> bool:
    """Apaga somente as mensagens de um produto, conversa e escopo."""
    if not str(produto_id or "").strip() or not str(conversa_id or "").strip():
        return False
    caminho = (
        _pasta_conversa(produto_id, conversa_id, escopo, criar=False)
        / "conversa.jsonl"
    )
    if not caminho.is_file():
        return False
    caminho.unlink()
    return True


def carregar_mensagens(
    produto_id: str,
    escopo: str | None,
    limite: int = 20,
    db_path: str | Path | None = None,
    *,
    conversa_id: str = "",
) -> list[dict[str, str]]:
    """Carrega um escopo ou, com ``None``, a conversa inteira do produto."""
    conversa_id = conversa_id or _ultima_conversa(produto_id)
    if not produto_id or not conversa_id:
        return []

    if escopo is None:
        pasta_conversa = (
            _pasta_produto(produto_id, criar=False)
            / "conversas"
            / _componente_seguro(conversa_id)
        )
        if not pasta_conversa.is_dir():
            return []
        arquivos = sorted(pasta_conversa.glob("*/conversa.jsonl"))
    else:
        caminho = (
            _pasta_conversa(produto_id, conversa_id, escopo, criar=False)
            / "conversa.jsonl"
        )
        arquivos = [caminho] if caminho.exists() else []
    if not arquivos:
        return []

    limite_seguro = max(1, min(int(limite), 100))
    ordenadas: list[tuple[str, str, int, dict[str, str]]] = []
    for arquivo in arquivos:
        try:
            linhas = arquivo.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for indice, linha in enumerate(linhas[-limite_seguro:]):
            try:
                item = json.loads(linha)
            except (TypeError, ValueError):
                continue
            if not isinstance(item, dict):
                continue
            mensagem = {
                "role": str(item.get("papel") or ""),
                "content": str(item.get("conteudo") or ""),
                "provider": str(item.get("provedor") or ""),
                "model": str(item.get("modelo") or ""),
                "status": str(item.get("status") or ""),
                "created_at": str(item.get("criada_em") or ""),
            }
            ordenadas.append(
                (
                    mensagem["created_at"],
                    arquivo.parent.name,
                    indice,
                    mensagem,
                )
            )

    ordenadas.sort(key=lambda item: (item[0], item[1], item[2]))
    return [item[3] for item in ordenadas[-limite_seguro:]]


def carregar_memoria_compartilhada_produto(
    produto_id: str,
    conversa_id: str,
    escopo_atual: str,
    *,
    limite_por_aba: int = 100,
    max_caracteres: int = 16000,
) -> list[dict[str, str]]:
    """Lê mensagens de outras abas do mesmo produto como contexto de referência.

    Não lê outros produtos nem a conversa visível da aba atual. O legado misto
    de Produção pode ser lido, mas sua origem de aba permanece sem identificação.
    """
    produto = str(produto_id or "").strip()
    conversa = str(conversa_id or "").strip()
    if not produto or not conversa:
        return []

    pasta_conversa = (
        _pasta_produto(produto, criar=False)
        / "conversas"
        / _componente_seguro(conversa)
    )
    if not pasta_conversa.is_dir():
        return []

    escopo_atual_seguro = _componente_seguro(escopo_atual or "Cadastro")
    limite_seguro = max(1, min(int(limite_por_aba), 100))
    caracteres_seguros = max(1000, min(int(max_caracteres), 40000))
    mensagens: list[dict[str, str]] = []

    for arquivo in sorted(pasta_conversa.glob("*/conversa.jsonl")):
        escopo = arquivo.parent.name
        if escopo == escopo_atual_seguro:
            continue
        try:
            linhas = arquivo.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for indice, linha in enumerate(linhas[-limite_seguro:]):
            try:
                item = json.loads(linha)
            except (TypeError, ValueError):
                continue
            if not isinstance(item, dict):
                continue
            papel = str(item.get("papel") or "")
            conteudo = str(item.get("conteudo") or "").strip()
            if papel not in {"user", "assistant"} or not conteudo:
                continue
            mensagens.append(
                {
                    "escopo": escopo,
                    "role": papel,
                    "content": conteudo,
                    "created_at": str(item.get("criada_em") or ""),
                    "_ordem": str(indice),
                }
            )

    mensagens.sort(
        key=lambda item: (
            item["created_at"],
            item["escopo"],
            int(item["_ordem"]),
        )
    )

    recentes: list[dict[str, str]] = []
    caracteres_usados = 0
    for mensagem in reversed(mensagens):
        rotulo = mensagem["escopo"]
        papel = mensagem["role"]
        custo_cabecalho = len(rotulo) + len(papel) + 24
        restante = caracteres_seguros - caracteres_usados - custo_cabecalho
        if restante <= 0:
            break
        conteudo = mensagem["content"]
        if len(conteudo) > restante:
            marcador = "[trecho final de mensagem longa]\n"
            if restante <= len(marcador):
                break
            conteudo = marcador + conteudo[-(restante - len(marcador)) :]
        recente = {
            "escopo": rotulo,
            "role": papel,
            "content": conteudo,
            "created_at": mensagem["created_at"],
        }
        recentes.append(recente)
        caracteres_usados += custo_cabecalho + len(conteudo)

    return list(reversed(recentes))


def carregar_historico_legado_producao(
    produto_id: str,
    conversa_id: str,
    limite: int = 100,
) -> list[dict[str, str]]:
    """Lê o histórico misto legado de Produção sem o mesclar às novas conversas."""
    if not str(produto_id or "").strip() or not str(conversa_id or "").strip():
        return []
    return carregar_mensagens(
        produto_id,
        "Producao",
        limite,
        conversa_id=conversa_id,
    )


def carregar_contexto(
    produto_id: str,
    escopo: str,
    limite: int = 20,
    db_path: str | Path | None = None,
    *,
    conversa_id: str = "",
) -> dict[str, Any]:
    return {
        "produto": obter_produto(produto_id, db_path),
        "mensagens": carregar_mensagens(
            produto_id,
            escopo,
            limite,
            db_path,
            conversa_id=conversa_id,
        ),
    }


def promover_rascunho(
    rascunho_id: str,
    produto_id: str,
    conversa_id: str = "",
) -> int:
    """Copia o historico do rascunho uma vez, mantendo a origem para auditoria."""
    identificador = str(rascunho_id or "").strip()
    produto = str(produto_id or "").strip()
    destino_conversa = str(conversa_id or "").strip()
    if not identificador or not produto or not destino_conversa:
        return 0

    pasta = caminho_rascunho(identificador)
    caminho_contexto = pasta / "contexto.json"
    meta = _ler_json(caminho_contexto)
    promovido = meta.get("promovido_para")
    if promovido:
        if (
            isinstance(promovido, dict)
            and str(promovido.get("produto_id") or "") == produto
            and str(promovido.get("conversa_id") or "") == destino_conversa
        ):
            limpar_rascunho_ativo(identificador)
            return 0
        raise ValueError("Este rascunho ja foi promovido para outro destino.")

    caminho_origem = pasta / "conversa.jsonl"
    if not caminho_origem.exists():
        meta["promovido_para"] = {
            "produto_id": produto,
            "conversa_id": destino_conversa,
            "promovida_em": _agora(),
            "mensagens": 0,
        }
        _escrever_json_atomico(caminho_contexto, meta)
        limpar_rascunho_ativo(identificador)
        return 0

    try:
        linhas = caminho_origem.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise RuntimeError("Nao foi possivel ler o historico do rascunho.") from exc

    transferidas = 0
    arquivos_vistos: dict[Path, set[str]] = {}
    for linha in linhas:
        try:
            origem = json.loads(linha)
        except (TypeError, ValueError):
            continue
        if not isinstance(origem, dict):
            continue
        conteudo = str(origem.get("conteudo") or "").strip()
        papel = str(origem.get("papel") or "").strip()
        if not conteudo or papel not in {"user", "assistant"}:
            continue

        escopo = str(origem.get("escopo") or "Cadastro")
        caminho_destino = (
            _pasta_conversa(produto, destino_conversa, escopo)
            / "conversa.jsonl"
        )
        if caminho_destino not in arquivos_vistos:
            existentes: set[str] = set()
            if caminho_destino.exists():
                try:
                    linhas_existentes = caminho_destino.read_text(
                        encoding="utf-8"
                    ).splitlines()
                except OSError as exc:
                    raise RuntimeError(
                        "Nao foi possivel verificar o historico de destino."
                    ) from exc
                for linha_existente in linhas_existentes:
                    try:
                        item_existente = json.loads(linha_existente)
                    except (TypeError, ValueError):
                        continue
                    origem_meta = item_existente.get("origem_rascunho")
                    if isinstance(origem_meta, dict):
                        chave = (
                            f"{origem_meta.get('rascunho_id', '')}:"
                            f"{origem_meta.get('mensagem_id', '')}"
                        )
                        existentes.add(chave)
            arquivos_vistos[caminho_destino] = existentes

        mensagem_origem_id = str(origem.get("mensagem_id") or "")
        chave_origem = f"{identificador}:{mensagem_origem_id}"
        if chave_origem in arquivos_vistos[caminho_destino]:
            continue

        mensagem = {
            "mensagem_id": uuid.uuid4().hex,
            "papel": papel,
            "conteudo": conteudo,
            "provedor": str(origem.get("provedor") or ""),
            "modelo": str(origem.get("modelo") or ""),
            "status": "rascunho_promovido",
            "criada_em": str(origem.get("criada_em") or _agora()),
            "origem_rascunho": {
                "rascunho_id": identificador,
                "mensagem_id": mensagem_origem_id,
            },
        }
        with caminho_destino.open("a", encoding="utf-8") as arquivo:
            arquivo.write(json.dumps(mensagem, ensure_ascii=False) + "\n")
        arquivos_vistos[caminho_destino].add(chave_origem)
        transferidas += 1

    meta["promovido_para"] = {
        "produto_id": produto,
        "conversa_id": destino_conversa,
        "promovida_em": _agora(),
        "mensagens": transferidas,
    }
    _escrever_json_atomico(caminho_contexto, meta)
    limpar_rascunho_ativo(identificador)
    return transferidas