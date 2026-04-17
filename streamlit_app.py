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
Además, clasifica cada producto como **BALANCIN, MECANICA o PROGRESIVA** según la máquina principal (la de mayor volumen de producción).
""")

# ==========================================
# LISTAS Y DICCIONARIOS DE MÁQUINAS
# ==========================================
MAQUINAS_ESTAMPADO = [
    "P-023", "P-024", "P-025", "P-026", "P-027", "P-028", "P-029", "P-030",
    "BAL-002", "BAL-003", "BAL-005", "BAL-006", "BAL-007", "BAL-008", "BAL-009", 
    "BAL-010", "BAL-011", "BAL-012", "BAL-013", "BAL-014", "BAL-015",
    "P-011", "P-012", "P-013", "P-014", "P-016", "P-017", "P-018", 
    "P-015", "P-019", "P-020", "P-021", "P-022", "GOF01"
]

def clasificar_maquina(maquina):
    """
    Clasifica la máquina según el criterio actualizado de Fumiscor.
    """
    m = str(maquina).upper().strip()
    
    # Todo lo que empiece con BAL es BALANCIN
    if m.startswith('BAL'):
        return 'BALANCIN'
    
    # Listas exactas según la nueva imagen
    mecanicas = ['P-015', 'P-016', 'P-019', 'P-020', 'P-021', 'P-022']
    progresivas = ['P-023', 'P-024', 'P-025', 'P-026', 'P-027']
    
    if m in mecanicas:
        return 'MECANICA'
    if m in progresivas:
        return 'PROGRESIVA'
        
    # Regla general de seguridad por si aparecen prensas que no están en la imagen exacta
    if m.startswith('P-'):
        try:
            num = int(m.split('-')[1])
            # Ahora el límite de las mecánicas llega hasta la 22
            if num <= 22:
                return 'MECANICA'
            else:
                return 'PROGRESIVA'
        except:
            pass
            
    return 'INDEFINIDO'

# ==========================================
# FUNCIONES DE EXTRACCIÓN Y PROCESAMIENTO
# ==========================================
def get_data_from_sql():
    try:
        conn = st.connection("wii_bi", type="sql")
        # Sumamos el volumen para saber cuál es la máquina principal (la que hace más piezas)
        query = """
        SELECT  
            pr.Code as PIEZA, 
            c.Name as MAQUINA,
            SUM(p.Good + p.Rework) as VOLUMEN
        FROM PROD_D_01 p 
        JOIN PRODUCT pr ON p.ProductId = pr.ProductId 
        JOIN CELL c ON p.CellId = c.CellId
        WHERE p.Date >= '2025-01-01'
        GROUP BY pr.Code, c.Name
        """
        df = conn.query(query)
        return df
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return pd.DataFrame()

def procesar_mapeo(df_raw):
    if df_raw.empty:
        return pd.DataFrame()
    
    # 1. Filtrar solo máquinas de Estampado oficiales
    df_filt = df_raw[df_raw['MAQUINA'].isin(MAQUINAS_ESTAMPADO)].copy()
    
    if df_filt.empty:
        st.warning("No se encontró producción en las máquinas de Estampado definidas desde 2025.")
        return pd.DataFrame()

    # 2. Ordenar por Pieza y por Volumen de producción (de mayor a menor)
    df_filt = df_filt.sort_values(by=['PIEZA', 'VOLUMEN'], ascending=[True, False])

    # 3. Determinar el Tipo de cada Pieza basándose en su Máquina Principal
    df_principal = df_filt.drop_duplicates(subset=['PIEZA'], keep='first').copy()
    df_principal['TIPO'] = df_principal['MAQUINA'].apply(clasificar_maquina)
    
    # Creamos un diccionario { 'COD_PIEZA': 'TIPO' } para mapear luego
    mapa_tipos = dict(zip(df_principal['PIEZA'], df_principal['TIPO']))

    # 4. Crear numeración de columnas (Máquina 1, Máquina 2...)
    df_filt['n'] = df_filt.groupby('PIEZA').cumcount() + 1
    df_filt['col_name'] = "MAQUINA " + df_filt['n'].astype(str)

    # 5. Pivotar la tabla
    df_pivot = df_filt.pivot(index='PIEZA', columns='col_name', values='MAQUINA').reset_index()
    df_pivot.columns.name = None
    
    # 6. Agregar columna TIPO y renombrar PIEZA
    df_pivot = df_pivot.rename(columns={'PIEZA': 'CODIGO DE PRODUCTO'})
    df_pivot['TIPO MATRIZ'] = df_pivot['CODIGO DE PRODUCTO'].map(mapa_tipos)
    
    # 7. Reordenar las columnas para que quede: CODIGO | TIPO | MAQUINA 1 | MAQUINA 2 ...
    columnas_maquinas = [col for col in df_pivot.columns if col.startswith('MAQUINA')]
    columnas_finales = ['CODIGO DE PRODUCTO', 'TIPO MATRIZ'] + columnas_maquinas
    df_final = df_pivot[columnas_finales]
    
    return df_final

# ==========================================
# INTERFAZ DE USUARIO
# ==========================================
if st.button("🔍 Extraer Datos y Clasificar Matrices (Desde 2025)", type="primary", use_container_width=True):
    with st.spinner("Consultando SQL, sumando volúmenes y clasificando..."):
        df_raw = get_data_from_sql()
        df_final = procesar_mapeo(df_raw)
        
        if not df_final.empty:
            st.success(f"¡Extracción exitosa! Se procesaron y clasificaron {len(df_final)} productos.")
            
            # Vista previa
            st.dataframe(df_final, use_container_width=True)
            
            # Preparar Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_final.to_excel(writer, index=False, sheet_name='Mapeo_Clasificado')
            
            # Botón de descarga
            st.download_button(
                label="📥 Descargar Excel de Mapeo Clasificado",
                data=output.getvalue(),
                file_name=f"Mapeo_Tipos_Maquinas_2025_{datetime.now().strftime('%d%m%y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
else:
    st.info("Presiona el botón para iniciar la conexión con la base de datos SQL.")

st.divider()
st.caption("Fumiscor S.A. - Herramienta de Mapeo de Planta v2.1")
