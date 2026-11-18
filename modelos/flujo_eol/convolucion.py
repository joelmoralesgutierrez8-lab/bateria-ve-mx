"""Retiros de baterías por convolución de cohortes anuales.

Una cohorte vendida en el año c (a mitad de año en promedio) tiene, durante el año y, edades entre
y - c - 0.5 y y - c + 0.5. La fracción de la cohorte que sale en el año y es
    p(y - c) = F(y - c + 0.5) - F(max(y - c - 0.5, 0))
y los retiros son  R(y) = sum_c V(c) p(y - c).  Con F(inf) = 1 toda cohorte termina saliendo
(conservación: sum_y R(y) -> sum_c V(c)).

Para varias entidades con Weibull distintas se convoluciona cada una con su parte de las ventas.
"""
from __future__ import annotations

import numpy as np

from modelos.vida_util import weibull as W


def pmf_anual(edades: np.ndarray, beta: float, eta: float) -> np.ndarray:
    alto = W.cdf(edades + 0.5, beta, eta)
    bajo = W.cdf(np.maximum(edades - 0.5, 0.0), beta, eta)
    return alto - bajo


def retiros(ventas: np.ndarray, beta: float, eta: float) -> np.ndarray:
    """ventas: (..., n_anios) desde el primer año de la serie. Devuelve retiros con la misma forma."""
    n = ventas.shape[-1]
    p = pmf_anual(np.arange(n, dtype=float), beta, eta)
    M = np.zeros((n, n))                        # M[c, y] = p(y - c) para y >= c
    for c in range(n):
        M[c, c:] = p[: n - c]
    return ventas @ M


def stock_en_uso(ventas: np.ndarray, retiros_: np.ndarray) -> np.ndarray:
    return np.cumsum(ventas - retiros_, axis=-1)
