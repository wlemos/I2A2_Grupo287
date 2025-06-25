"""
Sistema de Agentes CrewAI para Análise de Bases de Dados com Google Gemini

VERSÃO CORRIGIDA - Problema de file_path vazio resolvido + SUPORTE A ZIP DE NFs

"""

import os
import pandas as pd
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from crewai import Agent, Task, Crew, LLM
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import chardet
import unicodedata
import re
import textwrap
import tempfile
import zipfile
import shutil
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# =============================================================================
# PROCESSADOR DE DADOS UNIFICADO (MODIFICADO PARA SUPORTE A ZIP)
# =============================================================================

class BaseDataProcessor:
    """Processador centralizado que garante dados idênticos entre agentes + Suporte ZIP"""
    
    _cache_dataframes = {}
    _current_file_path = None
    
    @classmethod
    def get_processed_dataframe(cls, file_path: str) -> pd.DataFrame:
        abs_path = os.path.abspath(file_path)
        cls._current_file_path = abs_path
        
        if abs_path not in cls._cache_dataframes:
            print(f"🔄 Processando dados pela primeira vez: {file_path}")
            
            # NOVO: Verificar se é arquivo ZIP
            if file_path.lower().endswith('.zip'):
                df = cls._process_zip_nfs(file_path)
            else:
                df = cls._process_file_unified(file_path)
            
            cls._cache_dataframes[abs_path] = df
            print(f"✅ Dados processados e armazenados no cache: {len(df)} registros, {len(df.columns)} colunas")
            print(f"📋 Colunas: {list(df.columns)}")
        else:
            print(f"📦 Usando dados do cache: {file_path}")
            df = cls._cache_dataframes[abs_path]
        
        return df.copy()
    
    @classmethod
    def get_current_file_path(cls) -> str:
        """Retorna o file_path atual em uso"""
        return cls._current_file_path or ""
    
    @classmethod
    def _process_zip_nfs(cls, zip_path: str) -> pd.DataFrame:
        """NOVO: Processar arquivo ZIP contendo CSVs de Notas Fiscais"""
        try:
            print(f"📦 Processando arquivo ZIP de NFs: {zip_path}")
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extrair ZIP
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Procurar arquivos CSV específicos
                extracted_files = os.listdir(temp_dir)
                cabecalho_file = None
                itens_file = None
                
                for file in extracted_files:
                    if file.endswith('_NFs_Cabecalho.csv'):
                        cabecalho_file = os.path.join(temp_dir, file)
                        print(f"📄 Encontrado arquivo Cabeçalho: {file}")
                    elif file.endswith('_NFs_Itens.csv'):
                        itens_file = os.path.join(temp_dir, file)
                        print(f"📄 Encontrado arquivo Itens: {file}")
                
                if not cabecalho_file or not itens_file:
                    raise ValueError(
                        "Arquivo ZIP deve conter exatamente dois arquivos: "
                        "aaaamm_NFs_Cabecalho.csv e aaaamm_NFs_Itens.csv"
                    )
                
                # Processar cada arquivo CSV
                print("🔧 Processando arquivo Cabeçalho...")
                df_cabecalho = cls._process_file_unified(cabecalho_file)
                
                print("🔧 Processando arquivo Itens...")
                df_itens = cls._process_file_unified(itens_file)
                
                # Mergear baseado na CHAVE DE ACESSO
                print("🔗 Realizando merge baseado na CHAVE DE ACESSO...")
                
                # Normalizar nome da coluna chave em ambos DataFrames
                chave_col_cabecalho = cls._encontrar_coluna_chave(df_cabecalho.columns)
                chave_col_itens = cls._encontrar_coluna_chave(df_itens.columns)
                
                if not chave_col_cabecalho or not chave_col_itens:
                    raise ValueError("Não foi possível encontrar a coluna 'CHAVE DE ACESSO' em um dos arquivos")
                
                # Realizar merge
                df_merged = pd.merge(
                    df_cabecalho, 
                    df_itens, 
                    left_on=chave_col_cabecalho,
                    right_on=chave_col_itens,
                    how='inner',
                    suffixes=('_CABECALHO', '_ITENS')
                )
                
                print(f"✅ Merge realizado com sucesso: {len(df_merged)} registros finais")
                print(f"📊 Estatísticas do merge:")
                print(f"   - Registros Cabeçalho: {len(df_cabecalho)}")
                print(f"   - Registros Itens: {len(df_itens)}")
                print(f"   - Registros Merged: {len(df_merged)}")
                
                # Adicionar metadados específicos do ZIP
                df_merged.attrs['tipo_processamento'] = 'ZIP_NFs'
                df_merged.attrs['arquivo_cabecalho'] = os.path.basename(cabecalho_file)
                df_merged.attrs['arquivo_itens'] = os.path.basename(itens_file)
                df_merged.attrs['coluna_merge'] = chave_col_cabecalho
                df_merged.attrs['arquivo_origem'] = zip_path
                
                return df_merged
                
        except Exception as e:
            print(f"❌ Erro ao processar ZIP de NFs: {e}")
            raise e
    
    @classmethod
    def _encontrar_coluna_chave(cls, colunas: List[str]) -> Optional[str]:
        """Encontrar a coluna CHAVE DE ACESSO considerando normalizações"""
        for col in colunas:
            col_normalizada = col.upper().replace(' ', '').replace('_', '')
            if 'CHAVEDEACESSO' in col_normalizada or 'CHAVEACESSO' in col_normalizada:
                return col
        return None
    
    @classmethod
    def _process_file_unified(cls, file_path: str) -> pd.DataFrame:
        try:
            encoding = cls._detectar_encoding_robusto(file_path)
            print(f"🔍 Encoding detectado: {encoding}")
            
            df = pd.read_csv(file_path, encoding=encoding)
            print(f"📊 Arquivo lido: {len(df)} registros, {len(df.columns)} colunas")
            
            colunas_originais = list(df.columns)
            df = cls._normalizar_nomes_colunas(df)
            print(f"🔧 Colunas normalizadas: {list(df.columns)}")
            
            df.attrs['colunas_originais'] = colunas_originais
            df.attrs['encoding_usado'] = encoding
            df.attrs['arquivo_origem'] = file_path
            
            return df
            
        except Exception as e:
            print(f"❌ Erro no processamento unificado: {e}")
            raise e
    
    @classmethod
    def _detectar_encoding_robusto(cls, file_path: str) -> str:
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read()
            result = chardet.detect(raw_data)
            detected_encoding = result['encoding']
            
            encodings_comuns = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1', 'windows-1252']
            
            for encoding in encodings_comuns:
                try:
                    df_test = pd.read_csv(file_path, encoding=encoding, nrows=5)
                    problemas = sum(1 for col in df_test.columns 
                                  if any(char in col for char in ['Ã', 'Â', 'Ç', '¿', '½', '√', '∫']))
                    if problemas == 0:
                        return encoding
                except:
                    continue
            
            return detected_encoding or 'latin-1'
        except Exception:
            return 'latin-1'
    
    @classmethod
    def _normalizar_nomes_colunas(cls, df: pd.DataFrame) -> pd.DataFrame:
        colunas_normalizadas = []
        for col in df.columns:
            try:
                sem_acentos = unicodedata.normalize('NFD', col).encode('ascii', 'ignore').decode('utf-8')
            except:
                sem_acentos = col
            
            limpo = re.sub(r'[^\w\s-]', '', sem_acentos)
            normalizado = ' '.join(limpo.split())
            colunas_normalizadas.append(normalizado)
        
        df.columns = colunas_normalizadas
        return df
    
    @classmethod
    def clear_cache(cls):
        cls._cache_dataframes.clear()
        cls._current_file_path = None
        print("🗑️ Cache de DataFrames limpo")

