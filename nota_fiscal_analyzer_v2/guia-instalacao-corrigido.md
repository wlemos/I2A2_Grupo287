# Guia de Instalação e Execução - Versão Corrigida

## Sistema de Análise de Notas Fiscais com CrewAI

### Correções Aplicadas

Este guia apresenta as correções implementadas para resolver o erro do Pydantic com DataFrames e melhorar a estabilidade do sistema.

### 📋 Principais Correções Implementadas

#### 1. **Correção do Erro Pydantic com DataFrame**

**Problema identificado:**
```
Unable to generate pydantic-core schema for <class 'pandas.core.frame.DataFrame'>. 
Set arbitrary_types_allowed=True in the model_config to ignore this error
```

**Solução aplicada:**
- Adicionado `model_config = ConfigDict(arbitrary_types_allowed=True)` em todas as classes `BaseModel` que contêm campos `pd.DataFrame`
- Atualizado para Pydantic v2 com sintaxe correta

#### 2. **Arquivos Corrigidos**

| Arquivo Original | Arquivo Corrigido | Principais Correções |
|------------------|-------------------|---------------------|
| `crew_orchestrator.py` | `crew_orchestrator_fixed.py` | Modelos Pydantic para ferramentas |
| `main.py` | `main_fixed.py` | Estados de sessão e dados carregados |
| `viz_utils.py` | `viz_utils_fixed.py` | Modelos para dados de gráficos |
| `utils.py` | `data_utils_fixed.py` | Containers para DataFrames |
| `requirements.txt` | `requirements_fixed.txt` | Versões compatíveis |

### 🚀 Instalação Passo a Passo

#### Passo 1: Preparar o Ambiente

```bash
# 1. Criar ambiente virtual
python -m venv venv

# 2. Ativar ambiente virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. Atualizar pip
python -m pip install --upgrade pip
```

#### Passo 2: Instalar Dependências

```bash
# Instalar usando o arquivo de requirements corrigido
pip install -r requirements_fixed.txt

# Ou instalar manualmente as dependências principais:
pip install "pydantic>=2.4.0"
pip install "streamlit>=1.28.0"
pip install "crewai>=0.28.0"
pip install "google-generativeai>=0.3.0"
pip install "pandas>=2.0.0"
pip install "plotly>=5.17.0"
```

#### Passo 3: Estrutura de Diretórios

```
projeto-analise-notas-fiscais/
├── .env                              # Variáveis de ambiente
├── requirements_fixed.txt            # Dependências corrigidas
├── main_fixed.py                     # Aplicação principal corrigida
├── src/
│   ├── crew/
│   │   └── crew_orchestrator_fixed.py    # Orquestrador corrigido
│   ├── utils/
│   │   ├── data_utils_fixed.py           # Utilitários de dados corrigidos
│   │   └── viz_utils_fixed.py            # Visualizações corrigidas
│   └── agents/
│       └── agents_config_fixed.py        # Configuração dos agentes
├── config/
│   └── config.yaml                   # Configurações
├── data/
│   ├── uploads/                      # Arquivos enviados
│   ├── processed/                    # Dados processados
│   └── temp/                         # Arquivos temporários
└── logs/                             # Arquivos de log
```

#### Passo 4: Configurar Variáveis de Ambiente

Criar arquivo `.env`:

```env
# API Keys
GEMINI_API_KEY=sua_chave_api_gemini_aqui

# Configurações da aplicação
APP_NAME=Analisador de Notas Fiscais TCU
DEBUG=True
LOG_LEVEL=INFO

# Configurações Streamlit
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=localhost

# Configurações de upload
MAX_FILE_SIZE_MB=100
```

### 💻 Executando a Aplicação

#### Método 1: Execução Direta

```bash
# Navegar para o diretório do projeto
cd projeto-analise-notas-fiscais

# Executar a aplicação corrigida
streamlit run main_fixed.py
```

#### Método 2: Com Configurações Específicas

```bash
streamlit run main_fixed.py --server.port 8501 --server.address 0.0.0.0
```

