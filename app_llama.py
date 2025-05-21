
import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import os
import re
from io import BytesIO
from difflib import get_close_matches
from llama_cpp import Llama

st.set_page_config(page_title="Recomendações com LLaMA Local", layout="wide")
st.title("📄 Verificador de Recomendações com Modelo Local (LLaMA)")

# Carregar modelo .gguf
@st.cache_resource
def carregar_llama():
    return Llama(model_path="models/llama-2-7b-chat.Q3_K_L.gguf", n_ctx=2048)

llm = carregar_llama()

# Função para ler PDF
def ler_pdf(caminho_pdf):
    try:
        doc = fitz.open(caminho_pdf)
        texto = "\n".join(page.get_text() for page in doc)
        doc.close()
        return texto
    except Exception as e:
        return f"[Erro ao ler o PDF: {e}]"

# Função para rodar o LLaMA local
def extrair_recomendacoes_llama(texto):
    texto = texto[-3000:]
    prompt = (
        "### Instrução:\n"
        "Você é um especialista técnico. Abaixo está um trecho das conclusões de um relatório técnico.\n"
        "Extraia apenas as recomendações encontradas nas conclusões, em formato de bullet points.\n"
        "Ignore qualquer conteúdo que não seja sugestão ou ação recomendada.\n\n"
        f"{texto}\n\n### Resposta:"
    )
    try:
        output = llm(prompt, max_tokens=512, stop=["###"])
        return output["choices"][0]["text"].strip()
    except Exception as e:
        return f"[Erro ao processar com LLaMA: {e}]"

# Upload da planilha
uploaded_file = st.file_uploader("📤 Envie a planilha Excel com os projetos", type=[".xlsx"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    abas = xls.sheet_names
    aba_escolhida = st.selectbox("Escolha a aba:", abas)
    df = pd.read_excel(uploaded_file, sheet_name=aba_escolhida, header=None)

    # Detectar cabeçalho
    for i in range(10):
        if df.iloc[i].astype(str).str.contains("Empresa").any():
            df.columns = df.iloc[i].astype(str).str.strip()
            df = df[i+1:].reset_index(drop=True)
            break

    col1, col2 = st.columns(2)
    with col1:
        empresa_col = st.selectbox("Coluna com o nome da empresa:", df.columns)
    with col2:
        arquivo_col = st.selectbox("Coluna com o nome do arquivo:", df.columns)

    st.markdown("---")
    st.subheader("🔍 Resultado com LLaMA Local")

    resultados = []

    for _, row in df.iterrows():
        empresa = str(row[empresa_col]).strip()
        nome_arquivo = str(row[arquivo_col]).strip()

        pasta_final = os.path.join("pdfs", empresa, "FINAL")
        nome_desejado = f"{nome_arquivo}.pdf"

        if os.path.exists(pasta_final):
            arquivos = os.listdir(pasta_final)
            match = get_close_matches(nome_desejado, arquivos, n=1, cutoff=0.7)
            if match:
                caminho_pdf = os.path.join(pasta_final, match[0])
                texto = ler_pdf(caminho_pdf)
                recomendacoes = extrair_recomendacoes_llama(texto)
                status = "Encontrado"
            else:
                recomendacoes = "-"
                status = "Arquivo não encontrado (nome parecido não encontrado)"
        else:
            recomendacoes = "-"
            status = "Pasta FINAL não encontrada"

        resultados.append({
            "Empresa": empresa,
            "Arquivo": nome_arquivo,
            "Status": status,
            "Recomendações": recomendacoes
        })

    df_resultado = pd.DataFrame(resultados)
    st.dataframe(df_resultado, use_container_width=True)

    # Planilha para download
    buffer = BytesIO()
    df_resultado.to_excel(buffer, index=False)
    st.download_button(
        label="📥 Baixar Resultado Excel",
        data=buffer.getvalue(),
        file_name="recomendacoes_llama.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