# =============================================================================
# CONFIGURAÇÃO DO MODELO GEMINI
# =============================================================================

def configurar_gemini():
    # Remover aspas ou espaços que possam estar na chave
    gemini_api_key = os.getenv("GEMINI_API_KEY").strip().replace('"', '')
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY não encontrada nas variáveis de ambiente")

    gemini_llm = LLM(
        model='gemini/gemini-1.5-flash',
        api_key=gemini_api_key,
        temperature=0.5
    )
    return gemini_llm

# =============================================================================
# FERRAMENTAS PERSONALIZADAS - VERSÃO COM CORREÇÃO ESPECÍFICA
# =============================================================================

class DataAnalysisInput(BaseModel):
    file_path: str = Field(description="Caminho para o arquivo CSV")
    query: str = Field(description="Consulta para análise específica", default="")

class DataAnalysisTool(BaseTool):
    name: str = "data_analysis_tool"
    description: str = "Ferramenta para análise robusta de dados CSV com processamento unificado"
    args_schema: type[BaseModel] = DataAnalysisInput

    def _run(self, file_path: str, query: str = "") -> dict:
        try:
            print(f"🔍 DataAnalysisTool - Analisando: {file_path}")
            df = BaseDataProcessor.get_processed_dataframe(file_path)

            print(f"📊 DataAnalysisTool - DataFrame carregado: {len(df)} x {len(df.columns)}")
            print(f"📋 DataAnalysisTool - Colunas: {list(df.columns)}")

            info_basica = {
                "shape": list(df.shape),
                "columns": list(df.columns),
                "dtypes": df.dtypes.to_dict(),
                "null_values": df.isnull().sum().to_dict(),
                "encoding_usado": df.attrs.get('encoding_usado', 'utf-8')
            }

            numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
            numeric_stats = {}
            for col in numeric_cols:
                try:
                    stats = df[col].describe()
                    numeric_stats[col] = stats.to_dict()
                except:
                    pass
            info_basica["numeric_stats"] = numeric_stats

            unique_counts = {}
            for col in df.columns:
                try:
                    unique_counts[col] = df[col].nunique()
                except:
                    unique_counts[col] = 0
            info_basica["unique_values"] = unique_counts

            try:
                sample_data = df.head(3).to_dict('records')
                info_basica["sample_data"] = sample_data
            except:
                info_basica["sample_data"] = []

            colunas_mapeamento = {}
            if 'colunas_originais' in df.attrs:
                for i, col_orig in enumerate(df.attrs['colunas_originais']):
                    if i < len(df.columns):
                        colunas_mapeamento[col_orig] = df.columns[i]
            info_basica["mapeamento_colunas"] = colunas_mapeamento

            return info_basica

        except Exception as e:
            return {
                "erro": f"Erro ao analisar arquivo: {str(e)}",
                "sugestao": "Verifique se o arquivo existe e está em formato CSV válido"
            }

