FERRAMENTAS DA IA
=================

Esta pasta contém as capacidades operacionais autorizadas para a IA.

PRIMEIRA ENTREGA
----------------

1. ler_formulario_cadastro
   Lê somente o contexto autorizado do Cadastro e devolve:
   - identificador do campo;
   - finalidade;
   - tipo;
   - valor atual;
   - permissão de edição.
   Nome, descrição e serventia são os únicos campos preenchíveis pela IA.
   Campos de seleção podem ser usados para recomendações, mas não são
   alterados. Origem, destino e proporção não são enviados à IA.

2. editar_input_cadastro
   Primeiro cria uma proposta. A tela só é alterada quando a mesma proposta
   for enviada novamente com confirmar=True.

Exemplo conceitual:

    executor.executar(
        "editar_input_cadastro",
        {
            "campo_id": "descricao",
            "novo_valor": "Descrição revisada do produto",
            "motivo": "Organização das informações do cadastro",
        },
    )

    executor.executar(
        "editar_input_cadastro",
        {
            "confirmar": True,
            "proposta": resultado.dados["proposta"],
        },
    )

REGRAS
------

- A IA só conhece ferramentas registradas no catálogo.
- Campos desconhecidos são rejeitados.
- Campos somente leitura não podem ser alterados por esta ferramenta.
- Campos com opções aceitam somente valores válidos.
- Uma alteração sem confirmação explícita não chega ao widget.
- A confirmação final deve ocorrer no pop-up visual do painel; responder
  “sim” no chat apenas abre ou mantém essa confirmação e não aplica sozinho.
- O adaptador não permite acesso arbitrário aos atributos da janela.
- A pesquisa de links é genérica e tenta usar metadados, JSON-LD e texto público.
- Conteúdo técnico de páginas dinâmicas não é apresentado como dado de produto.
- Depois da pesquisa, o painel devolve o resultado à IA para montar a proposta.
- A conversa mostra texto legível; JSON permanece somente na comunicação interna.