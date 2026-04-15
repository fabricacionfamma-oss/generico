import streamlit as st
import pandas as pd
import plotly.express as px
from fpdf import FPDF
import base64
from datetime import datetime

# ==========================================
# CONFIGURACIÓN DE PÁGINA Y ESTÉTICA FAMMA
# ==========================================
st.set_page_config(page_title="Reporte Gerencial - Soldadura", layout="wide")

# CSS personalizado para emular los colores corporativos del PDF de referencia
st.markdown("""
    <style>
    .main { background-color: #FAFAFA; }
    h1, h2, h3 { color: #8B1A1A; font-family: 'Arial', sans-serif; }
    .stDataFrame { border: 1px solid #D3D3D3; border-radius: 5px; }
    div[data-testid="stMetricValue"] { color: #A52A2A; }
    </style>
""", unsafe_allow_html=True)

st.title("FAMMA: REPORTE GERENCIAL - SOLDADURA")
st.subheader("Análisis de Grupo: CELDAS NUEVAS RENAULT")
st.markdown("---")

# ==========================================
# CARGA DE ARCHIVO
# ==========================================
uploaded_file = st.file_uploader("Sube el archivo Excel o CSV extraído del sistema", type=['csv', 'xlsx'])

if uploaded_file:
    # Leer archivo
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    
    if 'Fábrica' in df.columns:
        # Filtrar por las Celdas Nuevas (Soldadura Nueva)
        df_sn = df[df['Fábrica'] == 'Soldadura Nueva'].copy()
        
        # Limpieza y conversión de fechas
        df_sn['Fecha Inicio'] = pd.to_datetime(df_sn['Fecha Inicio'], errors='coerce')
        df_sn['Fecha Fin'] = pd.to_datetime(df_sn['Fecha Fin'], errors='coerce')
        df_sn['Fecha'] = df_sn['Fecha Inicio'].dt.date
        
        # ==========================================
        # 1. CALENDARIO: INICIO Y CIERRE POR DÍA
        # ==========================================
        st.markdown("### 1. Horarios y Tiempo de Apertura (Por Día)")
        
        df_horarios = df_sn.groupby('Fecha').agg(
            Hora_Inicio=('Fecha Inicio', 'min'),
            Hora_Cierre=('Fecha Fin', 'max')
        ).reset_index()
        
        df_horarios['Hora_Inicio'] = df_horarios['Hora_Inicio'].dt.strftime('%H:%M:%S')
        df_horarios['Hora_Cierre'] = df_horarios['Hora_Cierre'].dt.strftime('%H:%M:%S')
        
        st.dataframe(df_horarios, use_container_width=True)

        # ==========================================
        # 2. TENDENCIA DE FALLAS POR ÁREA
        # ==========================================
        st.markdown("### 2. Cuadro de Tendencia: Tiempo de Falla por Área")
        
        # Filtrar solo eventos que sean FALLAS
        df_fallas = df_sn[df_sn['Nivel Evento 1'] == 'FALLAS'].copy()
        
        if not df_fallas.empty:
            df_tendencia = df_fallas.groupby(['Fecha', 'Nivel Evento 2'])['Tiempo (Min)'].sum().reset_index()
            df_tendencia.rename(columns={'Nivel Evento 2': 'Área'}, inplace=True)
            
            # Paleta de colores cálida estilo reporte FAMMA (Marrones, Naranjas, Rojos)
            colores_famma = ['#8B1A1A', '#CD5C5C', '#D2691E', '#FF8C00', '#A52A2A']
            
            fig = px.bar(df_tendencia, x='Fecha', y='Tiempo (Min)', color='Área', 
                         title='Evolución Diaria de Fallas (Minutos)',
                         barmode='group',
                         color_discrete_sequence=colores_famma)
            
            fig.update_layout(plot_bgcolor='white', paper_bgcolor='white', font_color='#333')
            st.plotly_chart(fig, use_container_width=True)
            
            # ==========================================
            # 3. TABLA DIARIA DE FALLAS Y DETALLE
            # ==========================================
            st.markdown("### 3. Detalle de Tiempos Perdidos")
            
            df_detalle = df_fallas[['Fecha', 'Máquina', 'Nivel Evento 2', 'Nivel Evento 3', 'Tiempo (Min)']].dropna(how='all')
            df_detalle.rename(columns={'Nivel Evento 2': 'Área', 'Nivel Evento 3': 'Detalle de Falla Registrada'}, inplace=True)
            df_detalle = df_detalle.sort_values(['Fecha', 'Tiempo (Min)'], ascending=[False, False])
            
            st.dataframe(df_detalle, use_container_width=True)
            
            # ==========================================
            # 4. EXPORTACIÓN A PDF
            # ==========================================
            st.markdown("---")
            st.markdown("### Generar Reporte")
            
            # Función para crear el PDF estructurado
            def generar_pdf(df_h, df_d):
                pdf = FPDF()
                pdf.add_page()
                
                # Título
                pdf.set_font("Arial", 'B', 16)
                pdf.set_text_color(139, 26, 26) # Rojo Oscuro FAMMA
                pdf.cell(190, 10, txt="FAMMA - REPORTE GERENCIAL DE SOLDADURA", ln=True, align='C')
                
                pdf.set_font("Arial", 'B', 12)
                pdf.set_text_color(50, 50, 50)
                pdf.cell(190, 10, txt="SECCION: CELDAS NUEVAS RENAULT", ln=True, align='C')
                pdf.ln(5)
                
                # Sección Horarios
                pdf.set_font("Arial", 'B', 12)
                pdf.set_text_color(139, 26, 26)
                pdf.cell(190, 10, txt="1. Horarios de Apertura y Cierre", ln=True)
                
                pdf.set_font("Arial", '', 10)
                pdf.set_text_color(0, 0, 0)
                for i, row in df_h.iterrows():
                    pdf.cell(190, 8, txt=f"Dia: {row['Fecha']} | Inicio: {row['Hora_Inicio']} | Cierre: {row['Hora_Cierre']}", ln=True)
                    
                pdf.ln(5)
                
                # Sección Detalle de Fallas
                pdf.set_font("Arial", 'B', 12)
                pdf.set_text_color(139, 26, 26)
                pdf.cell(190, 10, txt="2. Detalle de Fallas Diarias Registradas", ln=True)
                
                pdf.set_font("Arial", '', 9)
                pdf.set_text_color(0, 0, 0)
                for i, row in df_d.iterrows():
                    # Formatear el texto de la falla para evitar caracteres especiales rotos
                    detalle = str(row['Detalle de Falla Registrada']).encode('latin-1', 'replace').decode('latin-1')
                    area = str(row['Área']).encode('latin-1', 'replace').decode('latin-1')
                    txt_falla = f"{row['Fecha']} | {row['Máquina']} | {area} | {row['Tiempo (Min)']} min | {detalle}"
                    pdf.cell(190, 6, txt=txt_falla[:100], ln=True) # Truncado para no salirse del margen
                    
                return pdf.output(dest='S').encode('latin-1')
            
            pdf_data = generar_pdf(df_horarios, df_detalle)
            
            st.download_button(
                label="📥 Descargar Reporte en PDF",
                data=pdf_data,
                file_name=f"Reporte_CeldasNuevas_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf"
            )
            
        else:
            st.success("¡Excelente! No se registraron fallas para el período seleccionado en las Celdas Nuevas.")
            
    else:
        st.error("El archivo cargado no parece contener la columna 'Fábrica'. Por favor, asegúrate de utilizar el reporte del sistema estándar.")
