# -*- coding: utf-8 -*-

# =========================================================================================
#  Analisador de Notas Fiscais com CrewAI, Groq e Streamlit
#
#  Autor: Seu Nome/Empresa (como Arquiteto de Soluções AI)
#  Data: 2024-05-21
#
#  Descrição:
#  Este script implementa uma solução completa para analisar dados de notas fiscais
#  contidas em arquivos CSV. A aplicação utiliza uma interface Streamlit para o upload
#  de um arquivo .zip e para a interação com o usuário via chat.
#
#  A lógica de análise é orquestrada pelo CrewAI, que gerencia dois agentes autônomos:
#  1.  QueryInterpreterAgent: Converte perguntas em linguagem natural para código Python (Pandas).
#  2.  DataAnalysisAndVizAgent: Executa o código gerado, analisa os resultados e prepara
#      uma resposta completa com texto, tabelas e gráficos.
#
#  O motor de LLM utilizado é o Groq, escolhido por sua alta velocidade de inferência,
#  proporcionando uma experiência de usuário fluida e em tempo real.
#
#  Como executar:
#  1. Crie um arquivo .env na raiz do projeto com sua GROQ_API_KEY.
#  2. Instale as dependências: pip install -r requirements.txt
#  3. Execute o comando no terminal: streamlit run app.py
# =========================================================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import os
import zipfile
import io
import traceback
from textwrap import dedent

# --- Bibliotecas de IA e Agentes ---
from crewai import Agent, Task, Crew, Process
# from crewai_tools import BaseTool  # <- LINHA ANTIGA E INCORRETA
from crewai.tools import BaseTool   # <- LINHA NOVA E CORRETA
from langchain_groq import ChatGroq
from dotenv import load_dotenv
# --- Carregar variáveis de ambiente (GROQ_API_KEY) ---
load_dotenv()

# --- Configuração do LLM (Groq) ---
# Usamos um modelo rápido como o LLaMA3 8B para respostas instantâneas.
# A temperatura 0.0 garante respostas mais determinísticas e factuais.
llm = ChatGroq(
    api_key=os.environ.get("GROQ_API_KEY"),
    model="llama3-8b-8192",
    temperature=0.0
)

# =========================================================================================
#  FERRAMENTAS CUSTOMIZADAS (CUSTOM TOOLS) PARA OS AGENTES
# =========================================================================================

class PythonCodeExecutorTool(BaseTool):
    name: str = "Python Code Executor"
    description: str = dedent("""
        Executa um bloco de código Python para análise de dados com Pandas.
        O código DEVE operar sobre um DataFrame chamado 'df'.
        O script deve:
        1.  Imprimir um resumo textual da análise usando a função print().
        2.  Atribuir o DataFrame resultante final a uma variável chamada 'result_df'.
        3.  Gerar um gráfico Plotly e atribuí-lo a uma variável chamada 'fig'.
            Se um gráfico não for aplicável, 'fig' deve ser None.
    """)
    # --- MUDANÇA 1: Adicionar o DataFrame como um atributo da classe ---
    df: pd.DataFrame = None

    # --- MUDANÇA 2: Remover o 'df' da assinatura do _run ---
    def _run(self, code: str) -> dict:
        """
        Executa o código em um ambiente controlado e captura os resultados.
        O DataFrame 'self.df' é usado na execução.
        """
        if self.df is None:
            return {"error": "DataFrame não foi fornecido para a ferramenta."}

        # --- MUDANÇA 3: Usar self.df em vez de um argumento ---
        local_namespace = {'df': self.df, 'pd': pd, 'px': px, 'result_df': None, 'fig': None}
        
        output_capture = io.StringIO()
        import sys
        original_stdout = sys.stdout
        sys.stdout = output_capture
        
        try:
            exec(code, {}, local_namespace)
            
            text_output = output_capture.getvalue()
            result_df = local_namespace.get('result_df')
            fig = local_namespace.get('fig')

            if isinstance(result_df, pd.DataFrame):
                table_output = result_df.to_dict('records')
            else:
                table_output = None

            return {
                "text_output": text_output,
                "table": table_output,
                "figure": fig
            }

        except Exception as e:
            error_message = f"Erro ao executar o código: {e}\nTraceback:\n{traceback.format_exc()}"
            return {"error": error_message, "text_output": error_message}
            
        finally:
            sys.stdout = original_stdout

