"""Motor de predicción del Sistema de Alerta Temprana Saber 11.

Hace exactamente lo mismo que el modelo de Keras, pero solo con NumPy:
  1. Convierte las 13 respuestas en el vector one-hot de entrada (mismo orden que el OneHotEncoder del notebook).
  2. Forward pass de la red: z = a·W + b, ReLU en las capas ocultas y sigmoide en la salida.
  3. Calibra la probabilidad con la regresión isotónica ajustada en 2024.
Así la app no necesita TensorFlow y pesa unos pocos MB.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd

RUTA = Path(__file__).resolve().parent.parent / "modelos"

NOMBRES = {
    "cole_jornada": "Jornada del colegio", "cole_calendario": "Calendario", "cole_naturaleza": "Naturaleza del colegio",
    "cole_area_ubicacion": "Ubicación del colegio", "cole_bilingue": "Colegio bilingüe", "cole_caracter": "Carácter del colegio",
    "fami_tieneinternet": "Internet en el hogar", "fami_tienecomputador": "Computador en el hogar",
    "fami_educacionmadre": "Educación de la madre", "fami_educacionpadre": "Educación del padre",
    "fami_estratovivienda": "Estrato de la vivienda", "estu_genero": "Género", "grupo_edad": "Edad",
}
# Factores sobre los que el colegio puede hacer algo (apoyo con recursos o acompañamiento) frente a los que no
INTERVENIBLES = {"fami_tieneinternet", "fami_tienecomputador", "cole_jornada"}


class Motor:
    def __init__(self, ruta=RUTA):
        self.meta = json.load(open(ruta / "modelo_meta.json", encoding="utf-8"))
        pesos = np.load(ruta / "pesos_mlp.npz")
        self.W = [pesos[f"arr_{i}"] for i in range(len(pesos.files))]
        self.variables = self.meta["variables"]
        self.categorias = self.meta["categorias"]
        self.umbral = float(self.meta["umbral"])
        # Umbral por calendario: con uno solo, el modelo detectaba la mitad de los estudiantes en riesgo de calendario B
        self.umbral_calendario = {k: float(v) for k, v in self.meta.get("umbral_calendario", {}).items()}
        self.iso_x = np.array(self.meta["iso_x"]); self.iso_y = np.array(self.meta["iso_y"])
        self.fondo = pd.read_csv(ruta / "fondo_explicaciones.csv", dtype=str).iloc[:100]
        # posición de cada categoría dentro del vector one-hot
        self._pos, inicio = {}, 0
        for v in self.variables:
            self._pos[v] = {c: inicio + i for i, c in enumerate(self.categorias[v])}
            inicio += len(self.categorias[v])
        self.n_entradas = inicio

    # ------------------------------------------------------------------ datos
    @staticmethod
    def grupo_edad(edad):
        try:
            e = float(edad)
        except (TypeError, ValueError):
            return "No reportado"
        if np.isnan(e): return "No reportado"
        for lim, et in [(16, "15 o menos"), (17, "16"), (18, "17"), (19, "18"), (20, "19"), (25, "20 a 24"), (30, "25 a 29")]:
            if e < lim: return et
        return "30 o más"

    def limpiar(self, df):
        """Deja el archivo con las 13 variables. Devuelve los datos y un reporte de lo que se corrigió."""
        # Excel guarda los CSV con BOM: sin quitarlo, la primera columna no se reconoce (p. ej. id_estudiante)
        df = df.copy(); df.columns = [str(c).replace("﻿", "").strip() for c in df.columns]
        if "grupo_edad" not in df.columns and "edad" in df.columns:
            df["grupo_edad"] = df["edad"].map(self.grupo_edad)
        faltan = [v for v in self.variables if v not in df.columns]
        reporte = {"faltan": faltan, "corregidos": {}}
        for v in self.variables:
            if v in faltan:
                df[v] = "No reportado"; continue
            val = df[v].astype("string").str.strip().fillna("No reportado")
            invalidos = ~val.isin(self.categorias[v])
            if invalidos.any():
                reporte["corregidos"][v] = sorted(val[invalidos].unique().tolist())[:5] + ([f"... ({int(invalidos.sum())} filas)"])
            df[v] = val.where(~invalidos, "No reportado").astype(str)
        return df, reporte

    def codificar(self, df):
        X = np.zeros((len(df), self.n_entradas), dtype=np.float32)
        filas = np.arange(len(df))
        for v in self.variables:
            col = df[v].map(self._pos[v])
            ok = col.notna().values
            X[filas[ok], col[ok].astype(int).values] = 1.0  # categoría desconocida -> todo en cero (como handle_unknown="ignore")
        return X

    # ------------------------------------------------------------------ red
    def forward(self, X):
        a, n = X, len(self.W) // 2
        for k in range(n):
            z = a @ self.W[2 * k] + self.W[2 * k + 1]
            a = np.maximum(z, 0.0) if k < n - 1 else 1.0 / (1.0 + np.exp(-z))
        return a.ravel()

    def calibrar(self, p):
        return np.interp(p, self.iso_x, self.iso_y)

    def predecir(self, df, calibrada=True):
        p = self.forward(self.codificar(df))
        return self.calibrar(p) if calibrada else p

    def umbrales(self, df):
        """Umbral que le corresponde a cada estudiante según el calendario de su colegio."""
        return df["cole_calendario"].map(self.umbral_calendario).fillna(self.umbral).values.astype(float)

    # ------------------------------------------------------------------ explicaciones
    def explicar(self, df):
        """Aporte de cada variable a la probabilidad de cada estudiante.

        Para la variable j: probabilidad del estudiante menos la probabilidad promedio cuando su respuesta en j
        se reemplaza por la de 100 estudiantes de referencia. Positivo = esa respuesta sube el riesgo.
        """
        base = self.predecir(df)
        n, m = len(df), len(self.fondo)
        aportes = np.zeros((n, len(self.variables)))
        for j, v in enumerate(self.variables):
            rep = df.loc[df.index.repeat(m), self.variables].reset_index(drop=True)
            rep[v] = np.tile(self.fondo[v].values, n)
            p = self.predecir(rep).reshape(n, m).mean(axis=1)
            aportes[:, j] = base - p
        return pd.DataFrame(aportes, columns=self.variables, index=df.index)

    # ------------------------------------------------------------------ monitoreo
    def psi(self, df):
        """Population Stability Index de cada variable frente a los datos de entrenamiento (2019-2023)."""
        filas = []
        for v in self.variables:
            ref = pd.Series(self.meta["referencia"][v]); obs = df[v].value_counts(normalize=True)
            cats = sorted(set(ref.index) | set(obs.index))
            a = ref.reindex(cats, fill_value=0).values + 1e-4; b = obs.reindex(cats, fill_value=0).values + 1e-4
            filas.append({"variable": NOMBRES[v], "psi": float(((b - a) * np.log(b / a)).sum())})
        return pd.DataFrame(filas).sort_values("psi", ascending=False)
