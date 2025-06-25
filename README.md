# Sistema de Análise de Notas Fiscais com CrewAI

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.28+-red.svg)](https://streamlit.io/)
[![CrewAI](https://img.shields.io/badge/crewai-latest-green.svg)](https://crewai.com/)
[![Google Gemini](https://img.shields.io/badge/google--gemini-api-orange.svg)](https://ai.google.dev/)

Sistema inteligente de análise de dados de Notas Fiscais utilizando agentes CrewAI especializados, com interface web Streamlit e suporte nativo a arquivos ZIP de dados fiscais brasileiros.

## 🚀 Características Principais

### ✨ Funcionalidades

- **🤖 Agentes CrewAI Especializados**: Três agentes colaborativos com funções específicas
- **📊 Interface Web Intuitiva**: Dashboard Streamlit com visualizações interativas
- **📦 Processamento ZIP Nativo**: Suporte automático para arquivos ZIP de Notas Fiscais
- **🔄 Merge Inteligente**: União automática de dados de cabeçalho e itens por CHAVE DE ACESSO
- **📈 Visualizações Dinâmicas**: Gráficos interativos com Plotly
- **💬 Chat com IA**: Interface conversacional para análise de dados
- **🔍 Detecção Automática de Encoding**: Suporte robusto a arquivos brasileiros
- **⚡ Cache Inteligente**: Sistema de cache para otimização de performance

### 🏗️ Arquitetura Multi-Agente

O sistema utiliza três agentes CrewAI especializados que trabalham em colaboração:

1. **Agente de Metadados** - Especialista em caracterização de datasets
2. **Agente de Código Python** - Especialista em análise programática com pandas
3. **Agente de Linguagem Natural** - Especialista em comunicação clara

## 🛠️ Instalação e Configuração

### Pré-requisitos

- Python 3.10 ou superior
- Chave da API Google Gemini
- Sistema operacional: Windows, macOS ou Linux

### 1. Clone o Repositório

```bash
git clone <url-do-repositorio>
cd sistema-analise-notas-fiscais
```

### 2. Crie um Ambiente Virtual

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Instale as Dependências

```bash
pip install -r requirements.txt
```

### 4. Configure a Chave da API

Crie um arquivo `.env` na raiz do projeto:

```env
GEMINI_API_KEY=sua_chave_da_api_gemini_aqui
```

**⚠️ Importante:** 
- Obtenha sua chave gratuitamente em [Google AI Studio](https://makersuite.google.com/app/apikey)
- Nunca compartilhe sua chave da API
- Adicione `.env` ao seu `.gitignore`

### 5. Teste a Configuração

Execute o script de verificação:

```bash
python verificar_gemini.py
```

## 🚀 Como Usar

### Iniciando a Interface Web

```bash
streamlit run streamlit_crewai_interface.py
```

A aplicação será aberta automaticamente em `http://localhost:8501`

### Usando o Sistema Principal (CLI)

```bash
python sistema_analise_dados_crewai.py
```

## 📁 Formatos de Arquivo Suportados

### 📄 Arquivos CSV Individuais
- Qualquer arquivo CSV válido
- Detecção automática de encoding (UTF-8, Latin-1, CP1252, etc.)
- Normalização automática de nomes de colunas

### 📦 Arquivos ZIP de Notas Fiscais
O sistema suporta arquivos ZIP com a seguinte estrutura:

```
arquivo_nfs.zip
├── 202401_NFs_Cabecalho.csv    # Dados do cabeçalho das NFs
└── 202401_NFs_Itens.csv        # Dados dos itens das NFs
```

**Padrão de Nomes Obrigatório:**
- `aaaamm_NFs_Cabecalho.csv` (onde `aaaamm` = ano e mês)
- `aaaamm_NFs_Itens.csv`

**Requisitos para Merge:**
- Ambos arquivos devem conter uma coluna "CHAVE DE ACESSO"
- O merge é realizado automaticamente usando inner join
- Colunas duplicadas recebem sufixos `_CABECALHO` e `_ITENS`

## 🎯 Exemplos de Uso

### Interface Web - Upload de Arquivo

1. **Acesse a aplicação** em `http://localhost:8501`
2. **Faça upload** de um arquivo CSV ou ZIP
3. **Explore o Dashboard** com métricas e visualizações automáticas
4. **Use o Chat** para fazer perguntas sobre os dados

### Perguntas Exemplo no Chat

```
"Qual fornecedor teve o maior valor total de notas fiscais?"
"Quantas notas fiscais foram emitidas por estado?"
"Qual é a distribuição de valores por mês?"
"Quais são os 10 maiores valores de nota fiscal?"
"Como está a distribuição geográfica das operações?"
```

### CLI - Análise Programática

```python
from sistema_analise_dados_crewai import SistemaAnaliseBaseDados

# Inicializar sistema
sistema = SistemaAnaliseBaseDados()

# Processar arquivo
arquivo = "dados/202401_NFs.zip"
metadados = sistema.gerar_metadados(arquivo)

# Fazer pergunta
resposta = sistema.responder_pergunta(
    arquivo, 
    "Qual é o valor total das notas fiscais por UF?"
)
print(resposta)
```

## 📊 Interface Web - Recursos

### Dashboard Principal
- **Métricas Resumo**: Total de registros, colunas, valor total, período
- **Distribuição por UF**: Gráfico de barras interativo
- **Evolução Temporal**: Linha do tempo de emissões
- **Top Entidades**: Ranking de fornecedores/destinatários

### Chat com Agentes
- **Interface Conversacional**: Perguntas em linguagem natural
- **Processamento Inteligente**: Agentes CrewAI analisam e respondem
- **Histórico Persistente**: Conversa mantida durante a sessão
- **Respostas Detalhadas**: Análises completas com contexto

### Visualização de Metadados
- **Estrutura Completa**: Informações detalhadas do dataset
- **Estatísticas Descritivas**: Para colunas numéricas
- **Qualidade dos Dados**: Identificação de valores nulos
- **Informações de Processamento**: Detalhes sobre merge e encoding

## 🔧 Configuração Avançada

### Customizando Agentes

```python
# Modificar temperatura do modelo
def configurar_gemini():
    gemini_llm = LLM(
        model='gemini/gemini-1.5-flash',
        api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.7  # Aumentar criatividade
    )
    return gemini_llm
```

### Adicionando Novas Ferramentas

```python
from crewai.tools import BaseTool

class MinhaFerramentaCustomizada(BaseTool):
    name: str = "minha_ferramenta"
    description: str = "Descrição da ferramenta"
    
    def _run(self, input_data: str) -> str:
        # Implementar lógica da ferramenta
        return resultado
```

### Configurações de Cache

```python
# Limpar cache manualmente
BaseDataProcessor.clear_cache()

# Verificar arquivo atual
arquivo_atual = BaseDataProcessor.get_current_file_path()
```

## 🐛 Solução de Problemas

### Erro de Autenticação Gemini

```bash
# Verificar variável de ambiente
echo $GEMINI_API_KEY

# Recriar arquivo .env
echo "GEMINI_API_KEY=sua_chave" > .env
```

### Problemas de Encoding

O sistema detecta automaticamente o encoding, mas você pode forçar:

```python
# Em caso de problemas, o sistema tentará:
encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1', 'windows-1252']
```

### Erro no Merge de ZIP

Verifique se:
- Os dois arquivos CSV estão presentes
- Os nomes seguem o padrão correto
- Ambos contêm a coluna "CHAVE DE ACESSO"

```python
# Debug do processo
print("Arquivos encontrados:", extracted_files)
print("Coluna chave cabeçalho:", chave_col_cabecalho)
print("Coluna chave itens:", chave_col_itens)
```

## 📈 Performance e Otimização

### Cache do Sistema
- **Cache de DataFrames**: Evita reprocessamento
- **Cache de Metadados**: Acelera consultas repetidas
- **Processamento Unificado**: Garante consistência entre agentes

### Dicas de Performance
- Use arquivos menores para testes iniciais
- O primeiro processamento é mais lento (cache vazio)
- Perguntas similares são mais rápidas devido ao cache

## 🤝 Contribuindo

### Como Contribuir

1. **Fork** o repositório
2. **Crie** uma branch para sua feature (`git checkout -b feature/nova-feature`)
3. **Commit** suas mudanças (`git commit -am 'Adiciona nova feature'`)
4. **Push** para a branch (`git push origin feature/nova-feature`)
5. **Abra** um Pull Request

### Estrutura do Código

```
├── sistema_analise_dados_crewai.py    # Sistema principal
├── streamlit_crewai_interface.py      # Interface web
├── requirements.txt                   # Dependências
├── .env                              # Variáveis de ambiente
├── verificar_gemini.py               # Script de verificação
└── README.md                         # Documentação
```

### Diretrizes de Desenvolvimento

- **Código limpo** e bem documentado
- **Testes** para novas funcionalidades
- **Compatibilidade** com Python 3.10+
- **Seguir** padrões PEP 8

## 📝 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 🆘 Suporte

### Canais de Suporte

- **Issues**: [GitHub Issues](link-para-issues)
- **Documentação**: Este README e código comentado
- **Comunidade**: Discussões no GitHub

### FAQ

**P: O sistema funciona com outros modelos além do Gemini?**
R: Atualmente otimizado para Gemini, mas o CrewAI suporta outros modelos via LiteLLM.

**P: Posso processar arquivos maiores que 100MB?**
R: Sim, mas considere otimizações de memória para arquivos muito grandes.

**P: O sistema funciona offline?**
R: Não, requer conexão com a API do Google Gemini.

**P: Posso adicionar novos tipos de arquivo?**
R: Sim, estenda a classe `BaseDataProcessor` para suportar novos formatos.

## 🏆 Créditos

Desenvolvido com ❤️ utilizando:
- [CrewAI](https://crewai.com/) - Framework multi-agente
- [Streamlit](https://streamlit.io/) - Interface web
- [Google Gemini](https://ai.google.dev/) - Modelo de linguagem
- [Plotly](https://plotly.com/) - Visualizações interativas
- [Pandas](https://pandas.pydata.org/) - Manipulação de dados

---

**🚀 Pronto para começar? Execute `streamlit run streamlit_crewai_interface.py` e explore o poder dos agentes CrewAI!**