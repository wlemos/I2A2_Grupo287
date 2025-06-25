"""
Script de Verificação da Configuração da API Gemini
Execute este script para diagnosticar problemas de configuração
"""

from dotenv import load_dotenv
import os
import sys

def verificar_configuracao_gemini():
    print("🔍 VERIFICAÇÃO DA CONFIGURAÇÃO DA API GEMINI")
    print("=" * 50)

    # 1. Verificar se dotenv está instalado
    try:
        from dotenv import load_dotenv
        print("✅ python-dotenv está instalado")
    except ImportError:
        print("❌ python-dotenv NÃO está instalado")
        print("   Execute: pip install python-dotenv")
        return False

    # 2. Verificar se arquivo .env existe
    if os.path.exists('.env'):
        print("✅ Arquivo .env encontrado")
    else:
        print("❌ Arquivo .env NÃO encontrado")
        print("   Crie um arquivo .env no diretório raiz do projeto")
        return False

    # 3. Carregar variáveis de ambiente
    load_dotenv()

    # 4. Verificar se a chave está definida
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        print("✅ GEMINI_API_KEY encontrada")
        print(f"   Primeiros 10 caracteres: {api_key[:10]}...")

        # 5. Verificar formato da chave
        if api_key.startswith('AIzaSy'):
            print("✅ Formato da chave parece correto")
        else:
            print("⚠️  Formato da chave pode estar incorreto")
            print("   Chaves do Gemini geralmente começam com 'AIzaSy'")

        # 6. Verificar comprimento da chave
        if len(api_key) >= 35:
            print("✅ Comprimento da chave parece adequado")
        else:
            print("⚠️  Chave pode estar incompleta (muito curta)")

    else:
        print("❌ GEMINI_API_KEY NÃO encontrada")
        print("   Verifique se a variável está definida no arquivo .env")
        return False

    # 7. Testar importação do CrewAI
    try:
        from crewai import LLM
        print("✅ CrewAI está instalado")
    except ImportError:
        print("❌ CrewAI NÃO está instalado")
        print("   Execute: pip install crewai")
        return False

    # 8. Tentar criar instância do LLM (sem fazer chamadas)
    try:
        llm = LLM(
            model='gemini/gemini-1.5-flash',
            api_key=api_key,
            temperature=0.5
        )
        print("✅ Instância do LLM criada com sucesso")
    except Exception as e:
        print(f"❌ Erro ao criar instância do LLM: {e}")
        return False

    print("\n🎉 CONFIGURAÇÃO PARECE ESTAR CORRETA!")
    print("   Você pode tentar executar o sistema agora.")
    return True

if __name__ == "__main__":
    sucesso = verificar_configuracao_gemini()
    sys.exit(0 if sucesso else 1)