# =========================================================================================
#  DEFINIÇÃO DOS AGENTES E DA CREW
# =========================================================================================

def create_analysis_crew(df_schema: str):
    """
    Cria e configura a equipe de agentes para análise de dados.
    """
    # --- Agentes são definidos aqui, sem a ferramenta ainda ---
    interpreter_agent = Agent(...) # Mantenha a definição do agente como estava
    analysis_agent = Agent(...) # Mantenha a definição do agente, mas remova a 'tools' por enquanto

    def create_crew_tasks(question, df_for_tool):
        
        # --- MUDANÇA 4: Instanciar a ferramenta AQUI, com o DataFrame ---
        code_executor_tool = PythonCodeExecutorTool(df=df_for_tool)
        
        # --- MUDANÇA 5: Adicionar a ferramenta dinamicamente ao agente ---
        analysis_agent.tools = [code_executor_tool]

        # Tarefa 1: Gerar o código Python
        task_interpret = Task(
            description=dedent(f"""..."""), # Mantenha a descrição como estava
            agent=interpreter_agent,
            expected_output="Um bloco de código Python puro, sem formatação ou comentários extras."
        )

        # Tarefa 2: Executar o código e obter os resultados
        task_execute = Task(
            description=dedent("""
                Use a ferramenta 'Python Code Executor' para executar o script Python gerado na tarefa anterior.
                Passe o código gerado como argumento para a ferramenta.
            """),
            agent=analysis_agent,
            context=[task_interpret],
            expected_output="Um dicionário Python contendo 'text_output', 'table' e 'figure' com os resultados da análise.",
            # --- MUDANÇA 6: REMOVER a linha tools_input ---
            # tools_input={'df': df_for_tool} # <<-- REMOVER ISTO
        )
        
        return [task_interpret, task_execute]

    # Ajuste final: Remova a ferramenta da definição inicial do agente
    analysis_agent.tools = []
    
    return Crew(
        agents=[interpreter_agent, analysis_agent],
        process=Process.sequential,
        verbose=2
    ), create_crew_tasks

# =========================================================================================
#  FUNÇÕES AUXILIARES PARA A INTERFACE STREAMLIT
# =========================================================================================