class PythonExecutorInput(BaseModel):
    code: str = Field(description="Código Python para executar")
    file_path: str = Field(description="Caminho para o arquivo de dados")

class PythonExecutorTool(BaseTool):
    name: str = "python_executor_tool"
    description: str = "Executa código Python usando dados processados de forma unificada - CORREÇÃO file_path"
    args_schema: type[BaseModel] = PythonExecutorInput

    def _preparar_ambiente_execucao(self, file_path: str) -> Tuple[Dict, Optional[str]]:
        """CORREÇÃO PRINCIPAL: Usar file_path do cache se vazio"""
        try:
            # CORREÇÃO: Se file_path está vazio, usar o do cache
            if not file_path or file_path.strip() == "":
                file_path = BaseDataProcessor.get_current_file_path()
                print(f"🔧 Usando file_path do cache: {file_path}")

            if not file_path:
                return {}, "Erro: Nenhum arquivo de dados disponível"

            print(f"🐍 PythonExecutorTool - Preparando ambiente: {file_path}")

            # USAR PROCESSAMENTO UNIFICADO
            df = BaseDataProcessor.get_processed_dataframe(file_path)

            print(f"📊 PythonExecutorTool - DataFrame carregado: {len(df)} x {len(df.columns)}")
            print(f"📋 PythonExecutorTool - Colunas: {list(df.columns)}")

            # Preparar namespace completo
            namespace = {
                'pd': pd,
                'df': df,
                'file_path': file_path,
                'encoding_usado': df.attrs.get('encoding_usado', 'utf-8'),
                'os': os,
                're': re,
                'unicodedata': unicodedata,
                'result': None,
                'colunas_disponiveis': list(df.columns),
                'shape': df.shape,
                'print': print
            }

            return namespace, None

        except Exception as e:
            print(f"❌ Erro ao preparar ambiente: {e}")
            return {}, str(e)

    def _run(self, code: str, file_path: str) -> str:
        """MÉTODO PRINCIPAL CORRIGIDO: Tratamento de file_path vazio"""
        try:
            print(f"🐍 PythonExecutorTool - Executando código para: {file_path}")

            # Preparar ambiente com correção de file_path
            namespace, erro = self._preparar_ambiente_execucao(file_path)
            if erro:
                return f"Erro ao carregar dados: {erro}"

            # Processar e executar código
            codigo_processado = self._processar_codigo_json(code)

            print(f"🔧 Executando código processado...")

            # Executar código
            try:
                exec(codigo_processado, namespace)
                print("✅ Código executado com sucesso")
            except Exception as e:
                print(f"❌ Erro na execução: {e}")
                return self._executar_fallback_direto(namespace, f"Erro na execução: {e}")

            # Capturar resultado
            if 'result' in namespace and namespace['result'] is not None:
                resultado = namespace['result']

                if hasattr(resultado, 'to_string'):
                    return resultado.to_string()
                elif hasattr(resultado, 'to_dict'):
                    return str(resultado.to_dict())
                else:
                    return str(resultado)
            else:
                return "Código executado com sucesso. Verifique se o resultado foi atribuído à variável 'result'."

        except Exception as e:
            return self._executar_fallback_direto(namespace if 'namespace' in locals() else {}, f"Erro geral: {str(e)}")

    def _processar_codigo_json(self, code_input: str) -> str:
        """Processar código JSON com correção de encoding"""
        try:
            if code_input.startswith('{') and '"code"' in code_input:
                try:
                    data = json.loads(code_input)
                    codigo_bruto = data.get('code', code_input)
                except json.JSONDecodeError:
                    codigo_bruto = code_input
            else:
                codigo_bruto = code_input

            # Processar sequências de escape
            codigo_processado = codigo_bruto.replace('\\n', '\n')
            codigo_processado = codigo_processado.replace('\\\\', '\\')

            # Processar caracteres Unicode
            try:
                codigo_processado = codigo_processado.encode().decode('unicode_escape')
            except UnicodeDecodeError:
                codigo_processado = codigo_processado.replace('\\u00e3', 'ã')
                codigo_processado = codigo_processado.replace('\\u00e7', 'ç')

            # Normalizar indentação
            codigo_final = textwrap.dedent(codigo_processado)

            return codigo_final

        except Exception as e:
            print(f"❌ Erro ao processar código JSON: {e}")
            return code_input

    def _executar_fallback_direto(self, namespace: Dict, erro_original: str) -> str:
        """Execução de fallback usando DataFrame já carregado"""
        try:
            print(f"🔄 Executando fallback direto...")

            if 'df' not in namespace:
                return f"Erro original: {erro_original}\nDataFrame não disponível para fallback."

            df = namespace['df']

            # Fallback específico para perguntas sobre fornecedores/valores
            if 'NOME DESTINATARIO' in df.columns and 'VALOR NOTA FISCAL' in df.columns:
                print("🔍 Executando análise de fallback para fornecedores...")
                df['VALOR NOTA FISCAL'] = pd.to_numeric(df['VALOR NOTA FISCAL'], errors='coerce')
                resultado = df.groupby('NOME DESTINATARIO')['VALOR NOTA FISCAL'].sum().sort_values(ascending=False)
                top_fornecedor = resultado.index[0]
                valor_total = resultado.iloc[0]

                return f"Fornecedor com maior valor total: {top_fornecedor} - R$ {valor_total:,.2f}\n\nTop 5 fornecedores:\n{resultado.head().to_string()}"

            # Fallback para emitentes por CNPJ
            elif 'CPFCNPJ Emitente' in df.columns and 'VALOR NOTA FISCAL' in df.columns:
                print("🔍 Executando análise de fallback para emitentes por CNPJ...")
                df['VALOR NOTA FISCAL'] = pd.to_numeric(df['VALOR NOTA FISCAL'], errors='coerce')
                resultado = df.groupby('CPFCNPJ Emitente')['VALOR NOTA FISCAL'].sum().sort_values(ascending=False)
                top_emitente_cnpj = resultado.index[0]
                valor_total = resultado.iloc[0]

                # Tentar encontrar o nome do emitente
                nome_emitente = "Não informado"
                if 'RAZAO SOCIAL EMITENTE' in df.columns:
                    mask = df['CPFCNPJ Emitente'] == top_emitente_cnpj
                    nomes = df.loc[mask, 'RAZAO SOCIAL EMITENTE'].unique()
                    if len(nomes) > 0:
                        nome_emitente = nomes[0]

                return f"Fornecedor com maior valor total: {nome_emitente} (CNPJ: {top_emitente_cnpj}) - R$ {valor_total:,.2f}\n\nTop 5 fornecedores por CNPJ:\n{resultado.head().to_string()}"

            # Fallback genérico
            colunas_disponiveis = list(df.columns)
            return f"Erro original: {erro_original}\nColunas disponíveis: {colunas_disponiveis}\nShape: {df.shape}"

        except Exception as e2:
            return f"Erro original: {erro_original}\nErro no fallback: {str(e2)}"

