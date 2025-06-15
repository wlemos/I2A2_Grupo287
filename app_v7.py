# -*- coding: utf-8 -*-
"""
Analisador de Notas Fiscais com CrewAI, Groq e Streamlit
Versão corrigida e otimizada
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import zipfile
import io
import traceback
import re
import json

from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from langchain_community.chat_models.litellm import ChatLiteLLM
from dotenv import load_dotenv

load_dotenv()

llm = ChatLiteLLM(
    model="gemini/gemini-1.5-flash-latest",
    api_key=os.environ.get("GOOGLE_API_KEY"),
    temperature=0.0
)

# Funções de formatação
def format_currency(value):
    """Formata valor como moeda brasileira."""
    try:
        if pd.isna(value) or value is None:
            return "R$ 0,00"
        if isinstance(value, str):
            # Remove caracteres não numéricos exceto vírgula e ponto
            value = re.sub(r'[^\d.,]', '', value)
            value = value.replace(',', '.')
            value = float(value)
        return f"R$ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except Exception as e:
        return f"R$ {value}"

def format_number(value):
    """Formata número com separadores."""
    try:
        if pd.isna(value) or value is None:
            return "0"
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        return f"{value:,}".replace(',', '.')
    except Exception as e:
        return str(value)

def clean_ansi_codes(text):
    """Remove códigos ANSI."""
    if not isinstance(text, str):
        return str(text)
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

class PythonCodeExecutorTool(BaseTool):
    """Ferramenta para executar código Python."""
    name: str = "Python Code Executor"
    description: str = "Executa código Python para análise de dados com Pandas."
    df: pd.DataFrame = None

    def _run(self, code: str) -> dict:
        if self.df is None:
            return {"error": "DataFrame não fornecido."}

        local_namespace = {
            'df': self.df, 
            'pd': pd, 
            'px': px, 
            'go': go,
            'result_df': None, 
            'fig': None,
            'format_currency': format_currency,
            'format_number': format_number
        }
        
        output_capture = io.StringIO()
        import sys
        original_stdout = sys.stdout
        sys.stdout = output_capture
        
        try:
            # Executa o código no namespace local
            exec(code, {}, local_namespace)
            
            text_output = output_capture.getvalue()
            result_df = local_namespace.get('result_df')
            fig = local_namespace.get('fig')

            table_output = None
            if isinstance(result_df, pd.DataFrame) and not result_df.empty:
                table_output = result_df.to_dict('records')

            return {
                "success": True,
                "text_output": text_output,
                "table": table_output,
                "figure": fig
            }
        except Exception as e:
            error_msg = f"Erro na execução: {str(e)}\nTraceback: {traceback.format_exc()}"
            return {
                "error": error_msg,
                "text_output": f"❌ Erro durante análise: {str(e)}"
            }
        finally:
            sys.stdout = original_stdout

# Definição dos agentes
interpreter_agent = Agent(
    role="Analista de Dados",
    goal="Converter perguntas em código Python usando apenas pandas e plotly.",
    backstory="""Especialista em análises financeiras. Use apenas pandas para dados e plotly para gráficos. 
    NUNCA use matplotlib, seaborn ou outros módulos de visualização.
    SEMPRE defina variáveis antes de usá-las.""",
    llm=llm,
    verbose=False,
    allow_delegation=False
)

analysis_agent = Agent(
    role="Executor de Análises",
    goal="Executar código e apresentar resultados.",
    backstory="Especialista em execução de análises de dados.",
    llm=llm,
    verbose=False,
    allow_delegation=False
)

@st.cache_data
def create_dummy_zip():
    """Cria arquivo ZIP de exemplo."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        notas_data = {
            'numero_nota': [1001, 1002, 1003, 1004, 1005],
            'data_emissao': ['2024-01-10', '2024-01-15', '2024-01-18', '2024-01-20', '2024-02-05'],
            'fornecedor': ['Fornecedor A Ltda', 'Fornecedor B S.A.', 'Fornecedor A Ltda', 'Fornecedor C EIRELI', 'Fornecedor B S.A.'],
            'valor_total': [1500.50, 850.00, 320.75, 5000.00, 1200.00]
        }
        zf.writestr('notas_fiscais.csv', pd.DataFrame(notas_data).to_csv(index=False))
        
        itens_data = {
            'numero_nota': [1001, 1001, 1002, 1003, 1004, 1004, 1005],
            'descricao_item': ['Laptop Dell', 'Mouse Óptico', 'Teclado Mecânico', 'Cabo HDMI 2m', 'Consultoria Especializada', 'Licença Software', 'Monitor 24 polegadas'],
            'quantidade': [2, 5, 3, 10, 1, 1, 2],
            'valor_unitario': [750.25, 50.10, 283.33, 32.08, 5000.00, 1.00, 600.00]
        }
        zf.writestr('itens_nota.csv', pd.DataFrame(itens_data).to_csv(index=False))
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def process_zip_file(uploaded_file):
    """Processa arquivo ZIP."""
    try:
        with zipfile.ZipFile(uploaded_file) as z:
            csv_files = [f for f in z.namelist() if f.endswith('.csv')]
            
            if len(csv_files) < 2:
                st.error(f"Arquivos encontrados: {z.namelist()}. Necessário pelo menos 2 arquivos CSV.")
                return None

            # Lê o primeiro CSV como notas
            with z.open(csv_files[0]) as file:
                df_notas = pd.read_csv(file)
            
            # Lê o segundo CSV como itens
            with z.open(csv_files[1]) as file:
                df_itens = pd.read_csv(file)

            st.info(f"Colunas encontradas:")
            st.info(f"Arquivo 1 ({csv_files[0]}): {list(df_notas.columns)}")
            st.info(f"Arquivo 2 ({csv_files[1]}): {list(df_itens.columns)}")

            # Mapeia colunas automaticamente
            df_notas = map_columns(df_notas, 'notas')
            df_itens = map_columns(df_itens, 'itens')

            # Tenta fazer merge com diferentes estratégias
            merge_key = find_merge_key(df_notas, df_itens)
            
            if merge_key:
                df_merged = pd.merge(df_notas, df_itens, on=merge_key, how='inner')
                st.success(f"Merge realizado usando a coluna: {merge_key}")
            else:
                # Se não conseguir merge, concatena os DataFrames
                df_merged = pd.concat([df_notas, df_itens], ignore_index=True, sort=False)
                st.warning("Não foi possível fazer merge. Dados concatenados.")
            
            # Calcula valores derivados
            calculate_derived_values(df_merged)
            
            return df_merged
            
    except Exception as e:
        st.error(f"Erro ao processar arquivo: {e}")
        return None

