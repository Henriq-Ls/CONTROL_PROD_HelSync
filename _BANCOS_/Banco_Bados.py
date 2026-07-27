# 📁 _BANCOS_/Banco_Bados.py

from contextlib import contextmanager
import os
import sqlite3

from _GERENTE_PROJETO_.a__Gerente import Pasta_Raiz
BASE_DIR = Pasta_Raiz()
DB_FOLDER = os.path.join(BASE_DIR, "_BANCOS_")
DB_PATH = os.path.join(DB_FOLDER, "Base_Dados.db")

def get_conn():
    """Cria e retorna uma conexão com o banco SQLite."""
    os.makedirs(DB_FOLDER, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")

    return conn

# ⚠️  função grande (52 linhas)
def init_Banco_dados_db():
    """Cria todas as tabelas do banco caso não existam."""
    conn = get_conn()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS A_ENTRADA(
            PRODUTO     TEXT PRIMARY KEY NOT NULL,
            REFERENCIA  TEXT,
            DIRETORIO   TEXT,
            DESCRITION  TEXT,
            SERVENTIA   TEXT,
            ACOMPANHA   TEXT,
            ACABAMENTO  TEXT,
            KIT         TEXT,
            OBS         TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS VENDAS(
            ID                  TEXT NOT NULL,
            DATA                TEXT,
            NOME_PRODUTO        TEXT,
            KIT                 TEXT,
            PLATAFORMAS_POSTADO TEXT,
            PLATAFORMA_VENDA    TEXT,
            CLIENTE_NOME        TEXT,
            CLIENTE_CPF         TEXT,
            CLIENTE_TELEFONE    TEXT,
            ENDERECO            TEXT,
            VALOR_VENDA         REAL,
            CUSTO_PRODUTO       REAL,
            TAXA_PLATAFORMA     REAL,
            LUCRO               REAL,
            QUANTIDADE          INTEGER,
            OBSERVACOES         TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS MARKET_PLACE(
            ID                  TEXT NOT NULL,
            IMAGEM              TEXT,
            DATA                TEXT,
            NOME_PRODUTO        TEXT,
            KIT                 TEXT,
            PLATAFORMAS_POSTADO TEXT,
            PLATAFORMA_VENDA    TEXT,
            CLIENTE_NOME        TEXT,
            CLIENTE_CPF         TEXT,
            CLIENTE_TELEFONE    TEXT,
            ENDERECO            TEXT,
            VALOR_VENDA         REAL,
            CUSTO_PRODUTO       REAL,
            TAXA_PLATAFORMA     REAL,
            LUCRO               REAL,
            QUANTIDADE          INTEGER,
            TITULO              TEXT,
            DESCRITION          TEXT)''')
    conn.close()
# ══════════════════════════════════════════════════════
# MARKET_PLACE
# ══════════════════════════════════════════════════════

def esc_MARKET_PLACE(ID, IMAGEM, DATA, NOME_PRODUTO, KIT, PLATAFORMAS_POSTADO, VALOR_VENDA, CUSTO_PRODUTO, QUANTIDADE, TITULO, DESCRITION):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO MARKET_PLACE
        (ID,IMAGEM,DATA,NOME_PRODUTO,KIT,PLATAFORMAS_POSTADO,
         VALOR_VENDA,CUSTO_PRODUTO,TAXA_PLATAFORMA,QUANTIDADE,TITULO,DESCRITION)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
        (str(ID), str(IMAGEM), str(DATA), str(NOME_PRODUTO), str(KIT),
         str(PLATAFORMAS_POSTADO), float(VALOR_VENDA), float(CUSTO_PRODUTO),
         0.0, int(QUANTIDADE), str(TITULO), str(DESCRITION)))
    conn.commit()
    conn.close()


def ler_MARKET_PLACE():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM MARKET_PLACE")
    rows = c.fetchall()
    conn.close()
    return rows


def ler_MARKET_PLACE_prod(prod):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM MARKET_PLACE WHERE LOWER(NOME_PRODUTO) LIKE LOWER(?)",
              (f"%{prod.strip()}%",))
    rows = c.fetchall()
    conn.close()
    return rows


def ler_MARKET_PLACE_id(ID):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM MARKET_PLACE WHERE ID = ?", (ID,))
    rows = c.fetchall()
    conn.close()
    return rows


def ATUAL_MARKET_PLACE(ID, COLUNA, CONTEUDO, SOMAR=False):
    conn = get_conn()
    c = conn.cursor()
    if SOMAR:
        c.execute(f"SELECT {COLUNA} FROM MARKET_PLACE WHERE ID = ?", (ID,))
        atual = c.fetchone()
        CONTEUDO = str(atual[0] or '') + str(CONTEUDO)
    c.execute(f"UPDATE MARKET_PLACE SET {COLUNA} = ? WHERE ID = ?", (CONTEUDO, ID))
    conn.commit()
    conn.close()


def del_MARKET_PLACE(ID=''):
    conn = get_conn()
    c = conn.cursor()
    if ID:
        c.execute("DELETE FROM MARKET_PLACE WHERE ID = ?", (ID,))
    else:
        c.execute("DELETE FROM MARKET_PLACE")
    conn.commit()
    conn.close()


def listar_produtos_disponiveis():
    """Retorna produtos com estoque disponível (sem comprador)."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("""SELECT ID, NOME_PRODUTO, IMAGEM, KIT, VALOR_VENDA,
                        CUSTO_PRODUTO, PLATAFORMAS_POSTADO, COUNT(*) as ESTOQUE
                 FROM MARKET_PLACE
                 WHERE CLIENTE_NOME IS NULL OR CLIENTE_NOME = ''
                 GROUP BY ID, NOME_PRODUTO
                 ORDER BY NOME_PRODUTO""")
    rows = c.fetchall()
    conn.close()
    return rows


def contar_estoque(ID):
    """Conta unidades disponíveis de um produto."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM MARKET_PLACE WHERE ID = ? AND (CLIENTE_NOME IS NULL OR CLIENTE_NOME = '')", (ID,))
    total = c.fetchone()[0]
    conn.close()
    return total


def registrar_compra(ID, qt, CLIENTE_NOME, CLIENTE_CPF, CLIENTE_TELEFONE, ENDERECO, PLATAFORMA_VENDA, TAXA_PLATAFORMA):
    """Registra compra nas linhas disponíveis do produto."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT rowid FROM MARKET_PLACE WHERE ID = ? AND (CLIENTE_NOME IS NULL OR CLIENTE_NOME = '') LIMIT ?", (ID, qt))
    rows = c.fetchall()

    for row in rows:
        c.execute("""UPDATE MARKET_PLACE SET
            CLIENTE_NOME=?, CLIENTE_CPF=?, CLIENTE_TELEFONE=?,
            ENDERECO=?, PLATAFORMA_VENDA=?, TAXA_PLATAFORMA=?,
            LUCRO = VALOR_VENDA - CUSTO_PRODUTO - ?
            WHERE rowid=?""",
            (CLIENTE_NOME, CLIENTE_CPF, CLIENTE_TELEFONE,
             ENDERECO, PLATAFORMA_VENDA, float(TAXA_PLATAFORMA),
             float(TAXA_PLATAFORMA), row[0]))
    conn.commit()
    conn.close()
    return len(rows)


# ══════════════════════════════════════════════════════
# A_ENTRADA
# ══════════════════════════════════════════════════════

def esc_A_ENTRADA(PRODUTO, REFERENCIA, DIRETORIO, DESCRITION, SERVENTIA, ACOMPANHA, ACABAMENTO, KIT):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO A_ENTRADA
        (PRODUTO,REFERENCIA,DIRETORIO,DESCRITION,SERVENTIA,ACOMPANHA,ACABAMENTO,KIT)
        VALUES (?,?,?,?,?,?,?,?)''',
        (str(PRODUTO), str(REFERENCIA), str(DIRETORIO), str(DESCRITION),
         str(SERVENTIA), str(ACOMPANHA), str(ACABAMENTO), str(KIT)))
    conn.commit()
    conn.close()


def ler_A_ENTRADA():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM A_ENTRADA")
    rows = c.fetchall()
    conn.close()
    return rows


def Del_A_ENTRADA(ID=''):
    conn = get_conn()
    c = conn.cursor()
    if ID:
        c.execute("DELETE FROM A_ENTRADA WHERE PRODUTO = ?", (ID,))
    else:
        c.execute("DELETE FROM A_ENTRADA")
    conn.commit()
    conn.close()


# ══════════════════════════════════════════════════════
# VENDAS
# ══════════════════════════════════════════════════════

def esc_VENDAS(ID, DATA, NOME_PRODUTO, KIT, OBSERVACOES):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO VENDAS
        (ID,DATA,NOME_PRODUTO,KIT,OBSERVACOES)
        VALUES (?,?,?,?,?)''',
        (str(ID), str(DATA), str(NOME_PRODUTO), str(KIT), str(OBSERVACOES)))
    conn.commit()
    conn.close()


def ler_VENDAS():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM VENDAS")
    rows = c.fetchall()
    conn.close()
    return rows


def ler_VENDAS_prod(prod):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM VENDAS WHERE NOME_PRODUTO = ?", (prod,))
    rows = c.fetchall()
    conn.close()
    return rows


def ATUAL_VENDAS(ID, COLUNA, CONTEUDO, SOMAR=False):
    conn = get_conn()
    c = conn.cursor()
    if SOMAR:
        c.execute(f"SELECT {COLUNA} FROM VENDAS WHERE ID = ?", (ID,))
        atual = c.fetchone()
        CONTEUDO = str(atual[0] or '') + str(CONTEUDO)
    c.execute(f"UPDATE VENDAS SET {COLUNA} = ? WHERE ID = ?", (CONTEUDO, ID))
    conn.commit()
    conn.close()


def del_VENDAS(ID=''):
    conn = get_conn()
    c = conn.cursor()
    if ID:
        c.execute("DELETE FROM VENDAS WHERE ID = ?", (ID,))
    else:
        c.execute("DELETE FROM VENDAS")
    conn.commit()
    conn.close()


def ler_VENDAS_IMPRIMI(prod):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT ID,DATA, NOME_PRODUTO,VALOR_VENDA FROM VENDAS WHERE NOME_PRODUTO = ?", (prod,))
    rows = c.fetchall()
    conn.close()
    return rows


init_Banco_dados_db()

