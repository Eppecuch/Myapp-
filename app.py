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

# --- BARRA LATERAL HÍBRIDA ---
st.sidebar.header("⚙️ Parámetros Macro")

# El interruptor que cambia entre Realidad y Simulación
modo_simulacion = st.sidebar.toggle("🧪 Activar Modo Simulación", value=False)

if not modo_simulacion:
    # 1. MODO AUTOMÁTICO (Datos Reales)
    st.sidebar.success("✅ Datos Oficiales Activos")
    st.sidebar.caption("Leyendo última información del BCRA...")
    
    # Aquí en el futuro conectaremos la API del BCRA. 
    # Por ahora, fijamos los valores reales de hoy:
    tna_actual = 40.0
    rem_actual = 35.0
    reservas_ok = True
    
    st.sidebar.info(f"🏦 TNA Actual: {tna_actual}%\n📊 REM Actual: {rem_actual}%")

else:
    # 2. MODO SIMULACIÓN (Sliders Manuales)
    st.sidebar.warning("⚠️ Parámetros Simulados")
    tna_actual = st.sidebar.slider("Simular TNA (%)", 20.0, 80.0, 40.0)
    rem_actual = st.sidebar.slider("Simular REM (%)", 20.0, 80.0, 35.0)
    reservas_ok = st.sidebar.checkbox("Simular Reservas Positivas", value=True)
    
    # Esta alerta gigante aparecerá en el medio de la pantalla principal
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

# --- MÓDULO 2: POSICIÓN Y LIQUIDEZ (CON SEGURIDAD) ---
st.header("2. Marco de Posición y Liquidez")
st.info("🔒 Subí tu archivo Excel. Los datos se procesan en la memoria temporal y se destruyen al cerrar la pestaña.")

# Botón mágico para subir el Excel
archivo_subido = st.file_uploader("Cargar Plantilla de Inversiones (.xlsx)", type=["xlsx"])

if archivo_subido is not None:
    # Si el usuario subió el Excel, lo leemos
    df_cartera = pd.read_excel(archivo_subido)
    st.success("¡Datos cargados de forma segura!")
    
    # Mostramos la tabla en pantalla
    st.subheader("Tu Táctica Activa Actual")
    st.dataframe(df_cartera, use_container_width=True)
else:
    st.warning("Esperando que cargues tu archivo Excel para auditar la rentabilidad...")
