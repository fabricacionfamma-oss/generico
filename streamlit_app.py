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
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    
    if 'Fábrica' in df.columns:
        # Filtrar por Soldadura Nueva
        df_sn = df[df['Fábrica'] == 'Soldadura Nueva'].copy()
        
        # Limpieza de fechas
        df_sn['Fecha Inicio'] = pd.to_datetime(df_sn['Fecha Inicio'], errors='coerce')
        df_sn['Fecha Fin'] = pd.to_datetime(df_sn['Fecha Fin'], errors='coerce')
        df_sn['Fecha'] = df_sn['Fecha Inicio'].dt.date
        
        st.success(f"Datos cargados correctamente. Se procesaron {len(df_sn)} registros de Celdas Nuevas.")

        # ==========================================
        # VISUALIZACIONES RÁPIDAS EN PANTALLA
        # ==========================================
        st.markdown("### Previsualización Rápida de Fallas")
        df_fallas = df_sn[df_sn['Nivel Evento 1'] == 'FALLAS'].copy()
        
        if not df_fallas.empty:
            df_tendencia = df_fallas.groupby(['Fecha', 'Nivel Evento 2'])['Tiempo (Min)'].sum().reset_index()
            df_tendencia.rename(columns={'Nivel Evento 2': 'Área'}, inplace=True)
            colores_famma = ['#8B1A1A', '#CD5C5C', '#D2691E', '#FF8C00', '#A52A2A']
            fig = px.bar(df_tendencia, x='Fecha', y='Tiempo (Min)', color='Área', 
                         title='Tendencia de Fallas', barmode='group', color_discrete_sequence=colores_famma)
            fig.update_layout(plot_bgcolor='white', paper_bgcolor='white')
            st.plotly_chart(fig, use_container_width=True)

        # ==========================================
        # MOTOR DE EXPORTACIÓN A PDF (AVANZADO)
        # ==========================================
        st.markdown("---")
        st.markdown("### Generar Reporte PDF Detallado")
        st.info("El reporte incluirá un índice interactivo, tiempos de apertura por máquina/día, trazabilidad de operarios hora a hora y el listado cronológico de eventos.")
        
        def generar_pdf_famma(df_datos):
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            
            # 1. Agrupar máquinas y fechas para el Índice Interactivo
            maquinas = sorted(df_datos['Máquina'].dropna().unique())
            links_dict = {}
            for m in maquinas:
                links_dict[m] = {}
                fechas = sorted(df_datos[df_datos['Máquina'] == m]['Fecha'].dropna().unique())
                for f in fechas:
                    links_dict[m][f] = pdf.add_link() # Creamos el hipervínculo interno
                    
            # 2. PÁGINA DE ÍNDICE
            pdf.add_page()
            pdf.set_font("Arial", 'B', 18)
            pdf.set_text_color(139, 26, 26) # Rojo FAMMA
            pdf.cell(0, 10, txt="FAMMA", ln=True)
            pdf.set_font("Arial", 'B', 12)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(0, 6, txt="REPORTE GERENCIAL - SOLDADURA (CELDAS NUEVAS RENAULT)", ln=True)
            pdf.ln(10)
            
            pdf.set_font("Arial", 'B', 14)
            pdf.set_text_color(139, 26, 26)
            pdf.cell(0, 8, txt="ÍNDICE DEL REPORTE DETALLADO", ln=True)
            pdf.ln(2)
            
            for m in maquinas:
                pdf.set_font("Arial", 'B', 11)
                pdf.set_text_color(50, 50, 50)
                pdf.cell(0, 6, txt=f"> Máquina: {m}", ln=True)
                
                fechas = sorted(list(links_dict[m].keys()))
                pdf.set_font("Arial", 'U', 10)
                pdf.set_text_color(0, 0, 150) # Azul hipervínculo
                for f in fechas:
                    pdf.cell(10) # Sangría
                    str_f = f.strftime('%d/%m/%Y')
                    pdf.cell(0, 5, txt=f"- Ver detalles del Día {str_f}", ln=True, link=links_dict[m][f])
                pdf.ln(3)
                
            # 3. PÁGINAS DE DETALLE (POR MÁQUINA Y DÍA)
            for m in maquinas:
                fechas = sorted(list(links_dict[m].keys()))
                for f in fechas:
                    pdf.add_page()
                    pdf.set_link(links_dict[m][f]) # Anclamos el enlace del índice aquí
                    
                    df_mf = df_datos[(df_datos['Máquina'] == m) & (df_datos['Fecha'] == f)].copy()
                    str_f = f.strftime('%d/%m/%Y')
                    
                    # Encabezado FAMMA
                    pdf.set_font("Arial", 'B', 14)
                    pdf.set_text_color(139, 26, 26)
                    pdf.cell(0, 6, txt="FAMMA", ln=True)
                    pdf.set_font("Arial", 'B', 10)
                    pdf.set_text_color(80, 80, 80)
                    pdf.cell(0, 5, txt="REPORTE GERENCIAL - SOLDADURA", ln=True)
                    pdf.ln(3)
                    
                    pdf.set_font("Arial", 'B', 12)
                    pdf.set_text_color(139, 26, 26)
                    pdf.cell(0, 6, txt=f"MÁQUINA: {m} | PERIODO: {str_f}", ln=True)
                    pdf.line(10, pdf.get_y(), 200, pdf.get_y()) # Línea separadora
                    pdf.ln(5)
                    
                    # A. Horarios de Apertura
                    pdf.set_font("Arial", 'B', 11)
                    pdf.set_text_color(50, 50, 50)
                    pdf.cell(0, 6, txt="1. Horarios y Tiempo de Apertura", ln=True)
                    
                    hora_ini = df_mf['Fecha Inicio'].min()
                    hora_fin = df_mf['Fecha Fin'].max()
                    str_ini = hora_ini.strftime('%H:%M') if pd.notnull(hora_ini) else "N/A"
                    str_fin = hora_fin.strftime('%H:%M') if pd.notnull(hora_fin) else "N/A"
                    
                    if pd.notnull(hora_ini) and pd.notnull(hora_fin):
                        td = hora_fin - hora_ini
                        ts = int(td.total_seconds())
                        h, r = divmod(ts, 3600)
                        m_mins, _ = divmod(r, 60)
                        apertura = f"{h:02d}:{m_mins:02d} hs"
                    else:
                        apertura = "00:00 hs"
                    
                    # Tabla Apertura
                    pdf.set_font("Arial", 'B', 9)
                    pdf.set_text_color(255, 255, 255)
                    pdf.set_fill_color(139, 26, 26) # Fondo rojo FAMMA
                    pdf.cell(50, 6, "Máquina", 1, 0, 'C', True)
                    pdf.cell(40, 6, "Hora Inicio", 1, 0, 'C', True)
                    pdf.cell(40, 6, "Hora Cierre", 1, 0, 'C', True)
                    pdf.cell(50, 6, "Apertura Neta", 1, 1, 'C', True)
                    
                    pdf.set_font("Arial", '', 9)
                    pdf.set_text_color(0, 0, 0)
                    pdf.cell(50, 6, m, 1, 0, 'C')
                    pdf.cell(40, 6, str_ini, 1, 0, 'C')
                    pdf.cell(40, 6, str_fin, 1, 0, 'C')
                    pdf.cell(50, 6, apertura, 1, 1, 'C')
                    pdf.ln(5)
                    
                    # B. Trazabilidad de Operarios
                    pdf.set_font("Arial", 'B', 11)
                    pdf.set_text_color(50, 50, 50)
                    pdf.cell(0, 6, txt="2. Trazabilidad de Producción (Hora a Hora)", ln=True)
                    
                    df_ops = df_mf.dropna(subset=['Operador', 'Fecha Inicio']).copy()
                    if not df_ops.empty:
                        df_ops['Hora_Trun'] = df_ops['Fecha Inicio'].dt.floor('h')
                        df_ops['Franja'] = df_ops['Hora_Trun'].dt.strftime('%H:00') + " a " + (df_ops['Hora_Trun'] + pd.Timedelta(hours=1)).dt.strftime('%H:00')
                        df_horarios = df_ops.groupby('Franja')['Operador'].unique().apply(lambda x: " / ".join(x)).reset_index().sort_values('Franja')
                        
                        pdf.set_font("Arial", 'B', 9)
                        pdf.set_text_color(255, 255, 255)
                        pdf.cell(60, 6, "Franja Horaria", 1, 0, 'C', True)
                        pdf.cell(120, 6, "Operador(es) a cargo", 1, 1, 'C', True)
                        
                        pdf.set_font("Arial", '', 8)
                        pdf.set_text_color(0, 0, 0)
                        for _, row in df_horarios.iterrows():
                            ops = str(row['Operador']).encode('latin-1', 'replace').decode('latin-1')
                            pdf.cell(60, 6, row['Franja'], 1, 0, 'C')
                            pdf.cell(120, 6, ops[:70], 1, 1, 'L')
                    else:
                        pdf.set_font("Arial", '', 9)
                        pdf.set_text_color(0, 0, 0)
                        pdf.cell(0, 6, txt="No hay registros de operadores en este periodo.", ln=True)
                    pdf.ln(5)
                    
                    # C. Listado de Eventos
                    pdf.set_font("Arial", 'B', 11)
                    pdf.set_text_color(50, 50, 50)
                    pdf.cell(0, 6, txt="3. Listado Cronológico de Eventos y Fallas", ln=True)
                    
                    # Filtramos paradas y eventos que no sean "Producción" normal
                    df_ev = df_mf[df_mf['Evento'] != 'Producción'].copy()
                    if not df_ev.empty:
                        df_ev = df_ev.sort_values('Fecha Inicio')
                        
                        pdf.set_font("Arial", 'B', 8)
                        pdf.set_text_color(255, 255, 255)
                        # Columnas: Inicio, Fin, Tipo, Detalle, Minutos
                        pdf.cell(18, 6, "Inicio", 1, 0, 'C', True)
                        pdf.cell(18, 6, "Fin", 1, 0, 'C', True)
                        pdf.cell(30, 6, "Clasificación", 1, 0, 'C', True)
                        pdf.cell(100, 6, "Detalle Registrado en Sistema", 1, 0, 'C', True)
                        pdf.cell(14, 6, "Min.", 1, 1, 'C', True)
                        
                        pdf.set_font("Arial", '', 7)
                        pdf.set_text_color(0, 0, 0)
                        for _, row in df_ev.iterrows():
                            ini = row['Fecha Inicio'].strftime('%H:%M') if pd.notnull(row['Fecha Inicio']) else ""
                            fin = row['Fecha Fin'].strftime('%H:%M') if pd.notnull(row['Fecha Fin']) else ""
                            
                            # Tipo de Evento (Gestion, Falla, Proyecto)
                            tipo = str(row['Nivel Evento 1']).encode('latin-1', 'replace').decode('latin-1')[:15]
                            
                            # Detalle del Evento (Damos prioridad al Nivel 3, si no Nivel 2)
                            detalle = str(row['Nivel Evento 3']) if pd.notnull(row['Nivel Evento 3']) else str(row['Nivel Evento 2'])
                            detalle = detalle.encode('latin-1', 'replace').decode('latin-1')
                            
                            mins = str(int(row['Tiempo (Min)'])) if pd.notnull(row['Tiempo (Min)']) else "0"
                            
                            pdf.cell(18, 5, ini, 1, 0, 'C')
                            pdf.cell(18, 5, fin, 1, 0, 'C')
                            pdf.cell(30, 5, tipo, 1, 0, 'C')
                            pdf.cell(100, 5, detalle[:65], 1, 0, 'L')
                            pdf.cell(14, 5, mins, 1, 1, 'C')
                    else:
                        pdf.set_font("Arial", '', 9)
                        pdf.set_text_color(0, 0, 0)
                        pdf.cell(0, 6, txt="Jornada sin eventos ni fallas registradas.", ln=True)
                        
            return pdf.output(dest='S').encode('latin-1')
            
        pdf_data = generar_pdf_famma(df_sn)
        
        st.download_button(
            label="📥 Exportar Reporte PDF (Completo y Vinculado)",
            data=pdf_data,
            file_name=f"Reporte_Mensual_CeldasNuevas_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf"
        )
            
    else:
        st.error("El archivo no contiene la columna 'Fábrica'. Verifica el formato original.")
