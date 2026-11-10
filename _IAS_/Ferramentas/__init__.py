"""Ferramentas operacionais que podem ser chamadas pelo painel da IA.

Esta camada descreve e valida ações. A aplicação continua dona dos widgets,
do banco comercial e dos arquivos oficiais.
"""

from .cadastro_adapter import AdaptadorCadastro
from .catalogo import CatalogoFerramentas, criar_catalogo_inicial
from .edicao_input import EditorInputCadastro, PropostaEdicao
from .executor import ExecutorFerramentas
from .leitura_cadastro import ler_formulario_cadastro
from .pesquisa_link import pesquisar_link_produto
from .resultado import ResultadoFerramenta

__all__ = [
    "AdaptadorCadastro",
    "CatalogoFerramentas",
    "EditorInputCadastro",
    "ExecutorFerramentas",
    "PropostaEdicao",
    "ResultadoFerramenta",
    "criar_catalogo_inicial",
    "ler_formulario_cadastro",
    "pesquisar_link_produto",
]