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
    # Português
    "recomenda", "deve ser", "é necessário", "sugerimos",
    "aconselhamos", "indicamos", "importante que",
    "é essencial que", "convém que",
    
    # Inglês
    "recommend", "should", "must", "it is necessary",
    "we suggest", "we recommend", "we advise that",
    "critical that", "it is essential", "it is recommended that",
    "you ought to",
    
    # Francês
    "recommande", "doit être", "il est nécessaire",
    "nous suggérons", "nous conseillons", "nous indiquons",
    "il est important que", "il est essentiel que", "il faudrait",
    "nous recommandons", "vous devriez",
    
    # Espanhol
    "recomienda", "debe ser", "es necesario",
    "sugerimos", "aconsejamos", "indicamos",
    "es importante que", "es esencial que", "debería",
    "recomendamos", "conviene que"
]

# Função para buscar frases com recomendações no texto do PDF
def extrair_recomendacoes(texto):
    frases = re.split(r'[\.\!?]\s+', texto)
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
    # Carrega todas as abas
    xls = pd.ExcelFile(uploaded_file)
    abas = xls.sheet_names
    aba_escolhida = st.selectbox("Escolha a aba para analisar:", abas)
    # Lê a aba selecionada para DataFrame sem inferir cabeçalho
    df = pd.read_excel(uploaded_file, sheet_name=aba_escolhida, header=None)

    # Detectar a linha de cabeçalho e ajustar colunas
    for i in range(10):
        if df.iloc[i].astype(str).str.contains("Empresa").any():
            df.columns = df.iloc[i].astype(str).str.strip()
            df = df[i+1:].reset_index(drop=True)
            break

    # Colunas fixas
    empresa_col = "Empresa"
    arquivo_col = "Nome do arquivo salvo"

    # Seleção da empresa para análise
    empresas_disponiveis = sorted(df[empresa_col].dropna().astype(str).unique())
    empresa_selecionada = st.selectbox("Selecione a empresa para análise:", empresas_disponiveis)

    # Filtrar dataframe para a empresa escolhida
    df_filtrado = df[df[empresa_col].astype(str) == empresa_selecionada].copy()

    st.markdown("---")
    st.subheader("🔍 Resultados da Análise")

    resultados = []

    for _, row in df_filtrado.iterrows():
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

    # Mostrar resultados em DataFrame
    df_resultado = pd.DataFrame(resultados)
    st.dataframe(df_resultado, use_container_width=True)

    # Inserir recomendações na própria aba do arquivo original
    df_export = df.copy()
    # Adiciona coluna de Recomendações com valores vazios
    df_export['Recomendações'] = ""
    # Preenche somente para as linhas filtradas
    for idx, rec in zip(df_filtrado.index, df_resultado['Recomendações']):
        df_export.at[idx, 'Recomendações'] = rec

    # Gerar novo arquivo Excel com a aba atualizada
    buffer_full = BytesIO()
    with pd.ExcelWriter(buffer_full, engine='openpyxl') as writer:
        df_export.to_excel(writer, sheet_name=aba_escolhida, index=False)
    st.download_button(
        label="📥 Baixar Resultados",
        data=buffer_full.getvalue(),
        file_name="arquivo_atualizado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
