"""Índices de Sobol (sensibilidad global) con el esquema de Saltelli y los estimadores de Saltelli (2010)
para primer orden y de Jansen (1999) para efecto total. Entradas independientes uniformes en [min, max].

    S1_i = mean(f(B) * (f(AB_i) - f(A))) / V        fracción de la varianza que explica x_i sola
    ST_i = mean((f(A) - f(AB_i))^2) / (2 V)          incluye sus interacciones con las demás
donde AB_i es la matriz A con la columna i tomada de B. Costo: N (k + 2) evaluaciones.
Intervalos por bootstrap sobre las N filas.
"""
from __future__ import annotations

import numpy as np


def matrices(rangos: dict, n: int, rng: np.random.Generator):
    nombres = list(rangos)
    lo = np.array([rangos[k]["min"] for k in nombres], float)
    hi = np.array([rangos[k]["max"] for k in nombres], float)
    A = lo + (hi - lo) * rng.random((n, len(nombres)))
    B = lo + (hi - lo) * rng.random((n, len(nombres)))
    return nombres, A, B


def indices(f, rangos: dict, n: int, rng: np.random.Generator, bootstrap: int = 300) -> dict:
    """f: función que recibe dict nombre -> vector y devuelve un vector de salidas."""
    nombres, A, B = matrices(rangos, n, rng)
    a_dict = lambda M: {k: M[:, j] for j, k in enumerate(nombres)}
    fA, fB = f(a_dict(A)), f(a_dict(B))
    fAB = []
    for j in range(len(nombres)):
        AB = A.copy()
        AB[:, j] = B[:, j]
        fAB.append(f(a_dict(AB)))
    fAB = np.array(fAB)

    def calc(idx):
        a, b, ab = fA[idx], fB[idx], fAB[:, idx]
        v = np.var(np.concatenate([a, b]))
        s1 = np.mean(b * (ab - a), axis=1) / v
        st = 0.5 * np.mean((a - ab) ** 2, axis=1) / v
        return s1, st

    s1, st = calc(np.arange(n))
    boot = [calc(rng.integers(0, n, n)) for _ in range(bootstrap)]
    b1 = np.array([b[0] for b in boot])
    bt = np.array([b[1] for b in boot])
    return {"nombres": nombres, "S1": s1, "ST": st,
            "S1_ic": np.quantile(b1, [0.05, 0.95], axis=0), "ST_ic": np.quantile(bt, [0.05, 0.95], axis=0)}
