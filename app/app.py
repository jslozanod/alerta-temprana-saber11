"""Sistema de Alerta Temprana Saber 11 — aplicación de despliegue.

Pensada para coordinadores y docentes de colegios de Cali: suben la lista de su grupo y reciben a los estudiantes
ordenados por riesgo de obtener menos de 250 puntos, con los factores que más pesan en cada caso.
Los datos se procesan en memoria y no se guardan (Ley 1581 de 2012).
"""
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
import altair as alt
import streamlit as st

from motor import Motor, NOMBRES, INTERVENIBLES

st.set_page_config(page_title="Alerta Temprana Saber 11", page_icon="📘", layout="wide")
ROJO = "#C8102E"
st.markdown(f"""
<style>
h1, h2, h3, h1 *, h2 *, h3 *, [data-testid="stHeading"] * {{ font-family: Georgia, 'Times New Roman', serif !important; font-weight: 500 !important; }}
.cifra {{ font-family: Georgia, serif; font-size: 3.2rem; color: {ROJO}; line-height: 1; }}
.etq {{ letter-spacing: .18em; font-size: .72rem; color: {ROJO}; text-transform: uppercase; font-weight: 600; }}
.nota {{ color: #666; font-size: .85rem; }}
</style>""", unsafe_allow_html=True)


@st.cache_resource
def cargar():
    m = Motor()
    res = json.load(open(Path(__file__).resolve().parent.parent / "modelos" / "resultados_resumen.json", encoding="utf-8"))
    return m, res


motor, RES = cargar()
VARS = motor.variables


def plantilla():
    ej = pd.read_csv(Path(__file__).resolve().parent.parent / "modelos" / "ejemplo_grupo.csv", dtype=str)
    ej.insert(0, "id_estudiante", [f"E{i+1:03d}" for i in range(len(ej))])
    return ej


def leer_archivo(f):
    if f.name.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(f, dtype=str)
    return pd.read_csv(f, dtype=str, sep=None, engine="python", encoding_errors="replace")


def razones(fila_aportes, k=3):
    top = fila_aportes.sort_values(ascending=False)
    top = top[top > 0.005].head(k)
    return "; ".join(f"{NOMBRES[v]}" + (" (intervenible)" if v in INTERVENIBLES else "") for v in top.index) or "Sin factores destacados"


def grafico_aportes(serie, titulo):
    """Barras horizontales ordenadas: puntos porcentuales que cada variable suma o resta al riesgo."""
    d = pd.DataFrame({"Variable": [NOMBRES[v] for v in serie.index], "Puntos": serie.values * 100})
    d["Efecto"] = np.where(d["Puntos"] >= 0, "Sube el riesgo", "Baja el riesgo")
    return alt.Chart(d).mark_bar().encode(
        x=alt.X("Puntos:Q", title=titulo),
        y=alt.Y("Variable:N", sort="-x", title=None, axis=alt.Axis(labelLimit=260, labelOverlap=False)),
        color=alt.Color("Efecto:N", scale=alt.Scale(domain=["Sube el riesgo", "Baja el riesgo"], range=[ROJO, "#8A8A8A"]), legend=alt.Legend(orient="top", title=None)),
        tooltip=["Variable", alt.Tooltip("Puntos:Q", format=".1f")]).properties(height=alt.Step(26))


# ======================================================================== encabezado
st.markdown('<div class="etq">Inteligencia Artificial · Universidad Autónoma de Occidente</div>', unsafe_allow_html=True)
st.title("Sistema de Alerta Temprana — Saber 11")
st.write("Estima el riesgo de que un estudiante de grado 11 de Cali obtenga **menos de 250 puntos** en el Saber 11, "
         "para que el colegio sepa **a quién acompañar primero**. La alerta apoya al docente, no reemplaza su criterio.")

tab_grupo, tab_uno, tab_info = st.tabs(["📋 Mi grupo", "👤 Un estudiante", "ℹ️ Cómo funciona"])