def map_columns(df, tipo):
    """Mapeia colunas para nomes padrão."""
    mappings = {
        'notas': {
            'numero_nota': ['numero', 'numero_nota', 'nf', 'nota', 'number'],
            'data_emissao': ['data', 'data_emissao', 'date', 'emissao'],
            'fornecedor': ['fornecedor', 'razao_social', 'empresa', 'supplier'],
            'valor_total': ['valor', 'valor_total', 'total', 'value']
        },
        'itens': {
            'numero_nota': ['numero', 'numero_nota', 'nf', 'nota', 'number'],
            'descricao_item': ['descricao', 'item', 'produto', 'description'],
            'quantidade': ['quantidade', 'qtd', 'qty', 'quantity'],
            'valor_unitario': ['valor_unitario', 'preco', 'price', 'unit_price']
        }
    }
    
    df_mapped = df.copy()
    original_columns = [col.lower().strip() for col in df.columns]
    
    for standard_name, variations in mappings[tipo].items():
        for variation in variations:
            if variation.lower() in original_columns:
                original_col = df.columns[original_columns.index(variation.lower())]
                df_mapped.rename(columns={original_col: standard_name}, inplace=True)
                break
    
    return df_mapped

def find_merge_key(df1, df2):
    """Encontra chave comum para merge."""
    common_cols = set(df1.columns) & set(df2.columns)
    
    # Prioridade de colunas para merge
    priority = ['numero_nota', 'numero', 'nf', 'nota', 'id']
    
    for col in priority:
        if col in common_cols:
            return col
    
    # Se não encontrar, retorna a primeira coluna comum
    return list(common_cols)[0] if common_cols else None

def calculate_derived_values(df):
    """Calcula valores derivados."""
    try:
        # Valor do item
        if 'quantidade' in df.columns and 'valor_unitario' in df.columns:
            df['valor_item'] = pd.to_numeric(df['quantidade'], errors='coerce') * pd.to_numeric(df['valor_unitario'], errors='coerce')
        
        # Converte datas
        date_columns = [col for col in df.columns if 'data' in col.lower()]
        for col in date_columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
            
        # Converte valores numéricos
        numeric_columns = [col for col in df.columns if 'valor' in col.lower() or 'quantidade' in col.lower()]
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    except Exception as e:
        st.warning(f"Erro ao calcular valores derivados: {e}")

