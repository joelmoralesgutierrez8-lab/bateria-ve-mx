"""Segunda vida: ¿cuántas baterías retiradas pueden reutilizarse antes de reciclarse?

Dos piezas:
  1. Por celda de laboratorio: tiempo a 80 % (sale del vehículo) y a 70 % SoH (sale de la segunda vida).
     margen = (t70 - t80) / t80 = vida útil restante en segunda vida como fracción de la primera vida.
     Una celda es APTA si margen >= margen_minimo (SUPUESTO en config). Si nunca llega a 70 %, el margen
     observado es una cota inferior: si ya supera el mínimo es apta; si no, es "indeterminada" y queda
     fuera del denominador (se reporta cuántas).
  2. En la flota: una batería sale del vehículo por dos razones (Fase 3, vida_flota_entidad.csv):
     - por el vehículo (accidente/edad) con SoH > 80 %: candidata directa a reúso o segunda vida;
     - por la batería (SoH ~ 80 %): va a segunda vida si es apta, si no, directo a reciclaje.
     % apto = (1 - pb) + pb * p_apta, con pb = fracción de bajas causadas por la batería.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def margen_por_celda(t80: pd.DataFrame, t70: pd.DataFrame, margen_minimo: float) -> pd.DataFrame:
    """t80 y t70: salidas de eol_por_celda con umbral 0.80 y 0.70 (solo celdas incluidas)."""
    a = t80[t80["incluida"] & (t80["evento"] == 1)][["conjunto", "celda", "tiempo", "ultimo_ciclo"]]
    b = t70[t70["incluida"]][["conjunto", "celda", "tiempo", "evento"]]
    m = a.rename(columns={"tiempo": "t80"}).merge(
        b.rename(columns={"tiempo": "t70", "evento": "evento70"}), on=["conjunto", "celda"], how="left")
    m["margen"] = (m["t70"] - m["t80"]) / m["t80"]
    censurada = m["evento70"] != 1
    m["clase"] = np.where(m["margen"] >= margen_minimo, "apta",
                          np.where(censurada, "indeterminada", "no_apta"))
    return m


def p_apta(clases: np.ndarray) -> float:
    det = clases[clases != "indeterminada"]
    return float((det == "apta").mean()) if len(det) else np.nan


def bootstrap_p_apta(m: pd.DataFrame, n: int, rng: np.random.Generator, nivel: float) -> tuple[float, float]:
    """Remuestreo de celdas estratificado por conjunto."""
    grupos = [g["clase"].to_numpy() for _, g in m.groupby("conjunto")]
    valores = []
    for _ in range(n):
        muestra = np.concatenate([g[rng.integers(0, len(g), len(g))] for g in grupos])
        v = p_apta(muestra)
        if np.isfinite(v):
            valores.append(v)
    a = (1 - nivel) / 2
    return float(np.quantile(valores, a)), float(np.quantile(valores, 1 - a))


def destinos(unidades: pd.Series, toneladas: pd.Series, pb: float, p: float) -> dict:
    """Reparte las bajas de un año y tipo en tres destinos."""
    f = {"sale_por_vehiculo_soh_mayor_80": 1 - pb,
         "segunda_vida_80_70": pb * p,
         "reciclaje_directo": pb * (1 - p)}
    out = {}
    for k, v in f.items():
        out[f"unidades_{k}"] = unidades * v
        out[f"toneladas_{k}"] = toneladas * v
    out["pct_apto_reuso_o_segunda_vida"] = 100 * (f["sale_por_vehiculo_soh_mayor_80"] + f["segunda_vida_80_70"])
    return out