### 🔧 Verificação de Funcionamento

#### 1. **Teste das Correções Pydantic**

Criar arquivo `test_corrections.py`:

```python
from pydantic import BaseModel, ConfigDict
import pandas as pd

# Teste do modelo corrigido
class TestDataFrame(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    dados: pd.DataFrame

# Criar DataFrame de teste
df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})

# Testar criação do modelo
try:
    teste = TestDataFrame(dados=df)
    print("✅ Correção Pydantic funcionando!")
except Exception as e:
    print(f"❌ Erro: {e}")
```

```bash
python test_corrections.py
```

#### 2. **Verificar Importações**

```python
# Teste de importações
try:
    from src.crew.crew_orchestrator_fixed import NotaFiscalCrew
    from src.utils.data_utils_fixed import DataProcessor
    from src.utils.viz_utils_fixed import ChartGenerator
    print("✅ Todas as importações funcionando!")
except ImportError as e:
    print(f"❌ Erro de importação: {e}")
```

### 🐛 Resolução de Problemas Comuns

#### Problema 1: Erro de Importação

**Erro:**
```
ModuleNotFoundError: No module named 'src.crew.crew_orchestrator'
```

**Solução:**
- Certifique-se de usar os arquivos corrigidos (`*_fixed.py`)
- Verifique se a estrutura de diretórios está correta
- Execute a partir do diretório raiz do projeto

#### Problema 2: Erro de API Key

**Erro:**
```
google.api_core.exceptions.Unauthenticated: 401 API key not valid
```

**Solução:**
- Obtenha uma chave API válida do Google AI Studio
- Configure no arquivo `.env` ou diretamente na interface

#### Problema 3: Erro de Versão do Pydantic

**Erro:**
```
AttributeError: 'ConfigDict' object has no attribute 'arbitrary_types_allowed'
```

**Solução:**
- Atualize para Pydantic v2: `pip install "pydantic>=2.4.0"`
- Use a sintaxe corrigida com `model_config = ConfigDict(...)`

### 📝 Alterações nos Códigos

#### Antes (com erro):
```python
class DataAnalysisInput(BaseModel):
    query: str
    data: pd.DataFrame  # ❌ Causava erro
```

#### Depois (corrigido):
```python
class DataAnalysisInput(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)  # ✅ Correção
    
    query: str
    data: pd.DataFrame
```

### 🎯 Funcionalidades Validadas

Após as correções, o sistema agora suporta:

- ✅ Upload e processamento de arquivos ZIP
- ✅ Análise de dados com Pydantic v2
- ✅ Geração de gráficos interativos
- ✅ Interface de chat com agentes CrewAI
- ✅ Validação robusta de dados
- ✅ Formatação adequada de respostas

### 📋 Checklist de Execução

- [ ] Ambiente virtual criado e ativado
- [ ] Dependências instaladas com `requirements_fixed.txt`
- [ ] Arquivo `.env` configurado com API keys
- [ ] Estrutura de diretórios criada
- [ ] Arquivos corrigidos copiados para locais apropriados
- [ ] Teste de correções Pydantic executado
- [ ] Aplicação executada com sucesso
- [ ] Upload de dados testado
- [ ] Chat com agentes funcionando

### 🔄 Atualizações Futuras

Para manter o sistema atualizado:

1. **Monitore versões do CrewAI**: `pip install crewai --upgrade`
2. **Mantenha Pydantic v2**: Sempre use `pydantic>=2.4.0`
3. **Atualize Streamlit**: Para novas funcionalidades
4. **Backup de configurações**: Mantenha cópias dos arquivos `.env`

### 📞 Suporte

Em caso de problemas:

1. Verifique se todos os arquivos `*_fixed.py` estão sendo usados
2. Confirme que as versões das dependências estão corretas
3. Teste os modelos Pydantic isoladamente
4. Verifique logs de erro detalhados no terminal

---

**Versão:** 2.0 - Corrigida  
**Data:** Dezembro 2024  
**Status:** ✅ Totalmente Funcional