# Sistema de Alerta Temprana Saber 11 (Cali)

Proyecto final de Inteligencia Artificial · Universidad Autónoma de Occidente · 2026-2
**Equipo:** Juan Sebastián Lozano Díaz, Julián David Cuéllar Cubillos y Alejandro Cárdenas Anturi
**Profesores:** Jesús Alfonso López y José Luis Paniagua

Estimamos el riesgo de que un estudiante de grado 11 de Cali obtenga **menos de 250 puntos** en el Saber 11, para que el colegio sepa a quién acompañar primero. La alerta apoya al docente; no reemplaza su criterio.

## Qué hay en este repositorio

| Carpeta | Contenido |
|---|---|
| `app/` | La aplicación web (Streamlit). `motor.py` hace la predicción solo con NumPy; `comun.py` tiene la plantilla, la lectura de archivos y los gráficos; `app.py` arma la navegación y `app_pages/` tiene las cuatro páginas (Inicio, Mi grupo, Un estudiante y Cómo funciona). |
| `modelos/` | El modelo exportado: pesos de la red (`pesos_mlp.npz`), categorías, calibración y umbrales (`modelo_meta.json`), y archivos de ejemplo. |
| `notebooks/` | `03_Modelo_Final_y_Despliegue_Saber11.ipynb`: búsqueda de hiperparámetros, calibración, evaluación en 2025, equidad, monitoreo y exportación. |
| `tests/` | Pruebas automáticas. La principal verifica que la app da la misma probabilidad que el modelo de Keras. |
| `documentos/` | Documento del proyecto y protocolo de validación con docentes. |

## El modelo en una tabla

| | |
|---|---|
| Datos | Saber 11 de Cali (ICFES): 2019, 2020 y 2022–2023 para entrenar, 2024 para escoger y calibrar, 2025 para la prueba final |
| Entrada | 13 variables del colegio, la familia y el estudiante (72 columnas después del one-hot) |
| Red | MLP 128 → 64 → 1, ReLU, Dropout 0,3, L2 0,001, Adam 3·10⁻⁴, lotes de 1024 (17 665 parámetros) |
| Cómo se escogió | Búsqueda aleatoria de 30 configuraciones de hiperparámetros + estabilidad con 3 semillas |
| Salida | Probabilidad calibrada (regresión isotónica) y umbral por calendario (A: 0,32 · B: 0,14) |
| Resultado en 2025 (20 764 estudiantes) | AUC 0,754 · sensibilidad 84,4 % · precisión 52,2 % · si se atiende al 10 % de mayor riesgo, 80 % de esa lista sí estaba en riesgo |

## Cómo correr la app en tu computador

```bash
pip install -r requirements.txt
streamlit run app/app.py
```

La app no necesita TensorFlow: lee los pesos exportados y hace el *forward pass* con NumPy (`z = a·W + b`, ReLU y sigmoide).

## Pruebas

```bash
pip install pytest
pytest -q
```

## Despliegue

La app está publicada en Streamlit Community Cloud, que la construye a partir de este repositorio: archivo principal `app/app.py`, dependencias en `requirements.txt`. Cada cambio que se sube a la rama `main` se vuelve a desplegar solo.

## Privacidad

Los archivos que sube un colegio se procesan en memoria y no se guardan. La plantilla no pide nombres ni documentos, solo un identificador opcional (Ley 1581 de 2012). Los 40 estudiantes de ejemplo son registros anonimizados de 2025.

## Limitaciones

Solo se entrenó con estudiantes de Cali. No usa notas ni asistencia. En calendario B detecta cerca de dos de cada tres estudiantes en riesgo (en calendario A, casi nueve de cada diez). Es un prototipo académico para priorizar acompañamiento: no es un diagnóstico y no debe usarse para excluir ni etiquetar estudiantes.

## Fuente de los datos

Resultados Saber 11 publicados por el ICFES (DataIcfes y datos abiertos de Colombia). El proceso de limpieza está documentado en el segundo entregable del proyecto.
