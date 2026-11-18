"""Curva S de participación de mercado (Fisher-Pry), el análogo de Bass para un mercado de reemplazo.

    s(t) = s_max / (1 + exp(-k (t - t0)))          participación del tipo en las ventas del año t
    logit(s/s_max) = k t - k t0                     lineal en t: se ajusta por mínimos cuadrados

s_max (techo de participación) NO es identificable con datos de inicio de curva: se fija por escenario.
La incertidumbre de (k, t0) se obtiene con bootstrap de residuos del ajuste lineal.
"""
from __future__ import annotations

import numpy as np


def _logit(x):
    return np.log(x / (1 - x))


def ajustar(anios, s, s_max: float, pesos=None) -> dict:
    anios, s = np.asarray(anios, float), np.asarray(s, float)
    ok = (s > 0) & (s < s_max)
    if ok.sum() < 3:
        raise ValueError("se necesitan al menos 3 años con 0 < s < s_max")
    x, y = anios[ok], _logit(s[ok] / s_max)
    w = np.ones_like(x) if pesos is None else np.asarray(pesos, float)[ok]
    k, b = np.polyfit(x, y, 1, w=np.sqrt(w))
    resid = y - (k * x + b)
    return {"k": float(k), "t0": float(-b / k), "s_max": s_max, "residuos": resid, "x": x, "y_ajustada": k * x + b,
            "anios_usados": x}


def predecir(anios, k: float, t0: float, s_max: float):
    return s_max / (1.0 + np.exp(-k * (np.asarray(anios, float) - t0)))


def bootstrap(ajuste: dict, repeticiones: int, rng: np.random.Generator) -> np.ndarray:
    """Devuelve matriz (repeticiones x 2) con (k, t0) re-ajustados sobre y* = y_ajustada + residuo remuestreado."""
    x, yhat, r = ajuste["x"], ajuste["y_ajustada"], ajuste["residuos"]
    out = np.empty((repeticiones, 2))
    for i in range(repeticiones):
        y = yhat + rng.choice(r, len(r), replace=True)
        k, b = np.polyfit(x, y, 1)
        out[i] = (k, -b / k)
    return out
