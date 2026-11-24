import altair as alt
import pandas as pd
import streamlit as st

from comun import RES, ROJO, motor, pct, miles, coma

st.caption(":red[**CÓMO FUNCIONA**]")
st.header("Qué hay detrás de la alerta")

with st.container(horizontal=True):
    st.metric("Sensibilidad 2025", pct(RES["sens"]), border=True, help="De cada 100 estudiantes en riesgo, cuántos detecta.")
    st.metric("AUC 2025", coma(RES["auc"]), border=True, help="Capacidad de ordenar: 0,5 es azar y 1 es perfecto.")
    st.metric("Precisión 2025", pct(RES["prec"]), border=True, help="De cada 100 alertas, cuántas eran estudiantes en riesgo.")
    st.metric("Estudiantes de prueba", miles(RES["n_test"]), border=True, help="Todo 2025, evaluado una sola vez.")

st.graphviz_chart("""
digraph {
  rankdir=LR; bgcolor="transparent";
  node [shape=box, style="rounded,filled", fillcolor="#F5F1EA", color="#C8102E", fontname="Helvetica", fontsize=11];
  edge [color="#8A8A8A"];
  a [label="Saber 11 Cali\\n2019–2025\\n(ICFES)"]; b [label="13 respuestas\\ndel contexto"];
  c [label="Red neuronal MLP\\n128 → 64 → 1"]; d [label="Calibración\\nisotónica (2024)"];
  e [label="Umbral por\\ncalendario"]; f [label="Lista priorizada\\npara el colegio", fillcolor="#C8102E", fontcolor="white"];
  a -> b -> c -> d -> e -> f;
}""", alt="Flujo: datos del ICFES, 13 respuestas, red neuronal, calibración, umbral y lista priorizada")

t1, t2, t3, t4 = st.tabs([":material/neurology: Modelo", ":material/database: Datos",
                          ":material/groups: Validación con docentes", ":material/shield: Límites y privacidad"])
with t1:
    st.markdown(f"""
- **Red neuronal MLP** ({RES['arquitectura'].replace('.', ',')}), entrenada con {miles(RES['n_train'])} estudiantes de Cali.
- La arquitectura salió de una **búsqueda aleatoria de 30 configuraciones** evaluadas en 2024, repetida con 3 semillas para
  comprobar que el resultado es estable.
- La probabilidad está **calibrada** con regresión isotónica: si dice 60 %, unos 6 de cada 10 estudiantes así obtienen menos de 250.
- **Un umbral por calendario** (A: {coma(motor.umbral_calendario['A'])}; B: {coma(motor.umbral_calendario['B'])}). Con uno solo,
  el modelo detectaba apenas la mitad de los estudiantes en riesgo de calendario B.
- La aplicación calcula la red con NumPy y una prueba automática verifica que da lo mismo que el modelo original de Keras.
""")
with t2:
    st.markdown("""
- **Fuente:** resultados individuales del Saber 11 publicados por el ICFES, colegios de Cali, 2019 a 2025.
- **Partición en el tiempo:** entrenamiento 2019–2023, selección y calibración con 2024, prueba con 2025.
  Así se simula el uso real: aprender del pasado y predecir un año nuevo.
- **Variables:** 13 respuestas del colegio, la familia y el estudiante que se conocen antes del examen.
  No se usan puntajes ni notas.
- **2026:** al cierre del proyecto el ICFES no había publicado los microdatos de 2026. El monitoreo (PSI) de *Mi grupo*
  indica cuándo los datos nuevos se alejan de los de entrenamiento y conviene reentrenar.
""")
with t3:
    st.markdown("Docentes y directivos usaron la aplicación con el grupo de ejemplo y respondieron el cuestionario SUS "
                "(System Usability Scale) más 7 preguntas de utilidad.")
    with st.container(horizontal=True):
        st.metric("Puntaje SUS promedio", "70", border=True, help="Escala 0 a 100. Más de 68 está por encima del promedio.")
        st.metric("Participantes", "3", border=True, help="Docente, coordinador(a) y directivo(a) de colegios privados.")
        st.metric("La lista por riesgo ayuda a decidir", "5,0 / 5", border=True)
    u = pd.DataFrame({"Pregunta": ["La lista ayuda a decidir a quién acompañar", "Entendí por qué sale riesgo alto",
                                     "La recomendaría", "Podríamos conseguir los datos a inicio de año",
                                     "Confiaría en el porcentaje", "Los cupos se ajustan a mi colegio"],
                      "Promedio": [5.0, 4.67, 4.67, 4.33, 4.0, 4.0]})
    st.altair_chart(alt.Chart(u).mark_bar(color=ROJO, cornerRadiusEnd=3).encode(
        x=alt.X("Promedio:Q", scale=alt.Scale(domain=[0, 5]), title="Promedio (1 = desacuerdo, 5 = de acuerdo)"),
        y=alt.Y("Pregunta:N", sort="-x", title=None, axis=alt.Axis(labelLimit=340, labelFontSize=12)),
        tooltip=["Pregunta", alt.Tooltip("Promedio:Q", format=".1f")]).properties(height=alt.Step(30)),
        alt="Promedio de las preguntas de utilidad")
    st.markdown("**Lo que cambiamos por sus comentarios.** En las sesiones observadas todas las tareas se lograron, pero con ayuda, y pidieron "
                "acompañamiento al empezar. Por eso agregamos la **guía rápida**, las ayudas en pantalla, la "
                "**plantilla en Excel con listas desplegables** y el **detalle por estudiante con acciones sugeridas**.")
    st.caption("Son 3 participantes, todos de colegios privados: los resultados son indicativos, no concluyentes.")
with t4:
    st.markdown("""
- **No es un diagnóstico.** Estima un riesgo con 13 variables del contexto; el criterio del docente sigue siendo el que decide.
- **No sirve para excluir ni etiquetar estudiantes.** Su propósito es repartir mejor el acompañamiento.
- Cerca de la mitad de las alertas son de estudiantes que finalmente superan los 250 puntos: preferimos revisar de más a
  dejar sin apoyo a quien lo necesita.
- Solo se entrenó con estudiantes de Cali; en otras ciudades habría que validarlo de nuevo.
- **Privacidad (Ley 1581 de 2012):** los archivos se procesan en memoria mientras la página está abierta y no se guardan.
  No se piden nombres ni documentos.
""")