@st.cache_data
def create_dummy_zip():
    """Cria um arquivo .zip de exemplo em memória para demonstração."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Criando o notas_fiscais.csv
        notas_data = {
            'numero_nota': [1001, 1002, 1003, 1004, 1005],
            'data_emissao': ['2024-01-10 09:30:00', '2024-01-15 14:00:00', '2024-01-18 11:00:00', '2024-01-20 16:45:00', '2024-02-05 10:00:00'],
            'fornecedor': ['Fornecedor A', 'Fornecedor B', 'Fornecedor A', 'Fornecedor C', 'Fornecedor B'],
            'valor_total': [1500.50, 850.00, 320.75, 5000.00, 1200.00]
        }
        zf.writestr('notas_fiscais.csv', pd.DataFrame(notas_data).to_csv(index=False))

        # Criando o itens_nota.csv
        itens_data = {
            'numero_nota': [1001, 1001, 1002, 1003, 1004, 1004, 1005],
            'descricao_item': ['Laptop', 'Mouse', 'Teclado', 'Cabo HDMI', 'Serviço de Consultoria', 'Software Licença', 'Monitor'],
            'quantidade': [5, 10, 10, 15, 1, 1, 8],
            'valor_unitario': [250.00, 25.05, 85.00, 21.3833, 5000.00, 1, 150.00]
        }
        zf.writestr('itens_nota.csv', pd.DataFrame(itens_data).to_csv(index=False))
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def process_zip_file(uploaded_file):
    """
    Descompacta o arquivo .zip, lê os CSVs e os combina em um único DataFrame.
    Esta função representa a lógica dos Agentes de Ingestão e Combinação.
    """
    try:
        with zipfile.ZipFile(uploaded_file) as z:
            # Identificar e carregar os arquivos CSV
            if 'notas_fiscais.csv' not in z.namelist() or 'itens_nota.csv' not in z.namelist():
                st.error("O arquivo .zip deve conter 'notas_fiscais.csv' e 'itens_nota.csv'.")
                return None

            with z.open('notas_fiscais.csv') as nf_file:
                df_notas = pd.read_csv(nf_file, parse_dates=['data_emissao'])

            with z.open('itens_nota.csv') as in_file:
                df_itens = pd.read_csv(in_file)
            
            # Realizar o merge dos DataFrames
            df_merged = pd.merge(df_notas, df_itens, on='numero_nota')
            
            return df_merged
    except Exception as e:
        st.error(f"Ocorreu um erro ao processar o arquivo .zip: {e}")
        return None

# =========================================================================================
#  INTERFACE DO USUÁRIO (STREAMLIT)
# =========================================================================================

st.set_page_config(page_title="Analisador de Notas Fiscais com CrewAI", layout="wide")
st.title("🤖 Analisador de Notas Fiscais com Agentes Autônomos")
st.markdown("Faça perguntas em linguagem natural sobre seus dados de notas fiscais.")

# --- Inicialização do estado da sessão ---
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'df_analysis' not in st.session_state:
    st.session_state.df_analysis = None
if 'df_schema' not in st.session_state:
    st.session_state.df_schema = None

# --- Barra Lateral (Sidebar) para Upload ---
with st.sidebar:
    st.header("1. Carregue seus dados")
    uploaded_file = st.file_uploader(
        "Selecione o arquivo .zip com as notas fiscais",
        type="zip"
    )

    if st.button("Usar Dados de Exemplo"):
        # Usa os dados de exemplo em vez de um arquivo carregado
        dummy_zip_bytes = create_dummy_zip()
        uploaded_file = io.BytesIO(dummy_zip_bytes)
        st.success("Dados de exemplo carregados!")

    if uploaded_file is not None and st.session_state.df_analysis is None:
        with st.spinner("Processando e combinando arquivos..."):
            df = process_zip_file(uploaded_file)
            if df is not None:
                st.session_state.df_analysis = df
                # Gera o schema do DataFrame para passar ao agente
                schema_buffer = io.StringIO()
                df.info(buf=schema_buffer)
                st.session_state.df_schema = schema_buffer.getvalue()
                st.success("Arquivos processados com sucesso!")

    if st.session_state.df_analysis is not None:
        st.header("Dados Carregados")
        st.dataframe(st.session_state.df_analysis.head())
        st.info(f"{len(st.session_state.df_analysis)} linhas de dados combinados.")

# --- Área Principal de Chat ---
if st.session_state.df_analysis is None:
    st.info("Por favor, carregue um arquivo .zip ou use os dados de exemplo para começar.")
else:
    # Exibir histórico de mensagens
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "table" in message and message["table"] is not None:
                st.dataframe(pd.DataFrame(message["table"]))
            if "figure" in message and message["figure"] is not None:
                st.plotly_chart(message["figure"], use_container_width=True)

    # Campo de entrada para nova pergunta
    if prompt := st.chat_input("Qual sua pergunta? Ex: Qual fornecedor teve maior montante recebido?"):
        # Adicionar pergunta do usuário ao histórico e exibir
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Iniciar a análise com a CrewAI
        with st.chat_message("assistant"):
            with st.spinner("Analisando sua pergunta com a equipe de agentes..."):
                # Cria a crew e as tarefas dinamicamente com a pergunta atual
                analysis_crew, create_tasks_func = create_analysis_crew(st.session_state.df_schema)
                tasks = create_tasks_func(prompt, st.session_state.df_analysis)
                analysis_crew.tasks = tasks

                # Executa a crew
                result = analysis_crew.kickoff()
                
                # A resposta final está no output da última tarefa
                final_output = result
                
                # Tratamento do resultado
                if final_output and isinstance(final_output, dict) and "error" not in final_output:
                    response_text = final_output.get('text_output', "Não foi possível gerar um resumo textual.")
                    response_table = final_output.get('table')
                    response_figure = final_output.get('figure')

                    # Exibir a resposta
                    st.markdown(response_text)
                    if response_table:
                        st.dataframe(pd.DataFrame(response_table))
                    if response_figure:
                        st.plotly_chart(response_figure, use_container_width=True)
                    
                    # Adicionar resposta completa ao histórico
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response_text,
                        "table": response_table,
                        "figure": response_figure
                    })
                else:
                    error_msg = final_output.get('error', 'Ocorreu um erro desconhecido durante a análise.')
                    st.error(f"A equipe de agentes encontrou um problema:\n{error_msg}")
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": f"Desculpe, não consegui processar sua solicitação. Erro: {error_msg}"
                    })