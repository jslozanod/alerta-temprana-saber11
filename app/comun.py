"""Funciones compartidas por las páginas de la aplicación: modelo, plantillas, lectura de archivos y gráficos."""
import io
import json
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from motor import Motor, NOMBRES, INTERVENIBLES

ROJO, GRIS, CREMA = "#C8102E", "#8A8A8A", "#F5F1EA"
RAIZ = Path(__file__).resolve().parent.parent


@st.cache_resource
def cargar():
    m = Motor()
    res = json.load(open(RAIZ / "modelos" / "resultados_resumen.json", encoding="utf-8"))
    return m, res


motor, RES = cargar()
VARS = motor.variables

GRUPOS = [("Colegio", ":material/school:", ["cole_jornada", "cole_calendario", "cole_naturaleza", "cole_area_ubicacion",
                                             "cole_bilingue", "cole_caracter"]),
          ("Familia", ":material/home:", ["fami_tieneinternet", "fami_tienecomputador", "fami_educacionmadre",
                                          "fami_educacionpadre", "fami_estratovivienda"]),
          ("Estudiante", ":material/person:", ["estu_genero", "grupo_edad"])]


def pct(x, dec=0):
    return f"{x * 100:.{dec}f} %".replace(".", ",")


def miles(n):
    return f"{n:,}".replace(",", ".")


def coma(x, dec=2):
    return f"{x:.{dec}f}".replace(".", ",")


# ---------------------------------------------------------------------------- plantillas
def ejemplo():
    """Grupo de ejemplo: 40 estudiantes anonimizados de 2025."""
    ej = pd.read_csv(RAIZ / "modelos" / "ejemplo_grupo.csv", dtype=str)
    ej.insert(0, "id_estudiante", [f"E{i + 1:03d}" for i in range(len(ej))])
    return ej


