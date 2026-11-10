HelSync — Plataforma de Automação de E-commerce com IA
Sistema desktop desenvolvido em Python + Streamlit para automatizar o fluxo completo de publicação de produtos artesanais em marketplaces (Shopee, etc.) — desde o tratamento de fotos até a geração do anúncio pronto para publicar.

Sumário
O que é o HelSync
O problema que resolve
Funcionalidades
Fluxo principal
Estrutura do projeto
Módulos e arquivos em detalhe
Stack tecnológica
Tema visual e interface
Sistema de IA integrado
Ferramentas internas de desenvolvimento
Componentes reutilizáveis de UI
Utilitários gerais
Como rodar
Status do projeto
1. O que é o HelSync
HelSync é um sistema desktop local (sem necessidade de servidor externo) que automatiza o fluxo completo de venda de produtos artesanais em plataformas de e-commerce. A interface roda no navegador via Streamlit, mas tudo é processado localmente na máquina do usuário.

O sistema integra:

Processamento de imagens com IA (remoção de fundo, troca de fundo, sobreposição de logo/medidas)
Gestão de produtos com múltiplos tipos de kit
Geração automática de nomenclatura e referências
Publicação automatizada em marketplaces
Controle financeiro e de estoque
Ferramentas internas de qualidade de código (formatação, docstrings via IA)
2. O problema que resolve
Vender produtos artesanais em marketplaces exige um trabalho repetitivo e manual:

Tarefa manual	Como o HelSync resolve
Tirar fotos, editar, tirar fundo	Processamento automático com IA
Redimensionar, adicionar logo e medidas	Sobreposição automática nas imagens
Organizar kits com variações diferentes	Tipos de produto configuráveis
Gerar descrições criativas	Geração com IA (OpenRouter/GPT-4o)
Controlar estoque e financeiro	Módulo financeiro integrado
Publicar em múltiplas plataformas	API Shopee e outras integradas
3. Funcionalidades
Mídia
Remoção de fundo com IA
Troca de fundo das fotos
Redimensionamento automático
Sobreposição de logo, medidas e referência nas imagens
Geração de mosaicos para kits
Edição de vídeo: inserção de logo e música, exportação para marketplace
Produtos
Cadastro com suporte a quatro tipos:
Único — produto com vários modelos/tamanhos
Pares — produtos em dupla (ex: suporte esquerdo/direito)
Kit Diferentes — kits com peças distintas
Kit Iguais — kits com peças repetidas
Geração automática de referência e nomenclatura de arquivos
Controle de estoque e variações
Integrações
API Shopee e outros marketplaces
APIs de sites próprios
IA para geração de descrições e precificação
Financeiro
Controle de vendas
Sugestão de preços respeitando regras de variação (ex: regra 1:4 da Shopee)
4. Fluxo principal
CADASTRO
  └── Registra produto, tipo de kit, pasta de origem das fotos
ORGANIZAR
  └── Renomeia e separa fotos conforme o tipo do produto
PROCESSAR
  └── Tira fundo → coloca fundo → adiciona medidas → aplica logo
PUBLICAR
  └── Gera vídeo → gera descrição com IA → envia para o marketplace

5. Estrutura do projeto
CONTROLE_PRODUTOS_HelSync/
│
├── App_.py                          ← Ponto de entrada principal
├── Functions.py                     ← Funções utilitárias gerais
├── Rascunho.py                      ← Gerador de contexto para IA (CONTEXTO_IA.txt)
├── icon.ico                         ← Ícone da aplicação
│
├── _APP_/
│   ├── Functions_app.py             ← Componentes de UI Streamlit reutilizáveis
│   └── Html_app.py                  ← Sistema de tema visual (CSS injetado)
│
├── _GERENTE_PROJETO_/
│   ├── a__Gerente.py                ← Gerenciador do projeto (estrutura, contagem, saudação)
│   ├── b__FORMATAR_CODIGO.py        ← Formatador de código Python (6 etapas)
│   ├── b__GERAR_DOCSTRINGS.py       ← Gerador de docstrings via IA (Ollama / OpenRouter)
│   ├── c__LISTAR_PROJETO.py         ← Lister detalhado da estrutura do projeto
│   └── Decorar/
│       ├── Cor_Html.py              ← Sistema de cores HTML nomeadas
│       └── Materiais.py             ← Ícones Material Design em português
│
├── _BANCOS_/
│   └── Banco_Bados.py               ← Camada de banco de dados (SQLite)
│
└── _IAS_/
    └── OpenRouter.py                ← Integração com OpenRouter API

