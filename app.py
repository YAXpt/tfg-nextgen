import streamlit as st
import pandas as pd
import plotly.express as px
import re
from collections import defaultdict

st.set_page_config(page_title="TFG - Fondos Next Generation", layout="wide")

st.title("Análisis de los Fondos Next Generation EU en España")
col_sub, col_info = st.columns([4, 1])

with col_sub:
    st.markdown("Datos extraídos de la Base de Datos Nacional de Subvenciones (BDNS)")

with col_info:
    with st.popover("ℹ️ Sobre los datos", use_container_width=True):
        st.markdown("""
        **Origen y alcance metodológico**
        * **Fuente:** API pública de la Base de Datos Nacional de Subvenciones (BDNS).
        * **Alcance:** Incluye únicamente **subvenciones y ayudas directas**. No recoge grandes contratos públicos ni licitaciones de infraestructuras (que se tramitan en otras plataformas).
        * **Criterio de extracción:** Los registros han sido filtrados mediante palabras clave vinculadas a los fondos europeos (*Next Generation, PRTR, MRR*, etc.). Por tanto, los datos representan una muestra representativa de las ayudas identificables y pueden no recoger el 100% de los fondos ejecutados.
        * **Actualización:** Base de datos estática extraída en noviembre de 2026.
        """)
        
@st.cache_data
def cargar_datos():
    df = pd.read_parquet("datos_tfg.parquet")
    df['Año'] = pd.to_datetime(df['fechaConcesion'], errors='coerce').dt.year.astype('Int64')
    return df

@st.cache_data
def convertir_a_csv(dataframe):
    return dataframe.to_csv(index=False, sep=';').encode('utf-8-sig')

df = cargar_datos()

# Detectamos la columna de descripción/convocatoria si existe
col_texto = None
for posible in ['convocatoria', 'descripcion', 'titulo']:
    if posible in df.columns:
        col_texto = posible
        break

# --- FUNCIÓN PARA ANALIZAR PESO DE PALABRAS CLAVE ---
STOPWORDS = {
    "para", "como", "entre", "sobre", "desde", "hasta", "mediante", "marco", "plan",
    "recuperacion", "recuperación", "transformacion", "transformación", "resiliencia",
    "next", "generation", "nextgenerationeu", "fondos", "europeos", "union", "unión",
    "europea", "mecanismo", "subvenciones", "subvencion", "subvención", "ayudas", "ayuda",
    "programa", "convocatoria", "bases", "reguladoras", "concesion", "concesión",
    "directa", "destinadas", "destinados", "financiado", "financiadas", "financiados",
    "real", "decreto", "orden", "resolucion", "resolución", "anualidad", "ejercicio",
    "general", "publica", "pública", "nacional", "estatal", "comunidad", "autonoma",
    "autónoma", "gobierno", "ministerio", "consejeria", "consejería", "gestion", "gestión",
    "proyectos", "proyecto", "actuaciones", "medidas", "linea", "línea", "componente",
    "inversion", "inversión", "traves", "través", "ambito", "ámbito", "cargo", "apoyo",
    "prtr", "mrr", "primera", "efectua", "efectúa", "correspondiente", "dentro"
}

@st.cache_data
def calcular_peso_palabras(serie_texto, serie_importe, top_n=12):
    pesos_euros = defaultdict(float)
    conteo = defaultdict(int)
    
    for texto, importe in zip(serie_texto.fillna(""), serie_importe.fillna(0)):
        palabras = set(re.findall(r'[a-záéíóúñü]{4,}', str(texto).lower()))
        for p in palabras:
            if p not in STOPWORDS:
                pesos_euros[p] += importe
                conteo[p] += 1
                
    if not conteo:
        return pd.DataFrame()
        
    df_palabras = pd.DataFrame({
        "Palabra Clave": list(conteo.keys()),
        "Concesiones": list(conteo.values()),
        "Importe Total (€)": [pesos_euros[k] for k in conteo.keys()]
    })
    df_palabras["Importe (M€)"] = df_palabras["Importe Total (€)"] / 1e6
    return df_palabras.sort_values(by="Importe Total (€)", ascending=False).head(top_n)