@st.cache_data
def plantilla_vacia(filas=500):
    """Excel vacío: hoja Estudiantes con listas desplegables, hoja Opciones visible e Instrucciones."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.worksheet.datavalidation import DataValidation
    from openpyxl.utils import get_column_letter

    enc_font, enc_fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="C8102E")
    wb = Workbook(); ws = wb.active; ws.title = "Estudiantes"
    op = wb.create_sheet("Opciones")
    ins = wb.create_sheet("Instrucciones")
    cols = ["id_estudiante"] + VARS
    for j, c in enumerate(cols, 1):
        letra = get_column_letter(j)
        for hoja in (ws, op):
            celda = hoja.cell(1, j, c); celda.font = enc_font; celda.fill = enc_fill
            celda.alignment = Alignment(horizontal="center")
            hoja.column_dimensions[letra].width = max(18, len(c) + 4)
        if c == "id_estudiante":
            op.cell(2, j, "Código anónimo (ej. 11A-01)").font = Font(italic=True, color="666666")
            continue
        cats = motor.categorias[c]
        for i, cat in enumerate(cats, 2):
            op.cell(i, j, cat)
        dv = DataValidation(type="list", formula1=f"Opciones!${letra}$2:${letra}${len(cats) + 1}", allow_blank=True,
                            showErrorMessage=True, errorTitle="Valor no válido",
                            error="Elija una opción de la lista desplegable (vea la hoja Opciones).")
        ws.add_data_validation(dv); dv.add(f"{letra}2:{letra}{filas + 1}")
    ws.freeze_panes = "B2"; op.freeze_panes = "A2"
    textos = ["PLANTILLA DE CARGA · ALERTA TEMPRANA SABER 11", "",
              "1. En la hoja Estudiantes escriba un código anónimo por estudiante en id_estudiante.",
              "2. Complete una fila por estudiante. Use la lista desplegable de cada celda para elegir la respuesta.",
              "3. Las opciones de las listas son las mismas con que se entrenó el modelo; no cambie los encabezados.",
              "4. Si no conoce una respuesta, elija «No reportado» cuando esté disponible. No invente datos.",
              "5. Guarde el archivo en formato .xlsx y súbalo en «Mi grupo» → «Subir mi grupo (Excel o CSV)».",
              "6. No incluya nombres, documentos ni información que identifique directamente a los estudiantes.",
              f"7. Hay espacio para {filas} estudiantes (filas 2 a {filas + 1}). La hoja Opciones muestra las respuestas válidas.",
              "8. El resultado apoya la decisión del docente; no reemplaza su criterio ni es una evaluación académica.",
              "IMPORTANTE: las listas desplegables funcionan en Excel y Google Sheets; en otros programas pueden no verse."]
    for i, t in enumerate(textos, 1):
        ins.cell(i, 1, t).font = Font(bold=(i in (1, len(textos))), size=16 if i == 1 else 11,
                                      color="C8102E" if i == len(textos) else None)
    ins.column_dimensions["A"].width = 115
    buf = io.BytesIO(); wb.save(buf)
    return buf.getvalue()


def leer_archivo(f):
    if f.name.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(f, dtype=str)  # lee la primera hoja (Estudiantes)
    else:
        df = pd.read_csv(f, dtype=str, sep=None, engine="python", encoding="utf-8-sig", encoding_errors="replace")
    df.columns = df.columns.astype(str).str.replace("﻿", "").str.strip()
    return df.dropna(how="all")  # la plantilla trae filas vacías con listas desplegables


# ---------------------------------------------------------------------------- cálculo
@st.cache_data(max_entries=20, show_spinner="Calculando el riesgo de cada estudiante…")
def analizar(df):
    """Limpia, predice y explica. Se guarda en caché para que mover los controles no recalcule todo."""
    datos, rep = motor.limpiar(df)
    prob = motor.predecir(datos)
    aportes = motor.explicar(datos)
    umbral = motor.umbrales(datos)
    if "id_estudiante" in datos.columns:
        ident = datos["id_estudiante"].fillna("").astype(str).str.strip()
        ident = ident.where(ident != "", [f"Fila {i + 1}" for i in range(len(datos))])
    else:
        ident = pd.Series([f"Fila {i + 1}" for i in range(len(datos))], index=datos.index)
    incompletos = int((datos[VARS] == "No reportado").any(axis=1).sum())
    return datos, rep, prob, aportes, umbral, ident.values, incompletos


def razones(fila_aportes, k=3):
    top = fila_aportes.sort_values(ascending=False)
    top = top[top > 0.005].head(k)
    return " · ".join(NOMBRES[v] for v in top.index) or "Sin factores destacados"


def acciones(resp, p, u):
    a = []
    if resp.get("fami_tienecomputador") == "No" or resp.get("fami_tieneinternet") == "No":
        a.append((":material/computer:", "Dar acceso a sala de sistemas o biblioteca con internet para preparar el examen."))
    if resp.get("cole_jornada") in ("NOCHE", "SABATINA", "TARDE"):
        a.append((":material/schedule:", "Ofrecer refuerzos en horarios compatibles con su jornada."))
    if p >= u:
        a.append((":material/assignment_ind:", "Incluirlo en el plan de acompañamiento y en los simulacros desde el inicio del año."))
        a.append((":material/family_restroom:", "Conversar con la familia sobre el apoyo en casa durante la preparación."))
    return a


# ---------------------------------------------------------------------------- gráficos
def grafico_aportes(serie, titulo, k=None):
    serie = serie.sort_values(key=abs, ascending=False)
    if k:
        serie = serie.head(k)
    d = pd.DataFrame({"Variable": [NOMBRES[v] for v in serie.index], "Puntos": serie.values * 100,
                      "Tipo": ["Intervenible" if v in INTERVENIBLES else "Contexto" for v in serie.index]})
    d["Efecto"] = np.where(d["Puntos"] >= 0, "Sube el riesgo", "Baja el riesgo")
    return alt.Chart(d).mark_bar(cornerRadiusEnd=3).encode(
        x=alt.X("Puntos:Q", title=titulo),
        y=alt.Y("Variable:N", sort="-x", title=None, axis=alt.Axis(labelLimit=260)),
        color=alt.Color("Efecto:N", scale=alt.Scale(domain=["Sube el riesgo", "Baja el riesgo"], range=[ROJO, GRIS]),
                        legend=alt.Legend(orient="top", title=None)),
        tooltip=["Variable", "Tipo", alt.Tooltip("Puntos:Q", format=".1f", title="Puntos porcentuales")],
    ).properties(height=alt.Step(28))


def grafico_distribucion(tabla):
    """Cada punto es un estudiante; la posición es su riesgo. Ayuda a ver si el grupo está concentrado o disperso."""
    base = alt.Chart(tabla).encode(
        x=alt.X("Riesgo:Q", title="Riesgo estimado (%)", scale=alt.Scale(domain=[0, 100])),
    )
    puntos = base.mark_circle(size=140, opacity=0.85).encode(
        y=alt.Y("jitter:Q", axis=None, title=None),
        color=alt.Color("Prioridad:N", scale=alt.Scale(domain=["Priorizado", "No priorizado"], range=[ROJO, "#BDBDBD"]),
                        legend=alt.Legend(orient="top", title=None)),
        tooltip=["Estudiante", alt.Tooltip("Riesgo:Q", format=".0f", title="Riesgo (%)"), "Prioridad"],
    )
    return puntos.properties(height=170)