6. Módulos e arquivos em detalhe
App_.py — Ponto de entrada
Arquivo principal que inicializa o Streamlit com set_page_config, carrega o tema visual, conecta o banco de dados e chama a função app().

Responsabilidades:

Configura a página (título dinâmico baseado no nome da pasta raiz, layout wide, ícone)
Carrega o tema CSS via Carregamento_Temas(st)
Exibe estrutura do projeto no rodapé expansível
Controla o menu lateral com st.sidebar
Usa botões de duplo clique (Btn_Cliq_Duplo) para abrir/fechar painéis
Exibe saudação por hora do sistema
Functions.py — Utilitários gerais
Funções de propósito geral utilizadas em todo o projeto.

Função	Descrição
Criar_Arquivo_TEXTO(caminho, titulo, conteudo, ext)	Cria um arquivo de texto e retorna o caminho
wrap_text(text, width=80)	Quebra texto em múltiplas linhas preservando quebras originais
gerar_nome_unico(pasta_base, nome_desejado)	Gera nome único na pasta (ex: Projeto, Projeto_2, Projeto_3...)
carregar_imagem_segura(caminho_relativo, titulo)	Carrega e exibe imagem no Streamlit com tratamento completo de erros
Observação técnica: O arquivo configura STARTUPINFO e CREATE_NO_WINDOW para suprimir janelas CMD/PowerShell no Windows ao chamar subprocessos.

Rascunho.py — Gerador de contexto para IA
Script autônomo que percorre toda a estrutura do projeto e gera um único arquivo CONTEXTO_IA.txt com o conteúdo de todos os .py. Usado para enviar o projeto inteiro como contexto para assistentes de IA.

Configurações:

PASTAS_EXCLUIDAS — ignora .venv, __pycache__, .git, .idea
EXTENSOES — por padrão apenas .py
SAIDA — nome do arquivo de saída (CONTEXTO_IA.txt)
_APP_/Functions_app.py — Componentes de UI
Biblioteca interna de componentes Streamlit reutilizáveis.

Função	Descrição
Linha_Sep(Cor, Larg)	Linha horizontal colorida via HTML
Linha_Sep_Text(TEXT, Cor, Larg)	Linha separadora com texto centralizado
limpar_CASH()	Limpa cache_data e cache_resource do Streamlit
Alerta(st, msg)	Exibe caixa de alerta via st.dialog
_LOGS_popover(st, titulo, logs)	Popover com área de logs dinâmica (máx. 50 entradas)
Grade_Widget(lista, qt_col)	Exibe itens em grade de colunas
Btn_Cliq_Duplo(nome_aberto, nome_fechado, key, fechar_outras)	Botão alternável com estado persistente no session_state
controlar_altura(st, chave, ...)	Controla altura dinâmica de componente com botões ▲▼
controlar_altura_horiz(st, chave, ...)	Versão horizontal do controle de altura
Apagar_Arq(st, nome, diretorio)	Diálogo de confirmação para apagar arquivo/pasta
meu_foot(st, ID, TEXTO, widget, tam)	Gera rodapé/painel persistente (container, expander ou button)
Detalhe — Btn_Cliq_Duplo: Funciona como um toggle: clicando uma vez abre (tipo primary), clicando de novo fecha (tipo secondary). Suporta fechar outros botões automaticamente via fechar_outras=[lista_de_keys].

Detalhe — meu_foot: Cria painéis fixos no rodapé da tela. Aceita três modos:

'container' → expander dentro de container
'expander' → expander com altura controlada e autoscroll
'button' → painel que só aparece quando o botão está ativo
_APP_/Html_app.py — Sistema de Tema Visual
Aplica um tema visual completo e personalizado na interface Streamlit via CSS injetado. Usa st.markdown com unsafe_allow_html.

Paleta de cores padrão:

Variável	Cor	Uso
COR_WIDGET	preto_fosco (#1E1E1E)	Widgets, inputs, containers
COR_CAMPO	branco (#FFFFFF)	Campos de entrada
COR_MENU	laranja_fosco (#C68642)	Botões, logo, destaques
THEMA_APP1	preto_fosco (#0F0F0F)	Fundo principal
COR_TEXTO	verde_fosco (#22C576)	Texto principal
BG_STYLE	preto	Fundo geral absoluto
SD_STYLE	cinza_fosco (#181818)	Sidebar
WD_STYLE	azul_escuro (#1A1A1A)	Fundo interno widgets
Tipografia:

FONTE_MENU → JetBrains Mono (interface premium)
FONTE_CAMPO → Fira Code (estilo terminal/código)
Tamanho padrão: 16px (menu) / 15px (campos)
Elementos customizados:

Header Streamlit reposicionado (canto superior direito, transparente)
Sidebar com largura fixa de 400px
Botão sidebar flutuante (fixo, colorido)
Rodapés fixos (foot1 a foot4) ancorados no bottom
Popover de menu lateral posicionado absolutamente via CSS
Todos os widgets (selectbox, checkbox, slider, radio, tabs, expander, form) com estilo personalizado
_GERENTE_PROJETO_/a__Gerente.py — Gerenciador do Projeto
Módulo central de gestão e análise da estrutura do projeto.

Função	Descrição
Pasta_Raiz()	Retorna o Path da pasta raiz do projeto
_pastas_nao()	Retorna lista de pastas a ignorar (.venv, __pycache__, .git, etc.)
contar_estrutura(caminho_base)	Conta pastas, arquivos, extensões e detecta versões Python do ambiente virtual
mostrar_estrutura(st, dados)	Formata e exibe as informações de estrutura no Streamlit
listar_projeto(st)	Exibe a árvore completa do projeto com funções, classes, imports e docstrings via AST
saudacao_por_hora_sistema()	Retorna saudação contextual (Bom dia / Boa tarde / Boa noite / Boa madrugada)
ConvE_data(Data)	Converte data ISO (YYYY-MM-DD) para formato brasileiro (DD/MM/AAAA)
Como listar_projeto funciona internamente:

Primeira passada: percorre todos os .py e mapeia chamadas de funções (AST)
Segunda passada: exibe árvore de diretórios, para cada .py mostra:
Quantidade de funções e classes
Módulos importados
Para cada função: nome, docstring, quantidade de chamadas e quem chama
_GERENTE_PROJETO_/b__FORMATAR_CODIGO.py — Formatador de Código
Analisa e formata automaticamente todos os arquivos .py do projeto em 6 etapas sequenciais. Pode ser executado standalone (python b__FORMATAR_CODIGO.py) ou via interface.

Etapas do pipeline:

Etapa	Função	O que faz
0	_inserir_nome_no_topo	Insere comentário com nome do arquivo no topo (# arquivo.py ou # 📁 pasta/arquivo.py)
1	_normalizar_cabecalhos_arquivo	Colapsa definições de função/classe multi-linha em uma única linha
2	_compactar_layout_inteligente	Remove linhas em branco excessivas, mantendo espaçamento semântico
3	_processar_avisos_arquivo	Detecta funções longas (>50 linhas) e adiciona comentário de aviso # ⚠️ função grande
4	_detectar_strings_repetidas	Encontra strings literais duplicadas no projeto (candidatas a constantes)
5	_remover_imports_nao_usados	Remove via AST imports declarados mas não utilizados
6	_ordenar_imports_arquivo	Ordena imports em 3 grupos: stdlib → terceiros → locais (prefixo _)
Ao final: gera relatorio_codigo.txt com resumo completo de tudo que foi alterado.

Configurações:

LIMITE_LINHAS = 50 — Threshold para aviso de função longa
STDLIB_MODULOS — Set com todos os módulos da stdlib Python para classificação de imports
PREFIXOS_LOCAIS = ("_", "APP") — Prefixos que identificam módulos internos do projeto
_GERENTE_PROJETO_/b__GERAR_DOCSTRINGS.py — Gerador de Docstrings com IA
Percorre todos os arquivos .py do projeto, identifica funções e classes sem docstring, e gera automaticamente docstrings no estilo Google em português usando IA.

Provedores suportados:

Provedor	Configuração	Modelo padrão
OpenRouter (cloud)	OPENROUTER_API_KEY via .senhas	openai/gpt-4o-mini
Ollama (local)	Caminho do executável local	llama3.2
Pipeline por função:

Localiza funções/classes sem docstring via ast.parse
Extrai o cabeçalho completo da função (pode ser multi-linha)
Envia para a IA com prompt: "Gere docstring Google em português"
Valida a resposta (não pode parecer código)
Insere a docstring no arquivo, de baixo para cima (para não deslocar índices de linha)
Salva o arquivo
Variável de controle:

PROVEDOR = "openrouter"  # ou "ollama"

_GERENTE_PROJETO_/c__LISTAR_PROJETO.py — Lister Detalhado
Versão mais completa e standalone do lister de projeto, com integração ChatOpenRouter para análise de código assistida por IA.

_GERENTE_PROJETO_/Decorar/Cor_Html.py — Sistema de Cores
Define a classe Cores com um mapa de nomes amigáveis em português para valores hexadecimais.

Exemplo de cores disponíveis:

Cores("preto") → #000000
Cores("branco") → #FFFFFF
Cores("preto_fosco") → #1E1E1E
Cores("verde_fosco") → #22C576
Cores("laranja_fosco") → #C68642
Cores("cinza_fosco") → #181818
Cores("azul_escuro") → #1A1A1A
Também expõe a função eccor(st) para visualização de todas as cores disponíveis no Streamlit.

_GERENTE_PROJETO_/Decorar/Materiais.py — Ícones Material Design
Sistema de ícones Material Design acessíveis por nome em português. Compatível com a sintaxe nativa do Streamlit (:material/nome_icone:).

Função principal:

Material(nome, texto=None, quantidade=None, help=None) -> str

Exemplos de uso:

Material("pasta")           # → ":material/folder:"
Material("documento")       # → ":material/description:"
Material("gráfico alta")    # → ":material/trending_up:"
Material("lupa", texto="Buscar")  # → ":material/search: Buscar"
Material("correto", quantidade=3) # → ":material/check_circle: :material/check_circle: :material/check_circle:"

Categorias de ícones disponíveis:

Alertas e Segurança (alerta, emergencia, proibido, escudo, erro...)
Emoções (feliz, triste, raiva, chorando, rindo...)
Objetos e Tecnologia (computador, celular, servidor, terminal...)
Escritório (pasta, documento, calculadora, impressora...)
Código e Depuração (lupa, ferramentas, inseto, lampada...)
Dinheiro e Riqueza (dinheiro, moeda, gráfico alta, troféu...)
Setas e Direções (seta cima, seta baixo, seta circular...)
UI / Interface (menu, busca, filtro, salvar, download, upload...)
Mídia e Comunicação (foto, câmera, vídeo, música, email...)
Gráficos e Dados (dashboard, tabela, relatório...)
150 ícones no total
Também disponível: ver_todos_mat(st) — exibe todos os ícones em grade de 5 colunas no Streamlit.

7. Stack tecnológica
Camada	Tecnologia	Uso
Interface	Streamlit	Interface desktop via navegador
Linguagem	Python 3.x	Toda a lógica do sistema
Imagens	Pillow (PIL)	Processamento de fotos
Banco de dados	SQLite	Armazenamento local de produtos/vendas
IA — remoção de fundo	API externa (planejado)	Processamento de imagens
IA — textos	OpenRouter (GPT-4o-mini)	Geração de descrições, docstrings
IA — local	Ollama (llama3.2)	Alternativa offline para geração de texto
Marketplaces	API Shopee	Publicação de produtos
Formatação de código	ast (stdlib)	Análise e manipulação de código Python
Variáveis de ambiente	python-dotenv (.senhas)	Gerenciamento de chaves de API
Subprocessos	subprocess	Execução de Ollama sem abrir janelas CMD
8. Tema visual e interface
O HelSync usa um tema dark completamente customizado, injetado via CSS no Streamlit.

Características visuais:

Fundo preto absoluto com widgets em cinza escuro
Texto principal em verde fosco (#22C576) — estilo terminal
Destaques e botões em laranja fosco (#C68642)
Fontes de programação: JetBrains Mono (interface) e Fira Code (campos)
Sidebar fixa com 400px de largura e bordas visíveis
Header Streamlit original reposicionado e transparente
Rodapés fixos no bottom da tela (foot1 a foot4)
Animação suave em botões ao hover (scale 1.02)
Botão de toggle primário com borda vermelha (estado ativo)
Customizações especiais:

Popover de menu lateral flutuante posicionado ao lado do sidebar
Abas com cores diferentes para ativo/inativo
Formulários com fundo levemente diferente do container pai
Todos os !important para garantir sobrescrita do CSS nativo do Streamlit
9. Sistema de IA integrado
O projeto usa IA em dois contextos distintos:

Para o produto final (usuário final)
Remoção de fundo das fotos de produtos
Geração de descrições de produtos para marketplaces
Sugestão de preços com base em regras de precificação
Para desenvolvimento interno (desenvolvedor)
b__GERAR_DOCSTRINGS.py: Gera automaticamente docstrings para funções sem documentação
c__LISTAR_PROJETO.py: Análise do projeto com suporte de IA via ChatOpenRouter
Rascunho.py: Gera arquivo de contexto completo do projeto para enviar a assistentes de IA
Configuração da API OpenRouter
Arquivo: .senhas  (não commitado)
Variável: OPENROUTER_API_KEY
Modelo padrão: openai/gpt-4o-mini

Configuração Ollama (alternativa local/offline)
OLLAMA_EXE = r"C:\Users\henri\AppData\Local\Programs\Ollama\ollama.exe"
OLLAMA_MODELO = "llama3.2"

10. Ferramentas internas de desenvolvimento
O HelSync tem um conjunto completo de ferramentas para o próprio desenvolvimento do sistema:

Pipeline de qualidade de código (analisar_projeto())
Executar python _GERENTE_PROJETO_/b__FORMATAR_CODIGO.py roda automaticamente:

Etapa 0: Inserir nome do arquivo no topo de cada .py
Etapa 1: Normalizar cabeçalhos multi-linha de funções/classes
Etapa 2: Compactar layout (remover linhas em branco excessivas)
Etapa 3: Detectar e avisar funções longas (>50 linhas)
Etapa 4: Detectar strings repetidas (candidatas a constantes)
Etapa 5: Remover imports não utilizados
Etapa 6: Ordenar imports (stdlib → terceiros → locais)
  └── Gerar relatorio_codigo.txt com tudo que foi alterado

Gerador de docstrings automático
python _GERENTE_PROJETO_/b__GERAR_DOCSTRINGS.py

Percorre todos os .py, encontra funções sem docstring e gera via IA automaticamente.

Gerador de contexto para IA
python Rascunho.py

Gera CONTEXTO_IA.txt com todo o código do projeto em um único arquivo para enviar a assistentes de IA como contexto.

Visualizador de estrutura
Via interface Streamlit, o botão no rodapé abre a árvore completa do projeto com todas as funções, suas docstrings, quantas vezes são chamadas e por quem.

11. Componentes reutilizáveis de UI
Btn_Cliq_Duplo — Botão Toggle
aberto = Btn_Cliq_Duplo(
    nome_aberto="Fechar painel",    # label quando ativo
    nome_fechado="Abrir painel",    # label quando inativo
    key="meu_painel",
    fechar_outras=["outro_painel"]  # fecha outros automaticamente
)
if aberto:
    st.write("Conteúdo do painel")

meu_foot — Painel Rodapé
# Modo button (painel expansível no rodapé)
painel = meu_foot(st, 'foot1', 'Estrutura do Projeto', 'button', 710)
if painel:
    with painel:
        listar_projeto(st)
# Modo expander (sempre visível, expansível)
with meu_foot(st, 'foot2', 'Logs', 'expander'):
    st.write("conteúdo")

Alerta — Dialog de aviso
Alerta(st, "Você tem alterações não salvas!")

controlar_altura — Resize dinâmico
altura = controlar_altura(st, chave="minha_area", altura_inicial=200, passo=50)
st.container(height=altura)

Material — Ícone Material Design
st.button(f"{Material('salvar')} Salvar")
st.write(f"{Material('gráfico alta')} Vendas crescendo!")

12. Utilitários gerais
gerar_nome_unico
Evita sobrescrever arquivos existentes gerando automaticamente um sufixo numérico:

path = gerar_nome_unico(pasta_base=Path("projetos"), nome_desejado="MeuProjeto")
# Resultado: projetos/MeuProjeto_2 (se MeuProjeto já existe)

carregar_imagem_segura
Carrega uma imagem com tratamento completo de erros (arquivo não encontrado, sem permissão, erro PIL):

imagem = carregar_imagem_segura("fotos/produto.jpg", titulo="Foto principal")

ConvE_data
Converte datas do formato ISO para o formato brasileiro:

ConvE_data("2026-05-12 16:05:10")  # → "12/05/2026"
ConvE_data("2026-01-01")           # → "01/01/2026"

saudacao_por_hora_sistema
Retorna saudação automática com horário atual:

# Às 9h  → "Bom dia 09:00"
# Às 15h → "Boa tarde 15:00"
# Às 20h → "Boa noite 20:00"

13. Como rodar
Pré-requisitos
Python 3.10+
Ambiente virtual configurado (.venv ou .virto_stream)
Chave API OpenRouter (opcional, para IA)
Ollama instalado (opcional, para IA local)
Instalação
# Clonar / abrir o projeto
cd CONTROLE_PRODUTOS_HelSync
# Criar ambiente virtual
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
# Instalar dependências
pip install streamlit pillow python-dotenv openai

Configurar chaves de API (opcional)
Criar arquivo .senhas na raiz:

OPENROUTER_API_KEY=sk-or-...

Executar
streamlit run App_.py

Executar ferramentas de desenvolvimento
# Formatar todo o código do projeto
python _GERENTE_PROJETO_/b__FORMATAR_CODIGO.py
# Gerar docstrings faltantes com IA
python _GERENTE_PROJETO_/b__GERAR_DOCSTRINGS.py
# Gerar contexto para IA
python Rascunho.py

14. Status do projeto
🚧 Em desenvolvimento — Reconstrução do zero com arquitetura limpa.

O que já existe (implementado)
 Estrutura de pacotes e módulos
 Sistema de tema visual customizado completo
 Componentes de UI reutilizáveis (botão toggle, rodapé, alerta, grade)
 Sistema de ícones Material Design em português
 Sistema de cores HTML nomeadas
 Analisador de estrutura de projeto (AST)
 Formatador de código automático (6 etapas)
 Gerador de docstrings via IA (OpenRouter + Ollama)
 Gerador de contexto para IA
 Utilitários gerais (nomes únicos, imagens seguras, datas)
O que está planejado
 Processamento de imagens (remoção de fundo, sobreposição de logo)
 Cadastro de produtos com tipos de kit
 Integração com API Shopee
 Módulo financeiro
 Geração de descrições de produtos com IA
 Edição de vídeo para marketplace
Gerado com base no código-fonte completo do projeto. Última atualização: Maio 2026.