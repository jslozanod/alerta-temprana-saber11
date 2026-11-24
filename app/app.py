"""Sistema de Alerta Temprana Saber 11 — aplicación de despliegue.

Pensada para coordinadores y docentes de colegios de Cali: suben la lista de su grupo y reciben a los estudiantes
ordenados por riesgo de obtener menos de 250 puntos, con los factores que más pesan en cada caso.
Los datos se procesan en memoria y no se guardan (Ley 1581 de 2012).
"""
import streamlit as st

st.set_page_config(page_title="Alerta Temprana Saber 11", page_icon=":material/school:", layout="wide")

paginas = [
    st.Page("app_pages/inicio.py", title="Inicio", icon=":material/home:", default=True),
    st.Page("app_pages/grupo.py", title="Mi grupo", icon=":material/groups:"),
    st.Page("app_pages/estudiante.py", title="Un estudiante", icon=":material/person_search:"),
    st.Page("app_pages/como_funciona.py", title="Cómo funciona", icon=":material/info:"),
]
pagina = st.navigation(paginas, position="top")
pagina.run()

st.caption("Proyecto de Inteligencia Artificial · Universidad Autónoma de Occidente · 2026-2 — "
           "Juan Sebastián Lozano Díaz, Julián David Cuéllar Cubillos y Alejandro Cárdenas Anturi. "
           "Los archivos se procesan en memoria y no se guardan (Ley 1581 de 2012).")
