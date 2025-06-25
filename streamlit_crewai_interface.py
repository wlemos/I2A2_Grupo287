import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import tempfile
import zipfile
from sistema_analise_dados_crewai import SistemaAnaliseBaseDados, BaseDataProcessor
from dotenv import load_dotenv

# Carregar variáveis explicitamente no início
load_dotenv(override=True)

# Adicionar à sessão do Streamlit
if "GEMINI_API_KEY" not in st.session_state:
    st.session_state["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY", "").strip().replace('"', '')

# Configuração da página
st.set_page_config(
    page_title="Sistema de Análise de Notas Fiscais - CrewAI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stAlert {
        margin-top: 1rem;
    }
    .upload-section {
        border: 2px dashed #1f77b4;
        border-radius: 10px;
        padding: 20px;
        margin: 20px 0;
        background-color: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

def main():
    st.markdown('<h1 class="main-header">📊 Sistema de Análise de Notas Fiscais com CrewAI</h1>', unsafe_allow_html=True)
    
    # Inicializar estado da sessão
    if 'sistema' not in st.session_state:
        st.session_state.sistema = None
    if 'df' not in st.session_state:
        st.session_state.df = None
    if 'metadados' not in st.session_state:
        st.session_state.metadados = None
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'file_processed' not in st.session_state:
        st.session_state.file_processed = False
    
    # Sidebar para upload
    with st.sidebar:
        st.header("📁 Upload de Arquivos")
        
        # MODIFICADO: Aceitar tanto CSV quanto ZIP
        uploaded_file = st.file_uploader(
            "Escolha um arquivo:",
            type=['csv', 'zip'],
            help="Aceita arquivos CSV individuais ou ZIP contendo aaaamm_NFs_Cabecalho.csv e aaaamm_NFs_Itens.csv"
        )
        
        if uploaded_file is not None:
            # NOVO: Mostrar informações do arquivo
            file_type = "ZIP" if uploaded_file.name.endswith('.zip') else "CSV"
            st.info(f"📄 Arquivo detectado: {file_type}")
            st.write(f"**Nome:** {uploaded_file.name}")
            st.write(f"**Tamanho:** {uploaded_file.size:,} bytes")
            
            # MODIFICADO: Validação específica para ZIP
            if file_type == "ZIP":
                st.warning("⚠️ Para arquivos ZIP, certifique-se de que contêm exatamente dois arquivos CSV com os nomes padrão de Notas Fiscais.")
            
            if st.button("🚀 Processar e Inicializar", type="primary"):
                with st.spinner("Processando arquivo..."):
                    try:
                        # Salvar arquivo temporariamente
                        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_type.lower()}") as tmp_file:
                            tmp_file.write(uploaded_file.getbuffer())
                            tmp_file_path = tmp_file.name
                        
                        # NOVO: Validação específica para ZIP
                        if file_type == "ZIP":
                            if not validate_nf_zip(tmp_file_path):
                                st.error("❌ Arquivo ZIP inválido. Deve conter exatamente dois arquivos CSV com padrão de Notas Fiscais.")
                                os.unlink(tmp_file_path)
                                return
                        
                        # Inicializar sistema
                        sistema = SistemaAnaliseBaseDados()
                        
                        # Processar dados
                        df = BaseDataProcessor.get_processed_dataframe(tmp_file_path)
                        metadados = sistema.gerar_metadados(tmp_file_path)
                        
                        # Armazenar no estado da sessão
                        st.session_state.sistema = sistema
                        st.session_state.df = df
                        st.session_state.metadados = metadados
                        st.session_state.file_processed = True
                        st.session_state.file_path = tmp_file_path
                        
                        # NOVO: Informações específicas do tipo de processamento
                        if hasattr(df, 'attrs') and df.attrs.get('tipo_processamento') == 'ZIP_NFs':
                            st.success("✅ Arquivo ZIP de Notas Fiscais processado com sucesso!")
                            st.info(f"📊 Dados mesclados: {len(df)} registros de {df.attrs.get('arquivo_cabecalho')} + {df.attrs.get('arquivo_itens')}")
                        else:
                            st.success("✅ Arquivo CSV processado com sucesso!")
                        
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Erro ao processar arquivo: {str(e)}")
                        if 'tmp_file_path' in locals():
                            try:
                                os.unlink(tmp_file_path)
                            except:
                                pass
    
    # Conteúdo principal
    if st.session_state.file_processed:
        # Tabs principais
        tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "💬 Chat com Agentes", "📋 Metadados"])
        
        with tab1:
            show_dashboard()
        
        with tab2:
            show_chat_interface()
        
        with tab3:
            show_metadata()
    
    else:
        st.info("👆 Faça upload de um arquivo CSV ou ZIP de Notas Fiscais para começar a análise.")
        
        # Informações sobre tipos de arquivo suportados
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            ### 📄 Arquivo CSV Individual
            - Qualquer arquivo CSV válido
            - Será analisado diretamente pelos agentes
            - Suporte a diferentes encodings
            """)
        
        with col2:
            st.markdown("""
            ### 📦 Arquivo ZIP de Notas Fiscais
            - Deve conter exatamente 2 arquivos CSV:
              - `aaaamm_NFs_Cabecalho.csv`
              - `aaaamm_NFs_Itens.csv`
            - Os arquivos serão mesclados automaticamente
            - Baseado na coluna "CHAVE DE ACESSO"
            """)

def validate_nf_zip(zip_path: str) -> bool:
    """NOVA FUNÇÃO: Validar se o ZIP contém os arquivos corretos de NF"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            files = zip_ref.namelist()
            
            cabecalho_found = any(f.endswith('_NFs_Cabecalho.csv') for f in files)
            itens_found = any(f.endswith('_NFs_Itens.csv') for f in files)
            
            return cabecalho_found and itens_found and len(files) == 2
    except:
        return False

