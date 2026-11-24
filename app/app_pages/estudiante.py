import pandas as pd
import streamlit as st

from comun import GRUPOS, NOMBRES, motor, acciones, grafico_aportes, pct

st.caption(":red[**UN ESTUDIANTE**]")
st.header("Evaluar a un estudiante")
st.write("Elija las respuestas del estudiante. El resultado se actualiza al instante.")

# Punto de partida: un estudiante típico de Cali (colegio oficial urbano, calendario A, estrato 2)
TIPICO = {"cole_jornada": "MAÑANA", "cole_calendario": "A", "cole_naturaleza": "OFICIAL", "cole_area_ubicacion": "URBANO",
          "cole_bilingue": "N", "cole_caracter": "ACADÉMICO", "fami_tieneinternet": "Si", "fami_tienecomputador": "No",
          "fami_educacionmadre": "Secundaria (Bachillerato) completa", "fami_educacionpadre": "Secundaria (Bachillerato) completa",
          "fami_estratovivienda": "Estrato 2", "estu_genero": "F", "grupo_edad": "17"}

izq, der = st.columns([1, 1.25], gap="large")

with izq:
    resp = {}
    for titulo, icono, vs in GRUPOS:
        with st.container(border=True):
            st.markdown(f"**{icono} {titulo}**")
            cols = st.columns(2)
            for k, v in enumerate(vs):
                ops = motor.categorias[v]
                with cols[k % 2]:
                    resp[v] = st.selectbox(NOMBRES[v], ops, key=v,
                                           index=ops.index(TIPICO[v]) if TIPICO.get(v) in ops else 0)

uno = pd.DataFrame([resp])
p = float(motor.predecir(uno)[0]); u = float(motor.umbrales(uno)[0])
aporte = motor.explicar(uno).iloc[0]

with der:
    with st.container(border=True):
        with st.container(horizontal=True, vertical_alignment="center"):
            st.metric("Riesgo estimado", pct(p))
            st.metric("Umbral de su calendario", pct(u))
            if p >= u:
                st.badge("Con alerta", icon=":material/notification_important:", color="red")
            else:
                st.badge("Sin alerta", icon=":material/check_circle:", color="green")
        st.progress(min(p, 1.0))
        st.caption(f"Si el riesgo es {pct(p)}, de cada 100 estudiantes con estas respuestas se espera que unos "
                   f"{round(p * 100)} obtengan menos de 250. Es una estimación, no un diagnóstico.")

    with st.container(border=True):
        st.markdown("**Qué pesa en este resultado**")
        st.altair_chart(grafico_aportes(aporte, "Puntos porcentuales que suma o resta cada respuesta", k=8),
                        alt="Aporte de cada respuesta al riesgo")
        st.caption("A la derecha: la respuesta sube el riesgo frente a un estudiante típico de Cali. A la izquierda: lo baja.")

    with st.container(border=True):
        st.markdown("**:material/science: ¿Y si el colegio lo apoya?**")
        st.caption("Simule los apoyos que el colegio sí puede dar y vea cómo cambia la estimación.")
        sim = dict(resp)
        c1, c2 = st.columns(2)
        if c1.toggle("Acceso a computador e internet", key="sim_tic",
                     help="Por ejemplo, sala de sistemas o biblioteca en contra jornada."):
            sim["fami_tienecomputador"] = "Si"; sim["fami_tieneinternet"] = "Si"
        if c2.toggle("Refuerzo en jornada completa", key="sim_jor",
                     help="Sesiones de refuerzo como las de un colegio de jornada completa."):
            sim["cole_jornada"] = "COMPLETA"
        if sim != resp:
            p2 = float(motor.predecir(pd.DataFrame([sim]))[0])
            st.metric("Riesgo con apoyo", pct(p2), delta=f"{(p2 - p) * 100:+.0f} puntos".replace(".", ","),
                      delta_color="inverse")
            st.caption("Es una asociación aprendida de los datos, no un efecto garantizado: sirve para decidir qué "
                       "apoyo priorizar.")

    sug = acciones(resp, p, u)
    if sug:
        with st.container(border=True):
            st.markdown("**Acciones sugeridas**")
            for icono, texto in sug:
                st.markdown(f"{icono} {texto}")