def extract_result_from_output(output):
    """Extrai resultado da execução."""
    try:
        if isinstance(output, dict):
            return output
        
        # Se é string, tenta extrair JSON
        if isinstance(output, str):
            try:
                return json.loads(output)
            except:
                return {"text_output": output, "table": None, "figure": None}
        
        # Se tem atributo raw
        if hasattr(output, 'raw'):
            return extract_result_from_output(output.raw)
            
        # Caso padrão
        return {"text_output": str(output), "table": None, "figure": None}
        
    except Exception as e:
        return {"error": f"Erro ao processar resultado: {str(e)}"}

def validate_code_syntax(code):
    """Valida sintaxe do código Python."""
    try:
        compile(code, '<string>', 'exec')
        return True, None
    except SyntaxError as e:
        return False, f"Erro de sintaxe: {e}"
    except Exception as e:
        return False, f"Erro na validação: {e}"

# Interface Streamlit
st.set_page_config(page_title="Analisador de Notas Fiscais", layout="wide", page_icon="📊")
st.title("📊 Analisador de Notas Fiscais")

# Inicialização do estado
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'df_analysis' not in st.session_state:
    st.session_state.df_analysis = None

# Sidebar
with st.sidebar:
    st.header("📁 Dados")
    
    uploaded_file = st.file_uploader("Arquivo .zip", type="zip")
    
    if st.button("🎯 Usar Exemplo"):
        uploaded_file = io.BytesIO(create_dummy_zip())
        st.success("Dados de exemplo carregados!")

    if uploaded_file and st.session_state.df_analysis is None:
        with st.spinner("Processando..."):
            df = process_zip_file(uploaded_file)
            if df is not None:
                st.session_state.df_analysis = df
                st.success("Dados processados!")

    if st.session_state.df_analysis is not None:
        st.subheader("📊 Resumo")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Registros", format_number(len(st.session_state.df_analysis)))
        with col2:
            if 'valor_total' in st.session_state.df_analysis.columns:
                total = st.session_state.df_analysis['valor_total'].sum()
                st.metric("Valor Total", format_currency(total))
            elif 'valor_item' in st.session_state.df_analysis.columns:
                total = st.session_state.df_analysis['valor_item'].sum()
                st.metric("Valor Total", format_currency(total))

        # Mostra preview dos dados
        if st.checkbox("👀 Visualizar dados"):
            st.dataframe(st.session_state.df_analysis.head(), use_container_width=True)
            st.info(f"Colunas disponíveis: {', '.join(st.session_state.df_analysis.columns)}")

# Interface principal
if st.session_state.df_analysis is None:
    st.info("Carregue um arquivo .zip ou use dados de exemplo.")
    st.markdown("""
    **Exemplos de perguntas:**
    - Qual fornecedor recebeu mais dinheiro?
    - Quais os 5 itens mais vendidos?
    - Mostre gráfico dos valores por mês
    - Qual valor médio das notas fiscais?
    """)
