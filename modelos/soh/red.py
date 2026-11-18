"""Perceptrón multicapa (MLP) en NumPy puro: capas densas con ReLU, salida lineal, pérdida MSE con
regularización L2 y optimizador Adam. Sin dependencias fuera de NumPy, reproducible con semilla.

Se usa para regresión del cambio de SoH. La incertidumbre se estima con un ENSAMBLE de redes entrenadas con
semillas distintas: la dispersión entre miembros aproxima la incertidumbre del modelo (no la del ruido).
"""
from __future__ import annotations

import numpy as np


class MLP:
    def __init__(self, n_entradas: int, ocultas=(32, 16), semilla: int = 42, l2: float = 1e-4,
                 lr: float = 3e-3, epocas: int = 1500, lote: int = 128):
        self.rng = np.random.default_rng(semilla)
        dims = [n_entradas, *ocultas, 1]
        self.W = [self.rng.normal(0, np.sqrt(2.0 / a), (a, b)) for a, b in zip(dims[:-1], dims[1:])]   # He
        self.b = [np.zeros(b) for b in dims[1:]]
        self.l2, self.lr, self.epocas, self.lote = l2, lr, epocas, lote
        self.mu_x = self.sd_x = None
        self.mu_y = self.sd_y = 0.0

    def _forward(self, X):
        acts = [X]
        for i, (W, b) in enumerate(zip(self.W, self.b)):
            z = acts[-1] @ W + b
            acts.append(np.maximum(z, 0.0) if i < len(self.W) - 1 else z)
        return acts

    def fit(self, X, y):
        X, y = np.asarray(X, float), np.asarray(y, float)
        self.mu_x, self.sd_x = X.mean(0), X.std(0) + 1e-9
        self.mu_y, self.sd_y = y.mean(), y.std() + 1e-9
        Xn, yn = (X - self.mu_x) / self.sd_x, ((y - self.mu_y) / self.sd_y)[:, None]
        m = [np.zeros_like(p) for p in self.W + self.b]
        v = [np.zeros_like(p) for p in self.W + self.b]
        b1, b2, eps, t = 0.9, 0.999, 1e-8, 0
        n = len(Xn)
        for _ in range(self.epocas):
            orden = self.rng.permutation(n)
            for i in range(0, n, self.lote):
                idx = orden[i : i + self.lote]
                acts = self._forward(Xn[idx])
                delta = 2 * (acts[-1] - yn[idx]) / len(idx)
                gW, gb = [], []
                for k in range(len(self.W) - 1, -1, -1):
                    gW.insert(0, acts[k].T @ delta + self.l2 * self.W[k])
                    gb.insert(0, delta.sum(0))
                    if k > 0:
                        delta = (delta @ self.W[k].T) * (acts[k] > 0)
                t += 1
                params = self.W + self.b
                for j, (p, g) in enumerate(zip(params, gW + gb)):
                    m[j] = b1 * m[j] + (1 - b1) * g
                    v[j] = b2 * v[j] + (1 - b2) * g * g
                    p -= self.lr * (m[j] / (1 - b1**t)) / (np.sqrt(v[j] / (1 - b2**t)) + eps)
        return self

    def predict(self, X):
        Xn = (np.asarray(X, float) - self.mu_x) / self.sd_x
        return self._forward(Xn)[-1][:, 0] * self.sd_y + self.mu_y


class Ensamble:
    def __init__(self, n_entradas: int, miembros: int = 5, semilla: int = 42, **kw):
        self.redes = [MLP(n_entradas, semilla=semilla + i, **kw) for i in range(miembros)]

    def fit(self, X, y):
        for r in self.redes:
            r.fit(X, y)
        return self

    def predict(self, X):
        P = np.stack([r.predict(X) for r in self.redes])
        return P.mean(0), P.std(0)
