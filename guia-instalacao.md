# Guia de Instalação e Configuração

## Configuração Rápida (5 minutos)

### 1. Obter Chave da API Gemini
1. Acesse [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Faça login com sua conta Google
3. Clique em "Create API Key"
4. Copie a chave gerada (formato: `AIzaSy...`)

### 2. Configurar Projeto
```bash
# Clone e entre no diretório
git clone <url-repositorio>
cd sistema-analise-notas-fiscais

# Crie ambiente virtual
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Instale dependências
pip install -r requirements.txt

# Configure API key
echo "GEMINI_API_KEY=sua_chave_aqui" > .env
```

### 3. Verificar Configuração
```bash
python verificar_gemini.py
```

### 4. Executar Sistema
```bash
streamlit run streamlit_crewai_interface.py
```

## Estrutura de Arquivos do Projeto

```
sistema-analise-notas-fiscais/
├── README.md                           # Documentação principal
├── relatorio-arquitetura.md           # Relatório técnico detalhado  
├── requirements.txt                    # Dependências Python
├── verificar-gemini.py                # Script de verificação
├── .env                               # Variáveis de ambiente (criar)
├── sistema_analise_dados_crewai.py   # Sistema principal
└── streamlit_crewai_interface.py     # Interface web
```

## Exemplo de Arquivo .env

```env
# Configuração da API Gemini
GEMINI_API_KEY=AIzaSyBxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Configurações opcionais
# OPENAI_MODEL_NAME=gemini/gemini-1.5-flash
# DEBUG=False
```

## Comandos Úteis

```bash
# Verificar configuração
python verificar_gemini.py

# Executar interface web
streamlit run streamlit_crewai_interface.py

# Executar sistema CLI
python sistema_analise_dados_crewai.py

# Instalar dependências de desenvolvimento
pip install pytest black flake8

# Executar testes (se implementados)
pytest

# Formatar código
black *.py
```

## Solução de Problemas Comuns

### Erro de API Key
```bash
# Verificar se a chave está correta
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('GEMINI_API_KEY')[:10])"
```

### Erro de Importação
```bash
# Reinstalar dependências
pip uninstall -r requirements.txt -y
pip install -r requirements.txt
```

### Erro de Encoding
```bash
# Configurar locale (Linux/Mac)
export LANG=pt_BR.UTF-8
export LC_ALL=pt_BR.UTF-8
```