import streamlit as st
import pandas as pd
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Dashboard Patrimonial", layout="wide")
st.title("📊 Panel de Control: Gestión Patrimonial")
st.markdown("---")

# --- MOTOR DE DATOS: DOLAR API ---
@st.cache_data(ttl=3600)
def obtener_cotizaciones():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get("https://dolarapi.com/v1/dolares", headers=headers)
        if res.status_code == 200:
            dolares = res.json()
            oficial = next(d['venta'] for d in dolares if d['casa'] == 'oficial')
            mep = next(d['venta'] for d in dolares if d['casa'] == 'bolsa')
            brecha = ((mep / oficial) - 1) * 100
            return oficial, mep, brecha
    except:
        return 0, 0, 0

# --- MOTOR DE DATOS: BCRA / MACRO ---
@st.cache_data(ttl=3600)
def obtener_datos_macro():
    try:
        res_bcra = requests.get("https://api.bcra.gob.ar/estadisticas/v1/principalesvariables", verify=False, timeout=5)
        if res_bcra.status_code == 200:
            datos = res_bcra.json()['results']
            tna_bcra = next(item['valor'] for item in datos if item['idVariable'] == 6)
            inf_mensual = next(item['valor'] for item in datos if item['idVariable'] == 27)
            rem_bcra = ((1 + (inf_mensual / 100))**12 - 1) * 100
            return tna_bcra, rem_bcra, inf_mensual
    except: pass
    
    try:
        res_t = requests.get("https://api.argentinadatos.com/v1/finanzas/tasas/plazoFijo", timeout=5)
        res_i = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/inflacion", timeout=5)
        if res_t.status_code == 200 and res_i.status_code == 200:
            tna_ad = res_t.json()[-1]['valor'] * 100
            inf_mensual_ad = res_i.json()[-1]['valor']
            rem_ad = ((1 + inf_mensual_ad)**12 - 1) * 100
            return tna_ad, rem_ad, (inf_mensual_ad * 100)
    except: pass
    
    return 40.0, 35.0, 2.5 

oficial, mep, brecha_actual = obtener_cotizaciones()
tna_mercado, rem_mercado, inf_mensual_mercado = obtener_datos_macro()

# --- BARRA LATERAL HÍBRIDA ---
st.sidebar.header("⚙️ Parámetros Macro")
modo_simulacion = st.sidebar.toggle("🧪 Activar Modo Simulación", value=False)

if not modo_simulacion:
    st.sidebar.success("✅ Datos Oficiales Activos")
    tna_actual = tna_mercado
    rem_actual = rem_mercado
    inf_mensual = inf_mensual_mercado
    crawling_peg = 2.0
    reservas_ok = True
    st.sidebar.info(f"🏦 TNA: {tna_actual:.1f}%\n📊 Inflación (Mensual): {inf_mensual:.1f}%\n💵 Crawling Peg: {crawling_peg}%")
else:
    st.sidebar.warning("⚠️ Parámetros Simulados")
    tna_actual = st.sidebar.slider("Simular TNA (%)", 20.0, 80.0, tna_mercado)
    inf_mensual = st.sidebar.slider("Inflación Mensual (%)", 0.0, 10.0, inf_mensual_mercado)
    rem_actual = ((1 + (inf_mensual/100))**12 - 1) * 100
    crawling_peg = st.sidebar.slider("Crawling Peg (%)", 0.0, 5.0, 2.0)
    reservas_ok = st.sidebar.checkbox("Reservas Positivas", value=True)

# --- MÓDULO 1: FLASH DIARIO ---
st.header("1. Flash Diario de Mercado")
if oficial > 0: st.caption(f"Cotizaciones ➔ Oficial: $ {oficial} | MEP: $ {mep}")

col1, col2, col3, col4 = st.columns(4)

with col1:
    if brecha_actual < 20: st.success(f"🟢 Brecha: {brecha_actual:.1f}%")
    else: st.error(f"🔴 Brecha: {brecha_actual:.1f}%")

with col2:
    if reservas_ok: st.success("🟢 Reservas: Acumulación")
    else: st.error("🔴 Reservas: Drenaje")

with col3:
    if (tna_actual - rem_actual) > 0: st.success("🟢 Tasa Real Anual: Positiva")
    else: st.error("🔴 Tasa Real Anual: Negativa")

with col4:
    diferencia = inf_mensual - crawling_peg
    if diferencia > 0: st.success(f"🟢 Monitor CER: Favorable (+{diferencia:.1f}%)")
    elif diferencia > -0.5: st.warning(f"🟡 Monitor CER: Alerta ({diferencia:.1f}%)")
    else: st.error(f"🔴 Monitor CER: Desarmar ({diferencia:.1f}%)")

st.markdown("---")

# --- MÓDULO 2: POSICIÓN Y LIQUIDEZ ---
st.header("2. Marco de Posición y Liquidez")
st.info("🔒 Subí tu Excel. Los datos se agruparán por 'Cartera (Objetivo)' de forma automática.")

archivo_subido = st.file_uploader("Cargar Plantilla (.xlsx)", type=["xlsx"])

if archivo_subido is not None:
    df_cartera = pd.read_excel(archivo_subido)
    st.success("¡Datos cargados de forma segura!")
    st.dataframe(df_cartera, use_container_width=True)

    st.markdown("### 📊 Auditoría de Rendimiento Táctico")
    patrimonio_total = df_cartera["Capital Invertido"].sum()
    st.metric("Patrimonio Total Administrado", f"$ {patrimonio_total:,.2f}".replace(",", "."))
    
    df_cartera["Peso"] = df_cartera["Capital Invertido"] / patrimonio_total
    df_cartera["Aporte_Tasa"] = df_cartera["TNA Referencia"] * df_cartera["Peso"]
    tna_ponderada_cartera = df_cartera["Aporte_Tasa"].sum()
    
    crawling_anualizado = crawling_peg * 12
    spread_inflacion = tna_ponderada_cartera - rem_actual
    spread_usd = tna_ponderada_cartera - crawling_anualizado
    
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("TNA Promedio Cartera", f"{tna_ponderada_cartera:.1f}%")
    with col_b:
        if spread_inflacion > 0:
            st.success(f"📈 Tasa Real (ARS): +{spread_inflacion:.1f}%")
        else:
            st.warning(f"📉 Tasa Real (ARS): {spread_inflacion:.1f}%")
    with col_c:
        if spread_usd > 0:
            st.success(f"💵 Carry Trade (USD): +{spread_usd:.1f}%")
        else:
            st.error(f"⚠️ Peligro Cambiario: {spread_usd:.1f}%")

    st.markdown("### 🎯 Desglose por Objetivos (Mental Accounting)")
    resumen_bolsillos = df_cartera.groupby("Cartera (Objetivo)")["Capital Invertido"].sum().reset_index()
    st.bar_chart(resumen_bolsillos.set_index("Cartera (Objetivo)"))