# =============================================================================
# AGENTES (MANTIDOS COM PEQUENOS AJUSTES)
# =============================================================================

def criar_agente_metadados(llm):
    return Agent(
        role='Especialista em Metadados de Dados',
        goal='Gerar metadados completos e robustos para bases de dados CSV',
        backstory="""Você é um especialista em análise de dados com vasta experiência em
        caracterização de datasets. Sua especialidade é extrair e documentar metadados
        detalhados de bases de dados, incluindo tipos de dados, distribuições,
        relacionamentos, qualidade dos dados e padrões identificados.""",
        verbose=True,
        allow_delegation=False,
        tools=[DataAnalysisTool()],
        llm=llm
    )

def criar_agente_codigo(llm):
    return Agent(
        role='Especialista em Código Python para Análise de Dados',
        goal='Gerar código Python eficiente para responder perguntas específicas sobre dados',
        backstory="""Você é um programador Python especializado em análise de dados
        com pandas, numpy e outras bibliotecas. Você recebe metadados de uma base de dados
        e uma pergunta do usuário, e gera código Python preciso e eficiente para
        responder à pergunta. IMPORTANTE: Use sempre o DataFrame 'df' que já está
        carregado no ambiente. O arquivo de dados será carregado automaticamente.
        Sempre atribua o resultado final à variável result.""",
        verbose=True,
        allow_delegation=False,
        tools=[PythonExecutorTool()],
        llm=llm
    )

