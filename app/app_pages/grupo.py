import numpy as np
import pandas as pd
import streamlit as st

from comun import (NOMBRES, INTERVENIBLES, VARS, motor, ejemplo, plantilla_vacia, leer_archivo, analizar, razones,
                   acciones, grafico_aportes, grafico_distribucion, pct, coma)

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

st.caption(":red[**MI GRUPO**]")
st.header("¿A quién acompañar primero?")

# ============================================================================ 1. datos
with st.container(border=True):
    with st.container(horizontal=True, vertical_alignment="center"):
        st.subheader("1. Cargue su grupo")
        st.space("stretch")
        with st.popover("¿Cómo lleno la plantilla?", icon=":material/help:"):
            st.markdown("1. Descargue la **plantilla vacía (Excel)**.\n"
                        "2. Escriba un código por estudiante en `id_estudiante` (por ejemplo 11A-01). **Sin nombres.**\n"
                        "3. En cada celda elija la respuesta de la **lista desplegable**. Si no la sabe: «No reportado».\n"
                        "4. Guarde y súbalo aquí en *Mi archivo*.")
            st.caption("Las 13 preguntas son las del formulario socioeconómico del ICFES. El colegio puede recogerlas "
                       "con su propio formulario al inicio del año.")

    fuente = st.segmented_control("Fuente de los datos", ["Mi archivo", "Grupo de ejemplo"], default="Mi archivo",
                                  key="fuente", required=True)
    if fuente == "Mi archivo":
        archivo = st.file_uploader("Archivo del grupo (Excel o CSV)", type=["xlsx", "xls", "csv"])
    else:
        archivo = None
        st.caption("40 estudiantes reales de Cali (2025), anonimizados, para probar la herramienta sin preparar nada.")

    with st.container(horizontal=True):
        st.download_button("Plantilla vacía (Excel)", plantilla_vacia(), "plantilla_grupo_saber11.xlsx", XLSX,
                           icon=":material/table_view:", type="primary" if fuente == "Mi archivo" else "secondary")
        st.download_button("Grupo de ejemplo (CSV)", ejemplo().to_csv(index=False).encode("utf-8-sig"),
                           "ejemplo_grupo_saber11.csv", "text/csv", icon=":material/download:")

crudo = None
if fuente == "Mi archivo":
    if archivo is None:
        st.info("Suba el archivo de su grupo para ver los resultados. Si aún no lo tiene, descargue la plantilla vacía.",
                icon=":material/upload_file:")
        st.stop()
    try:
        crudo = leer_archivo(archivo)
    except Exception as e:  # archivo dañado o con otro formato
        st.error(f"No se pudo leer el archivo. Revise que sea la plantilla en Excel o un CSV. Detalle: {e}",
                 icon=":material/error:")
        st.stop()
else:
    crudo = ejemplo()

if crudo is None or not len(crudo):
    st.warning("El archivo no tiene estudiantes. Llene al menos una fila desde la fila 2.", icon=":material/warning:")
    st.stop()

datos, rep, prob, aportes, umbral, ident, incompletos = analizar(crudo)
n = len(datos)

# calidad de los datos
with st.container(horizontal=True, gap="small"):
    st.badge(f"{n} estudiantes", icon=":material/groups:", color="blue")
    if incompletos:
        st.badge(f"{incompletos} con alguna respuesta «No reportado»", icon=":material/info:", color="orange")
    else:
        st.badge("Datos completos", icon=":material/check_circle:", color="green")
    if rep["faltan"]:
        st.badge(f"Faltan {len(rep['faltan'])} columnas", icon=":material/error:", color="red")
if rep["faltan"]:
    st.warning("No se encontraron estas columnas y se tomaron como «No reportado»: "
               + ", ".join(NOMBRES.get(v, v) for v in rep["faltan"]) + ". Use la plantilla para evitarlo.",
               icon=":material/warning:")
if rep["corregidos"]:
    with st.expander(f"Valores no reconocidos en {len(rep['corregidos'])} columnas (se tomaron como «No reportado»)",
                     icon=":material/rule:"):
        for v, ej in rep["corregidos"].items():
            st.write(f"**{NOMBRES[v]}**: {', '.join(map(str, ej))}")

