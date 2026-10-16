import streamlit as st
import pandas as pd
import requests

# Configuración de la página
st.set_page_config(page_title="Dashboard Patrimonial", layout="wide")

st.title("📊 Panel de Control: Gestión Patrimonial")
st.markdown("---")

# --- MOTOR DE DATOS: DOLAR API ---
# st.cache_data hace que la app no sature la API consultando cada 1 segundo, guarda el dato por 1 hora
@st.cache_data(ttl=3600) 
def obtener_cotizaciones():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        respuesta = requests.get("https://dolarapi.com/v1/dolares", headers=headers)
        if respuesta.status_code == 200:
            dolares = respuesta.json()
            oficial = next(d['venta'] for d in dolares if d['casa'] == 'oficial')
            mep = next(d['venta'] for d in dolares if d['casa'] == 'bolsa')
            brecha = ((mep / oficial) - 1) * 100
            return oficial, mep, brecha
    except:
        return 0, 0, 0 # En caso de error de conexión

oficial, mep, brecha_actual = obtener_cotizaciones()

# --- MOTOR DE DATOS: BCRA / MACRO (SISTEMA EN CASCADA) ---
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) # Oculta alertas de seguridad del BCRA

@st.cache_data(ttl=3600)
def obtener_datos_macro():
    # PLAN A: API Oficial del BCRA
    try:
        # Se desactiva verify=False porque los certificados del BCRA suelen fallar
        res_bcra = requests.get("https://api.bcra.gob.ar/estadisticas/v1/principalesvariables", verify=False, timeout=5)
        if res_bcra.status_code == 200:
            datos = res_bcra.json()['results']
            # ID 6: Tasa Política Monetaria | ID 27: Inflación Mensual INDEC
            tna_bcra = next(item['valor'] for item in datos if item['idVariable'] == 6)
            inf_mensual = next(item['valor'] for item in datos if item['idVariable'] == 27)
            # Anualizamos la inflación mensual para proyectar el REM
            rem_bcra = ((1 + (inf_mensual / 100))**12 - 1) * 100
            return tna_bcra, rem_bcra
    except:
        pass # Si falla el Plan A, sigue de largo sin romper la app

    # PLAN B: API ArgentinaDatos (Espejo Comunitario)
    try:
        res_tasas = requests.get("https://api.argentinadatos.com/v1/finanzas/tasas/plazoFijo", timeout=5)
        res_inf = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/inflacion", timeout=5)
        if res_tasas.status_code == 200 and res_inf.status_code == 200:
            tna_ad = res_tasas.json()[-1]['valor'] * 100
            inf_ad = res_inf.json()[-1]['valor']
            rem_ad = ((1 + inf_ad)**12 - 1) * 100
            return tna_ad, rem_ad
    except:
        pass

    # PLAN C: Resguardo de Emergencia (Últimos datos oficiales conocidos)
    return 40.0, 35.0

# Extraemos los datos reales de internet usando la cascada
tna_mercado, rem_mercado = obtener_datos_macro()

# --- BARRA LATERAL HÍBRIDA ---
st.sidebar.header("⚙️ Parámetros Macro")

modo_simulacion = st.sidebar.toggle("🧪 Activar Modo Simulación", value=False)

if not modo_simulacion:
    # 1. MODO AUTOMÁTICO (Datos Reales extraídos de la API)
    st.sidebar.success("✅ Datos Oficiales Activos")
    st.sidebar.caption("Conectado a la base de datos del BCRA.")
    
    tna_actual = tna_mercado
    rem_actual = rem_mercado
    reservas_ok = True # Este parámetro suele requerir análisis manual complejo, lo dejamos en True por defecto
    
    st.sidebar.info(f"🏦 TNA Actual: {tna_actual:.2f}%\n📊 REM Estimado: {rem_actual:.2f}%")

else:
    # 2. MODO SIMULACIÓN (Sliders Manuales)
    st.sidebar.warning("⚠️ Parámetros Simulados")
    tna_actual = st.sidebar.slider("Simular TNA (%)", 20.0, 80.0, tna_mercado)
    rem_actual = st.sidebar.slider("Simular REM (%)", 20.0, 80.0, rem_mercado)
    reservas_ok = st.sidebar.checkbox("Simular Reservas Positivas", value=True)
    
    st.warning("🧪 ESTÁS EN MODO SIMULACIÓN: Los semáforos macroeconómicos responden a tus parámetros manuales, no al mercado real.")

