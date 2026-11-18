"""Series de ventas de INEGI listas para modelar."""
from __future__ import annotations

import numpy as np
import pandas as pd

TIPOS = ["BEV", "PHEV", "HEV"]


def serie_nacional_mensual(df: pd.DataFrame) -> pd.DataFrame:
    """fecha (inicio de mes) x tipo, unidades."""
    d = df.copy()
    d["fecha"] = pd.to_datetime(d["fecha"])
    s = d.groupby(["fecha", "tipo"])["unidades"].sum().unstack()[TIPOS].sort_index()
    return s.asfreq("MS").fillna(0.0)


def participacion_entidad(df: pd.DataFrame, meses: int = 24) -> pd.DataFrame:
    """Participación de cada entidad en las ventas de cada tipo en los últimos `meses` (para repartir la
    proyección nacional). 'No especificado' se conserva: no se puede asignar a un clima."""
    d = df.copy()
    d["fecha"] = pd.to_datetime(d["fecha"])
    d = d[d["fecha"] > d["fecha"].max() - pd.DateOffset(months=meses)]
    t = d.groupby(["entidad", "tipo"])["unidades"].sum().unstack()[TIPOS].fillna(0.0)
    return t / t.sum()


def indice_estacional(serie: pd.Series) -> np.ndarray:
    """Índice mensual (12 valores, media 1) por razón a la media móvil centrada 2x12, sobre log1p para que el
    crecimiento explosivo no domine. Devuelve factores multiplicativos ene..dic."""
    y = np.log1p(serie)
    mm = y.rolling(12, center=True).mean().rolling(2).mean().shift(-1)
    dif = (y - mm).dropna()
    f = np.exp(dif.groupby(dif.index.month).mean().reindex(range(1, 13)).fillna(0.0).to_numpy())
    return f / f.mean()


def anual(serie_mensual: pd.DataFrame, mercado_total: dict, anio_parcial: int | None) -> pd.DataFrame:
    """Ventas anuales por tipo y participación en el mercado total. Si el último año está incompleto, su
    mercado total se estima como el del año anterior x (meses observados / 12) - SUPUESTO declarado."""
    a = serie_mensual.groupby(serie_mensual.index.year).sum()
    meses = serie_mensual.groupby(serie_mensual.index.year).size()
    total = pd.Series({int(k): float(v) for k, v in mercado_total.items()})
    if anio_parcial is not None and anio_parcial in a.index and anio_parcial not in total:
        total[anio_parcial] = total[anio_parcial - 1] * meses[anio_parcial] / 12
    a = a.loc[a.index.isin(total.index)]
    out = a.copy()
    out["mercado_total"] = total.reindex(a.index)
    out["meses"] = meses.reindex(a.index)
    for t in TIPOS:
        out[f"s_{t}"] = out[t] / out["mercado_total"]
    return out
