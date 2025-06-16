# main.py
"""
Sistema de Análise de Notas Fiscais com CrewAI
Interface Streamlit principal que orquestra múltiplos agentes autônomos
VERSÃO CORRIGIDA - Com suporte adequado para pandas DataFrame
"""

import streamlit as st
import pandas as pd
import numpy as np
import os
import zipfile
import tempfile
from pathlib import Path
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict
from typing import Dict, Any, Optional

# Configurações da página
st.set_page_config(
    page_title="Análise de Notas Fiscais - TCU",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Carregar variáveis de ambiente
load_dotenv()

# ===============================
# MODELOS PYDANTIC CORRIGIDOS
# ===============================

class SessionStateModel(BaseModel):
    """Modelo para estado da sessão - CORRIGIDO"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    data_loaded: bool = False
    merged_data: Optional[pd.DataFrame] = None
    chat_history: list = []
    crew: Optional[Any] = None

class UploadedDataModel(BaseModel):
    """Modelo para dados carregados - CORRIGIDO"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    notas_fiscais: pd.DataFrame
    itens_nota: pd.DataFrame
    file_info: Dict[str, Any] = {}

# Importar módulos locais (com verificação de existência)
try:
    from src.crew.crew_orchestrator import NotaFiscalCrew
    from src.utils.data_utils import DataValidator, FileProcessor
    from src.utils.viz_utils import ChartGenerator
except ImportError as e:
    st.error(f"Erro ao importar módulos: {str(e)}")
    st.info("Certifique-se de que todos os módulos estão disponíveis no diretório correto.")

class NotaFiscalApp:
    """Aplicação principal com correções para Pydantic - VERSÃO CORRIGIDA"""
    
    def __init__(self):
        self.config = self.load_config()
        self.initialize_session_state()
        
    def load_config(self):
        """Carrega configurações do arquivo YAML"""
        try:
            config_path = Path('config/config.yaml')
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as file:
                    return yaml.safe_load(file)
            else:
                # Configuração padrão caso arquivo não exista
                return self.get_default_config()
        except Exception as e:
            st.warning(f"Erro ao carregar configuração: {str(e)}. Usando configuração padrão.")
            return self.get_default_config()
    
    def get_default_config(self):
        """Retorna configuração padrão"""
        return {
            'agents': {
                'file_processor': {
                    'role': 'Especialista em Processamento de Arquivos',
                    'goal': 'Extrair e validar dados de arquivos ZIP e CSV',
                    'backstory': 'Especialista em processamento de dados fiscais'
                },
                'data_merger': {
                    'role': 'Especialista em Integração de Dados',
                    'goal': 'Combinar datasets de notas fiscais',
                    'backstory': 'Especialista em engenharia de dados'
                },
                'nlp_interpreter': {
                    'role': 'Intérprete de Linguagem Natural',
                    'goal': 'Converter perguntas em operações analíticas',
                    'backstory': 'Linguista computacional especializado'
                },
                'analyzer': {
                    'role': 'Analista de Dados Fiscais',
                    'goal': 'Executar análises e gerar visualizações',
                    'backstory': 'Analista sênior com expertise governamental'
                },
                'memory_manager': {
                    'role': 'Gerente de Memória',
                    'goal': 'Manter contexto e logs',
                    'backstory': 'Administrador de dados'
                }
            },
            'data': {
                'merge_key': 'CHAVE DE ACESSO',
                'date_columns': ['DATA EMISSÃO', 'DATA/HORA EVENTO MAIS RECENTE'],
                'numeric_columns': ['VALOR TOTAL', 'VALOR UNITÁRIO', 'QUANTIDADE'],
                'categorical_columns': ['UF EMITENTE', 'UF DESTINATÁRIO']
            }
        }
    
    def initialize_session_state(self):
        """Inicializa o estado da sessão Streamlit - CORRIGIDO"""
        # Inicializar estado básico sem usar modelos Pydantic para sessão do Streamlit
        if 'data_loaded' not in st.session_state:
            st.session_state.data_loaded = False
        if 'merged_data' not in st.session_state:
            st.session_state.merged_data = None
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        if 'crew' not in st.session_state:
            st.session_state.crew = None
        if 'uploaded_data' not in st.session_state:
            st.session_state.uploaded_data = None
    
    def render_header(self):
        """Renderiza o cabeçalho da aplicação"""
        st.title("🏛️ Análise de Notas Fiscais - TCU")
        st.markdown("""
        ### Sistema Inteligente de Análise com CrewAI
        
        Faça upload de arquivos ZIP contendo dados de notas fiscais e 
        realize consultas em linguagem natural com o auxílio de agentes 
        especializados orquestrados pelo CrewAI.
        """)
        
        # Barra de progresso do pipeline
        if st.session_state.data_loaded:
            st.success("✅ Dados carregados e processados com sucesso!")
            
            # Mostrar informações dos dados carregados
            if st.session_state.merged_data is not None:
                data = st.session_state.merged_data
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Registros", f"{len(data):,}")
                with col2:
                    st.metric("Período", f"{data['DATA EMISSÃO'].dt.date.min()} a {data['DATA EMISSÃO'].dt.date.max()}")
                with col3:
                    st.metric("Valor Total", f"R$ {data['VALOR TOTAL'].sum():,.2f}")
        else:
            st.info("📤 Aguardando upload dos dados...")
    
    def render_sidebar(self):
        """Renderiza a barra lateral com configurações"""
        with st.sidebar:
            st.header("⚙️ Configurações")
            
            # Status dos agentes
            st.subheader("Status dos Agentes")
            agent_status = {
                "File Processor": "🟢 Ativo",
                "Data Merger": "🟢 Ativo", 
                "NLP Interpreter": "🟢 Ativo",
                "Analyzer": "🟢 Ativo",
                "Memory Manager": "🟢 Ativo"
            }
            
            for agent, status in agent_status.items():
                st.text(f"{agent}: {status}")
            
            st.divider()
            
            # Configurações de API
            st.subheader("🔧 API Configuration")
            api_key_status = "🟢 Configurada" if os.getenv("GEMINI_API_KEY") else "🔴 Não configurada"
            st.text(f"Gemini API: {api_key_status}")
            
            if not os.getenv("GEMINI_API_KEY"):
                st.warning("Configure sua chave da API Gemini no arquivo .env")
                
                # Permitir configuração manual da API key
                with st.expander("Configurar API Key"):
                    api_key = st.text_input("Gemini API Key", type="password")
                    if st.button("Salvar API Key") and api_key:
                        os.environ["GEMINI_API_KEY"] = api_key
                        st.success("API Key configurada!")
                        st.rerun()
            
            st.divider()
            
            # Estatísticas dos dados
            if st.session_state.data_loaded and st.session_state.merged_data is not None:
                st.subheader("📈 Estatísticas dos Dados")
                data = st.session_state.merged_data
                
                try:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Total de Registros", f"{len(data):,}")
                        if 'RAZÃO SOCIAL EMITENTE' in data.columns:
                            st.metric("Fornecedores Únicos", f"{data['RAZÃO SOCIAL EMITENTE'].nunique():,}")
                    
                    with col2:
                        if 'VALOR TOTAL' in data.columns:
                            st.metric("Valor Total", f"R$ {data['VALOR TOTAL'].sum():,.2f}")
                        if 'DATA EMISSÃO' in data.columns:
                            date_range = f"{data['DATA EMISSÃO'].dt.date.min()} a {data['DATA EMISSÃO'].dt.date.max()}"
                            st.text(f"Período: {date_range}")
                except Exception as e:
                    st.error(f"Erro ao calcular estatísticas: {str(e)}")
    
    def process_uploaded_file(self, uploaded_file):
        """Processa o arquivo ZIP enviado pelo usuário - CORRIGIDO"""
        try:
            # Criar diretório temporário
            with tempfile.TemporaryDirectory() as temp_dir:
                # Salvar arquivo enviado
                zip_path = os.path.join(temp_dir, "uploaded.zip")
                with open(zip_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # Extrair arquivos
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Buscar arquivos CSV esperados
                csv_files = {}
                csv_file_info = {}
                
                for root, _, files in os.walk(temp_dir):
                    for file_name in files:
                        if file_name.endswith('.csv'):
                            file_path = os.path.join(root, file_name)

                # for file_name in os.listdir(temp_dir):
                #     if file_name.endswith('.csv'):
                #         file_path = os.path.join(temp_dir, file_name)
                        
                        # Tentar ler o arquivo
                        try:
                            df = pd.read_csv(file_path, encoding='utf-8')
                        except UnicodeDecodeError:
                            try:
                                df = pd.read_csv(file_path, encoding='latin-1')
                            except Exception as e:
                                st.error(f"Erro ao ler arquivo {file_name}: {str(e)}")
                                continue
                        
                        # Identificar tipo de arquivo
                        if 'notas_fiscais' in file_name.lower() or 'notas' in file_name.lower():
                            csv_files['notas_fiscais'] = df
                            csv_file_info['notas_fiscais'] = {
                                'filename': file_name,
                                'rows': len(df),
                                'columns': list(df.columns)
                            }
                        elif 'itens_nota' in file_name.lower() or 'itens' in file_name.lower():
                            csv_files['itens_nota'] = df
                            csv_file_info['itens_nota'] = {
                                'filename': file_name,
                                'rows': len(df),
                                'columns': list(df.columns)
                            }
                
                # Validar arquivos encontrados
                if len(csv_files) != 2:
                    st.error(f"Arquivos necessários não encontrados! Encontrados {len(csv_files)} arquivos CSV")
                    st.info("Certifique-se de que o ZIP contém arquivos com 'notas_fiscais' e 'itens_nota' no nome.")
                    st.info(f"Arquivos CSV encontrados: {[file_name for _, _, files in os.walk(temp_dir) for file_name in files if file_name.endswith('.csv')]}")

                    return None
                
                # Validar colunas obrigatórias
                required_columns = {
                    'notas_fiscais': ['CHAVE DE ACESSO'],
                    'itens_nota': ['CHAVE DE ACESSO', 'VALOR TOTAL']
                }
                
                for df_name, req_cols in required_columns.items():
                    if df_name in csv_files:
                        missing_cols = [col for col in req_cols if col not in csv_files[df_name].columns]
                        if missing_cols:
                            st.error(f"Colunas obrigatórias ausentes em {df_name}: {missing_cols}")
                            return None
                
                # Criar modelo de dados carregados - CORRIGIDO
                uploaded_data = UploadedDataModel(
                    notas_fiscais=csv_files['notas_fiscais'],
                    itens_nota=csv_files['itens_nota'],
                    file_info=csv_file_info
                )
                
                # Inicializar crew e processar dados
                crew = NotaFiscalCrew(self.config)
                st.session_state.crew = crew
                st.session_state.uploaded_data = uploaded_data
                
                # Processar dados através dos agentes
                with st.spinner("Processando dados através dos agentes..."):
                    merged_data = crew.process_files({
                        'notas_fiscais': uploaded_data.notas_fiscais,
                        'itens_nota': uploaded_data.itens_nota
                    })
                
                return merged_data
                
        except Exception as e:
            st.error(f"Erro ao processar arquivo: {str(e)}")
            # Log detalhado para debug
            import traceback
            st.error(f"Detalhes do erro: {traceback.format_exc()}")
            return None
    
    def render_upload_section(self):
        """Renderiza a seção de upload de arquivos"""
        st.header("📤 Upload de Dados")
        
        # Instruções
        with st.expander("📋 Instruções para Upload"):
            st.markdown("""
            **Formato esperado:**
            - Arquivo ZIP contendo 2 arquivos CSV
            - Um arquivo deve conter 'notas_fiscais' no nome
            - Outro arquivo deve conter 'itens_nota' no nome
            
            **Colunas obrigatórias:**
            - `CHAVE DE ACESSO`: presente em ambos os arquivos para relacionamento
            - `VALOR TOTAL`: presente no arquivo de itens
            - `DATA EMISSÃO`: recomendada no arquivo de notas
            
            **Exemplo de estrutura:**
            ```
            dados_tcu.zip
            ├── notas_fiscais.csv
            └── itens_nota.csv
            ```
            """)
        
        uploaded_file = st.file_uploader(
            "Selecione o arquivo ZIP com os dados das notas fiscais",
            type=['zip'],
            help="O arquivo deve conter 'notas_fiscais.csv' e 'itens_nota.csv'"
        )
        
        if uploaded_file is not None:
            # Mostrar informações do arquivo
            st.info(f"Arquivo selecionado: {uploaded_file.name} ({uploaded_file.size:,} bytes)")
            
            col1, col2 = st.columns([1, 4])
            
            with col1:
                if st.button("🚀 Processar Dados", type="primary"):
                    with st.spinner("Processando arquivo..."):
                        merged_data = self.process_uploaded_file(uploaded_file)
                        
                        if merged_data is not None:
                            st.session_state.merged_data = merged_data
                            st.session_state.data_loaded = True
                            st.success("✅ Dados processados com sucesso!")
                            st.rerun()
            
            with col2:
                if st.button("🔄 Limpar Dados"):
                    st.session_state.data_loaded = False
                    st.session_state.merged_data = None
                    st.session_state.chat_history = []
                    st.session_state.crew = None
                    st.session_state.uploaded_data = None
                    st.success("Dados limpos com sucesso!")
                    st.rerun()
    
    def render_data_overview(self):
        """Renderiza visão geral dos dados carregados"""
        if not st.session_state.data_loaded or st.session_state.merged_data is None:
            st.info("Nenhum dado carregado ainda.")
            return
        
        st.header("📊 Visão Geral dos Dados")
        
        data = st.session_state.merged_data
        
        try:
            # Métricas principais
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                unique_notes = data['CHAVE DE ACESSO'].nunique() if 'CHAVE DE ACESSO' in data.columns else 0
                st.metric(
                    "Total de Notas",
                    f"{unique_notes:,}",
                    help="Número único de notas fiscais"
                )
            
            with col2:
                total_value = data['VALOR TOTAL'].sum() if 'VALOR TOTAL' in data.columns else 0
                st.metric(
                    "Valor Total",
                    f"R$ {total_value:,.2f}",
                    help="Soma de todos os valores dos itens"
                )
            
            with col3:
                unique_suppliers = data['RAZÃO SOCIAL EMITENTE'].nunique() if 'RAZÃO SOCIAL EMITENTE' in data.columns else 0
                st.metric(
                    "Fornecedores",
                    f"{unique_suppliers:,}",
                    help="Número de fornecedores únicos"
                )
            
            with col4:
                unique_items = data['DESCRIÇÃO DO PRODUTO/SERVIÇO'].nunique() if 'DESCRIÇÃO DO PRODUTO/SERVIÇO' in data.columns else 0
                st.metric(
                    "Itens Únicos",
                    f"{unique_items:,}",
                    help="Tipos diferentes de produtos/serviços"
                )
            
            # Gráficos de overview se as colunas existirem
            col1, col2 = st.columns(2)
            
            with col1:
                if 'RAZÃO SOCIAL EMITENTE' in data.columns and 'VALOR TOTAL' in data.columns:
                    st.subheader("Top 10 Fornecedores por Valor")
                    top_suppliers = data.groupby('RAZÃO SOCIAL EMITENTE')['VALOR TOTAL'].sum().sort_values(ascending=False).head(10)
                    
                    # Usar Plotly para gráfico
                    import plotly.express as px
                    fig = px.bar(
                        x=top_suppliers.values,
                        y=top_suppliers.index,
                        orientation='h',
                        title="Maiores Fornecedores",
                        labels={'x': 'Valor (R$)', 'y': 'Fornecedor'}
                    )
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Colunas necessárias não encontradas para gráfico de fornecedores")
            
            with col2:
                if 'UF EMITENTE' in data.columns and 'VALOR TOTAL' in data.columns:
                    st.subheader("Distribuição por UF")
                    uf_dist = data.groupby('UF EMITENTE')['VALOR TOTAL'].sum().sort_values(ascending=False)
                    
                    import plotly.express as px
                    fig = px.pie(
                        values=uf_dist.values,
                        names=uf_dist.index,
                        title="Participação por UF"
                    )
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Colunas necessárias não encontradas para gráfico de UF")
            
            # Tabela de amostra dos dados
            st.subheader("📋 Amostra dos Dados")
            st.dataframe(data.head(100), use_container_width=True)
            
            # Informações sobre colunas
            with st.expander("🔍 Informações das Colunas"):
                col_info = []
                for col in data.columns:
                    col_info.append({
                        'Coluna': col,
                        'Tipo': str(data[col].dtype),
                        'Não Nulos': f"{data[col].notna().sum():,}",
                        'Nulos': f"{data[col].isna().sum():,}",
                        'Únicos': f"{data[col].nunique():,}"
                    })
                
                st.dataframe(pd.DataFrame(col_info), use_container_width=True)
                
        except Exception as e:
            st.error(f"Erro ao gerar visão geral: {str(e)}")
            st.dataframe(data.head(), use_container_width=True)
    
    def render_chat_interface(self):
        """Renderiza interface de chat com agentes"""
        if not st.session_state.data_loaded or st.session_state.merged_data is None:
            st.info("Carregue os dados primeiro para fazer perguntas.")
            return
        
        st.header("💬 Análise Inteligente")
        st.markdown("Faça perguntas sobre os dados em linguagem natural:")
        
        # Exemplos de perguntas
        with st.expander("💡 Exemplos de Perguntas"):
            st.markdown("""
            - Qual fornecedor teve maior montante recebido?
            - Quantas notas fiscais foram emitidas em janeiro de 2024?
            - Quais os três itens mais comprados por valor total?
            - Mostre a distribuição de notas por UF
            - Compare o volume de compras entre diferentes CFOPs
            - Qual o valor médio das notas fiscais?
            - Quem são os top 5 fornecedores?
            - Qual produto teve maior volume vendido?
            """)
        
        # Histórico do chat
        for i, message in enumerate(st.session_state.chat_history):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if "chart" in message and message["chart"] is not None:
                    st.plotly_chart(message["chart"], use_container_width=True)
                if "table" in message and message["table"] is not None:
                    st.dataframe(message["table"], use_container_width=True)
        
        # Chat input
        user_question = st.chat_input("Digite sua pergunta sobre os dados...")
        
        # Processar nova pergunta
        if user_question:
            # Adicionar pergunta do usuário ao histórico
            st.session_state.chat_history.append({
                "role": "user",
                "content": user_question
            })
            
            with st.chat_message("user"):
                st.markdown(user_question)
            
            # Processar através do crew
            with st.chat_message("assistant"):
                with st.spinner("Analisando..."):
                    try:
                        crew = st.session_state.crew
                        if crew is None:
                            st.error("Sistema não inicializado. Tente recarregar os dados.")
                            return

                        response = crew.analyze_query(user_question, st.session_state.merged_data, limit=None)

                        
                        # Exibir resposta
                        response_text = response.get("text", "Desculpe, não consegui processar sua pergunta.")
                        st.markdown(response_text)
                        
                        # Exibir gráfico se disponível
                        chart = response.get("chart")
                        if chart is not None:
                            st.plotly_chart(chart, use_container_width=True)
                        
                        # Exibir tabela se disponível
                        table = response.get("table")
                        if table is not None:
                            st.dataframe(table, use_container_width=True)
                        
                        # Adicionar resposta ao histórico
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": response_text,
                            "chart": chart,
                            "table": table
                        })
                        
                    except Exception as e:
                        error_msg = f"Erro ao processar pergunta: {str(e)}"
                        st.error(error_msg)
                        
                        # Adicionar erro ao histórico
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": error_msg
                        })
    
    def run(self):
        """Executa a aplicação principal"""
        try:
            self.render_header()
            self.render_sidebar()
            
            if not st.session_state.data_loaded:
                self.render_upload_section()
            else:
                # Tabs principais
                tab1, tab2 = st.tabs(["📊 Visão Geral", "💬 Análise Inteligente"])
                
                with tab1:
                    self.render_data_overview()
                
                with tab2:
                    self.render_chat_interface()
                    
        except Exception as e:
            st.error(f"Erro na aplicação: {str(e)}")
            import traceback
            st.error(f"Detalhes: {traceback.format_exc()}")

# Ponto de entrada da aplicação
if __name__ == "__main__":
    # Verificar dependências básicas
    try:
        app = NotaFiscalApp()
        app.run()
    except Exception as e:
        st.error(f"Erro ao inicializar aplicação: {str(e)}")
        st.info("Verifique se todas as dependências estão instaladas e configuradas corretamente.")