# ============================================================================ 2. criterio
with st.container(border=True):
    st.subheader("2. ¿Cuántos estudiantes puede acompañar?")
    c1, c2 = st.columns([1, 1.4], vertical_alignment="bottom")
    with c1:
        modo = st.segmented_control("Criterio", ["Cupos de refuerzo", "Alerta del modelo"], default="Cupos de refuerzo",
                                    required=True, key="modo",
                                    help="**Cupos**: usted dice cuántos puede atender y se escogen los de mayor riesgo. "
                                         "**Alerta**: se marcan todos los que pasan el umbral de su calendario.")
    alerta = prob >= umbral
    with c2:
        if modo == "Cupos de refuerzo":
            cupos = st.slider("Cupos disponibles", 1, n, min(max(1, n // 4), n), key="cupos")
            prioridad = np.zeros(n, bool); prioridad[np.argsort(-prob, kind="stable")[:cupos]] = True
        else:
            st.caption(f"Umbral calendario A: **{coma(motor.umbral_calendario['A'])}** · calendario B: "
                       f"**{coma(motor.umbral_calendario['B'])}**. Elegidos para detectar al menos el 85 % de los "
                       "estudiantes en riesgo de cada calendario.")
            prioridad = alerta

with st.container(horizontal=True):
    st.metric("Estudiantes", n, border=True)
    st.metric("Priorizados", int(prioridad.sum()), border=True,
              help="Estudiantes que la herramienta sugiere acompañar primero con el criterio elegido.")
    st.metric("Con alerta del modelo", int(alerta.sum()), border=True,
              help="Riesgo por encima del umbral de su calendario.")
    st.metric("Riesgo promedio", pct(prob.mean()), border=True,
              help="Si el riesgo es 60 %, se espera que unos 6 de cada 10 estudiantes así obtengan menos de 250.")

# ============================================================================ tabla base
tabla = pd.DataFrame({
    "Estudiante": ident,
    "Riesgo": prob * 100,
    "Prioridad": np.where(prioridad, "Priorizado", "No priorizado"),
    "Alerta": np.where(alerta, "Sí", "No"),
    "Factores que más pesan": [razones(aportes.loc[i]) for i in datos.index],
    "fila": np.arange(n),
})
tabla["jitter"] = np.random.default_rng(7).uniform(0, 1, n)
tabla = tabla.sort_values("Riesgo", ascending=False, kind="stable").reset_index(drop=True)
tabla.insert(0, "Puesto", np.arange(1, n + 1))

g1, g2 = st.columns([1.3, 1])
with g1, st.container(border=True, height="stretch"):
    st.markdown("**Así se reparte el riesgo en el grupo**")
    st.altair_chart(grafico_distribucion(tabla), alt="Riesgo estimado de cada estudiante del grupo")
    st.caption("Cada punto es un estudiante. Pase el mouse para ver su código y su riesgo.")
with g2, st.container(border=True, height="stretch"):
    st.markdown("**Qué pesa más en los priorizados**")
    prom = (aportes[prioridad] if prioridad.any() else aportes).mean()
    st.altair_chart(grafico_aportes(prom, "Puntos porcentuales de riesgo", k=6), alt="Factores que más pesan en el grupo")
    st.caption("Internet, computador y jornada son **intervenibles**: el colegio puede compensarlos.")


# ============================================================================ 3. lista
@st.dialog("Detalle del estudiante", position="right", width="medium")
def detalle(fila):
    d = datos.iloc[[fila]]
    p, u = float(prob[fila]), float(umbral[fila])
    st.subheader(str(ident[fila]))
    with st.container(horizontal=True):
        st.metric("Riesgo estimado", pct(p), border=True)
        st.metric("Umbral de su calendario", pct(u), border=True)
    if p >= u:
        st.error("Supera el umbral de su calendario: conviene revisarlo con prioridad.", icon=":material/notification_important:")
    else:
        st.success("Por debajo del umbral de su calendario.", icon=":material/check_circle:")
    st.altair_chart(grafico_aportes(aportes.iloc[fila], "Puntos que suma o resta cada respuesta", k=8),
                    alt="Aporte de cada respuesta al riesgo del estudiante")
    st.caption("A la derecha: la respuesta sube el riesgo frente a un estudiante típico de Cali. A la izquierda: lo baja.")
    resp = d[VARS].iloc[0].to_dict()
    sug = acciones(resp, p, u)
    if sug:
        st.markdown("**Acciones sugeridas**")
        for icono, texto in sug:
            st.markdown(f"{icono} {texto}")
    with st.expander("Respuestas registradas", icon=":material/list_alt:"):
        st.dataframe(pd.DataFrame({"Pregunta": [NOMBRES[v] for v in VARS], "Respuesta": [resp[v] for v in VARS]}),
                     hide_index=True, alt="Respuestas del estudiante")


def abrir_detalle():
    clic = st.session_state.get("ver")
    if clic is not None:
        st.session_state["abrir"] = int(st.session_state["_vista"].iloc[clic.row]["fila"])


with st.container(border=True):
    with st.container(horizontal=True, vertical_alignment="bottom"):
        st.subheader("3. Estudiantes ordenados por riesgo")
        st.space("stretch")
        filtro = st.segmented_control("Mostrar", ["Priorizados", "Con alerta", "Todos"], default="Todos",
                                      required=True, key="filtro", label_visibility="collapsed")
        buscar = st.text_input("Buscar código", placeholder="Buscar código", icon=":material/search:",
                               label_visibility="collapsed", width=200)
    vista = tabla
    if filtro == "Priorizados":
        vista = vista[vista["Prioridad"] == "Priorizado"]
    elif filtro == "Con alerta":
        vista = vista[vista["Alerta"] == "Sí"]
    if buscar:
        vista = vista[vista["Estudiante"].astype(str).str.contains(buscar.strip(), case=False, regex=False)]
    vista = vista.assign(Detalle=":material/visibility: Ver").reset_index(drop=True)
    st.session_state["_vista"] = vista
    st.dataframe(
        vista[["Puesto", "Estudiante", "Riesgo", "Prioridad", "Alerta", "Factores que más pesan", "Detalle"]],
        hide_index=True, height=min(38 + 35 * max(len(vista), 1), 520), alt="Lista de estudiantes ordenada por riesgo",
        column_config={
            "Puesto": st.column_config.NumberColumn("#", width="small"),
            "Riesgo": st.column_config.ProgressColumn("Riesgo estimado", format="%.0f %%", min_value=0, max_value=100),
            "Prioridad": st.column_config.TextColumn("Prioridad"),
            "Alerta": st.column_config.TextColumn("Alerta", width="small",
                                                  help="Riesgo por encima del umbral de su calendario"),
            "Factores que más pesan": st.column_config.TextColumn("Factores que más pesan", width="large"),
            "Detalle": st.column_config.ButtonColumn("Detalle", type="tertiary", on_click=abrir_detalle, key="ver"),
        },
    )
    st.caption(f"Mostrando {len(vista)} de {n} estudiantes. Use **Ver** para abrir el detalle de cada uno.")
    salida = tabla[["Puesto", "Estudiante", "Riesgo", "Prioridad", "Alerta", "Factores que más pesan"]].copy()
    salida["Riesgo"] = salida["Riesgo"].round(1)
    st.download_button("Descargar resultados (CSV)", salida.to_csv(index=False).encode("utf-8-sig"),
                       "resultados_alerta_saber11.csv", "text/csv", icon=":material/download:")

if "abrir" in st.session_state:
    detalle(st.session_state.pop("abrir"))

# ============================================================================ monitoreo
with st.expander("Monitoreo: ¿este grupo se parece a los datos con que se entrenó el modelo?",
                 icon=":material/monitoring:", on_change="rerun", key="exp_psi") as exp:
    if exp.open:
        ps = motor.psi(datos)
        if n < 200:
            st.info("Con menos de 200 estudiantes el índice varía mucho; úselo como referencia, no como alarma.",
                    icon=":material/info:")
        ps = ps.assign(Estado=np.select([ps.psi > 0.25, ps.psi > 0.10], ["Cambio grande", "Revisar"], "Estable"))
        st.dataframe(ps.rename(columns={"variable": "Variable", "psi": "PSI"}), hide_index=True,
                     column_config={"PSI": st.column_config.NumberColumn(format="%.3f")}, alt="Índice de estabilidad PSI")
        st.caption("PSI (Population Stability Index): menos de 0,10 estable · 0,10 a 0,25 revisar · más de 0,25 "
                   "conviene reentrenar el modelo.")