# --- BARRA LATERAL DE FILTROS CON BOTÓN ---
st.sidebar.header("🔍 Filtros de búsqueda")

with st.sidebar.form(key="form_filtros"):
    busqueda_empresa = st.text_input("Buscar por empresa o beneficiario:")

    busqueda_clave = ""
    if col_texto:
        busqueda_clave = st.text_input(
            f"Buscar palabra clave en {col_texto}:",
            placeholder="Ej: digital, hidrógeno, turismo..."
        )

    ejercicios_disponibles = sorted(df['Año'].dropna().unique().tolist(), reverse=True)
    ejercicios_seleccionados = st.multiselect(
        "Año de concesión:",
        ejercicios_disponibles,
        placeholder="Todos los años"
    )

    instrumentos_disponibles = sorted(df['instrumento'].dropna().unique().tolist())
    instrumentos_seleccionados = st.multiselect(
        "Tipo de instrumento:",
        instrumentos_disponibles,
        placeholder="Todos los instrumentos"
    )

    st.form_submit_button("🔎 Aplicar filtros", type="primary", use_container_width=True)

# --- APLICAR FILTROS ---
df_filtrado = df.copy()

if busqueda_empresa:
    df_filtrado = df_filtrado[df_filtrado['beneficiario'].str.contains(busqueda_empresa, case=False, na=False, regex=False)]

if busqueda_clave and col_texto:
    df_filtrado = df_filtrado[df_filtrado[col_texto].str.contains(busqueda_clave, case=False, na=False, regex=False)]

if ejercicios_seleccionados:
    df_filtrado = df_filtrado[df_filtrado['Año'].isin(ejercicios_seleccionados)]

if instrumentos_seleccionados:
    df_filtrado = df_filtrado[df_filtrado['instrumento'].isin(instrumentos_seleccionados)]

# --- TARJETAS DE KPIs ---
col1, col2, col3, col4 = st.columns(4)

total_concesiones = len(df_filtrado)
total_importe = df_filtrado['importe'].sum()
total_ayuda = df_filtrado['ayudaEquivalente'].sum()
importe_medio = df_filtrado['importe'].mean() if total_concesiones > 0 else 0

col1.metric("Total Concesiones", f"{total_concesiones:,}".replace(",", "."))
col2.metric("Importe Total", f"{total_importe/1e6:,.2f} M€")
col3.metric("Ayuda Equivalente", f"{total_ayuda/1e6:,.2f} M€")
col4.metric("Importe Medio", f"{importe_medio:,.2f} €")

st.divider()

if total_concesiones == 0:
    st.info("No se han encontrado concesiones con los filtros aplicados. Prueba a ampliar la búsqueda.")
    st.stop()

# --- GRÁFICOS INTERACTIVOS ---
g_col1, g_col2 = st.columns(2)

with g_col1:
    st.subheader("📈 Evolución de fondos por año")
    df_ejercicios = df_filtrado.groupby('Año', as_index=False)['importe'].sum()
    df_ejercicios['Importe (M€)'] = df_ejercicios['importe'] / 1e6
    fig_ejercicio = px.bar(
        df_ejercicios, x='Año', y='Importe (M€)',
        text_auto='.1f', color_discrete_sequence=['#1f77b4']
    )
    fig_ejercicio.update_layout(xaxis=dict(type='category'), yaxis_title="Millones de €")
    st.plotly_chart(fig_ejercicio, use_container_width=True)

with g_col2:
    if col_texto:
        st.subheader("🔑 Peso de palabras clave (Top conceptos)")
        df_kw = calcular_peso_palabras(df_filtrado[col_texto], df_filtrado['importe'])
        if not df_kw.empty:
            fig_kw = px.bar(
                df_kw.sort_values(by="Importe (M€)", ascending=True),
                x="Importe (M€)", y="Palabra Clave",
                orientation='h', text_auto='.1f',
                hover_data=["Concesiones"],
                color_discrete_sequence=['#2ca02c']
            )
            fig_kw.update_layout(yaxis_title="", xaxis_title="Millones de € vinculados")
            st.plotly_chart(fig_kw, use_container_width=True)
    elif 'nivel1' in df_filtrado.columns:
        st.subheader("🏛️ Reparto por Administración (Nivel 1)")
        df_admin = df_filtrado.groupby('nivel1', as_index=False)['importe'].sum().nlargest(10, 'importe')
        df_admin['Importe (M€)'] = df_admin['importe'] / 1e6
        fig_admin = px.bar(df_admin, x='Importe (M€)', y='nivel1', orientation='h', text_auto='.1f')
        st.plotly_chart(fig_admin, use_container_width=True)

