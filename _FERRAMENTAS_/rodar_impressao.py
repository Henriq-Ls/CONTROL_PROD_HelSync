# rodar_impressao.py
import sys
import json
from Impressora import imprimir_etiquetas_grade_BANCO

dados = json.loads(sys.argv[1])

imprimir_etiquetas_grade_BANCO(
    textos=dados["textos"],
    largura_folha_mm=dados["largura_folha_mm"],
    altura_folha_mm=dados["altura_folha_mm"],
    colunas=dados["colunas"],
    linhas=dados["linhas"],
    margem_folha_mm=dados["margem_folha_mm"],
    espaco_entre_mm=dados["espaco_entre_mm"],
    tamanho_fonte=dados["tamanho_fonte"],
    alinhamento=dados["alinhamento"],
    borda=dados["borda"],
    rotacao = dados.get("rotacao", 0)

)
