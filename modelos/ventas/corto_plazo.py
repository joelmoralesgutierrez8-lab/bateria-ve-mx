"""Modelos mensuales de corto plazo (horizonte 12 meses) y su comparación con validación de origen móvil.

Todos trabajan en log1p(unidades) y devuelven el pronóstico en unidades. Cada modelo es una función
f(y_entrenamiento: pd.Series, h: int, semilla: int) -> np.ndarray de largo h.
Los que dependen de librerías opcionales (statsmodels, lightgbm, torch) se omiten con aviso si no están.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd


# ---------------------------------------------------------------- línea base
def naive_estacional(y: pd.Series, h: int, semilla: int = 42) -> np.ndarray:
    ult = y.to_numpy()[-12:]
    return np.array([ult[i % 12] for i in range(h)])


def deriva_estacional(y: pd.Series, h: int, semilla: int = 42) -> np.ndarray:
    """Naive estacional en log + crecimiento interanual medio de los últimos 12 meses (captura la tendencia,
    que el naive puro no tiene en una serie que crece rápido)."""
    l = np.log1p(y.to_numpy())
    g = np.mean(l[-12:] - l[-24:-12]) if len(l) >= 24 else 0.0
    base = l[-12:]
    return np.expm1(np.array([base[i % 12] + g * (1 + i // 12) for i in range(h)]))


# ---------------------------------------------------------------- statsmodels
def sarima(y: pd.Series, h: int, semilla: int = 42) -> np.ndarray:
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    l = np.log1p(y)
    mejor, mejor_aic = None, np.inf
    for orden in [(0, 1, 1), (1, 1, 0), (1, 1, 1), (0, 1, 2)]:
        for est in [(0, 1, 1, 12), (0, 0, 0, 12)]:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    r = SARIMAX(l, order=orden, seasonal_order=est, enforce_stationarity=False,
                                enforce_invertibility=False).fit(disp=False)
                except Exception:
                    continue
            if r.aic < mejor_aic:
                mejor, mejor_aic = r, r.aic
    return np.expm1(np.asarray(mejor.forecast(h)))


def ets(y: pd.Series, h: int, semilla: int = 42) -> np.ndarray:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    l = np.log1p(y)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = ExponentialSmoothing(l, trend="add", damped_trend=True, seasonal="add", seasonal_periods=12).fit()
    return np.expm1(np.asarray(r.forecast(h)))


# ---------------------------------------------------------------- LightGBM directo multi-horizonte
def _rasgos(l: np.ndarray, fin: int, meses: np.ndarray) -> list:
    """Rasgos en el índice fin (último observado): rezagos y diferencias. Relativos al último valor para que
    el árbol aprenda CAMBIOS (no niveles, que no puede extrapolar)."""
    u = l[fin]
    return [l[fin - k] - u for k in (1, 2, 3, 6, 11, 12)] + [u - l[fin - 12], meses[fin]]


def lightgbm_directo(y: pd.Series, h: int, semilla: int = 42) -> np.ndarray:
    import lightgbm as lgb

    l = np.log1p(y.to_numpy())
    meses = y.index.month.to_numpy()
    pred = []
    for paso in range(1, h + 1):
        X, Y = [], []
        for fin in range(12, len(l) - paso):
            X.append(_rasgos(l, fin, meses))
            Y.append(l[fin + paso] - l[fin])          # objetivo: cambio log a `paso` meses
        # interfaz nativa de LightGBM (no requiere scikit-learn)
        params = {"objective": "regression", "learning_rate": 0.03, "num_leaves": 8, "min_data_in_leaf": 5,
                  "bagging_fraction": 0.8, "bagging_freq": 1, "seed": semilla, "deterministic": True,
                  "verbose": -1}
        m = lgb.train(params, lgb.Dataset(np.array(X), np.array(Y)), num_boost_round=300)
        pred.append(l[-1] + m.predict(np.array([_rasgos(l, len(l) - 1, meses)]))[0])
    return np.expm1(np.array(pred))


# ---------------------------------------------------------------- LSTM pequeña
def lstm(y: pd.Series, h: int, semilla: int = 42, ventana: int = 12, epocas: int = 300) -> np.ndarray:
    import torch
    from torch import nn

    torch.manual_seed(semilla)
    l = np.log1p(y.to_numpy()).astype(np.float32)
    d = np.diff(l)                                   # trabaja en cambios: estacionaria aprox.
    mu, sd = d.mean(), d.std() + 1e-6
    z = (d - mu) / sd
    X = np.stack([z[i : i + ventana] for i in range(len(z) - ventana)])[..., None]
    Y = z[ventana:]

    class Red(nn.Module):
        def __init__(self):
            super().__init__()
            self.lstm = nn.LSTM(1, 16, batch_first=True)
            self.sal = nn.Linear(16, 1)

        def forward(self, x):
            o, _ = self.lstm(x)
            return self.sal(o[:, -1]).squeeze(-1)

    red = Red()
    opt = torch.optim.Adam(red.parameters(), lr=0.01)
    Xt, Yt = torch.tensor(X), torch.tensor(Y)
    for _ in range(epocas):
        opt.zero_grad()
        perdida = nn.functional.mse_loss(red(Xt), Yt)
        perdida.backward()
        opt.step()
    ventana_actual = list(z[-ventana:])
    nivel, pred = l[-1], []
    with torch.no_grad():
        for _ in range(h):
            dz = float(red(torch.tensor(np.array(ventana_actual[-ventana:], np.float32)[None, :, None])))
            ventana_actual.append(dz)
            nivel += dz * sd + mu
            pred.append(nivel)
    return np.expm1(np.array(pred))


MODELOS = {"naive_estacional": naive_estacional, "deriva_estacional": deriva_estacional, "sarima": sarima,
           "ets": ets, "lightgbm": lightgbm_directo, "lstm": lstm}


# ---------------------------------------------------------------- validación de origen móvil
def mase_escala(y_entreno: np.ndarray) -> float:
    """Escala del MASE en log1p: MAE del naive estacional dentro del entrenamiento. Se usa escala log porque
    la serie creció ~100x; en unidades, la escala quedaría dominada por los años con decenas de ventas y el
    MASE sería engañoso."""
    l = np.log1p(y_entreno)
    return float(np.mean(np.abs(l[12:] - l[:-12])))


def origen_movil(y: pd.Series, modelos: dict, origenes: int, h: int, semilla: int = 42) -> pd.DataFrame:
    """Para cada origen o en los últimos `origenes` meses (con h meses por delante disponibles... o los que
    haya), entrena con y[:o] y pronostica h. Devuelve errores por modelo, origen y horizonte."""
    filas = []
    n = len(y)
    for o in range(n - origenes, n):
        entreno = y.iloc[:o]
        real = y.iloc[o : o + h].to_numpy()
        if len(real) == 0:
            continue
        escala = mase_escala(entreno.to_numpy())
        for nombre, f in modelos.items():
            try:
                p = np.asarray(f(entreno, len(real), semilla))[: len(real)]
            except ImportError as e:
                warnings.warn(f"{nombre} omitido (falta la librería): {e}")
                continue
            except Exception as e:                       # un modelo que falla no detiene la validación
                warnings.warn(f"{nombre} falló en el origen {y.index[o]:%Y-%m}: {type(e).__name__}: {e}")
                continue
            for k in range(len(real)):
                filas.append({"modelo": nombre, "origen": y.index[o], "horizonte": k + 1, "real": real[k],
                              "pred": p[k], "error_abs": abs(real[k] - p[k]),
                              "error_log": abs(np.log1p(real[k]) - np.log1p(max(p[k], 0.0))), "escala_mase": escala})
    return pd.DataFrame(filas)


def resumen(errores: pd.DataFrame) -> pd.DataFrame:
    g = errores.assign(err2=lambda d: (d.real - d.pred) ** 2,
                       ape=lambda d: np.abs(d.real - d.pred) / np.maximum(d.real, 1),
                       esc=lambda d: d.error_log / d.escala_mase)
    out = g.groupby("modelo").agg(MAE=("error_abs", "mean"), RMSE=("err2", lambda s: np.sqrt(s.mean())),
                                  MAPE=("ape", "mean"), MASE=("esc", "mean"), n=("error_abs", "size"))
    return out.sort_values("MASE")