# ======================================================================== MI GRUPO
with tab_grupo:
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("1. Sube la lista de tu grupo")
        st.write("Un archivo CSV o Excel con una fila por estudiante y las 13 respuestas del formulario. "
                 "Puede tener una columna `id_estudiante` para reconocer a cada uno; no pongas nombres ni documentos.")
    with c2:
        pl = plantilla()
        st.download_button("⬇️ Descargar plantilla (CSV)", pl.to_csv(index=False).encode("utf-8-sig"),
                           "plantilla_grupo_saber11.csv", "text/csv", use_container_width=True)
        st.caption("La plantilla trae 40 estudiantes de ejemplo (anonimizados, de 2025) para probar la app.")

    archivo = st.file_uploader("Archivo del grupo", type=["csv", "xlsx", "xls"])
    usar_ejemplo = st.checkbox("Usar el grupo de ejemplo", value=archivo is None)

    datos = None
    if archivo is not None:
        try:
            datos = leer_archivo(archivo)
        except Exception as e:
            st.error(f"No pude leer el archivo: {e}")
    elif usar_ejemplo:
        datos = plantilla()

    if datos is not None and len(datos):
        datos, rep = motor.limpiar(datos)
        if rep["faltan"]:
            st.warning("Faltan estas columnas y se tomaron como «No reportado»: " + ", ".join(NOMBRES.get(v, v) for v in rep["faltan"]))
        if rep["corregidos"]:
            with st.expander(f"⚠️ Se encontraron valores no válidos en {len(rep['corregidos'])} variables (se tomaron como «No reportado»)"):
                for v, ej in rep["corregidos"].items():
                    st.write(f"**{NOMBRES[v]}**: {', '.join(map(str, ej))}")

        prob = motor.predecir(datos)
        aportes = motor.explicar(datos)
        ident = datos["id_estudiante"] if "id_estudiante" in datos.columns else pd.Series([f"Fila {i+1}" for i in range(len(datos))], index=datos.index)

        st.subheader("2. ¿Cuántos estudiantes puede acompañar el colegio?")
        modo = st.radio("Criterio", ["Según los cupos de refuerzo", "Según el umbral del modelo"], horizontal=True)
        if modo == "Según los cupos de refuerzo":
            cupos = st.slider("Cupos de refuerzo disponibles", 1, len(datos), min(max(1, len(datos) // 4), len(datos)))
            orden = np.argsort(-prob); prioridad = np.zeros(len(datos), bool); prioridad[orden[:cupos]] = True
        else:
            u = motor.umbral_calendario
            st.caption(f"Umbral calendario A: {str(u['A']).replace('.', ',')} · calendario B: {str(u['B']).replace('.', ',')}. Se eligieron en 2024 para detectar al menos "
                       "85 % de los estudiantes en riesgo en cada calendario.")
            prioridad = prob >= motor.umbrales(datos)

        tabla = pd.DataFrame({"Estudiante": ident.values, "Riesgo estimado": prob * 100, "Priorizar": np.where(prioridad, "Sí", "No"),
                              "Factores que más pesan": [razones(aportes.loc[i]) for i in datos.index]})
        tabla = tabla.sort_values("Riesgo estimado", ascending=False).reset_index(drop=True)
        tabla.index += 1

        k1, k2, k3 = st.columns(3)
        k1.markdown(f'<div class="etq">Estudiantes</div><div class="cifra">{len(datos)}</div>', unsafe_allow_html=True)
        k2.markdown(f'<div class="etq">A priorizar</div><div class="cifra">{int(prioridad.sum())}</div>', unsafe_allow_html=True)
        k3.markdown(f'<div class="etq">Riesgo promedio</div><div class="cifra">{prob.mean():.0%}</div>', unsafe_allow_html=True)
        st.caption(f"Si el riesgo de un grupo de estudiantes es 60 %, se espera que unos 6 de cada 10 obtengan menos de 250 "
                   f"(probabilidades calibradas con datos de 2024).")

        st.subheader("3. Estudiantes ordenados por riesgo")
        st.dataframe(tabla, use_container_width=True,
                     column_config={"Riesgo estimado": st.column_config.ProgressColumn("Riesgo estimado", format="%.0f %%", min_value=0, max_value=100)})
        salida = tabla.copy(); salida["Riesgo estimado"] = salida["Riesgo estimado"].round(1)
        st.download_button("⬇️ Descargar resultados (CSV)", salida.to_csv(index_label="Puesto").encode("utf-8-sig"),
                           "resultados_alerta_saber11.csv", "text/csv")

        st.subheader("4. ¿Qué pesa más en este grupo?")
        prom = aportes[prioridad].mean().sort_values(ascending=False) if prioridad.any() else aportes.mean().sort_values(ascending=False)
        st.altair_chart(grafico_aportes(prom, "Puntos porcentuales de riesgo (promedio de los priorizados)"), use_container_width=True)
        st.caption("Aporte promedio de cada variable en los estudiantes priorizados. Las marcadas como intervenibles en la tabla "
                   "(internet, computador, jornada) son las que el colegio puede compensar con recursos u horarios de apoyo.")

        with st.expander("🔎 Monitoreo: ¿este grupo se parece a los datos con que se entrenó el modelo?"):
            ps = motor.psi(datos)
            if len(datos) < 200:
                st.info("Con menos de 200 estudiantes el índice es muy variable; úsalo como referencia, no como alarma.")
            st.dataframe(ps.assign(estado=np.select([ps.psi > 0.25, ps.psi > 0.10], ["Cambio grande", "Cambio moderado"], "Estable")),
                         use_container_width=True, hide_index=True)
            st.caption("PSI (Population Stability Index). Menos de 0,10: estable · 0,10–0,25: revisar · más de 0,25: el modelo debería reentrenarse.")

# ======================================================================== UN ESTUDIANTE
with tab_uno:
    st.subheader("Evaluar a un estudiante")
    col = st.columns(3); resp = {}
    grupos = [("Colegio", ["cole_jornada", "cole_calendario", "cole_naturaleza", "cole_area_ubicacion", "cole_bilingue", "cole_caracter"]),
              ("Familia", ["fami_tieneinternet", "fami_tienecomputador", "fami_educacionmadre", "fami_educacionpadre", "fami_estratovivienda"]),
              ("Estudiante", ["estu_genero", "grupo_edad"])]
    for (titulo, vs), c in zip(grupos, col):
        with c:
            st.markdown(f'<div class="etq">{titulo}</div>', unsafe_allow_html=True)
            for v in vs:
                ops = motor.categorias[v]
                resp[v] = st.selectbox(NOMBRES[v], ops, index=ops.index("No reportado") if "No reportado" in ops else 0, key=v)
    uno = pd.DataFrame([resp])
    p1 = float(motor.predecir(uno)[0]); a1 = motor.explicar(uno).iloc[0]; u1 = float(motor.umbrales(uno)[0])
    r1, r2 = st.columns([1, 2])
    with r1:
        st.markdown(f'<div class="etq">Riesgo estimado</div><div class="cifra">{p1:.0%}</div>', unsafe_allow_html=True)
        if p1 >= u1:
            st.error(f"Alerta: supera el umbral de {u1:.0%} de su calendario. Conviene revisarlo con prioridad.")
        else:
            st.success(f"Sin alerta: está por debajo del umbral de {u1:.0%} de su calendario.")
        st.caption("Es una estimación con 13 variables del contexto; no es un diagnóstico del estudiante.")
    with r2:
        st.altair_chart(grafico_aportes(a1, "Puntos porcentuales que suma o resta cada respuesta"), use_container_width=True)
        st.caption("Barras a la derecha: la respuesta sube el riesgo frente a un estudiante típico. A la izquierda: lo baja.")
    acciones = []
    if resp["fami_tienecomputador"] == "No" or resp["fami_tieneinternet"] == "No":
        acciones.append("Facilitar acceso a sala de sistemas o biblioteca con internet para preparar el examen.")
    if resp["cole_jornada"] in ("NOCHE", "SABATINA", "TARDE"):
        acciones.append("Ofrecer sesiones de refuerzo en horarios compatibles con su jornada.")
    if p1 >= u1:
        acciones.append("Incluirlo en el plan de acompañamiento y simulacros del colegio desde el inicio del año.")
    if acciones:
        st.markdown("**Acciones sugeridas**"); [st.write("• " + a) for a in acciones]

# ======================================================================== CÓMO FUNCIONA
with tab_info:
    st.subheader("Cómo funciona")
    a, b, c, d = st.columns(4)
    a.markdown(f'<div class="etq">Sensibilidad 2025</div><div class="cifra">{RES["sens"]:.0%}</div>', unsafe_allow_html=True)
    b.markdown(f'<div class="etq">AUC 2025</div><div class="cifra">{f'{RES["auc"]:.2f}'.replace('.', ',')}</div>', unsafe_allow_html=True)
    miles = lambda n: f"{n:,}".replace(",", ".")
    c.markdown(f'<div class="etq">Estudiantes de prueba</div><div class="cifra">{miles(RES["n_test"])}</div>', unsafe_allow_html=True)
    d.markdown(f'<div class="etq">Precisión 2025</div><div class="cifra">{RES["prec"]:.0%}</div>', unsafe_allow_html=True)
    st.markdown(f"""
**Modelo.** Red neuronal MLP ({RES['arquitectura'].replace('.', ',')}) entrenada con {miles(RES['n_train'])} estudiantes de Cali (Saber 11 de 2019, 2020, 2022 y 2023).
La arquitectura se escogió con una búsqueda de hiperparámetros usando 2024 y se evaluó una sola vez con los {miles(RES['n_test'])} estudiantes de 2025.
La probabilidad está **calibrada** con regresión isotónica sobre 2024. El umbral de alerta es distinto por calendario
(A: {str(RES['umbral_calendario']['A']).replace('.', ',')}; B: {str(RES['umbral_calendario']['B']).replace('.', ',')}) porque con un solo umbral el modelo
detectaba apenas la mitad de los estudiantes en riesgo de calendario B.

**Datos de entrada.** Las 13 respuestas vienen del formulario socioeconómico del ICFES. Para usar la alerta al inicio del año escolar,
el colegio puede recoger esas mismas preguntas con su propio formulario (la plantilla trae las columnas).

**Para qué no sirve.** No es un diagnóstico individual, no usa notas ni asistencia, solo se entrenó con estudiantes de Cali y no debe usarse para
excluir ni etiquetar estudiantes: su propósito es priorizar acompañamiento.

**Privacidad (Ley 1581 de 2012).** Los archivos se procesan en memoria mientras la página está abierta y no se guardan en ningún servidor.
No se piden nombres ni documentos de identidad.
""")
    st.caption("Proyecto académico — Juan Sebastián Lozano Díaz, Julián David Cuéllar Cubillos y Alejandro Cárdenas Anturi · "
               "Profesores Jesús Alfonso López y José Luis Paniagua · UAO 2026-2")
