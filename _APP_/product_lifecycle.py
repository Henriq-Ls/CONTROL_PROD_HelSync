"""Persistência do ciclo pendente → produto permanente → anúncios.

O esquema novo é sempre aplicado por ação explícita da interface. A rotina
cria e valida uma cópia SQLite antes de qualquer alteração no banco original.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from _APP_.PySide6_core import DB_PATH


SCHEMA_VERSION = 1
MARKETPLACES_PADRAO = ("Site", "Shopee", "Amazon", "Mercado Livre")
_CAMPOS_PRODUTO = (
    "PRODUTO",
    "REFERENCIA",
    "DIRETORIO",
    "DESCRITION",
    "SERVENTIA",
    "ACOMPANHA",
    "ACABAMENTO",
    "KIT",
    "OBS",
    "REGRAS_ANUNCIO",
    "PROPORCAO",
)


def _conectar(path: str | Path = DB_PATH) -> sqlite3.Connection:
    conexao = sqlite3.connect(str(path), timeout=15)
    conexao.row_factory = sqlite3.Row
    return conexao


@contextmanager
def _banco(path: str | Path = DB_PATH) -> Iterator[sqlite3.Connection]:
    conexao = _conectar(path)
    try:
        yield conexao
    except Exception:
        conexao.rollback()
        raise
    else:
        conexao.commit()
    finally:
        conexao.close()


def _tabelas(conexao: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in conexao.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }


def esquema_instalado(conexao: sqlite3.Connection) -> bool:
    return {
        "PRODUTOS_ATIVOS",
        "MARKETPLACES",
        "ANUNCIOS",
        "ANUNCIO_IDS",
        "HPC_SCHEMA_VERSION",
    }.issubset(_tabelas(conexao))


def migracao_concluida(banco: str | Path = DB_PATH) -> bool:
    caminho = Path(banco).expanduser()
    if not caminho.is_file():
        return False
    with _banco(caminho) as conexao:
        if not esquema_instalado(conexao):
            return False
        linha = conexao.execute(
            "SELECT MAX(VERSAO) FROM HPC_SCHEMA_VERSION"
        ).fetchone()
        return bool(linha and int(linha[0] or 0) >= SCHEMA_VERSION)


def _validar_integridade(caminho: Path) -> None:
    with _banco(caminho) as conexao:
        resultado = conexao.execute("PRAGMA integrity_check").fetchone()
    if not resultado or str(resultado[0]).casefold() != "ok":
        raise RuntimeError(
            f"A verificação de integridade falhou para {caminho.name}: "
            f"{resultado[0] if resultado else 'sem resultado'}"
        )


def _contagens_tabelas(caminho: Path, tabelas: set[str]) -> dict[str, int]:
    with _banco(caminho) as conexao:
        existentes = _tabelas(conexao)
        return {
            tabela: int(
                conexao.execute(
                    f'SELECT COUNT(*) FROM "{tabela}"'
                ).fetchone()[0]
            )
            for tabela in tabelas
            if tabela in existentes
        }


def _criar_esquema(conexao: sqlite3.Connection) -> None:
    comandos = (
        """
        CREATE TABLE IF NOT EXISTS HPC_SCHEMA_VERSION(
            VERSAO INTEGER PRIMARY KEY,
            APLICADO_EM TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS PRODUTOS_ATIVOS(
            PRODUTO TEXT PRIMARY KEY NOT NULL,
            REFERENCIA TEXT,
            DIRETORIO TEXT,
            DESCRITION TEXT,
            SERVENTIA TEXT,
            ACOMPANHA TEXT,
            ACABAMENTO TEXT,
            KIT TEXT,
            OBS TEXT,
            REGRAS_ANUNCIO TEXT,
            PROPORCAO TEXT,
            CONCLUIDO_EM TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS MARKETPLACES(
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            NOME TEXT NOT NULL COLLATE NOCASE UNIQUE,
            ATIVO INTEGER NOT NULL DEFAULT 1 CHECK (ATIVO IN (0, 1)),
            CRIADO_EM TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS ANUNCIOS(
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            PRODUTO TEXT NOT NULL,
            MARKETPLACE_ID INTEGER NOT NULL,
            TITULO TEXT NOT NULL DEFAULT '',
            DESCRITION TEXT NOT NULL DEFAULT '',
            ATIVO INTEGER NOT NULL DEFAULT 1 CHECK (ATIVO IN (0, 1)),
            CRIADO_EM TEXT NOT NULL,
            ATUALIZADO_EM TEXT NOT NULL,
            UNIQUE (PRODUTO COLLATE NOCASE, MARKETPLACE_ID),
            FOREIGN KEY (MARKETPLACE_ID) REFERENCES MARKETPLACES(ID)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS ANUNCIO_IDS(
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            ANUNCIO_ID INTEGER NOT NULL,
            ID_PRODUCAO TEXT NOT NULL,
            PRECO REAL NOT NULL CHECK (PRECO >= 0),
            UNIQUE (ANUNCIO_ID, ID_PRODUCAO),
            FOREIGN KEY (ANUNCIO_ID) REFERENCES ANUNCIOS(ID)
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS IDX_ANUNCIOS_PRODUTO
        ON ANUNCIOS(PRODUTO, ATIVO)
        """,
        """
        CREATE INDEX IF NOT EXISTS IDX_ANUNCIO_IDS_PRODUCAO
        ON ANUNCIO_IDS(ID_PRODUCAO)
        """,
    )
    for comando in comandos:
        conexao.execute(comando)

    agora = datetime.now().astimezone().isoformat(timespec="seconds")
    for nome in MARKETPLACES_PADRAO:
        conexao.execute(
            """
            INSERT INTO MARKETPLACES (NOME, ATIVO, CRIADO_EM)
            VALUES (?, 1, ?)
            ON CONFLICT(NOME) DO NOTHING
            """,
            (nome, agora),
        )
    conexao.execute(
        """
        INSERT INTO HPC_SCHEMA_VERSION (VERSAO, APLICADO_EM)
        VALUES (?, ?)
        ON CONFLICT(VERSAO) DO NOTHING
        """,
        (SCHEMA_VERSION, agora),
    )


def criar_backup_e_migrar(
    *,
    confirmado: bool,
    banco: str | Path = DB_PATH,
) -> Path:
    """Faz backup validado e aplica o esquema somente após confirmação."""
    if not confirmado:
        raise PermissionError(
            "A migração exige confirmação explícita do usuário."
        )

    origem = Path(banco).expanduser().resolve()
    if not origem.is_file():
        raise FileNotFoundError(f"Banco SQLite não encontrado: {origem}")
    if migracao_concluida(origem):
        return origem

    with _banco(origem) as conexao:
        existentes = _tabelas(conexao)
        ausentes = {"A_ENTRADA", "VENDAS", "MARKET_PLACE"} - existentes
        if ausentes:
            raise RuntimeError(
                "O banco não contém as tabelas esperadas: "
                + ", ".join(sorted(ausentes))
            )
        integridade = conexao.execute("PRAGMA integrity_check").fetchone()
        if not integridade or str(integridade[0]).casefold() != "ok":
            raise RuntimeError(
                "O banco original falhou na verificação de integridade. "
                "Nenhuma migração foi aplicada."
            )

    pasta_backups = origem.parent / "backups"
    pasta_backups.mkdir(parents=True, exist_ok=True)
    instante = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    backup = pasta_backups / f"{origem.stem}_{instante}.db"
    indice = 1
    while backup.exists():
        backup = pasta_backups / f"{origem.stem}_{instante}_{indice}.db"
        indice += 1

    with _banco(origem) as fonte, _banco(backup) as destino:
        fonte.backup(destino)
    if not backup.is_file() or backup.stat().st_size == 0:
        raise RuntimeError("A cópia de segurança ficou vazia.")
    _validar_integridade(backup)
    tabelas_criticas = {"A_ENTRADA", "VENDAS", "MARKET_PLACE"}
    if _contagens_tabelas(origem, tabelas_criticas) != _contagens_tabelas(
        backup,
        tabelas_criticas,
    ):
        raise RuntimeError(
            "A cópia não corresponde às contagens das tabelas originais. "
            "A migração não foi aplicada."
        )

    try:
        with _banco(origem) as conexao:
            conexao.execute("PRAGMA foreign_keys = ON")
            conexao.execute("BEGIN IMMEDIATE")
            _criar_esquema(conexao)
            conexao.execute("COMMIT")
        _validar_integridade(origem)
        if not migracao_concluida(origem):
            raise RuntimeError(
                "O esquema novo não passou pela verificação final."
            )
    except Exception:
        # O backup permanece disponível para recuperação manual.
        raise
    return backup


def exigir_esquema(conexao: sqlite3.Connection) -> None:
    if not esquema_instalado(conexao):
        raise RuntimeError(
            "O novo modelo ainda não foi instalado. Use a ação "
            "“Atualizar banco com backup” na área Ferramentas."
        )
    linha = conexao.execute(
        "SELECT MAX(VERSAO) FROM HPC_SCHEMA_VERSION"
    ).fetchone()
    if not linha or int(linha[0] or 0) < SCHEMA_VERSION:
        raise RuntimeError("A versão do esquema do banco não é compatível.")


def listar_marketplaces(
    *,
    incluir_inativos: bool = False,
    conexao: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    propria = conexao is None
    db = conexao or _conectar()
    try:
        if not esquema_instalado(db):
            return [
                {"id": None, "name": nome, "active": True}
                for nome in MARKETPLACES_PADRAO
            ]
        where = "" if incluir_inativos else "WHERE ATIVO = 1"
        rows = db.execute(
            f"""
            SELECT ID, NOME, ATIVO
            FROM MARKETPLACES
            {where}
            ORDER BY NOME COLLATE NOCASE
            """
        ).fetchall()
        return [
            {
                "id": int(row["ID"]),
                "name": str(row["NOME"]),
                "active": bool(row["ATIVO"]),
            }
            for row in rows
        ]
    finally:
        if propria:
            db.close()


def adicionar_marketplace(nome: str) -> None:
    nome_limpo = str(nome or "").strip()
    if not nome_limpo:
        raise ValueError("Informe o nome do marketplace.")
    if len(nome_limpo) > 80:
        raise ValueError("O nome do marketplace deve ter até 80 caracteres.")
    with _banco() as conexao:
        exigir_esquema(conexao)
        conexao.execute(
            """
            INSERT INTO MARKETPLACES (NOME, ATIVO, CRIADO_EM)
            VALUES (?, 1, ?)
            ON CONFLICT(NOME) DO UPDATE SET ATIVO = 1
            """,
            (nome_limpo, datetime.now().astimezone().isoformat(timespec="seconds")),
        )


def definir_marketplace_ativo(marketplace_id: int, ativo: bool) -> None:
    with _banco() as conexao:
        exigir_esquema(conexao)
        cursor = conexao.execute(
            "UPDATE MARKETPLACES SET ATIVO = ? WHERE ID = ?",
            (1 if ativo else 0, int(marketplace_id)),
        )
        if cursor.rowcount != 1:
            raise ValueError("Marketplace não encontrado.")


def _colunas_entrada(conexao: sqlite3.Connection) -> set[str]:
    return {
        str(row[1])
        for row in conexao.execute("PRAGMA table_info(A_ENTRADA)")
    }


def buscar_dados_produto(produto: str) -> tuple | None:
    nome = str(produto or "").strip()
    if not nome or not Path(DB_PATH).is_file():
        return None
    with _banco() as conexao:
        if esquema_instalado(conexao):
            row = conexao.execute(
                """
                SELECT PRODUTO, REFERENCIA, DIRETORIO, DESCRITION,
                       SERVENTIA, ACOMPANHA, ACABAMENTO, KIT, OBS,
                       REGRAS_ANUNCIO, PROPORCAO
                FROM PRODUTOS_ATIVOS
                WHERE PRODUTO = ? COLLATE NOCASE
                """,
                (nome,),
            ).fetchone()
            if row:
                return tuple(row)
        colunas = _colunas_entrada(conexao)
        campos = [
            campo if campo in colunas else f'NULL AS "{campo}"'
            for campo in _CAMPOS_PRODUTO
        ]
        row = conexao.execute(
            f"""
            SELECT {", ".join(campos)}
            FROM A_ENTRADA
            WHERE PRODUTO = ? COLLATE NOCASE
            """,
            (nome,),
        ).fetchone()
        return tuple(row) if row else None


def listar_produtos_permanentes() -> list[tuple]:
    """Lista somente produtos concluídos para as telas do Marketplace."""
    if not Path(DB_PATH).is_file():
        return []
    with _banco() as conexao:
        if not esquema_instalado(conexao):
            raise RuntimeError(
                "As telas do Marketplace mostram apenas produtos concluídos. "
                "Atualize o banco em Configuração > Banco de dados."
            )
        rows = conexao.execute(
            """
            SELECT PRODUTO, REFERENCIA, DIRETORIO, DESCRITION,
                   SERVENTIA, ACOMPANHA, ACABAMENTO, KIT, OBS,
                   REGRAS_ANUNCIO, PROPORCAO
            FROM PRODUTOS_ATIVOS
            ORDER BY rowid DESC
            """
        ).fetchall()
    return [
        tuple(row[campo] for campo in _CAMPOS_PRODUTO)
        for row in rows
        if str(row["PRODUTO"] or "").strip()
    ]


def listar_produtos_pendentes() -> list[tuple]:
    """Lista os produtos de A_ENTRADA usados pelo fluxo da área Cadastro."""
    if not Path(DB_PATH).is_file():
        raise FileNotFoundError(f"O banco existente não foi encontrado: {DB_PATH}")
    with _banco() as conexao:
        if "A_ENTRADA" not in _tabelas(conexao):
            raise RuntimeError("A tabela A_ENTRADA não existe no banco atual.")
        colunas = _colunas_entrada(conexao)
        obrigatorias = {
            "PRODUTO",
            "REFERENCIA",
            "DIRETORIO",
            "DESCRITION",
            "SERVENTIA",
            "ACOMPANHA",
            "ACABAMENTO",
        }
        ausentes = obrigatorias - colunas
        if ausentes:
            nomes = ", ".join(sorted(ausentes))
            raise RuntimeError(
                f"A_ENTRADA não contém os campos necessários: {nomes}"
            )
        campos = [
            f'"{campo}"' if campo in colunas else f'NULL AS "{campo}"'
            for campo in _CAMPOS_PRODUTO
        ]
        rows = conexao.execute(
            f"""
            SELECT {", ".join(campos)}
            FROM A_ENTRADA
            ORDER BY rowid DESC
            """
        ).fetchall()
    return [
        tuple(row)
        for row in rows
        if str(row[0] or "").strip()
    ]


def listar_produtos_para_midias_avulsas() -> list[tuple]:
    """Lista produtos pendentes e permanentes para a ferramenta de Cadastro."""
    pendentes = listar_produtos_pendentes()
    with _banco() as conexao:
        tem_esquema_permanente = esquema_instalado(conexao)
    permanentes = (
        listar_produtos_permanentes()
        if tem_esquema_permanente
        else []
    )

    resultado: list[tuple] = []
    vistos: set[str] = set()
    for row in [*permanentes, *pendentes]:
        nome = str(row[0] or "").strip()
        chave = nome.casefold()
        if not nome or chave in vistos:
            continue
        vistos.add(chave)
        resultado.append(row)
    return resultado


def contar_produtos_pendentes() -> int:
    if not Path(DB_PATH).is_file():
        return 0
    with _banco() as conexao:
        if "A_ENTRADA" not in _tabelas(conexao):
            return 0
        row = conexao.execute("SELECT COUNT(*) FROM A_ENTRADA").fetchone()
        return int(row[0] or 0)


def listar_precos_anuncio(
    produto: str,
    marketplace: str | None = None,
    *,
    conexao: sqlite3.Connection | None = None,
) -> dict[str, dict[str, float]]:
    propria = conexao is None
    db = conexao or _conectar()
    try:
        if not esquema_instalado(db):
            return {}
        params: list[object] = [str(produto or "").strip()]
        filtro = ""
        if marketplace:
            filtro = "AND mp.NOME = ? COLLATE NOCASE"
            params.append(str(marketplace).strip())
        rows = db.execute(
            f"""
            SELECT ai.ID_PRODUCAO, mp.NOME, ai.PRECO
            FROM ANUNCIOS AS a
            JOIN MARKETPLACES AS mp ON mp.ID = a.MARKETPLACE_ID
            JOIN ANUNCIO_IDS AS ai ON ai.ANUNCIO_ID = a.ID
            WHERE a.PRODUTO = ? COLLATE NOCASE
              AND a.ATIVO = 1
              AND mp.ATIVO = 1
              {filtro}
            """,
            params,
        ).fetchall()
        resultado: dict[str, dict[str, float]] = {}
        for row in rows:
            resultado.setdefault(str(row["ID_PRODUCAO"]), {})[
                str(row["NOME"])
            ] = float(row["PRECO"] or 0)
        return resultado
    finally:
        if propria:
            db.close()


def salvar_ofertas_marketplace(
    conexao: sqlite3.Connection,
    produto: str,
    titulo: str,
    descricao: str,
    itens: list[dict[str, Any]],
) -> None:
    """Persiste preços por ID/canal; o estoque físico fica em MARKET_PLACE."""
    if not esquema_instalado(conexao):
        return
    agora = datetime.now().astimezone().isoformat(timespec="seconds")
    for item in itens:
        item_id = str(item.get("id") or "").strip()
        ofertas = item.get("offers") or []
        for oferta in ofertas:
            nome_marketplace = str(oferta.get("marketplace") or "").strip()
            if not nome_marketplace:
                continue
            marketplace = conexao.execute(
                """
                SELECT ID FROM MARKETPLACES
                WHERE NOME = ? COLLATE NOCASE AND ATIVO = 1
                """,
                (nome_marketplace,),
            ).fetchone()
            if not marketplace:
                raise ValueError(
                    f"O marketplace “{nome_marketplace}” está inativo ou "
                    "não foi cadastrado."
                )
            conexao.execute(
                """
                INSERT INTO ANUNCIOS
                    (PRODUTO, MARKETPLACE_ID, TITULO, DESCRITION, ATIVO,
                     CRIADO_EM, ATUALIZADO_EM)
                VALUES (?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(PRODUTO, MARKETPLACE_ID) DO UPDATE SET
                    TITULO = CASE WHEN excluded.TITULO = ''
                                  THEN ANUNCIOS.TITULO ELSE excluded.TITULO END,
                    DESCRITION = CASE WHEN excluded.DESCRITION = ''
                                      THEN ANUNCIOS.DESCRITION
                                      ELSE excluded.DESCRITION END,
                    ATIVO = 1,
                    ATUALIZADO_EM = excluded.ATUALIZADO_EM
                """,
                (
                    produto,
                    int(marketplace["ID"]),
                    titulo,
                    descricao,
                    agora,
                    agora,
                ),
            )
            anuncio = conexao.execute(
                """
                SELECT ID FROM ANUNCIOS
                WHERE PRODUTO = ? COLLATE NOCASE AND MARKETPLACE_ID = ?
                """,
                (produto, int(marketplace["ID"])),
            ).fetchone()
            conexao.execute(
                """
                INSERT INTO ANUNCIO_IDS (ANUNCIO_ID, ID_PRODUCAO, PRECO)
                VALUES (?, ?, ?)
                ON CONFLICT(ANUNCIO_ID, ID_PRODUCAO) DO UPDATE SET
                    PRECO = excluded.PRECO
                """,
                (
                    int(anuncio["ID"]),
                    item_id,
                    float(oferta.get("sale_price") or 0),
                ),
            )


def salvar_textos_marketplace(
    conexao: sqlite3.Connection,
    produto: str,
    titulo: str,
    descricao: str,
    marketplace: str | None = None,
) -> int:
    if not esquema_instalado(conexao):
        return 0
    params: list[object] = [titulo, descricao,
                            datetime.now().astimezone().isoformat(timespec="seconds"),
                            produto]
    if marketplace:
        filtro_marketplace = """
          AND MARKETPLACE_ID IN (
              SELECT ID FROM MARKETPLACES
              WHERE NOME = ? COLLATE NOCASE AND ATIVO = 1
          )
        """
        params.append(marketplace)
    else:
        filtro_marketplace = """
          AND MARKETPLACE_ID IN (
              SELECT ID FROM MARKETPLACES WHERE ATIVO = 1
          )
        """
    cursor = conexao.execute(
        f"""
        UPDATE ANUNCIOS
        SET TITULO = ?, DESCRITION = ?, ATUALIZADO_EM = ?
        WHERE PRODUTO = ? COLLATE NOCASE
          AND ATIVO = 1
          {filtro_marketplace}
        """,
        params,
    )
    return int(cursor.rowcount)


def listar_textos_marketplace(
    produto: str,
    *,
    conexao: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    propria = conexao is None
    db = conexao or _conectar()
    try:
        if not esquema_instalado(db):
            return []
        rows = db.execute(
            """
            SELECT a.ID, mp.NOME AS MARKETPLACE, a.TITULO, a.DESCRITION,
                   a.ATIVO
            FROM ANUNCIOS AS a
            JOIN MARKETPLACES AS mp ON mp.ID = a.MARKETPLACE_ID
            WHERE a.PRODUTO = ? COLLATE NOCASE
            ORDER BY mp.NOME COLLATE NOCASE
            """,
            (str(produto or "").strip(),),
        ).fetchall()
        return [
            {
                "id": int(row["ID"]),
                "marketplace": str(row["MARKETPLACE"]),
                "title": str(row["TITULO"] or ""),
                "description": str(row["DESCRITION"] or ""),
                "active": bool(row["ATIVO"]),
            }
            for row in rows
        ]
    finally:
        if propria:
            db.close()


def obter_texto_marketplace(
    produto: str,
    marketplace: str,
    *,
    conexao: sqlite3.Connection | None = None,
) -> dict[str, Any] | None:
    propria = conexao is None
    db = conexao or _conectar()
    try:
        if not esquema_instalado(db):
            return None
        row = db.execute(
            """
            SELECT a.ID, a.TITULO, a.DESCRITION
            FROM ANUNCIOS AS a
            JOIN MARKETPLACES AS mp ON mp.ID = a.MARKETPLACE_ID
            WHERE a.PRODUTO = ? COLLATE NOCASE
              AND mp.NOME = ? COLLATE NOCASE
              AND a.ATIVO = 1
            """,
            (produto, marketplace),
        ).fetchone()
        if not row:
            return None
        return {
            "id": int(row["ID"]),
            "title": str(row["TITULO"] or ""),
            "description": str(row["DESCRITION"] or ""),
        }
    finally:
        if propria:
            db.close()


def salvar_preco_anuncio(
    produto: str,
    marketplace: str,
    item_id: str,
    preco: float,
) -> None:
    valor = float(preco)
    if valor <= 0:
        raise ValueError("O preço do anúncio deve ser maior que zero.")
    with _banco() as conexao:
        exigir_esquema(conexao)
        cursor = conexao.execute(
            """
            UPDATE ANUNCIO_IDS
            SET PRECO = ?
            WHERE ID_PRODUCAO = ?
              AND ANUNCIO_ID IN (
                  SELECT a.ID
                  FROM ANUNCIOS AS a
                  JOIN MARKETPLACES AS mp ON mp.ID = a.MARKETPLACE_ID
                  WHERE a.PRODUTO = ? COLLATE NOCASE
                    AND mp.NOME = ? COLLATE NOCASE
                    AND a.ATIVO = 1
              )
            """,
            (valor, item_id, produto, marketplace),
        )
        if cursor.rowcount != 1:
            raise ValueError(
                f"Não há preço salvo para o ID {item_id} em {marketplace}."
            )


def obter_preco_para_venda(
    conexao: sqlite3.Connection,
    produto: str,
    item_id: str,
    marketplace: str,
) -> float | None:
    if not esquema_instalado(conexao):
        return None
    row = conexao.execute(
        """
        SELECT ai.PRECO
        FROM ANUNCIOS AS a
        JOIN MARKETPLACES AS mp ON mp.ID = a.MARKETPLACE_ID
        JOIN ANUNCIO_IDS AS ai ON ai.ANUNCIO_ID = a.ID
        WHERE a.PRODUTO = ? COLLATE NOCASE
          AND ai.ID_PRODUCAO = ?
          AND mp.NOME = ? COLLATE NOCASE
          AND a.ATIVO = 1
          AND mp.ATIVO = 1
        LIMIT 1
        """,
        (produto, item_id, marketplace),
    ).fetchone()
    return float(row[0]) if row else None


def concluir_produto_pendente(produto: str) -> None:
    """Copia fatos permanentes e remove a fila somente ao final da transação."""
    nome = str(produto or "").strip()
    if not nome:
        raise ValueError("Produto inválido.")
    with _banco() as conexao:
        exigir_esquema(conexao)
        conexao.execute("PRAGMA foreign_keys = ON")
        conexao.execute("BEGIN IMMEDIATE")
        colunas = _colunas_entrada(conexao)
        campos = [
            campo if campo in colunas else f'NULL AS "{campo}"'
            for campo in _CAMPOS_PRODUTO
        ]
        entrada = conexao.execute(
            f"""
            SELECT {", ".join(campos)}
            FROM A_ENTRADA
            WHERE PRODUTO = ? COLLATE NOCASE
            """,
            (nome,),
        ).fetchone()
        if not entrada:
            raise ValueError("O produto não está mais na fila pendente.")

        produto_key = nome.casefold()
        ids: set[str] = set()
        for tabela in ("VENDAS", "MARKET_PLACE"):
            registros_ids = conexao.execute(
                f"""
                SELECT ID, NOME_PRODUTO
                FROM "{tabela}"
                WHERE ID IS NOT NULL AND TRIM(ID) <> ''
                """
            ).fetchall()
            ids.update(
                str(row["ID"]).strip()
                for row in registros_ids
                if str(row["NOME_PRODUTO"] or "").strip().casefold()
                == produto_key
            )
        if not ids:
            raise ValueError(
                "O produto ainda não tem IDs em VENDAS nem em MARKET_PLACE."
            )
        ids_sem_anuncio = []
        for item_id in sorted(ids):
            ligado = conexao.execute(
                """
                SELECT 1
                FROM ANUNCIOS AS a
                JOIN ANUNCIO_IDS AS ai ON ai.ANUNCIO_ID = a.ID
                JOIN MARKETPLACES AS mp ON mp.ID = a.MARKETPLACE_ID
                WHERE a.PRODUTO = ? COLLATE NOCASE
                  AND ai.ID_PRODUCAO = ?
                  AND a.ATIVO = 1 AND mp.ATIVO = 1
                LIMIT 1
                """,
                (nome, item_id),
            ).fetchone()
            if not ligado:
                ids_sem_anuncio.append(item_id)
        if ids_sem_anuncio:
            raise ValueError(
                "Configure preço e marketplace para todos os IDs antes de "
                "concluir: " + ", ".join(ids_sem_anuncio)
            )

        agora = datetime.now().astimezone().isoformat(timespec="seconds")
        campos_gravados = [campo for campo in _CAMPOS_PRODUTO if campo != "PRODUTO"]
        colunas_sql = ", ".join(["PRODUTO", *campos_gravados, "CONCLUIDO_EM"])
        placeholders = ", ".join("?" for _ in range(len(_CAMPOS_PRODUTO) + 1))
        atualizacoes = ", ".join(
            f"{campo} = excluded.{campo}" for campo in campos_gravados
        ) + ", CONCLUIDO_EM = excluded.CONCLUIDO_EM"
        valores = [entrada[campo] for campo in _CAMPOS_PRODUTO] + [agora]
        conexao.execute(
            f"""
            INSERT INTO PRODUTOS_ATIVOS ({colunas_sql})
            VALUES ({placeholders})
            ON CONFLICT(PRODUTO) DO UPDATE SET {atualizacoes}
            """,
            valores,
        )
        salvo = conexao.execute(
            """
            SELECT 1 FROM PRODUTOS_ATIVOS
            WHERE PRODUTO = ? COLLATE NOCASE
            """,
            (nome,),
        ).fetchone()
        if not salvo:
            raise RuntimeError("A cópia permanente do produto não foi confirmada.")
        cursor = conexao.execute(
            "DELETE FROM A_ENTRADA WHERE PRODUTO = ? COLLATE NOCASE",
            (nome,),
        )
        if cursor.rowcount != 1:
            raise RuntimeError(
                "A entrada pendente mudou durante a conclusão. "
                "A transação foi cancelada."
            )
