"""Catalogo que informa à IA quais ferramentas existem."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class DefinicaoFerramenta:
    nome: str
    descricao: str
    modo: str
    requer_confirmacao: bool
    parametros: tuple[dict[str, Any], ...]

    def como_dict(self) -> dict[str, Any]:
        dados = asdict(self)
        dados["parametros"] = [dict(item) for item in self.parametros]
        return dados


class CatalogoFerramentas:
    """Registro explícito; não há descoberta arbitrária de métodos."""

    def __init__(self, ferramentas: Iterable[DefinicaoFerramenta] = ()):
        self._ferramentas: dict[str, DefinicaoFerramenta] = {}
        for ferramenta in ferramentas:
            self.registrar(ferramenta)

    def registrar(self, ferramenta: DefinicaoFerramenta) -> None:
        nome = ferramenta.nome.strip()
        if not nome:
            raise ValueError("Uma ferramenta precisa ter nome.")
        if nome in self._ferramentas:
            raise ValueError(f"Ferramenta já registrada: {nome}")
        self._ferramentas[nome] = ferramenta

    def obter(self, nome: str) -> DefinicaoFerramenta | None:
        return self._ferramentas.get(str(nome or "").strip())

    def listar(self) -> list[dict[str, Any]]:
        return [
            ferramenta.como_dict()
            for ferramenta in self._ferramentas.values()
        ]

    def para_ia(self) -> dict[str, Any]:
        return {
            "tipo": "catalogo_de_ferramentas",
            "instrucoes": (
                "Use somente ferramentas listadas. Ferramentas de escrita "
                "retornam proposta e exigem confirmação antes de aplicar."
            ),
            "ferramentas": self.listar(),
        }

    def para_provedor(self) -> list[dict[str, Any]]:
        """Converte o catálogo para o formato de tools OpenAI/Ollama."""
        ferramentas: list[dict[str, Any]] = []
        for ferramenta in self._ferramentas.values():
            # O snapshot completo já é enviado no contexto da conversa. Não
            # ofereça uma ferramenta de leitura para mensagens comuns: isso
            # fazia o modelo parar de conversar e tentar consultar o cadastro
            # em toda solicitação.
            if ferramenta.nome == "ler_formulario_cadastro":
                continue
            propriedades: dict[str, Any] = {}
            obrigatorios: list[str] = []
            for parametro in ferramenta.parametros:
                nome = str(parametro.get("nome") or "").strip()
                if not nome or nome == "snapshot":
                    continue
                tipo = str(parametro.get("tipo") or "texto")
                tipo_json = "string"
                if tipo == "booleano":
                    tipo_json = "boolean"
                elif tipo == "objeto":
                    tipo_json = "object"
                elif tipo == "lista":
                    tipo_json = "array"
                propriedades[nome] = {
                    "type": tipo_json,
                    "description": str(parametro.get("descricao") or ""),
                }
                if parametro.get("obrigatorio"):
                    obrigatorios.append(nome)
            parametros: dict[str, Any] = {
                "type": "object",
                "properties": propriedades,
            }
            if obrigatorios:
                parametros["required"] = obrigatorios
            ferramentas.append(
                {
                    "type": "function",
                    "function": {
                        "name": ferramenta.nome,
                        "description": ferramenta.descricao,
                        "parameters": parametros,
                    },
                }
            )
        return ferramentas


def criar_catalogo_inicial() -> CatalogoFerramentas:
    return CatalogoFerramentas(
        (
            DefinicaoFerramenta(
                nome="ler_formulario_cadastro",
                descricao=(
                    "Lê os campos atuais do Cadastro, suas finalidades, tipos "
                    "e permissões de edição."
                ),
                modo="leitura",
                requer_confirmacao=False,
                parametros=(
                    {
                        "nome": "snapshot",
                        "tipo": "objeto",
                        "obrigatorio": True,
                        "descricao": "Snapshot atual publicado pelo Cadastro.",
                    },
                ),
            ),
            DefinicaoFerramenta(
                nome="editar_input_cadastro",
                descricao=(
                    "Prepara uma proposta de alteração em um campo de texto "
                    "autorizado do Cadastro. A tela pedirá confirmação antes "
                    "de aplicar; esta ferramenta nunca altera o campo sozinha."
                ),
                modo="leitura_e_escrita_controlada",
                requer_confirmacao=True,
                parametros=(
                    {
                        "nome": "campo_id",
                        "tipo": "texto",
                        "obrigatorio": True,
                        "descricao": (
                            "Use somente: nome, descricao ou serventia. "
                            "Campos de seleção são apenas sugestões e não "
                            "podem ser alterados pela IA."
                        ),
                    },
                    {
                        "nome": "novo_valor",
                        "tipo": "texto_ou_lista",
                        "obrigatorio": True,
                        "descricao": "Valor que será proposto para o campo.",
                    },
                    {
                        "nome": "motivo",
                        "tipo": "texto",
                        "obrigatorio": False,
                        "descricao": "Motivo ou origem da sugestão.",
                    },
                ),
            ),
            DefinicaoFerramenta(
                nome="pesquisar_link_produto",
                descricao=(
                    "Consulta uma URL pública de produto e retorna somente "
                    "metadados e texto encontrados na própria página."
                ),
                modo="leitura_externa",
                requer_confirmacao=False,
                parametros=(
                    {
                        "nome": "url",
                        "tipo": "texto",
                        "obrigatorio": True,
                        "descricao": "URL pública http ou https a consultar.",
                    },
                ),
            ),
        )
    )