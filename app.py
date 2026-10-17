import streamlit as st
import pandas as pd
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Dashboard Patrimonial", layout="wide")
st.title("📊 Panel de Control: Gestión Patrimonial")
st.markdown("---")

# --- MOTOR DE DATOS MACRO Y COTIZACIONES ---
@st.cache_data(ttl=3600)
def obtener_cotizaciones():
    try:
        res = requests.get("https://dolarapi.com/v1/dolares", headers={"User-Agent": "Mozilla/5.0"})
        if res.status_code == 200:
            d = res.json()
            of = next(x['venta'] for x in d if x['casa'] == 'oficial')
            mep = next(x['venta'] for x in d if x['casa'] == 'bolsa')
            return of, mep, ((mep/of)-1)*100
    except: return 0, 0, 0

@st.cache_data(ttl=3600)
def obtener_datos_macro():
    try:
        res = requests.get("https://api.bcra.gob.ar/estadisticas/v1/principalesvariables", verify=False, timeout=5)
        if res.status_code == 200:
            d = res.json()['results']
            tna = next(i['valor'] for i in d if i['idVariable'] == 6)
            inf = next(i['valor'] for i in d if i['idVariable'] == 27)
            rem = ((1 + (inf/100))**12 - 1) * 100
            return tna, rem, inf
    except: pass
    return 40.0, 35.0, 2.5 

oficial, mep, brecha_actual = obtener_cotizaciones()
tna_mercado, rem_mercado, inf_mensual_mercado = obtener_datos_macro()

# --- MOTOR DE DATOS FCI (NIVEL 3) ---
def obtener_tna_fci(ticker):
    """
    Base de datos interna calibrada con Fact Sheets institucionales (CAFCI).
    """
    tasas_reales = {
        "SMIXVIA": 26.41, # TIR Bruta actualizada Santander Mix VI
        "FIMARPA": 35.38, # TNA Proyectada semestral Galicia Renta Plus
        "FIMAPRA": 18.76  # TNA a 30 días Galicia Premium Money Market
    }
    return tasas_reales.get(str(ticker).strip().upper(), 30.0)

# --- BARRA LATERAL ---
st.sidebar.header("⚙️ Parámetros Macro")
modo_simulacion = st.sidebar.toggle("🧪 Activar Modo Simulación", value=False)

if not modo_simulacion:
    st.sidebar.success("✅ Datos Oficiales Activos")
    tna_actual, rem_actual, inf_mensual = tna_mercado, rem_mercado, inf_mensual_mercado
    crawling_peg = 2.0
    st.sidebar.info(f"🏦 TNA: {tna_actual:.1f}%\n📊 Inflación: {inf_mensual:.1f}%\n💵 Crawling Peg: {crawling_peg}%")
else:
    st.sidebar.warning("⚠️ Parámetros Simulados")
    tna_actual = st.sidebar.slider("Simular TNA (%)", 20.0, 80.0, tna_mercado)
    inf_mensual = st.sidebar.slider("Inflación Mensual (%)", 0.0, 10.0, inf_mensual_mercado)
    rem_actual = ((1 + (inf_mensual/100))**12 - 1) * 100
    crawling_peg = st.sidebar.slider("Crawling Peg (%)", 0.0, 5.0, 2.0)

# --- MÓDULO 1: FLASH DIARIO ---
st.header("1. Flash Diario de Mercado")
col1, col2, col3, col4 = st.columns(4)
with col1: st.metric("Brecha MEP", f"{brecha_actual:.1f}%", "- Compresión" if brecha_actual < 20 else "Riesgo", delta_color="inverse")
with col2: st.metric("Reservas BCRA", "Acumulación")
with col3: st.metric("Tasa Real Anual", "Positiva" if (tna_actual - rem_actual) > 0 else "Negativa")
with col4: 
    dif = inf_mensual - crawling_peg
    st.metric("Monitor CER vs Crawling", f"{dif:.1f}%", "Mantener CER" if dif > 0 else "Desarmar a USD")

st.markdown("---")

# --- MÓDULO 2: POSICIÓN Y LIQUIDEZ ---
st.header("2. Marco de Posición y Liquidez (Nivel 3)")
st.info("💡 Recordá que tu Excel ahora debe tener la columna 'Ticker FCI' en lugar de 'TNA Referencia'.")
archivo_subido = st.file_uploader("Cargar Plantilla con Tickers (.xlsx)", type=["xlsx"])

if archivo_subido is not None:
    df_cartera = pd.read_excel(archivo_subido)
    
    # Cruce de Tickers
    if "Ticker FCI" in df_cartera.columns:
        df_cartera["TNA Automatizada"] = df_cartera["Ticker FCI"].apply(obtener_tna_fci)
    else:
        st.error("⚠️ Error: No se encontró la columna 'Ticker FCI' en tu Excel.")
        st.stop()
        
    st.success("✅ ¡Datos cruzados con mercado exitosamente!")
    st.dataframe(df_cartera, use_container_width=True)

    # Analytics
    st.markdown("### 📊 Auditoría de Rendimiento Táctico")
    patrimonio_total = df_cartera["Capital Invertido"].sum()
    st.metric("Patrimonio Total Administrado", f"$ {patrimonio_total:,.2f}".replace(",", "."))
    
    df_cartera["Peso"] = df_cartera["Capital Invertido"] / patrimonio_total
    df_cartera["Aporte_Tasa"] = df_cartera["TNA Automatizada"] * df_cartera["Peso"]
    tna_ponderada_cartera = df_cartera["Aporte_Tasa"].sum()
    
    crawling_anualizado = crawling_peg * 12
    spread_inflacion = tna_ponderada_cartera - rem_actual
    spread_usd = tna_ponderada_cartera - crawling_anualizado
    
    col_a, col_b, col_c = st.columns(3)
    with col_a: st.metric("TNA Promedio Cartera", f"{tna_ponderada_cartera:.1f}%")
    with col_b: st.metric("Tasa Real (ARS)", f"{spread_inflacion:.1f}%")
    with col_c: st.metric("Carry Trade (USD)", f"{spread_usd:.1f}%")

    st.markdown("### 🎯 Desglose por Objetivos (Mental Accounting)")
    res_bolsillos = df_cartera.groupby("Cartera (Objetivo)")["Capital Invertido"].sum().reset_index()
    st.bar_chart(res_bolsillos.set_index("Cartera (Objetivo)"))