def show_dashboard():
    """Dashboard com visualizações dos dados"""
    df = st.session_state.df
    
    if df is None:
        st.warning("Nenhum dado carregado.")
        return
    
    st.header("📊 Dashboard dos Dados")
    
    # NOVO: Informações específicas sobre tipo de processamento
    if hasattr(df, 'attrs') and df.attrs.get('tipo_processamento') == 'ZIP_NFs':
        st.info(f"📦 Dados processados de ZIP de Notas Fiscais - Merge realizado pela coluna: {df.attrs.get('coluna_merge')}")
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📄 Total de Registros", f"{len(df):,}")
    
    with col2:
        st.metric("📋 Colunas", len(df.columns))
    
    with col3:
        # Tentar calcular valor total se existir coluna de valor
        valor_cols = [col for col in df.columns if 'VALOR' in col.upper() and 'NOTA' in col.upper()]
        if valor_cols:
            valor_col = valor_cols[0]
            df_temp = df.copy()
            df_temp[valor_col] = pd.to_numeric(df_temp[valor_col], errors='coerce')
            total_valor = df_temp[valor_col].sum()
            st.metric("💰 Valor Total", f"R$ {total_valor:,.2f}")
        else:
            st.metric("💰 Valor Total", "N/A")
    
    with col4:
        st.metric("🗓️ Período de Dados", get_date_range(df))
    
    # Visualizações
    st.subheader("📈 Visualizações")
    
    # Distribuição por UF (se existir)
    uf_cols = [col for col in df.columns if 'UF' in col.upper()]
    if uf_cols:
        show_uf_distribution(df, uf_cols[0])
    
    # Evolução temporal (se existir coluna de data)
    date_cols = [col for col in df.columns if 'DATA' in col.upper()]
    if date_cols:
        show_temporal_evolution(df, date_cols[0])
    
    # Top fornecedores/destinatários
    show_top_entities(df)

