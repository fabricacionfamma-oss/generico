import streamlit as st
import pandas as pd
import plotly.express as px
from fpdf import FPDF
from datetime import datetime

# ==========================================
# CONFIGURACIÓN DE PÁGINA Y ESTÉTICA FAMMA
# ==========================================
st.set_page_config(page_title="Reporte Gerencial - Soldadura", layout="wide")

# CSS personalizado para emular los colores corporativos
st.markdown("""
    <style>
    .main { background-color: #FAFAFA; }
    h1, h2, h3 { color: #8B1A1A; font-family: 'Arial', sans-serif; }
    .stDataFrame { border: 1px solid #D3D3D3; border-radius: 5px; }
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
        # 1. HORARIOS Y TIEMPO DE APERTURA (FORMATO FAMMA)
        # ==========================================
        st.markdown("### 1. Horarios y Tiempo de Apertura")
        
        # Agrupar por Fecha, Máquina y Turno (si existe)
        groupby_cols = ['Fecha', 'Máquina']
        if 'Turno' in df_sn.columns:
            groupby_cols.insert(1, 'Turno')
            
        df_horarios = df_sn.groupby(groupby_cols).agg(
            Hora_Inicio_Real=('Fecha Inicio', 'min'),
            Hora_Cierre_Real=('Fecha Fin', 'max')
        ).reset_index()
        
        # Cálculo de Apertura Neta
        df_horarios['Apertura Neta Total'] = df_horarios['Hora_Cierre_Real'] - df_horarios['Hora_Inicio_Real']
        
        # Formatear a strings (HH:MM y HH:MM hs)
        df_horarios['Hora Inicio'] = df_horarios['Hora_Inicio_Real'].dt.strftime('%H:%M')
        df_horarios['Hora Cierre'] = df_horarios['Hora_Cierre_Real'].dt.strftime('%H:%M')
        
        def format_timedelta(td):
            if pd.isnull(td): return "00:00 hs"
            total_seconds = int(td.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            return f"{hours:02d}:{minutes:02d} hs"
            
        df_horarios['Apertura Neta'] = df_horarios['Apertura Neta Total'].apply(format_timedelta)
        
        # Ordenar columnas para mostrar
        cols_display = ['Fecha', 'Máquina'] + (['Turno'] if 'Turno' in df_sn.columns else []) + ['Hora Inicio', 'Hora Cierre', 'Apertura Neta']
        st.dataframe(df_horarios[cols_display], use_container_width=True)

        # ==========================================
        # 2. OPERARIOS HORA POR HORA
        # ==========================================
        st.markdown("### 2. Trazabilidad de Operarios (Hora por Hora)")
        
        # Filtrar registros válidos con operadores
        df_ops = df_sn.dropna(subset=['Operador', 'Fecha Inicio']).copy()
        
        # Crear la "Franja Horaria" redondeando la hora hacia abajo
        df_ops['Hora_Trun'] = df_ops['Fecha Inicio'].dt.floor('h') # Redondea a la hora exacta (ej. 06:00:00)
        df_ops['Franja Horaria'] = df_ops['Hora_Trun'].dt.strftime('%H:00') + " - " + (df_ops['Hora_Trun'] + pd.Timedelta(hours=1)).dt.strftime('%H:00')
        
        # Agrupar para ver quién estuvo en cada máquina en cada franja
        df_operarios_hora = df_ops.groupby(['Fecha', 'Máquina', 'Franja Horaria'])['Operador'].unique().apply(lambda x: " / ".join(x)).reset_index()
        df_operarios_hora = df_operarios_hora.sort_values(by=['Fecha', 'Máquina', 'Franja Horaria'])
        
        st.dataframe(df_operarios_hora, use_container_width=True)

        # ==========================================
        # 3. TENDENCIA DE FALLAS POR ÁREA
        # ==========================================
        st.markdown("### 3. Cuadro de Tendencia: Tiempo de Falla por Área")
        
        df_fallas = df_sn[df_sn['Nivel Evento 1'] == 'FALLAS'].copy()
        
        if not df_fallas.empty:
            df_tendencia = df_fallas.groupby(['Fecha', 'Nivel Evento 2'])['Tiempo (Min)'].sum().reset_index()
            df_tendencia.rename(columns={'Nivel Evento 2': 'Área'}, inplace=True)
            
            colores_famma = ['#8B1A1A', '#CD5C5C', '#D2691E', '#FF8C00', '#A52A2A']
            fig = px.bar(df_tendencia, x='Fecha', y='Tiempo (Min)', color='Área', 
                         title='Evolución Diaria de Fallas (Minutos)',
                         barmode='group',
                         color_discrete_sequence=colores_famma)
            
            fig.update_layout(plot_bgcolor='white', paper_bgcolor='white', font_color='#333')
            st.plotly_chart(fig, use_container_width=True)
            
            # ==========================================
            # 4. TABLA DIARIA DE FALLAS Y DETALLE
            # ==========================================
            st.markdown("### 4. Detalle de Tiempos Perdidos")
            
            df_detalle = df_fallas[['Fecha', 'Máquina', 'Nivel Evento 2', 'Nivel Evento 3', 'Tiempo (Min)']].dropna(how='all')
            df_detalle.rename(columns={'Nivel Evento 2': 'Área', 'Nivel Evento 3': 'Detalle de Falla Registrada'}, inplace=True)
            df_detalle = df_detalle.sort_values(['Fecha', 'Tiempo (Min)'], ascending=[False, False])
            
            st.dataframe(df_detalle, use_container_width=True)
            
            # ==========================================
            # 5. EXPORTACIÓN A PDF (Ajustada a la nueva info)
            # ==========================================
            st.markdown("---")
            st.markdown("### Generar Reporte PDF")
            
            def generar_pdf(df_h, df_op, df_d):
                pdf = FPDF()
                pdf.add_page()
                
                # Título
                pdf.set_font("Arial", 'B', 16)
                pdf.set_text_color(139, 26, 26)
                pdf.cell(190, 10, txt="FAMMA - REPORTE GERENCIAL DE SOLDADURA", ln=True, align='C')
                
                pdf.set_font("Arial", 'B', 12)
                pdf.set_text_color(50, 50, 50)
                pdf.cell(190, 10, txt="SECCION: CELDAS NUEVAS RENAULT", ln=True, align='C')
                pdf.ln(5)
                
                # 1. Horarios
                pdf.set_font("Arial", 'B', 12)
                pdf.set_text_color(139, 26, 26)
                pdf.cell(190, 8, txt="1. Horarios y Apertura Neta", ln=True)
                pdf.set_font("Arial", '', 9)
                pdf.set_text_color(0, 0, 0)
                for i, row in df_h.iterrows():
                    txt_h = f"{row['Fecha']} | {row['Máquina']} | Ini: {row['Hora Inicio']} - Fin: {row['Hora Cierre']} | Neta: {row['Apertura Neta']}"
                    pdf.cell(190, 6, txt=txt_h, ln=True)
                pdf.ln(5)
                
                # 2. Fallas
                pdf.set_font("Arial", 'B', 12)
                pdf.set_text_color(139, 26, 26)
                pdf.cell(190, 8, txt="2. Detalle de Fallas Registradas", ln=True)
                pdf.set_font("Arial", '', 8)
                pdf.set_text_color(0, 0, 0)
                for i, row in df_d.iterrows():
                    detalle = str(row['Detalle de Falla Registrada']).encode('latin-1', 'replace').decode('latin-1')
                    area = str(row['Área']).encode('latin-1', 'replace').decode('latin-1')
                    txt_falla = f"{row['Fecha']} | {row['Máquina']} | {area} | {row['Tiempo (Min)']} min | {detalle}"
                    pdf.cell(190, 5, txt=txt_falla[:115], ln=True)
                    
                return pdf.output(dest='S').encode('latin-1')
            
            pdf_data = generar_pdf(df_horarios, df_operarios_hora, df_detalle)
            
            st.download_button(
                label="📥 Descargar Reporte en PDF",
                data=pdf_data,
                file_name=f"Reporte_Completo_CeldasNuevas_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf"
            )
            
        else:
            st.success("¡Excelente! No se registraron fallas para el período seleccionado.")
            
    else:
        st.error("El archivo cargado no contiene la columna 'Fábrica'.")