st.divider()

# --- TABLA DE RESULTADOS INTERACTIVA ---
st.subheader(f"📋 Detalle de concesiones (mostrando las primeras 100 de {total_concesiones:,})")

st.download_button(
    label="📥 Descargar resultados filtrados (CSV)",
    data=convertir_a_csv(df_filtrado),
    file_name="concesiones_nextgen_filtradas.csv",
    mime="text/csv"
)

st.caption("💡 Marca una o varias casillas a la izquierda (máximo 3 a la vez) para comparar sus fichas completas debajo.")

df_vista = df_filtrado.sort_values(by="importe", ascending=False).head(100).reset_index(drop=True)
df_vista.insert(0, "Nº", range(1, len(df_vista) + 1))

columnas_visibles = [c for c in ['Nº', 'fechaConcesion', 'beneficiario', 'instrumento', 'importe', 'ayudaEquivalente', 'urlBR'] if c in df_vista.columns]

evento = st.dataframe(
    df_vista[columnas_visibles],
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="multi-row",
    column_config={
        "Nº": st.column_config.NumberColumn("Nº", format="#%d", width="small"),
        "fechaConcesion": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
        "beneficiario": st.column_config.TextColumn("Beneficiario", width="large"),
        "instrumento": st.column_config.TextColumn("Instrumento", width="medium"),
        "importe": st.column_config.NumberColumn("Importe", format="%.2f €"),
        "ayudaEquivalente": st.column_config.NumberColumn("Ayuda Equiv.", format="%.2f €"),
        "urlBR": st.column_config.LinkColumn("Bases (BOE)", display_text="Ver BOE 🔗")
    }
)

# --- COMPARADOR DE FICHAS EN PARALELO (MÁXIMO 3) ---
MAX_FICHAS = 3
COLORES = [
    ("🔵", "blue"),
    ("🟢", "green"),
    ("🟠", "orange")
]

filas_seleccionadas = evento.selection.rows

if filas_seleccionadas:
    if len(filas_seleccionadas) > MAX_FICHAS:
        st.warning(f"Has seleccionado {len(filas_seleccionadas)} concesiones. Para compararlas en paralelo, solo se muestran las primeras {MAX_FICHAS}.")
        filas_seleccionadas = filas_seleccionadas[:MAX_FICHAS]

    st.markdown(f"### ⚖️ Comparador de concesiones ({len(filas_seleccionadas)}/{MAX_FICHAS})")

    cols = st.columns(len(filas_seleccionadas))

    for i, indice in enumerate(filas_seleccionadas):
        fila = df_vista.iloc[indice]
        emoji, color = COLORES[i]
        num_fila = int(fila["Nº"])
        fecha_str = pd.to_datetime(fila['fechaConcesion']).strftime('%d/%m/%Y') if pd.notna(fila.get('fechaConcesion')) else "-"

        with cols[i]:
            with st.container(border=True):
                st.markdown(f"#### {emoji} :{color}[Fila #{num_fila}]")
                st.markdown(f"**{fila.get('beneficiario', 'No disponible')}**")
                
                st.metric("Importe concedido", f"{fila.get('importe', 0):,.2f} €")
                st.metric("Ayuda equivalente", f"{fila.get('ayudaEquivalente', 0):,.2f} €")
                
                st.markdown(f"**Fecha:** {fecha_str} | **Código:** `{fila.get('codConcesion', '-')}`")
                st.markdown(f"**Instrumento:** {fila.get('instrumento', '-')}")

                if col_texto and pd.notna(fila.get(col_texto)):
                    with st.expander("📄 Ver título de la convocatoria"):
                        st.write(fila[col_texto])

                if 'urlBR' in fila and pd.notna(fila['urlBR']):
                    st.link_button("🔗 Abrir en el BOE", fila['urlBR'], use_container_width=True)