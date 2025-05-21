import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import os
import re
from io import BytesIO
from difflib import get_close_matches
import openai

st.set_page_config(page_title="Analisador de Recomendações", layout="wide")
st.title("📄 Verificador de Recomendações em Relatórios PDF com IA")

# Solicitar chave da API
api_key = st.text_input("🔑 Cole sua API Key da OpenAI:", type="password")

if not api_key:
    st.warning("Por favor, insira sua chave da API da OpenAI para continuar.")
    st.stop()

openai.api_key = api_key

# Função para ler texto do PDF
def ler_pdf(caminho_pdf):
    try:
        doc = fitz.open(caminho_pdf)
        texto = "\n".join(page.get_text() for page in doc)
        doc.close()
        return texto
    except Exception as e:
        return f"[Erro ao ler o PDF: {e}]"

# Função para extrair recomendações com IA focando nas conclusões

# Função para extrair recomendações com IA focando nas conclusões
def extrair_recomendacoes_ia(texto):
    # Pega os últimos 3000 caracteres, supondo que as conclusões estão no fim
    trecho_final = texto[-3000:]

    prompt_inicial = (
        "Você é um especialista técnico. Abaixo está um trecho das conclusões de um relatório técnico.\n"
        "Extraia apenas as recomendações encontradas nas conclusões, em formato de lista com marcadores (bullet points).\n"
        "Ignore qualquer informação que não seja uma sugestão, orientação ou ação proposta.\n\n"
        f"Texto:\n\"\"\"\n{trecho_final}\n\"\"\""
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um especialista técnico. Extraia recomendações das conclusões de relatórios."},
                {"role": "user", "content": prompt_inicial}
            ],
            temperature=0.2
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"[Erro ao usar OpenAI: {e}]"


# Upload do Excel
uploaded_file = st.file_uploader("📤 Envie o arquivo Excel com os projetos", type=[".xlsx"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    abas = xls.sheet_names
    aba_escolhida = st.selectbox("Escolha a aba para analisar:", abas)
    df = pd.read_excel(uploaded_file, sheet_name=aba_escolhida, header=None)

    # Detectar a linha de cabeçalho
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
    st.subheader("🔍 Resultados da Análise com IA (Conclusões)")

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
                recomendacoes = extrair_recomendacoes_ia(texto)
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

    # Gerar planilha para download
    buffer = BytesIO()
    df_resultado.to_excel(buffer, index=False)
    st.download_button(
        label="📥 Baixar Resultado em Excel",
        data=buffer.getvalue(),
        file_name="resultado_recomendacoes_ia.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
