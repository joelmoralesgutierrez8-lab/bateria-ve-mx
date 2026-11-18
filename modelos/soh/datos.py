"""Ventanas de entrenamiento para predecir el SoH futuro a partir de su historia reciente.

Tarea: con las últimas `ventana` mediciones de SoH de una celda (suavizado), predecir el SoH `h` mediciones
después. El objetivo es el CAMBIO de SoH (futuro - último), no el nivel, para que el modelo aprenda la forma
de la degradación y no memorice niveles.
Rasgos: los `ventana` valores relativos al último, el último SoH, la pendiente lineal de la ventana,
la temperatura de prueba y la posición (medición número) normalizada por la longitud típica del conjunto.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from modelos.vida_util.eol_celdas import soh_robusto, suavizar


def curvas(df: pd.DataFrame, cfg_det: dict, celdas: list[str], paso: int = 1, temp_defecto: float = 25.0) -> dict:
    """{celda: (soh suavizado submuestreado cada `paso`, temperatura)}"""
    out = {}
    for c in celdas:
        g = df[df["bateria"] == c].sort_values("ciclo")
        soh, _ = soh_robusto(g["capacidad_ah"].to_numpy(float), cfg_det)
        s = suavizar(soh, cfg_det["ventana_suavizado"])
        s = pd.Series(s).interpolate(limit_direction="both").to_numpy()[::paso]
        temp = float(g["temp_ambiente_c"].iloc[0]) if "temp_ambiente_c" in g else temp_defecto
        out[c] = (s, temp)
    return out


def ventanas(curvas_: dict, ventana: int, h: int, largo_ref: float):
    X, y, grupo, ultimo = [], [], [], []
    for c, (s, temp) in curvas_.items():
        for fin in range(ventana - 1, len(s) - h):
            w = s[fin - ventana + 1 : fin + 1]
            pend = np.polyfit(np.arange(ventana), w, 1)[0]
            X.append(list(w - w[-1]) + [w[-1], pend, temp, fin / largo_ref])
            y.append(s[fin + h] - w[-1])
            grupo.append(c)
            ultimo.append(w[-1])
    return np.array(X), np.array(y), np.array(grupo), np.array(ultimo)


def base_persistencia(X, ventana: int):
    return np.zeros(len(X))                                  # el SoH no cambia


def base_lineal(X, ventana: int, h: int):
    return X[:, ventana + 1] * h                              # extrapola la pendiente de la ventana