def criar_agente_linguagem_natural(llm):
    return Agent(
        role='Especialista em Comunicação de Dados',
        goal='Converter resultados técnicos em respostas claras em linguagem natural',
        backstory="""Você é um comunicador especializado em traduzir resultados
        técnicos e numéricos em explicações claras e compreensíveis para usuários
        não técnicos. Você recebe códigos Python e seus resultados e cria respostas
        em linguagem natural que são informativas, precisas e fáceis de entender.""",
        verbose=True,
        allow_delegation=False,
        llm=llm
    )

# =============================================================================
# TAREFAS (CORREÇÃO ESPECÍFICA)
# =============================================================================

def criar_tarefa_metadados(agente, file_path):
    return Task(
        description=f"""Analise a base de dados localizada em {file_path} e gere
        metadados completos e robustos. Os metadados devem incluir:

        1. Informações básicas: número de linhas, colunas, tamanho
        2. Descrição detalhada de cada coluna: tipo, valores únicos e padrões
        3. Estatísticas descritivas para colunas numéricas
        4. Identificação de valores nulos ou inconsistências

        Use a ferramenta data_analysis_tool para extrair as informações necessárias.""",
        expected_output="""Um relatório detalhado de metadados contendo:
        - Estrutura da base de dados
        - Descrição de cada campo/coluna
        - Estatísticas e distribuições
        - Qualidade dos dados""",
        agent=agente
    )

def criar_tarefa_codigo(agente, user_query, metadata, file_path):
    return Task(
        description=f"""Com base nos metadados fornecidos e na pergunta do usuário,
        gere código Python usando pandas para responder à pergunta:

        PERGUNTA DO USUÁRIO: {user_query}

        METADADOS DA BASE DE DADOS: {metadata}

        ARQUIVO DE DADOS: {file_path}

        INSTRUÇÕES CRÍTICAS:
        1. O DataFrame 'df' JÁ ESTÁ CARREGADO no ambiente de execução
        2. NÃO tente carregar arquivos CSV com pd.read_csv()
        3. Use APENAS o DataFrame 'df' disponível
        4. SEMPRE atribua o resultado final à variável result
        5. Inclua comentários explicativos no código
        6. Faça agregações, filtragens ou cálculos diretamente no 'df'
        7. O sistema carregará automaticamente os dados do arquivo: {file_path}

        EXEMPLO DE CÓDIGO CORRETO:
        # O DataFrame 'df' já está carregado
        # Agrupa por coluna e soma valores
        resultado = df.groupby('COLUNA')['VALOR'].sum()
        result = resultado.to_string()

        Use a ferramenta python_executor_tool para executar e testar o código.""",
        expected_output="""Código Python funcional que:
        - Usa o DataFrame 'df' já carregado
        - Processa os dados conforme a pergunta
        - Atribui o resultado à variável result
        - Inclui comentários explicativos
        - Retorna o resultado da execução""",
        agent=agente
    )

