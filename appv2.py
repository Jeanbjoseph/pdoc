import streamlit as st
import re
import fitz
from io import BytesIO
from azure.storage.blob import BlobServiceClient

st.set_page_config(page_title="Analisador V2 – Azure Blob", layout="wide")
st.title("📄 Verificador de Recomendações (Azure Blob)")

# 1. Credenciais Azure
conn_str = st.text_input("AZURE_STORAGE_CONNECTION_STRING", type="password")
container_name = st.text_input("Container name", value="bkmrelatoriostecnicos")

# 2. Conexão e listagem de blobs
if conn_str:
    try:
        service_client = BlobServiceClient.from_connection_string(conn_str)
        container_client = service_client.get_container_client(container_name)
        blob_list = [b.name for b in container_client.list_blobs() if b.name.lower().endswith(".pdf")]
    except Exception as e:
        st.error(f"Erro ao conectar ao Azure Blob: {e}")
        blob_list = []
else:
    st.warning("Informe a Connection String do Azure para listar os relatórios.")
    blob_list = []

# 3. Seleção de relatório
empresa_selecionada = st.selectbox("Escolha o relatório (blob) para analisar", blob_list)

# 4. Download e extração de texto
texto = ""
if empresa_selecionada:
    blob_client = container_client.get_blob_client(empresa_selecionada)
    pdf_bytes = blob_client.download_blob().readall()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    texto = "\n".join(page.get_text() for page in doc)

# 5. Extração de recomendações
KEYWORDS = [
    # Português
    "recomenda", "deve ser", "é necessário", "sugerimos",
    "aconselhamos", "indicamos", "importante que", "é essencial que", "convém que",
    # Inglês
    "recommend", "should", "must", "it is necessary", "we suggest",
    "we recommend", "we advise that", "critical that", "it is essential",
    "it is recommended that", "you ought to",
    # Francês
    "recommande", "doit être", "il est nécessaire", "nous suggérons",
    "nous conseillons", "nous indiquons", "il est important que",
    "il est essentiel que", "il faudrait", "nous recommandons", "vous devriez",
    # Espanhol
    "recomienda", "debe ser", "es necesario", "sugerimos",
    "aconsejamos", "indicamos", "es importante que", "es esencial que",
    "debería", "recomendamos", "conviene que"
]

def extrair_recomendacoes(texto):
    frases = re.split(r'[\.\!?]\s+', texto)
    return [frase.strip() for frase in frases if any(kw in frase.lower() for kw in KEYWORDS)]

if texto:
    recs = extrair_recomendacoes(texto)
    st.markdown("### Recomendações encontradas")
    if recs:
        for r in recs:
            st.write(f"- {r}")
    else:
        st.info("Nenhuma recomendação identificada.")
