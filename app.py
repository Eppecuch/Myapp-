import streamlit as st
import pandas as pd

# Configuración de la página
st.set_page_config(page_title="Dashboard Patrimonial", layout="wide")

st.title("📊 Panel de Control: Gestión Patrimonial")
st.markdown("---")

# --- MÓDULO 1: FLASH DIARIO (SEMÁFOROS) ---
st.header("1. Flash Diario de Mercado")
st.caption("Semáforos de riesgo sistémico (Simulación interactiva)")

# Usamos la barra lateral para simular la entrada de datos (luego esto será automático con APIs)
st.sidebar.header("Panel de Control Manual")
st.sidebar.caption("Ajustá los valores para probar los semáforos")
brecha_actual = st.sidebar.slider("Brecha Cambiaria (%)", 0.0, 50.0, 15.0)
tna_actual = st.sidebar.slider("Tasa Política Monetaria (TNA %)", 20.0, 60.0, 40.0)
rem_actual = st.sidebar.slider("Inflación REM Anualizada (%)", 20.0, 80.0, 35.0)
reservas_ok = st.sidebar.checkbox("Reservas BCRA (Acumulación Positiva)", value=True)

col1, col2, col3 = st.columns(3)

# Lógica del Semáforo: Brecha
with col1:
    if brecha_actual < 20:
        st.success(f"🟢 Brecha: {brecha_actual}% (Comprimida/Estable)")
        st.write("➡️ *Atractivo el carry trade en pesos.*")
    else:
        st.error(f"🔴 Brecha: {brecha_actual}% (Ampliándose)")
        st.write("➡️ *Alerta: Riesgo devaluatorio.*")

# Lógica del Semáforo: Reservas
with col2:
    if reservas_ok:
        st.success("🟢 Reservas BCRA: Acumulación")
        st.write("➡️ *Respaldo del esquema cambiario.*")
    else:
        st.error("🔴 Reservas BCRA: Drenaje")
        st.write("➡️ *Alerta: Riesgo de salto discrecional.*")

# Lógica del Semáforo: Tasa vs REM
with col3:
    tasa_real = tna_actual - rem_actual
    if tasa_real > 0:
        st.success(f"🟢 Tasa Real: +{tasa_real:.1f}%")
        st.write("➡️ *Tasa positiva frente al crawling peg/REM.*")
    else:
        st.error(f"🔴 Tasa Real: {tasa_real:.1f}%")
        st.write("➡️ *Tasa negativa frente a expectativas.*")

st.markdown("---")

# --- MÓDULO 2: POSICIÓN Y LIQUIDEZ ---
st.header("2. Marco de Posición y Liquidez")

col_cap1, col_cap2 = st.columns(2)
col_cap1.metric("Capital Base Inicial", "$ 14.822.288,84")
col_cap2.metric("Valuación MTM", "Auditoría Activa")

st.subheader("Táctica Activa Actual")
# Creamos una tabla de ejemplo con tu fondo
datos_fondo = pd.DataFrame({
    "Activo": ["FCI Supergestión Mix VI"],
    "Entidad": ["Santander"],
    "Capital Invertido": ["$ 1.000.000,00"],
    "TNA Referencia": ["29%"],
    "Fecha Suscripción": ["21/09/26"]
})
st.table(datos_fondo)
