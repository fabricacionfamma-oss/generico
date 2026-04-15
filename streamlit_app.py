import streamlit as st
import pandas as pd
import plotly.express as px
from fpdf import FPDF
from datetime import datetime, timedelta

# ==========================================
# CONFIGURACIÓN DE PÁGINA Y ESTÉTICA FAMMA
# ==========================================
st.set_page_config(page_title="FAMMA - Reporte de Celdas Renault", layout="wide")

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
uploaded_file = st.file_uploader("Sube el archivo Excel o CSV", type=['csv', 'xlsx'])

if uploaded_file:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    
    if 'Fábrica' in df.columns:
        df_sn = df[df['Fábrica'] == 'Soldadura Nueva'].copy()
        df_sn['Fecha Inicio'] = pd.to_datetime(df_sn['Fecha Inicio'], errors='coerce')
        df_sn['Fecha Fin'] = pd.to_datetime(df_sn['Fecha Fin'], errors='coerce')
        
        # BLINDAJE CONTRA EL ERROR NaT: Descartar registros sin fecha de inicio
        df_sn = df_sn.dropna(subset=['Fecha Inicio']) 
        
        df_sn['Fecha'] = df_sn['Fecha Inicio'].dt.date
        
        st.success(f"Datos de 'Soldadura Nueva' cargados. {len(df_sn)} registros encontrados.")

        # ==========================================
        # MOTOR DE PDF ACTUALIZADO
        # ==========================================
        def generar_pdf_v3(df_datos):
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            
            maquinas = sorted(df_datos['Máquina'].dropna().unique())
            links_dict = {}
            for m in maquinas:
                links_dict[m] = {}
                fechas = sorted(df_datos[df_datos['Máquina'] == m]['Fecha'].dropna().unique())
                for f in fechas:
                    links_dict[m][f] = pdf.add_link()

            # --- PÁGINA 1: ÍNDICE ---
            pdf.add_page()
            pdf.set_font("Arial", 'B', 20)
            pdf.set_text_color(139, 26, 26)
            pdf.cell(0, 12, txt="FAMMA", ln=True)
            pdf.set_font("Arial", 'B', 12)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 6, txt="REPORTE GERENCIAL: CELDAS NUEVAS RENAULT", ln=True)
            pdf.ln(10)
            
            pdf.set_font("Arial", 'B', 14)
            pdf.set_text_color(139, 26, 26)
            pdf.cell(0, 8, txt="ÍNDICE DE CONTENIDOS", ln=True)
            pdf.ln(4)
            
            for m in maquinas:
                pdf.set_font("Arial", 'B', 11)
                pdf.set_text_color(50, 50, 50)
                pdf.cell(0, 7, txt=f"> {m}", ln=True)
                fechas = sorted(list(links_dict[m].keys()))
                pdf.set_font("Arial", 'U', 10)
                pdf.set_text_color(0, 0, 150)
                for f in fechas:
                    pdf.cell(10)
                    pdf.cell(0, 5, txt=f"Detalle del dia {f.strftime('%d/%m/%Y')}", ln=True, link=links_dict[m][f])
                pdf.ln(2)

            # --- PÁGINA 2: RESUMEN GENERAL DE HORARIOS ---
            pdf.add_page()
            pdf.set_font("Arial", 'B', 14)
            pdf.set_text_color(139, 26, 26)
            pdf.cell(0, 10, txt="RESUMEN GENERAL DE HORARIOS POR MÁQUINA", ln=True)
            pdf.ln(5)
            
            for m in maquinas:
                pdf.set_font("Arial", 'B', 11)
                pdf.set_text_color(139, 26, 26)
                pdf.cell(0, 8, txt=f"Cronograma: {m}", ln=True)
                
                # Encabezado tabla resumen
                pdf.set_font("Arial", 'B', 9)
                pdf.set_text_color(255, 255, 255)
                pdf.set_fill_color(139, 26, 26)
                pdf.cell(40, 7, "Fecha", 1, 0, 'C', True)
                pdf.cell(40, 7, "Hora Inicio", 1, 0, 'C', True)
                pdf.cell(40, 7, "Hora Cierre", 1, 1, 'C', True)
                
                pdf.set_font("Arial", '', 9)
                pdf.set_text_color(0, 0, 0)
                # AQUÍ APLICAMOS LA CORRECCIÓN .dropna()
                fechas_m = sorted(df_datos[df_datos['Máquina'] == m]['Fecha'].dropna().unique())
                
                for f in fechas_m:
                    temp = df_datos[(df_datos['Máquina'] == m) & (df_datos['Fecha'] == f)]
                    h_ini = temp['Fecha Inicio'].min().strftime('%H:%M')
                    h_fin = temp['Fecha Fin'].max().strftime('%H:%M')
                    pdf.cell(40, 6, f.strftime('%d/%m/%Y'), 1, 0, 'C')
                    pdf.cell(40, 6, h_ini, 1, 0, 'C')
                    pdf.cell(40, 6, h_fin, 1, 1, 'C')
                pdf.ln(5)

            # --- PÁGINAS DETALLADAS ---
            for m in maquinas:
                fechas = sorted(list(links_dict[m].keys()))
                for f in fechas:
                    pdf.add_page()
                    pdf.set_link(links_dict[m][f])
                    df_mf = df_datos[(df_datos['Máquina'] == m) & (df_datos['Fecha'] == f)].copy().sort_values('Fecha Inicio')
                    
                    # Encabezado por día
                    pdf.set_font("Arial", 'B', 14)
                    pdf.set_text_color(139, 26, 26)
                    pdf.cell(0, 8, txt=f"MÁQUINA: {m} | DÍA: {f.strftime('%d/%m/%Y')}", ln=True)
                    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                    pdf.ln(5)

                    # 1. TRAZABILIDAD HORA A HORA (Real)
                    pdf.set_font("Arial", 'B', 11)
                    pdf.set_text_color(50, 50, 50)
                    pdf.cell(0, 7, txt="1. Trazabilidad de Operarios (Hora por Hora)", ln=True)
                    
                    min_h = df_mf['Fecha Inicio'].min().hour
                    max_h = df_mf['Fecha Fin'].max().hour
                    
                    pdf.set_font("Arial", 'B', 9)
                    pdf.set_text_color(255, 255, 255)
                    pdf.set_fill_color(139, 26, 26)
                    pdf.cell(50, 6, "Franja Horaria", 1, 0, 'C', True)
                    pdf.cell(130, 6, "Operador(es) Detectado(s)", 1, 1, 'C', True)
                    
                    pdf.set_font("Arial", '', 8)
                    pdf.set_text_color(0, 0, 0)
                    
                    for h_base in range(min_h, max_h + 1):
                        franja_ini = datetime.combine(f, datetime.min.time()) + timedelta(hours=h_base)
                        franja_fin = franja_ini + timedelta(hours=1)
                        
                        mask = (df_mf['Fecha Inicio'] < franja_fin) & (df_mf['Fecha Fin'] > franja_ini)
                        ops = df_mf[mask]['Operador'].dropna().unique()
                        ops_text = " / ".join(ops) if len(ops) > 0 else "Sin registro"
                        
                        pdf.cell(50, 6, f"{h_base:02d}:00 a {h_base+1:02d}:00", 1, 0, 'C')
                        pdf.cell(130, 6, ops_text[:85].encode('latin-1', 'replace').decode('latin-1'), 1, 1, 'L')
                    pdf.ln(5)

                    # 2. LISTADO CRONOLÓGICO DE EVENTOS (Incluyendo Producción)
                    pdf.set_font("Arial", 'B', 11)
                    pdf.set_text_color(50, 50, 50)
                    pdf.cell(0, 7, txt="2. Listado de Eventos Completo (Producción + Paradas)", ln=True)
                    
                    pdf.set_font("Arial", 'B', 8)
                    pdf.set_text_color(255, 255, 255)
                    pdf.cell(15, 6, "Inicio", 1, 0, 'C', True)
                    pdf.cell(15, 6, "Fin", 1, 0, 'C', True)
                    pdf.cell(30, 6, "Tipo", 1, 0, 'C', True)
                    pdf.cell(110, 6, "Detalle del Sistema", 1, 0, 'C', True)
                    pdf.cell(12, 6, "Min", 1, 1, 'C', True)
                    
                    pdf.set_font("Arial", '', 7)
                    pdf.set_text_color(0, 0, 0)
                    
                    for _, row in df_mf.iterrows():
                        if row['Evento'] == 'Producción':
                            pdf.set_text_color(100, 100, 100)
                        else:
                            pdf.set_text_color(0, 0, 0)
                            
                        ini = row['Fecha Inicio'].strftime('%H:%M')
                        fin = row['Fecha Fin'].strftime('%H:%M') if pd.notnull(row['Fecha Fin']) else ini
                        tipo = str(row['Nivel Evento 1']).encode('latin-1', 'replace').decode('latin-1')
                        
                        det = row['Nivel Evento 3'] if pd.notnull(row['Nivel Evento 3']) else row['Nivel Evento 2']
                        if pd.isnull(det): det = row['Evento']
                        det_str = str(det).encode('latin-1', 'replace').decode('latin-1')
                        
                        minutos = str(int(row['Tiempo (Min)'])) if pd.notnull(row['Tiempo (Min)']) else "0"
                        
                        pdf.cell(15, 5, ini, 1, 0, 'C')
                        pdf.cell(15, 5, fin, 1, 0, 'C')
                        pdf.cell(30, 5, tipo[:18], 1, 0, 'C')
                        pdf.cell(110, 5, det_str[:75], 1, 0, 'L')
                        pdf.cell(12, 5, minutos, 1, 1, 'C')
                    
                    pdf.set_text_color(0, 0, 0) 

            return pdf.output(dest='S').encode('latin-1')

        pdf_final = generar_pdf_v3(df_sn)
        st.download_button(
            label="📥 Descargar Reporte PDF Detallado",
            data=pdf_final,
            file_name=f"FAMMA_CeldasRenault_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf"
        )
