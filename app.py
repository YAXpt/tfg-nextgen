import streamlit as st
import pandas as pd

st.set_page_config(page_title="TFG - Fondos Next Generation", layout="wide")

st.title("🇪🇺 Análisis de los Fondos Next Generation EU en España")
st.markdown("Datos extraídos de la Base de Datos Nacional de Subvenciones (BDNS)")

@st.cache_data 
def cargar_datos():
    # Streamlit lee el archivo Parquet directamente
    return pd.read_parquet("datos_tfg.parquet")

df = cargar_datos()

total_ayuda = df['ayudaEquivalente'].sum()
st.metric(label="Total Ayuda Equivalente Extraída", value=f"{total_ayuda:,.2f} €")

st.subheader("Base de Datos General")
st.dataframe(df.head(100))