else:
    # Histórico
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                if message.get("content"):
                    st.markdown(message["content"])
                if message.get("table"):
                    st.dataframe(pd.DataFrame(message["table"]), use_container_width=True)
                if message.get("figure"):
                    st.plotly_chart(message["figure"], use_container_width=True)
            else:
                st.markdown(message["content"])

    # Input do usuário
    if prompt := st.chat_input("Digite sua pergunta..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analisando..."):
                try:
                    code_executor_tool = PythonCodeExecutorTool(df=st.session_state.df_analysis)

                    # Prepara informações sobre as colunas disponíveis
                    columns_info = []
                    for col in st.session_state.df_analysis.columns:
                        sample_values = st.session_state.df_analysis[col].dropna().head(3).tolist()
                        columns_info.append(f"- {col}: {sample_values}")
                    
                    columns_description = "\n".join(columns_info)

                    task_interpret = Task(
                        description=f"""
                        Crie script Python VÁLIDO e COMPLETO para: "{prompt}"
                        
                        REGRAS CRÍTICAS:
                        1. Use apenas o DataFrame 'df' disponível
                        2. Use apenas: pandas (pd), plotly.express (px), plotly.graph_objects (go)
                        3. NÃO use matplotlib, seaborn ou outros módulos de visualização
                        4. Para gráficos use APENAS Plotly: px.bar(), px.pie(), px.line(), px.scatter()
                        5. SEMPRE defina 'result_df' (DataFrame ou None) e 'fig' (figura Plotly ou None)
                        6. Use print() com format_currency() para valores monetários
                        7. Use print() com format_number() para números grandes
                        8. VALIDAÇÃO: Certifique-se que todas as variáveis estão definidas antes do uso
                        9. NUNCA use variáveis não definidas como 'row' fora de loops
                        
                        TEMPLATE OBRIGATÓRIO:
                        ```python
                        # Inicialização obrigatória
                        result_df = None
                        fig = None
                        
                        try:
                            # Sua análise aqui
                            # ... código da análise ...
                            
                            # Definir result_df e fig se necessário
                            # result_df = ...
                            # fig = px.bar(...)
                            
                            # Prints informativos
                            print("Análise concluída com sucesso")
                            
                        except Exception as e:
                            print(f"Erro na análise: {{e}}")
                        ```
                        
                        COLUNAS E DADOS DISPONÍVEIS:
                        {columns_description}
                        
                        EXEMPLOS CORRETOS:
                        
                        Para análise de fornecedores:
                        ```python
                        result_df = None
                        fig = None
                        
                        try:
                            if 'fornecedor' in df.columns and 'valor_total' in df.columns:
                                result_df = df.groupby('fornecedor')['valor_total'].sum().reset_index()
                                result_df = result_df.sort_values('valor_total', ascending=False)
                                fig = px.bar(result_df, x='fornecedor', y='valor_total', 
                                           title='Faturamento por Fornecedor')
                                print("Top fornecedores por faturamento:")
                                for index, row in result_df.head().iterrows():
                                    print(f"{{row['fornecedor']}}: {{format_currency(row['valor_total'])}}")
                            else:
                                print("Colunas necessárias não encontradas")
                        except Exception as e:
                            print(f"Erro: {{e}}")
                        ```
                        
                        Para análise de itens:
                        ```python
                        result_df = None
                        fig = None
                        
                        try:
                            if 'descricao_item' in df.columns and 'quantidade' in df.columns:
                                result_df = df.groupby('descricao_item')['quantidade'].sum().reset_index()
                                result_df = result_df.sort_values('quantidade', ascending=False)
                                fig = px.bar(result_df.head(10), x='descricao_item', y='quantidade', 
                                           title='Top 10 Itens Mais Vendidos')
                                print("Top 10 itens mais vendidos:")
                                for index, row in result_df.head(10).iterrows():
                                    print(f"{{row['descricao_item']}}: {{format_number(row['quantidade'])}} unidades")
                            else:
                                print("Colunas necessárias não encontradas")
                        except Exception as e:
                            print(f"Erro: {{e}}")
                        ```
                        
                        Pergunta do usuário: "{prompt}"
                        """,
                        agent=interpreter_agent,
                        expected_output="Código Python válido e completo usando apenas pandas e plotly"
                    )

                    task_execute = Task(
                        description="Execute o código Python gerado usando a ferramenta Python Code Executor.",
                        agent=analysis_agent,
                        context=[task_interpret],
                        tools=[code_executor_tool],
                        expected_output="Resultado da análise com dados, gráficos ou texto"
                    )

                    crew = Crew(
                        agents=[interpreter_agent, analysis_agent],
                        tasks=[task_interpret, task_execute],
                        process=Process.sequential,
                        verbose=False
                    )
                    
                    # Executa o crew
                    crew_result = crew.kickoff()
                    result = extract_result_from_output(task_execute.output)
                    
                    # Processa o resultado
                    if "error" in result:
                        st.error(f"❌ {result['error']}")
                        content = f"❌ Erro: {result['error']}"
                        table_data = None
                        figure_data = None
                    else:
                        text_output = clean_ansi_codes(result.get('text_output', ''))
                        table_data = result.get('table')
                        figure_data = result.get('figure')
                        
                        content = text_output if text_output.strip() else "Análise concluída."
                        
                        # Exibe os resultados
                        if content:
                            st.markdown(content)
                        
                        if table_data:
                            st.dataframe(pd.DataFrame(table_data), use_container_width=True)
                        
                        if figure_data:
                            st.plotly_chart(figure_data, use_container_width=True)

                    # Salva no histórico
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": content,
                        "table": table_data,
                        "figure": figure_data
                    })

                except Exception as e:
                    error_msg = f"❌ Erro na execução: {str(e)}"
                    st.error(error_msg)
                    
                    # Debug info
                    with st.expander("Detalhes do erro"):
                        st.code(traceback.format_exc())
                    
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": error_msg
                    })