def criar_tarefa_linguagem_natural(agente, user_query, codigo_resultado):
    return Task(
        description=f"""Converta o resultado técnico em uma resposta clara
        em linguagem natural para a pergunta do usuário.

        PERGUNTA DO USUÁRIO: {user_query}

        CÓDIGO E RESULTADO TÉCNICO: {codigo_resultado}

        Instruções:
        1. Forneça uma resposta direta e clara à pergunta
        2. Explique o resultado em termos simples
        3. Inclua números relevantes ou estatísticas quando apropriado
        4. Contextualize o resultado se necessário
        5. Use linguagem acessível para usuários não técnicos
        6. Se houver limitações ou considerações importantes, mencione-as""",
        expected_output="""Uma resposta em linguagem natural que:
        - Responde diretamente à pergunta do usuário
        - Explica os resultados de forma clara
        - Inclui dados relevantes formatados de forma legível
        - Fornece contexto quando necessário
        - É compreensível para usuários não técnicos""",
        agent=agente
    )

# =============================================================================
# CLASSE PRINCIPAL (CORREÇÃO ESPECÍFICA)
# =============================================================================

class SistemaAnaliseBaseDados:
    """Sistema principal com correção para file_path vazio"""

    def __init__(self):
        self.llm = configurar_gemini()
        self.agente_metadados = criar_agente_metadados(self.llm)
        self.agente_codigo = criar_agente_codigo(self.llm)
        self.agente_linguagem_natural = criar_agente_linguagem_natural(self.llm)
        self.metadados_cache = {}
        self.current_file_path = None  # NOVO: Manter referência do file_path atual

    # def gerar_metadados(self, file_path: str) -> str:
    #     if file_path in self.metadados_cache:
    #         return self.metadados_cache[file_path]

    #     print(f"🔍 Gerando metadados para: {file_path}")
    #     self.current_file_path = file_path  # NOVO: Salvar file_path atual

    #     # Garantir que dados estão processados
    #     BaseDataProcessor.get_processed_dataframe(file_path)

    #     tarefa_metadados = criar_tarefa_metadados(self.agente_metadados, file_path)
    #     crew_metadados = Crew(
    #         agents=[self.agente_metadados],
    #         tasks=[tarefa_metadados],
    #         verbose=True
    #     )

    #     resultado = crew_metadados.kickoff()
    #     self.metadados_cache[file_path] = str(resultado)
    #     return str(resultado)

    def gerar_metadados(self, file_path: str) -> dict:
        """MÉTODO CORRIGIDO: Retorna dict ao invés de str para evitar erro de JSON"""
        if file_path in self.metadados_cache:
            return self.metadados_cache[file_path]

        print(f"🔍 Gerando metadados para: {file_path}")
        self.current_file_path = file_path

        # Garantir que dados estão processados
        df = BaseDataProcessor.get_processed_dataframe(file_path)
        
        # Gerar metadados estruturados diretamente
        metadados = {
            "informacoes_basicas": {
                "total_registros": len(df),
                "total_colunas": len(df.columns),
                "encoding_usado": df.attrs.get('encoding_usado', 'utf-8'),
                "tipo_processamento": df.attrs.get('tipo_processamento', 'CSV'),
                "arquivo_origem": df.attrs.get('arquivo_origem', file_path)
            },
            "colunas": {
                col: {
                    "tipo": str(df[col].dtype),
                    "valores_unicos": int(df[col].nunique()),
                    "valores_nulos": int(df[col].isnull().sum()),
                    "porcentagem_nulos": round(float(df[col].isnull().sum() / len(df) * 100), 2)
                } for col in df.columns
            },
            "estatisticas_numericas": {},
            "amostras": df.head(3).to_dict('records')
        }
        
        # Adicionar estatísticas para colunas numéricas
        numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
        for col in numeric_cols:
            try:
                stats = df[col].describe()
                metadados["estatisticas_numericas"][col] = {
                    "media": float(stats['mean']),
                    "mediana": float(stats['50%']),
                    "desvio_padrao": float(stats['std']),
                    "minimo": float(stats['min']),
                    "maximo": float(stats['max']),
                    "q25": float(stats['25%']),
                    "q75": float(stats['75%'])
                }
            except:
                pass
        
        # Informações específicas do ZIP se aplicável
        if df.attrs.get('tipo_processamento') == 'ZIP_NFs':
            metadados["informacoes_zip"] = {
                "arquivo_cabecalho": df.attrs.get('arquivo_cabecalho', ''),
                "arquivo_itens": df.attrs.get('arquivo_itens', ''),
                "coluna_merge": df.attrs.get('coluna_merge', '')
            }
        
        self.metadados_cache[file_path] = metadados
        return metadados


    def responder_pergunta(self, file_path: str, user_query: str) -> str:
        print(f"❓ Pergunta: {user_query}")
        print(f"📊 Base de dados: {file_path}")

        try:
            # CORREÇÃO: Garantir que file_path está disponível globalmente
            self.current_file_path = file_path
            BaseDataProcessor.clear_cache()

            # Passo 1: Gerar/obter metadados
            metadados = self.gerar_metadados(file_path)

            # Passo 2: Gerar código Python - CORREÇÃO: Passar file_path explicitamente
            print("🐍 Gerando código Python...")
            tarefa_codigo = criar_tarefa_codigo(
                self.agente_codigo, user_query, metadados, file_path  # file_path explícito
            )

            crew_codigo = Crew(
                agents=[self.agente_codigo],
                tasks=[tarefa_codigo],
                verbose=True
            )

            codigo_resultado = crew_codigo.kickoff()

            # Passo 3: Converter para linguagem natural
            print("📝 Convertendo para linguagem natural...")
            tarefa_linguagem = criar_tarefa_linguagem_natural(
                self.agente_linguagem_natural, user_query, str(codigo_resultado)
            )

            crew_linguagem = Crew(
                agents=[self.agente_linguagem_natural],
                tasks=[tarefa_linguagem],
                verbose=True
            )

            resposta_final = crew_linguagem.kickoff()
            return str(resposta_final)

        except Exception as e:
            print(f"❌ Erro no processamento: {e}")
            return f"Erro ao processar pergunta: {str(e)}"

    def limpar_cache(self):
        self.metadados_cache.clear()
        BaseDataProcessor.clear_cache()
        self.current_file_path = None  # NOVO: Limpar file_path também
        print("🗑️ Todos os caches limpos")

