# -*- coding: utf-8 -*-

# =========================================================================================
#  Analisador de Notas Fiscais com CrewAI, Groq e Streamlit
#
#  Autor: Arquiteto de Soluções AI
#  Data: 2024-05-21 (Versão Refatorada e Corrigida)
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
#  2. Crie um requirements.txt e instale as dependências: pip install -r requirements.txt
#  3. Execute o comando no terminal: streamlit run app.py
# =========================================================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import zipfile
import io
import traceback
from textwrap import dedent
import re
import json

# --- Bibliotecas de IA e Agentes ---
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
# from langchain_groq import ChatGroq
# from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_models.litellm import ChatLiteLLM
from dotenv import load_dotenv

# --- Carregar variáveis de ambiente (GROQ_API_KEY) ---
# Garanta que o arquivo .env está na mesma pasta que o app.py
load_dotenv()

# --- Configuração do LLM (A ABORDAGEM CORRETA E DEFINITIVA) ---
# Usamos o ChatLiteLLM, a integração direta da LangChain com o LiteLLM.
# Isso garante que o nome do modelo é passado sem modificações para a camada
# do LiteLLM, resolvendo o conflito de prefixos.
# O LiteLLM irá automaticamente pegar a GOOGLE_API_KEY do ambiente.
llm = ChatLiteLLM(
    model="gemini/gemini-1.5-flash-latest",
    api_key=os.environ.get("GOOGLE_API_KEY"),
    temperature=0.0
)

# =========================================================================================
#  FERRAMENTA CUSTOMIZADA (CUSTOM TOOL) PARA OS AGENTES
# =========================================================================================

class PythonCodeExecutorTool(BaseTool):
    """
    Uma ferramenta para executar código Python e retornar os resultados.
    Esta ferramenta é a mais robusta, recebendo o DataFrame em sua inicialização
    para evitar problemas de validação com o Pydantic.
    """
    name: str = "Python Code Executor"
    description: str = dedent("""
        Executa um bloco de código Python para análise de dados com Pandas.
        O código DEVE operar sobre um DataFrame que já está disponível na ferramenta.
        O script deve:
        1.  Imprimir um resumo textual da análise usando a função print().
        2.  Atribuir o DataFrame resultante final a uma variável chamada 'result_df'.
        3.  Gerar um gráfico Plotly e atribuí-lo a uma variável chamada 'fig'.
            Se um gráfico não for aplicável, 'fig' deve ser None.
    """)
    df: pd.DataFrame = None

    def _run(self, code: str) -> dict:
        """
        Executa o código em um ambiente controlado e captura os resultados.
        O DataFrame 'self.df' é usado na execução.
        """
        if self.df is None:
            return {"error": "DataFrame não foi fornecido para a ferramenta."}

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

            table_output = result_df.to_dict('records') if isinstance(result_df, pd.DataFrame) else None

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
#  DEFINIÇÃO DOS AGENTES
# =========================================================================================

# Agentes são definidos no escopo global para serem reutilizados.
# Suas configurações são estáveis e não precisam ser recriadas a cada pergunta.

interpreter_agent = Agent(
    role="Tradutor de Linguagem Natural para Código Python",
    goal="Converter perguntas de usuários em código Python (Pandas) executável e preciso para análise de dados.",
    backstory=dedent("""
        Você é um especialista em análise de dados que traduz requisições de negócio em linguagem natural
        para scripts Python precisos e eficientes usando a biblioteca Pandas. Você recebe uma pergunta
        e o schema do DataFrame e devolve apenas o código necessário para responder àquela pergunta.
    """),
    llm=llm,
    verbose=True,
    allow_delegation=False
)

analysis_agent = Agent(
    role="Analista de Dados Sênior e Especialista em Visualização",
    goal="Executar código Python de análise, interpretar os resultados e comunicá-los de forma clara.",
    backstory=dedent("""
        Você é um analista de dados experiente. Sua função é pegar um script Python,
        executá-lo de forma segura e interpretar os resultados. Você não escreve
        o código, apenas o executa e apresenta as conclusões,
        juntamente com tabelas e gráficos relevantes.
    """),
    llm=llm,
    verbose=True,
    allow_delegation=False
)

