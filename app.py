import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import os
import re
from io import BytesIO
from difflib import get_close_matches

st.set_page_config(page_title="Analisador de Recomendações", layout="wide")
st.title("📄 Verificador de Recomendações em Relatórios PDF")

# Palavras-chave para identificar recomendações
KEYWORDS = [
    "recomenda", "deve ser", "é necessário", "sugerimos",
    "aconselhamos", "indicamos", "importante que"
]

# Função para buscar frases com recomendações no texto do PDF
def extrair_recomendacoes(texto):
    frases = re.split(r'[\.!?]\s+', texto)
    recomendacoes = [frase.strip() for frase in frases if any(kw in frase.lower() for kw in KEYWORDS)]
    return recomendacoes

# Função para ler texto do PDF
def ler_pdf(caminho_pdf):
    try:
        doc = fitz.open(caminho_pdf)
        texto = "\n".join(page.get_text() for page in doc)
        doc.close()
        return texto
    except Exception as e:
        return f"[Erro ao ler o PDF: {e}]"

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
    st.subheader("🔍 Resultados da Análise")

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
                recomendacoes = extrair_recomendacoes(texto)
                status = "Encontrado" if recomendacoes else "Sem recomendações"
            else:
                recomendacoes = []
                status = "Arquivo não encontrado (nome parecido não encontrado)"
        else:
            recomendacoes = []
            status = "Pasta FINAL não encontrada"

        recomendacoes_formatadas = "\n".join([f"{i+1}. {rec}" for i, rec in enumerate(recomendacoes)]) if recomendacoes else "-"

        resultados.append({
            "Empresa": empresa,
            "Arquivo": nome_arquivo,
            "Status": status,
            "Recomendações": recomendacoes_formatadas
        })

    df_resultado = pd.DataFrame(resultados)
    st.dataframe(df_resultado, use_container_width=True)

    # Gerar planilha para download
    buffer = BytesIO()
    df_resultado.to_excel(buffer, index=False)
    st.download_button(
        label="📥 Baixar Resultado em Excel",
        data=buffer.getvalue(),
        file_name="resultado_recomendacoes.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
