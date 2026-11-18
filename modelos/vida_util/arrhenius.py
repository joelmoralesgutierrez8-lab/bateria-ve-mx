"""Aceleración de la degradación por temperatura (Arrhenius).

    AF(T) = exp[(Ea / R) (1/T_ref - 1/T)]        T en kelvin; AF > 1 si T > T_ref
    vida(T) = vida(T_ref) / AF(T)

Como la degradación se acumula mes a mes, el factor efectivo de un lugar es el PROMEDIO de AF sobre sus
temperaturas mensuales, no AF de la temperatura promedio (AF es convexa: por la desigualdad de Jensen,
promediar primero subestimaría el efecto de los meses calurosos).

Limitación: usa temperatura del AIRE (NASA POWER). La del paquete depende del manejo térmico del auto; por eso
el resultado es una cota del efecto del clima, no una medición.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

R = 8.314462618  # J/(mol K)


def factor_aceleracion(temp_c, ea_kj_mol, temp_ref_c: float = 25.0):
    t = np.asarray(temp_c, float) + 273.15
    t_ref = temp_ref_c + 273.15
    ea = np.asarray(ea_kj_mol, float) * 1000.0
    return np.exp((ea / R) * (1.0 / t_ref - 1.0 / t))


def factor_efectivo(temps_mensuales_c, ea_kj_mol, temp_ref_c: float = 25.0):
    """Promedio de AF sobre una serie de temperaturas mensuales. ea_kj_mol puede ser un vector (una Ea por
    simulación): devuelve un vector del mismo largo."""
    temps = np.asarray(temps_mensuales_c, float)[None, :]
    ea = np.atleast_1d(np.asarray(ea_kj_mol, float))[:, None]
    af = factor_aceleracion(temps, ea, temp_ref_c).mean(axis=1)
    return af if np.ndim(ea_kj_mol) else float(af[0])


def temperaturas_por_entidad(power: pd.DataFrame, mapeo: dict, anios: tuple[int, int]) -> dict:
    """{entidad: vector de T2M mensual} usando la capital de cada estado. Ignora puntos que no estén en mapeo
    (minas y el registro histórico 'Coahuila y Texas')."""
    p = power.copy()
    p["anio"] = pd.to_datetime(p["fecha"]).dt.year
    p = p[(p["anio"] >= anios[0]) & (p["anio"] <= anios[1]) & p["id"].isin(mapeo)]
    return {mapeo[i]: g.sort_values("fecha")["T2M"].to_numpy(float) for i, g in p.groupby("id")}
