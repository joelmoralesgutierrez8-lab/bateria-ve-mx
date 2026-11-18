"""Fin de vida (EoL) por celda a partir de las curvas de capacidad procesadas en la Fase 2.

Para cada celda:
  1. Descarta lecturas imposibles (capacidad < capacidad_minima_valida_ah).
  2. Referencia = mediana de los primeros `ciclos_referencia` ciclos válidos (más robusta que el primer
     ciclo, que en NASA trae valores anómalos). SoH = capacidad / referencia.
  3. Suaviza el SoH con mediana móvil centrada (quita picos de medición y recuperaciones por reposo).
  4. Fin de vida = primer ciclo en que el SoH suavizado queda por debajo del umbral en
     `puntos_consecutivos` puntos seguidos; el tiempo se interpola linealmente entre el último punto arriba
     y el primero abajo.
  5. Si nunca cruza: censurada por la derecha en su último ciclo.
  6. Excluye celdas con referencia anómala (< ref_minima_vs_nominal x nominal), SoH implausible o listadas
     en config con su razón. Nada se borra en silencio: la tabla de salida lleva la razón.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def soh_robusto(capacidad: np.ndarray, cfg: dict) -> tuple[np.ndarray, float]:
    validas = capacidad[capacidad >= cfg["capacidad_minima_valida_ah"]]
    if len(validas) < cfg["ciclos_referencia"]:
        return np.full_like(capacidad, np.nan, dtype=float), np.nan
    ref = float(np.median(validas[: cfg["ciclos_referencia"]]))
    soh = np.where(capacidad >= cfg["capacidad_minima_valida_ah"], capacidad / ref, np.nan)
    return soh, ref


def suavizar(soh: np.ndarray, ventana: int) -> np.ndarray:
    return pd.Series(soh).rolling(ventana, center=True, min_periods=1).median().to_numpy()


def primer_cruce(ciclos: np.ndarray, soh_suave: np.ndarray, umbral: float, consecutivos: int):
    """Devuelve el ciclo (interpolado) del primer cruce sostenido del umbral, o None."""
    abajo = soh_suave < umbral
    for i in range(len(abajo) - consecutivos + 1):
        if abajo[i : i + consecutivos].all():
            if i == 0:
                return float(ciclos[0])
            x0, x1 = ciclos[i - 1], ciclos[i]
            y0, y1 = soh_suave[i - 1], soh_suave[i]
            if not (np.isfinite(y0) and np.isfinite(y1)) or y0 == y1:
                return float(x1)
            return float(x0 + (umbral - y0) * (x1 - x0) / (y1 - y0))
    return None


def eol_por_celda(df: pd.DataFrame, conjunto: str, cfg_conjunto: dict, cfg_det: dict,
                  umbral: float) -> pd.DataFrame:
    excluir = cfg_conjunto.get("excluir") or {}
    nominal = cfg_conjunto["capacidad_nominal_ah"]
    filas = []
    for celda, g in df.sort_values(["bateria", "ciclo"]).groupby("bateria"):
        ciclos = g["ciclo"].to_numpy(float)
        cap = g["capacidad_ah"].to_numpy(float)
        soh, ref = soh_robusto(cap, cfg_det)
        suave = suavizar(soh, cfg_det["ventana_suavizado"])
        fila = {"conjunto": conjunto, "celda": celda, "n_mediciones": len(g),
                "ultimo_ciclo": float(ciclos.max()), "capacidad_ref_ah": ref,
                "ref_vs_nominal": ref / nominal if np.isfinite(ref) else np.nan,
                "temperatura_c": float(g["temp_ambiente_c"].iloc[0]) if "temp_ambiente_c" in g
                else cfg_conjunto.get("temperatura_c"),
                "soh_final_suavizado": float(np.nanmedian(suave[-3:])) if len(suave) else np.nan}
        motivo = None
        if celda in excluir:
            motivo = f"config: {excluir[celda]}"
        elif not np.isfinite(ref):
            motivo = "menos ciclos válidos que los necesarios para la referencia"
        elif ref < cfg_det["ref_minima_vs_nominal"] * nominal:
            motivo = f"referencia {ref:.3f} Ah < {cfg_det['ref_minima_vs_nominal']:.0%} de la nominal"
        elif np.nanmax(suave) > cfg_det["soh_maximo_plausible"]:
            motivo = f"SoH suavizado máximo {np.nanmax(suave):.2f} implausible"
        if motivo:
            fila.update(incluida=False, motivo_exclusion=motivo, tiempo=np.nan, evento=np.nan)
        else:
            t = primer_cruce(ciclos, suave, umbral, cfg_det["puntos_consecutivos"])
            fila.update(incluida=True, motivo_exclusion="",
                        tiempo=t if t is not None else float(ciclos.max()),
                        evento=1 if t is not None else 0)
        filas.append(fila)
    return pd.DataFrame(filas)
