# Análise de Notas Fiscais com CrewAI e Gemini

Sistema completo de análise de dados de notas fiscais usando múltiplos agentes autônomos orquestrados pelo CrewAI, interface web em Streamlit e análise via Gemini API.

## Estrutura do Projeto

```
nota_fiscal_analyzer/
├── src/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── file_processor.py      # Agente de ingestão
│   │   ├── data_merger.py         # Agente de combinação
│   │   ├── nlp_interpreter.py     # Agente interpretador
│   │   ├── analyzer.py            # Agente analítico
│   │   └── memory_manager.py      # Agente de memória
│   ├── crew/
│   │   ├── __init__.py
│   │   └── crew_orchestrator.py   # Orquestrador principal
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── data_utils.py         # Utilitários de dados
│   │   └── viz_utils.py          # Utilitários de visualização
│   └── main.py                   # Interface Streamlit principal
├── config/
│   └── config.yaml               # Configurações
├── requirements.txt
├── .env.example
└── README.md
```

## Tecnologias Utilizadas

- **CrewAI**: Orquestração de agentes
- **Google Gemini API**: Modelos de linguagem
- **Streamlit**: Interface web
- **Pandas**: Manipulação de dados
- **Matplotlib/Seaborn**: Visualizações
- **Plotly**: Gráficos interativos

## Características Principais

### Agentes Especializados
1. **File Processor**: Processamento de arquivos ZIP e CSV
2. **Data Merger**: Combinação inteligente dos datasets
3. **NLP Interpreter**: Interpretação de perguntas em linguagem natural
4. **Analyzer**: Análise estatística e geração de visualizações
5. **Memory Manager**: Gerenciamento de memória entre sessões

### Funcionalidades
- Upload de arquivos ZIP com validação
- Análise em linguagem natural
- Geração automática de gráficos e tabelas
- Memória persistente entre perguntas
- Interface intuitiva e responsiva

### Exemplos de Perguntas Suportadas
- "Qual fornecedor teve maior montante recebido?"
- "Quantas notas fiscais foram emitidas em janeiro de 2024?"
- "Quais os três itens mais comprados por valor total?"
- "Mostre a distribuição de notas por UF"
- "Compare o volume de compras entre diferentes CFOPs"
