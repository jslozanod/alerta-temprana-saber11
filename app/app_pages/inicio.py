import streamlit as st

from comun import RES, pct, miles, coma


st.caption(":red[**INTELIGENCIA ARTIFICIAL · UNIVERSIDAD AUTÓNOMA DE OCCIDENTE**]")
st.title("Sistema de Alerta Temprana Saber 11")
st.markdown(
    "En Cali, **4 de cada 10** estudiantes de grado 11 obtienen **menos de 250 puntos** en el Saber 11 "
    "(42,8 % de 128.260 resultados entre 2019 y 2025), y el colegio se entera cuando el estudiante ya se graduó. "
    "Esta herramienta estima ese riesgo **al inicio del año** para que el colegio sepa **a quién acompañar primero**."
)

with st.container(horizontal=True):
    if st.button("Analizar mi grupo", type="primary", icon=":material/groups:"):
        st.switch_page("app_pages/grupo.py")
    if st.button("Evaluar un estudiante", icon=":material/person_search:"):
        st.switch_page("app_pages/estudiante.py")

st.subheader("Cómo se usa")
c1, c2, c3 = st.columns(3, border=True)
with c1:
    st.markdown("##### :material/upload_file: 1. Cargue su grupo")
    st.caption("Plantilla en Excel con listas desplegables. Solo 13 preguntas del contexto del estudiante, "
               "sin nombres ni documentos.")
with c2:
    st.markdown("##### :material/format_list_numbered: 2. Vea la prioridad")
    st.caption("Los estudiantes salen ordenados por riesgo. Usted indica cuántos cupos de refuerzo tiene y la "
               "herramienta marca a quiénes atender primero.")
with c3:
    st.markdown("##### :material/lightbulb: 3. Entienda cada caso")
    st.caption("Para cada estudiante se muestran los factores que más pesan y acciones concretas, como acceso a "
               "computador o refuerzos en otro horario.")

st.subheader("Qué tan confiable es")
with st.container(horizontal=True):
    st.metric("Estudiantes en riesgo que detecta", pct(RES["sens"]), border=True,
              help="Sensibilidad en 2025: de cada 100 estudiantes que sacaron menos de 250, la alerta marcó a 84.")
    st.metric("Capacidad para ordenar (AUC)", coma(RES["auc"]), border=True,
              help="Probabilidad de que un estudiante en riesgo quede por encima de uno que no lo está. 0,5 es azar.")
    st.metric("Estudiantes de 2025 evaluados", miles(RES["n_test"]), border=True,
              help="Datos que el modelo nunca vio durante el entrenamiento ni la selección.")
    st.metric("Estudiantes para entrenar", miles(RES["n_train"]), border=True,
              help="Saber 11 de Cali, 2019 a 2023.")

st.info("La alerta apoya al docente, no lo reemplaza. No es un diagnóstico y no debe usarse para excluir ni etiquetar "
        "estudiantes: sirve para repartir mejor el acompañamiento.", icon=":material/handshake:")
