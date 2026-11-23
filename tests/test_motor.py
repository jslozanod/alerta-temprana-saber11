"""Pruebas del motor de la app. Se corren con:  pytest -q"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
from motor import Motor

M = Motor()
PAR = pd.read_csv(Path(__file__).resolve().parent.parent / "modelos" / "paridad_2025.csv", dtype={v: str for v in M.variables})


def test_paridad_con_keras():
    """La app (NumPy) debe dar la misma probabilidad que el modelo de Keras del notebook para 300 estudiantes de 2025."""
    p_app = M.predecir(PAR[M.variables])
    assert np.max(np.abs(p_app - PAR["prob_keras_calibrada"].values)) < 1e-5


def test_one_hot_un_uno_por_variable():
    X = M.codificar(PAR[M.variables])
    assert X.shape[1] == M.n_entradas == 72
    assert (X.sum(axis=1) == len(M.variables)).all()


def test_valores_raros_y_columnas_faltantes():
    df = pd.DataFrame([{"cole_jornada": "mañanita", "edad": "17.4"}])
    limpio, rep = M.limpiar(df)
    assert "cole_jornada" in rep["corregidos"] and len(rep["faltan"]) == 11
    assert limpio.loc[0, "grupo_edad"] == "17" and limpio.loc[0, "cole_jornada"] == "No reportado"
    p = M.predecir(limpio)
    assert 0 <= p[0] <= 1


def test_explicacion_y_umbral_por_calendario():
    muestra = PAR[M.variables].head(5)
    assert M.explicar(muestra).shape == (5, 13)
    u = M.umbrales(pd.DataFrame({"cole_calendario": ["A", "B", "No reportado"]}))
    assert u[0] == M.umbral_calendario["A"] and u[1] == M.umbral_calendario["B"] and u[2] == M.umbral
