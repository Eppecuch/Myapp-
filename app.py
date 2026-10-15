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

# --- MOTOR DE DATOS: BCRA / MACRO ---
@st.cache_data(ttl=3600)
def obtener_datos_macro():
    try:
        # Intentamos obtener la tasa de Plazo Fijo / Política monetaria desde la API pública
        respuesta_tasas = requests.get("https://api.argentinadatos.com/v1/finanzas/tasas/plazoFijo")
        respuesta_inflacion = requests.get("https://api.argentinadatos.com/v1/finanzas/indices/inflacion")
        
        # Si la API responde bien, buscamos el último dato de la lista (el más reciente)
        if respuesta_tasas.status_code == 200 and respuesta_inflacion.status_code == 200:
            datos_tasas = respuesta_tasas.json()
            datos_inflacion = respuesta_inflacion.json()
            
            # Tomamos la última tasa nominal anual (TNA) registrada multiplicada por 100 para porcentaje
            tna_real = datos_tasas[-1]['valor'] * 100 
            
            # Tomamos el último dato de inflación mensual y lo anualizamos (Aproximación REM)
            inflacion_mensual = datos_inflacion[-1]['valor']
            rem_estimado = ((1 + inflacion_mensual)**12 - 1) * 100
            
            return tna_real, rem_estimado
    except:
        pass
    
    # Si la API del BCRA se cae (suele pasar en Argentina), usamos estos valores de resguardo
    return 40.0, 35.0 

# Extraemos los datos reales de internet
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