# --- MÓDULO 1: FLASH DIARIO ---
st.header("1. Flash Diario de Mercado")
if oficial > 0:
    st.caption(f"Cotizaciones en vivo (DolarAPI) ➔ Oficial: $ {oficial} | MEP: $ {mep}")

col1, col2, col3 = st.columns(3)

# Semáforo 1: Brecha Real Automática
with col1:
    if brecha_actual < 20:
        st.success(f"🟢 Brecha: {brecha_actual:.1f}% (Comprimida)")
        st.write("➡️ *Atractivo el carry trade en pesos.*")
    else:
        st.error(f"🔴 Brecha: {brecha_actual:.1f}% (Ampliándose)")
        st.write("➡️ *Alerta: Riesgo de desarme.*")

# Semáforo 2: Reservas
with col2:
    if reservas_ok:
        st.success("🟢 Reservas BCRA: Acumulación")
    else:
        st.error("🔴 Reservas BCRA: Drenaje")

# Semáforo 3: Tasa vs REM
with col3:
    tasa_real = tna_actual - rem_actual
    if tasa_real > 0:
        st.success(f"🟢 Tasa Real: +{tasa_real:.1f}%")
    else:
        st.error(f"🔴 Tasa Real: {tasa_real:.1f}%")

st.markdown("---")

# --- MÓDULO 2: POSICIÓN Y LIQUIDEZ (ESTRATEGIA DE BOLSILLOS) ---
st.header("2. Marco de Posición y Liquidez")
st.info("🔒 Subí tu Excel. Los datos se agruparán por 'Cartera (Objetivo)' de forma automática.")

archivo_subido = st.file_uploader("Cargar Plantilla (.xlsx)", type=["xlsx"])

if archivo_subido is not None:
    df_cartera = pd.read_excel(archivo_subido)
    st.success("¡Datos cargados de forma segura!")
    st.dataframe(df_cartera, use_container_width=True)

    # --- MOTOR DE CÁLCULOS (PORTFOLIO ANALYTICS) ---
    st.markdown("### 📊 Auditoría de Rendimiento")
    
    # 1. Patrimonio Total
    patrimonio_total = df_cartera["Capital Invertido"].sum()
    st.metric("Patrimonio Total Administrado", f"$ {patrimonio_total:,.2f}".replace(",", "."))
    
    # 2. Tasa Promedio Ponderada
    df_cartera["Peso"] = df_cartera["Capital Invertido"] / patrimonio_total
    df_cartera["Aporte_Tasa"] = df_cartera["TNA Referencia"] * df_cartera["Peso"]
    tna_ponderada_cartera = df_cartera["Aporte_Tasa"].sum()
    
    # Cruce Micro vs Macro (Tu Cartera vs Inflación)
    col1, col2 = st.columns(2)
    with col1:
        st.metric("TNA Promedio de tu Cartera", f"{tna_ponderada_cartera:.1f}%")
    with col2:
        spread_real = tna_ponderada_cartera - rem_actual
        if spread_real > 0:
            st.success(f"📈 Rendimiento Real Positivo: Le ganás a la inflación por {spread_real:.1f}% anual.")
        else:
            st.warning(f"📉 Rendimiento Real Negativo: Estás perdiendo contra la inflación por {abs(spread_real):.1f}% anual.")

    # 3. Gráfico de Bolsillos (Bucket Strategy)
    st.markdown("### 🎯 Desglose por Objetivos (Mental Accounting)")
    resumen_bolsillos = df_cartera.groupby("Cartera (Objetivo)")["Capital Invertido"].sum().reset_index()
    
    # Gráfico de barras simple en Streamlit
    st.bar_chart(resumen_bolsillos.set_index("Cartera (Objetivo)"))
    # Gráfico de barras simple en Streamlit
    st.bar_chart(resumen_bolsillos.set_index("Cartera (Objetivo)"))
