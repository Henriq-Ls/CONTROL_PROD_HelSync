"""Catalogo dos campos que as ferramentas podem ler no Cadastro."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


CAMPOS_EDITAVEIS_IA: frozenset[str] = frozenset(
    {"nome", "descricao", "serventia"}
)

# Estes campos ajudam a IA a fazer recomendações, mas a escolha continua sendo
# manual no Cadastro.
CAMPOS_SUGESTAO_IA: frozenset[str] = frozenset(
    {
        "tipo",
        "variacoes",
        "acabamento",
        "tambem_em_kit",
        "pecas_no_kit",
        "variacao_do_kit",
        "quantidade_de_kits",
    }
)

CAMPOS_CONTEXTO_IA: frozenset[str] = (
    CAMPOS_EDITAVEIS_IA | CAMPOS_SUGESTAO_IA
)

_CHAVES_NAO_ENVIAR_IA = frozenset(
    {
        "origem",
        "origem_midias",
        "source_dir",
        "source_path",
        "destino",
        "diretorio",
        "diretorio_base",
        "products_dir",
        "destination_path",
        "proporcao",
        "arquivo_txt_origem",
    }
)


def sanitizar_snapshot_para_ia(valor: Any) -> Any:
    """Remove caminhos e opções locais do snapshot antes do envio ao modelo."""
    if isinstance(valor, Mapping):
        return {
            chave: sanitizar_snapshot_para_ia(conteudo)
            for chave, conteudo in valor.items()
            if str(chave).strip().casefold() not in _CHAVES_NAO_ENVIAR_IA
        }
    if isinstance(valor, (list, tuple)):
        return [sanitizar_snapshot_para_ia(item) for item in valor]
    return valor


@dataclass(frozen=True)
class CampoCadastro:
    """Contrato de um campo visivel ou relacionado ao formulario."""

    id: str
    rotulo: str
    finalidade: str
    tipo: str
    editavel: bool
    chave_snapshot: str
    widget: str | None = None
    obrigatorio: bool = False
    opcoes: tuple[str, ...] = ()

    def como_dict(self, valor: Any = "") -> dict[str, Any]:
        dados = asdict(self)
        dados["opcoes"] = list(self.opcoes)
        dados["valor_atual"] = valor
        dados["acao_ia"] = (
            "preencher"
            if self.id in CAMPOS_EDITAVEIS_IA
            else "sugerir"
            if self.id in CAMPOS_SUGESTAO_IA
            else "somente_leitura"
        )
        return dados


CAMPOS_CADASTRO: tuple[CampoCadastro, ...] = (
    CampoCadastro(
        "nome",
        "Nome",
        "Nome usado para identificar o produto no cadastro.",
        "texto",
        True,
        "nome",
        "product_name",
        obrigatorio=True,
    ),
    CampoCadastro(
        "origem",
        "Origem",
        "Pasta que contém as imagens e os vídeos originais.",
        "caminho",
        True,
        "origem_midias",
        "source_dir",
    ),
    CampoCadastro(
        "destino",
        "Destino",
        "Pasta onde será criada a pasta final do produto.",
        "caminho",
        True,
        "diretorio_base",
        "products_dir",
    ),
    CampoCadastro(
        "descricao",
        "Descrição",
        "Descrição comercial e informativa do produto.",
        "texto_longo",
        True,
        "descricao",
        "description",
    ),
    CampoCadastro(
        "serventia",
        "Como pode ser usado",
        "Uso, aplicação ou finalidade prática do produto.",
        "texto_longo",
        True,
        "serventia",
        "usage",
    ),
    CampoCadastro(
        "acompanha",
        "Acompanha",
        "Itens que acompanham o produto.",
        "texto",
        False,
        "acompanha",
        "accompanies",
    ),
    CampoCadastro(
        "acabamento",
        "Acabamento",
        "Acabamentos ou trabalhos possíveis para o produto. A IA apenas sugere.",
        "multiseleção",
        False,
        "acabamento",
        "finish",
    ),
    CampoCadastro(
        "proporcao",
        "Proporção",
        "Proporção usada no processamento das imagens.",
        "opcao",
        False,
        "proporcao",
        "proportion",
        opcoes=("3:4", "1:1", "4:5", "9:16", "16:9"),
    ),
    CampoCadastro(
        "tipo",
        "Tipo",
        "Define se o cadastro é de produto único ou kit. A IA apenas sugere.",
        "opcao",
        False,
        "tipo",
        "product_type",
        opcoes=("Único", "Kit"),
    ),
    CampoCadastro(
        "variacoes",
        "Variações",
        "Quantidade de variações do produto. A IA apenas sugere.",
        "opcao",
        False,
        "variacoes",
        "variations",
        opcoes=tuple(str(numero) for numero in range(1, 10)),
    ),
    CampoCadastro(
        "tambem_em_kit",
        "Também em kit",
        "Indica se o produto único também será vendido em kit. A IA apenas sugere.",
        "opcao",
        False,
        "tambem_em_kit",
        "also_kit",
        opcoes=("Não", "Sim"),
    ),
    CampoCadastro(
        "pecas_no_kit",
        "Peças no kit",
        "Quantidade de peças diferentes que compõem o kit. A IA apenas sugere.",
        "opcao",
        False,
        "pecas_no_kit",
        "kit_pieces",
        opcoes=tuple(str(numero) for numero in range(2, 11)),
    ),
    CampoCadastro(
        "variacao_do_kit",
        "Variação do kit",
        "Variação usada para organizar as imagens do kit. A IA apenas sugere.",
        "opcao",
        False,
        "variacao_do_kit",
        "kit_variation",
    ),
    CampoCadastro(
        "quantidade_de_kits",
        "Quantidade de kits",
        "Quantidade de kits configurada no cadastro. A IA apenas sugere.",
        "opcao",
        False,
        "quantidade_de_kits",
        "kit_count",
        opcoes=tuple(str(numero) for numero in range(1, 11)),
    ),
    CampoCadastro(
        "arquivos",
        "Mídias",
        "Imagens e vídeos selecionados para o produto.",
        "lista",
        False,
        "arquivos",
    ),
    CampoCadastro(
        "medidas",
        "Medidas",
        "Medidas e pesos associados aos grupos de mídias.",
        "lista",
        False,
        "medidas",
    ),
)


def campo_por_id(campo_id: str) -> CampoCadastro | None:
    alvo = str(campo_id or "").strip()
    return next((campo for campo in CAMPOS_CADASTRO if campo.id == alvo), None)


def campos_com_valores(snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        campo.como_dict(snapshot.get(campo.chave_snapshot, ""))
        for campo in CAMPOS_CADASTRO
    ]


def snapshot_para_ia(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Retorna os fatos do Cadastro que são necessários à conversa.

    A IA precisa conhecer os dados para conversar com precisão. Conhecer um
    campo não concede permissão para alterá-lo: a permissão de escrita continua
    limitada por ``CAMPOS_EDITAVEIS_IA`` e pelo executor de propostas. Caminhos
    locais e a proporção de processamento não são enviados ao provedor.
    """
    resultado: dict[str, Any] = {}
    for campo in CAMPOS_CADASTRO:
        resultado[campo.chave_snapshot] = snapshot.get(
            campo.chave_snapshot,
            "",
        )
    for chave in (
        "produto_id",
        "memoria_id",
        "memoria_tipo",
        "id_origem",
        "nome_legado",
        "referencia",
        "registro_banco",
        "salvo_no_banco",
        "arquivo_txt_origem",
        "texto_txt_origem",
        "quantidade_arquivos",
    ):
        if chave in snapshot:
            resultado[chave] = snapshot[chave]
    return sanitizar_snapshot_para_ia(resultado)