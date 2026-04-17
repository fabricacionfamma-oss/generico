import streamlit as st
import pandas as pd
import io
from datetime import datetime

# ==========================================
# CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(page_title="Extractor de Mapeo Estampado", page_icon="📊")

st.title("📊 Extractor de Mapeo: Producto vs. Máquinas")
st.markdown("""
Esta aplicación extrae la relación de **Productos y Máquinas de Estampado** detectadas en la base de datos de producción desde el **01/01/2025**.
""")

# ==========================================
# LISTA DE MÁQUINAS OFICIALES (ESTAMPADO)
# ==========================================
MAQUINAS_ESTAMPADO = [
    "P-023", "P-024", "P-025", "P-026", "P-027", "P-028", "P-029", "P-030",
    "BAL-002", "BAL-003", "BAL-005", "BAL-006", "BAL-007", "BAL-008", "BAL-009", 
    "BAL-010", "BAL-011", "BAL-012", "BAL-013", "BAL-014", "BAL-015",
    "P-011", "P-012", "P-013", "P-014", "P-016", "P-017", "P-018", 
    "P-015", "P-019", "P-020", "P-021", "P-022", "GOF01"
]

# ==========================================
# FUNCIONES DE EXTRACCIÓN Y PROCESAMIENTO
# ==========================================
def get_data_from_sql():
    try:
        conn = st.connection("wii_bi", type="sql")
        # Consulta filtrada desde Enero 2025
        query = """
        SELECT DISTINCT 
            pr.Code as PIEZA, 
            c.Name as MAQUINA
        FROM PROD_D_01 p 
        JOIN PRODUCT pr ON p.ProductId = pr.ProductId 
        JOIN CELL c ON p.CellId = c.CellId
        WHERE p.Date >= '2025-01-01'
        """
        df = conn.query(query)
        return df
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return pd.DataFrame()

def procesar_mapeo(df_raw):
    if df_raw.empty:
        return pd.DataFrame()
    
    # 1. Filtrar solo máquinas de Estampado
    df_filt = df_raw[df_raw['MAQUINA'].isin(MAQUINAS_ESTAMPADO)].copy()
    
    if df_filt.empty:
        st.warning("No se encontró producción en las máquinas de Estampado definidas desde 2025.")
        return pd.DataFrame()

    # 2. Crear numeración de columnas (Máquina 1, Máquina 2...)
    df_filt = df_filt.sort_values(['PIEZA', 'MAQUINA'])
    df_filt['n'] = df_filt.groupby('PIEZA').cumcount() + 1
    df_filt['col_name'] = "MAQUINA " + df_filt['n'].astype(str)

    # 3. Pivotar la tabla
    df_pivot = df_filt.pivot(index='PIEZA', columns='col_name', values='MAQUINA').reset_index()
    df_pivot.columns.name = None
    
    # Renombrar columna principal
    df_pivot = df_pivot.rename(columns={'PIEZA': 'CODIGO DE PRODUCTO'})
    
    return df_pivot

# ==========================================
# INTERFAZ DE USUARIO
# ==========================================
if st.button("🔍 Extraer Datos de Producción (Desde 2025)", type="primary", use_container_width=True):
    with st.spinner("Consultando SQL y organizando máquinas..."):
        df_raw = get_data_from_sql()
        df_final = procesar_mapeo(df_raw)
        
        if not df_final.empty:
            st.success(f"¡Extracción exitosa! Se encontraron {len(df_final)} productos.")
            
            # Vista previa
            st.dataframe(df_final, use_container_width=True)
            
            # Preparar Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_final.to_excel(writer, index=False, sheet_name='Mapeo_2025')
            
            # Botón de descarga
            st.download_button(
                label="📥 Descargar Excel de Mapeo",
                data=output.getvalue(),
                file_name=f"Mapeo_Maquinas_Fumiscor_2025_{datetime.now().strftime('%d%m%y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
else:
    st.info("Presiona el botón para iniciar la conexión con la base de datos SQL.")

st.divider()
st.caption("Fumiscor S.A. - Herramienta de Mantenimiento Técnico v1.0 (Independiente)")