# =============================================================================
# FUNÇÃO PRINCIPAL (MANTIDA INALTERADA)
# =============================================================================

def main():
    try:
        sistema = SistemaAnaliseBaseDados()

        file_path = "notas_fiscais.csv"

        perguntas_exemplo = [
            "Qual fornecedor teve o maior valor total recebido?",
            "Quantas notas fiscais foram emitidas por cada estado?",
            "Qual é a média dos valores das notas fiscais?",
            "Quais são os 5 maiores valores de nota fiscal?",
            "Quantas notas fiscais são operações interestaduais vs internas?"
        ]

        print("🚀 Sistema de Análise de Base de Dados inicializado!")
        print("Exemplos de perguntas que você pode fazer:")
        for i, pergunta in enumerate(perguntas_exemplo, 1):
            print(f"{i}. {pergunta}")

        while True:
            print("=" * 60)
            pergunta = input("💬 Digite sua pergunta (ou 'quit' para sair): ").strip()

            if pergunta.lower() in ['quit', 'sair', 'exit']:
                print("👋 Encerrando sistema...")
                break

            if not pergunta:
                print("⚠️ Por favor, digite uma pergunta válida.")
                continue

            try:
                resposta = sistema.responder_pergunta(file_path, pergunta)
                print(f"✅ RESPOSTA:")
                print(resposta)
            except Exception as e:
                print(f"❌ Erro ao processar pergunta: {str(e)}")

    except Exception as e:
        print(f"❌ Erro ao inicializar sistema: {str(e)}")
        print("💡 Dicas:")
        print("1. Certifique-se de ter configurado a GEMINI_API_KEY")
        print("2. Instale as dependências: pip install crewai pandas google-generativeai")
        print("3. Verifique se o arquivo CSV existe no caminho especificado")

if __name__ == "__main__":
    main()