# =========================================================================================
#  FUNÇÕES AUXILIARES PARA A INTERFACE STREAMLIT
# =========================================================================================

@st.cache_data
def create_dummy_zip():
    """Cria um arquivo .zip de exemplo em memória para demonstração."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        notas_data = {
            'numero_nota': [1001, 1002, 1003, 1004, 1005],
            'data_emissao': ['2024-01-10 09:30:00', '2024-01-15 14:00:00', '2024-01-18 11:00:00', '2024-01-20 16:45:00', '2024-02-05 10:00:00'],
            'fornecedor': ['Fornecedor A', 'Fornecedor B', 'Fornecedor A', 'Fornecedor C', 'Fornecedor B'],
            'valor_total': [1500.50, 850.00, 320.75, 5000.00, 1200.00]
        }
        zf.writestr('notas_fiscais.csv', pd.DataFrame(notas_data).to_csv(index=False))
        itens_data = {
            'numero_nota': [1001, 1001, 1002, 1003, 1004, 1004, 1005],
            'descricao_item': ['Laptop', 'Mouse', 'Teclado', 'Cabo HDMI', 'Serviço de Consultoria', 'Software Licença', 'Monitor'],
            'quantidade': [5, 10, 10, 15, 1, 1, 8],
            'valor_unitario': [250.00, 25.05, 85.00, 21.3833, 5000.00, 1.00, 150.00]
        }
        zf.writestr('itens_nota.csv', pd.DataFrame(itens_data).to_csv(index=False))
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def process_zip_file(uploaded_file):
    """
    Descompacta o .zip, lê os CSVs, mapeia os nomes de colunas do TCU para nomes padrão,
    e os combina usando uma chave composta.
    """
    try:
        # Assumindo que o primeiro arquivo é o de notas e o segundo o de itens
        # Idealmente, os nomes dos arquivos seriam fixos como 'notas.csv' e 'itens.csv'
        # Por enquanto, vamos manter a premissa de 'notas_fiscais.csv' e 'itens_nota.csv'
        zip_file_name = "xxxxxxxxxx.zip" # Substitua pelo nome real se quiser
        notas_csv_name = 'notas_fiscais.csv' # Nome esperado dentro do zip
        itens_csv_name = 'itens_nota.csv' # Nome esperado dentro do zip

        with zipfile.ZipFile(uploaded_file) as z:
            if notas_csv_name not in z.namelist() or itens_csv_name not in z.namelist():
                st.error(f"O arquivo .zip deve conter '{notas_csv_name}' e '{itens_csv_name}'.")
                st.info(f"Arquivos encontrados no zip: {z.namelist()}")
                return None

            with z.open(notas_csv_name) as nf_file:
                df_notas = pd.read_csv(nf_file)
                st.info(f"Colunas originais em '{notas_csv_name}':")
                st.write(df_notas.columns.tolist())

            with z.open(itens_csv_name) as in_file:
                df_itens = pd.read_csv(in_file)
                st.info(f"Colunas originais em '{itens_csv_name}':")
                st.write(df_itens.columns.tolist())

            # --- MAPEAMENTO DE COLUNAS PARA PADRÃO INTERNO ---
            # Mapeia os nomes reais (em minúsculas) para os nomes que os agentes vão usar.
            notas_mapping = {
                'chave_acesso': ['chave de acesso'],
                'modelo': ['modelo'],
                'serie': ['série'],
                'numero_nota': ['número'],
                'natureza_operacao': ['natureza da operação'],
                'data_emissao': ['data emissão'],
                'fornecedor': ['razão social emitente'], # Usando o emitente como fornecedor
                'valor_total': ['valor nota fiscal']
            }

            itens_mapping = {
                'chave_acesso': ['chave de acesso'],
                'modelo': ['modelo'],
                'serie': ['série'],
                'numero_nota': ['número'],
                'descricao_item': ['descrição do produto/serviço'],
                'quantidade': ['quantidade'],
                'valor_unitario': ['valor unitário']
                # O 'valor total' do item será calculado, então não precisamos mapear
            }

            def rename_columns(df, mapping):
                renamed_cols = {}
                df_cols_lower = {col.lower(): col for col in df.columns}
                for standard_name, possible_names in mapping.items():
                    for p_name in possible_names:
                        if p_name in df_cols_lower:
                            renamed_cols[df_cols_lower[p_name]] = standard_name
                            break
                df.rename(columns=renamed_cols, inplace=True)
                return df

            df_notas = rename_columns(df_notas, notas_mapping)
            df_itens = rename_columns(df_itens, itens_mapping)
            
            # --- CHAVE DE MERGE COMPOSTA ---
            # As colunas que identificam unicamente uma nota fiscal
            merge_keys = ['chave_acesso', 'modelo', 'serie', 'numero_nota']

            # Seleciona apenas as colunas que vamos usar para evitar redundância
            cols_to_keep_notas = merge_keys + ['data_emissao', 'fornecedor', 'valor_total']
            df_notas_final = df_notas[[col for col in cols_to_keep_notas if col in df_notas.columns]]

            cols_to_keep_itens = merge_keys + ['descricao_item', 'quantidade', 'valor_unitario']
            df_itens_final = df_itens[[col for col in cols_to_keep_itens if col in df_itens.columns]]

            # Validação
            if not all(key in df_notas_final.columns for key in merge_keys) or \
               not all(key in df_itens_final.columns for key in merge_keys):
                st.error("As colunas da chave de merge não foram encontradas em ambos os arquivos após o mapeamento.")
                st.write("Chaves esperadas:", merge_keys)
                st.write("Colunas encontradas em Notas:", df_notas_final.columns.tolist())
                st.write("Colunas encontradas em Itens:", df_itens_final.columns.tolist())
                return None

            st.success("Colunas mapeadas e prontas para o merge:")
            st.write("Notas:", df_notas_final.columns.tolist())
            st.write("Itens:", df_itens_final.columns.tolist())

            # Conversão de tipos de dados antes do merge
            df_notas_final['data_emissao'] = pd.to_datetime(df_notas_final['data_emissao'], errors='coerce')
            
            # Converte colunas numéricas, tratando vírgulas como separador decimal
            for col in ['valor_total']:
                 if col in df_notas_final.columns:
                    df_notas_final[col] = df_notas_final[col].astype(str).str.replace(',', '.').astype(float)
            
            for col in ['quantidade', 'valor_unitario']:
                 if col in df_itens_final.columns:
                    df_itens_final[col] = df_itens_final[col].astype(str).str.replace(',', '.').astype(float)

            # --- MERGE FINAL USANDO A CHAVE COMPOSTA ---
            df_merged = pd.merge(df_notas_final, df_itens_final, on=merge_keys, how='inner')
            st.success("Merge dos arquivos realizado com sucesso usando a chave composta!")
            
            return df_merged
            
    except Exception as e:
        st.error(f"Ocorreu um erro crítico ao processar o arquivo .zip: {e}")
        traceback.print_exc()
        return None

def extract_result_from_output(output):
    """
    Extrai o resultado da execução do agente, tratando diferentes formatos de saída.
    """
    try:
        # Se o output já é um dicionário, usa diretamente
        if isinstance(output, dict):
            return output
        
        # Se é uma string, tenta fazer parse como JSON
        if isinstance(output, str):
            # Tenta encontrar um JSON válido na string
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                # Se não conseguir fazer parse do JSON, procura por padrões
                # Isso é um fallback para casos onde a string contém o resultado mas não é JSON puro
                return {"text_output": output, "table": None, "figure": None}
        
        # Se tem atributo raw, usa ele
        if hasattr(output, 'raw'):
            return extract_result_from_output(output.raw)
        
        # Se tem atributo result, usa ele
        if hasattr(output, 'result'):
            return extract_result_from_output(output.result)
        
        # Fallback: converte para string
        return {"text_output": str(output), "table": None, "figure": None}
        
    except Exception as e:
        return {"error": f"Erro ao processar resultado: {str(e)}"}

def convert_plotly_dict_to_figure(fig_dict):
    """
    Converte um dicionário Plotly em um objeto Figure válido.
    """
    try:
        if fig_dict is None:
            return None
        
        if isinstance(fig_dict, dict):
            # Importa plotly.graph_objects para criar a figura
            import plotly.graph_objects as go
            
            # Cria a figura a partir do dicionário
            fig = go.Figure(fig_dict)
            return fig
        else:
            # Se já é um objeto Figure, retorna como está
            return fig_dict
            
    except Exception as e:
        st.warning(f"Não foi possível converter o gráfico: {e}")
        return None

def clean_ansi_codes(text):
    """Função para remover códigos de cor ANSI do texto."""
    if not isinstance(text, str):
        return str(text)
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

# =========================================================================================
#  INTERFACE DO USUÁRIO (STREAMLIT)
# =========================================================================================

st.set_page_config(page_title="Analisador de Notas Fiscais com CrewAI", layout="wide")
st.title("🤖 Analisador de Notas Fiscais com Agentes Autônomos")
st.markdown("Faça perguntas em linguagem natural sobre seus dados de notas fiscais.")

if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'df_analysis' not in st.session_state:
    st.session_state.df_analysis = None
if 'df_schema' not in st.session_state:
    st.session_state.df_schema = None

with st.sidebar:
    st.header("1. Carregue seus dados")
    uploaded_file = st.file_uploader("Selecione o arquivo .zip", type="zip")
    if st.button("Usar Dados de Exemplo"):
        uploaded_file = io.BytesIO(create_dummy_zip())
        st.success("Dados de exemplo carregados!")

    if uploaded_file is not None and st.session_state.df_analysis is None:
        with st.spinner("Processando e combinando arquivos..."):
            df = process_zip_file(uploaded_file)
            if df is not None:
                st.session_state.df_analysis = df
                schema_buffer = io.StringIO()
                df.info(buf=schema_buffer)
                st.session_state.df_schema = schema_buffer.getvalue()
                st.success("Arquivos processados com sucesso!")

    if st.session_state.df_analysis is not None:
        st.header("Dados Carregados")
        st.dataframe(st.session_state.df_analysis.head())
        st.info(f"{len(st.session_state.df_analysis)} linhas de dados combinados.")

if st.session_state.df_analysis is None:
    st.info("Por favor, carregue um arquivo .zip ou use os dados de exemplo para começar.")
else:
    # Exibir histórico de mensagens
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                # Formatação especial para respostas do assistente
                if message["content"] and message["content"].strip():
                    st.markdown(f"**📊 Resultado da Análise:**")
                    st.markdown(message["content"])
                
                if "table" in message and message["table"] is not None:
                    try:
                        df_table = pd.DataFrame(message["table"])
                        if not df_table.empty:
                            st.markdown("**📋 Detalhamento dos Dados:**")
                            st.dataframe(df_table, use_container_width=True)
                    except:
                        pass
                
                if "figure" in message and message["figure"] is not None:
                    try:
                        st.markdown("**📈 Visualização:**")
                        st.plotly_chart(message["figure"], use_container_width=True)
                    except:
                        pass
            else:
                # Mensagens do usuário
                st.markdown(message["content"])

    # Campo de entrada para nova pergunta
    if prompt := st.chat_input("Qual sua pergunta? Ex: Qual o item mais vendido?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analisando sua pergunta com a equipe de agentes..."):
                try:
                    # 1. Instanciar a ferramenta com o DataFrame da sessão ATUAL
                    code_executor_tool = PythonCodeExecutorTool(df=st.session_state.df_analysis)

                    # 2. Criar as tarefas para a execução ATUAL
                    task_interpret = Task(
                        description=dedent(f"""
                            Sua tarefa é escrever um script Python para responder à pergunta de um usuário sobre dados de notas fiscais.

                            **REGRAS ABSOLUTAS:**
                            1.  Você deve usar um DataFrame que já existe na memória, chamado `df`.
                            2.  **NÃO** inclua `pd.read_csv()` ou qualquer outra função de leitura de arquivo no seu código.
                            3.  Seu script DEVE produzir as seguintes variáveis como resultado:
                                - `result_df`: um DataFrame pandas com os dados da resposta.
                                - `fig`: uma figura do Plotly Express (use `px.bar`, `px.pie`, etc.). Se nenhum gráfico for aplicável, use `fig = None`.
                                - Use `print()` para escrever um resumo textual da sua descoberta.
                            4.  O seu output final deve ser **APENAS O CÓDIGO PYTHON**. Não inclua a palavra "python" no início, nem ` ``` `, nem qualquer explicação.

                            **SCHEMA DO DATAFRAME `df` DISPONÍVEL:**
                            ```
                            {st.session_state.df_schema}
                            ```

                            **PERGUNTA DO USUÁRIO:**
                            "{prompt}"

                            Agora, escreva o código Python completo e válido para responder a esta pergunta.
                        """),
                        agent=interpreter_agent,
                        expected_output="Um bloco de código Python puro, completo e sintaticamente correto."
                    )

                    task_execute = Task(
                        description="Use a ferramenta 'Python Code Executor' para executar o script Python da tarefa anterior.",
                        agent=analysis_agent,
                        context=[task_interpret],
                        tools=[code_executor_tool],
                        expected_output="Um dicionário Python com as chaves 'text_output', 'table' e 'figure'."
                    )

                    # 3. Criar e executar a Crew
                    analysis_crew = Crew(
                        agents=[interpreter_agent, analysis_agent],
                        tasks=[task_interpret, task_execute],
                        process=Process.sequential,
                        verbose=True
                    )
                    
                    # A execução popula o atributo 'output' das tarefas
                    crew_result = analysis_crew.kickoff()

                    # 4. Tratamento e exibição do resultado (VERSÃO CORRIGIDA)
                    # Usa a função helper para extrair o resultado
                    final_output = extract_result_from_output(task_execute.output)
                    
                    # Verifica se há erro explícito
                    if isinstance(final_output, dict) and "error" in final_output:
                        # Há um erro explícito
                        error_msg = final_output["error"]
                        st.error(f"Erro na execução: {error_msg}")
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": f"Desculpe, ocorreu um erro: {error_msg}"
                        })
                    else:
                        # Tenta processar como resultado válido
                        try:
                            # Extrai os componentes do resultado
                            response_text = clean_ansi_codes(final_output.get('text_output', "Análise concluída."))
                            response_table = final_output.get('table')
                            response_figure_dict = final_output.get('figure')
                            
                            # Converte o dicionário do gráfico em um objeto Figure
                            response_figure = convert_plotly_dict_to_figure(response_figure_dict)

                            # Exibe o texto de forma mais elegante
                            if response_text and response_text.strip():
                                # Remove linhas vazias e formata melhor
                                clean_text = response_text.strip()
                                if clean_text:
                                    st.markdown(f"**📊 Resultado da Análise:**")
                                    st.markdown(clean_text)
                            
                            # Exibe a tabela se disponível
                            if response_table is not None:
                                try:
                                    df_table = pd.DataFrame(response_table)
                                    if not df_table.empty:
                                        st.markdown("**📋 Detalhamento dos Dados:**")
                                        st.dataframe(df_table, use_container_width=True)
                                except Exception as e:
                                    st.warning(f"Não foi possível exibir a tabela: {e}")
                            
                            # Exibe o gráfico se disponível
                            if response_figure is not None:
                                try:
                                    st.markdown("**📈 Visualização:**")
                                    st.plotly_chart(response_figure, use_container_width=True)
                                except Exception as e:
                                    st.warning(f"Não foi possível exibir o gráfico: {e}")
                                    # Fallback: mostra que há um gráfico disponível
                                    st.info("Um gráfico foi gerado mas não pôde ser exibido.")
                            
                            # Adiciona ao histórico - só o texto limpo para não poluir
                            clean_text_for_history = clean_ansi_codes(final_output.get('text_output', "Análise concluída.")).strip()
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": clean_text_for_history,
                                "table": response_table,
                                "figure": response_figure
                            })
                            
                        except Exception as e:
                            st.error(f"Erro ao processar resultado: {str(e)}")
                            # Debug info apenas quando há erro
                            with st.expander("🔍 Informações de Debug"):
                                st.write("Tipo do resultado:", type(final_output))
                                st.write("Resultado bruto:", final_output)
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": f"Desculpe, ocorreu um erro ao processar o resultado: {str(e)}"
                            })

                except Exception as e:
                    st.error(f"Erro geral na execução: {str(e)}")
                    st.write("Traceback:", traceback.format_exc())
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": f"Desculpe, ocorreu um erro inesperado: {str(e)}"
                    })