def show_chat_interface():
    """Interface de chat com os agentes"""
    st.header("💬 Chat com Agentes CrewAI")
    
    if st.session_state.sistema is None:
        st.warning("Sistema não inicializado.")
        return
    
    # Área de chat
    chat_container = st.container()
    
    with chat_container:
        # Mostrar histórico
        for i, (pergunta, resposta) in enumerate(st.session_state.chat_history):
            with st.chat_message("user"):
                st.write(pergunta)
            with st.chat_message("assistant"):
                st.write(resposta)
    
    # Input para nova pergunta
    user_question = st.chat_input("Digite sua pergunta sobre os dados...")
    
    if user_question:
        # Adicionar pergunta ao chat
        with st.chat_message("user"):
            st.write(user_question)
        
        # Processar com agentes
        with st.chat_message("assistant"):
            with st.spinner("Agentes processando sua pergunta..."):
                try:
                    # CORREÇÃO: Método correto e ordem dos parâmetros
                    resposta = st.session_state.sistema.responder_pergunta(
                        st.session_state.file_path,
                        user_question
                    )
                    st.write(resposta)
                    
                    # Adicionar ao histórico
                    st.session_state.chat_history.append((user_question, resposta))
                    
                except Exception as e:
                    st.error(f"Erro ao processar pergunta: {str(e)}")

def show_metadata():
    """Mostrar metadados detalhados"""
    st.header("📋 Metadados dos Dados")
    
    if st.session_state.metadados is None:
        st.warning("Metadados não disponíveis.")
        return
    
    st.json(st.session_state.metadados)

def get_date_range(df):
    """Extrair período de datas dos dados"""
    date_cols = [col for col in df.columns if 'DATA' in col.upper()]
    if not date_cols:
        return "N/A"
    
    try:
        date_col = date_cols[0]
        df_temp = df.copy()
        df_temp[date_col] = pd.to_datetime(df_temp[date_col], errors='coerce')
        min_date = df_temp[date_col].min()
        max_date = df_temp[date_col].max()
        
        if pd.isna(min_date) or pd.isna(max_date):
            return "N/A"
        
        return f"{min_date.strftime('%m/%Y')} - {max_date.strftime('%m/%Y')}"
    except:
        return "N/A"

def show_uf_distribution(df, uf_col):
    """Mostrar distribuição por UF"""
    try:
        uf_counts = df[uf_col].value_counts().head(10)
        
        fig = px.bar(
            x=uf_counts.index,
            y=uf_counts.values,
            title=f"Distribuição por {uf_col}",
            labels={'x': uf_col, 'y': 'Quantidade'}
        )
        st.plotly_chart(fig, use_container_width=True)
    except:
        pass

def show_temporal_evolution(df, date_col):
    """Mostrar evolução temporal"""
    try:
        df_temp = df.copy()
        df_temp[date_col] = pd.to_datetime(df_temp[date_col], errors='coerce')
        df_temp = df_temp.dropna(subset=[date_col])
        
        daily_counts = df_temp.groupby(df_temp[date_col].dt.date).size()
        
        fig = px.line(
            x=daily_counts.index,
            y=daily_counts.values,
            title=f"Evolução Temporal ({date_col})",
            labels={'x': 'Data', 'y': 'Quantidade'}
        )
        st.plotly_chart(fig, use_container_width=True)
    except:
        pass

def show_top_entities(df):
    """Mostrar top entidades (fornecedores/destinatários)"""
    try:
        # Procurar colunas de entidades
        entity_cols = []
        for col in df.columns:
            if any(term in col.upper() for term in ['DESTINATARIO', 'EMITENTE', 'FORNECEDOR']):
                if 'NOME' in col.upper() or 'RAZAO' in col.upper():
                    entity_cols.append(col)
        
        if entity_cols:
            entity_col = entity_cols[0]
            top_entities = df[entity_col].value_counts().head(10)
            
            fig = px.bar(
                x=top_entities.values,
                y=top_entities.index,
                orientation='h',
                title=f"Top 10 - {entity_col}",
                labels={'x': 'Quantidade', 'y': entity_col}
            )
            st.plotly_chart(fig, use_container_width=True)
    except:
        pass

if __name__ == "__main__":
    main()
