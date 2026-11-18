"""Vida de la batería en la FLOTA mexicana, en años, por simulación de vehículos.

Para cada vehículo simulado k de un tipo (BEV, PHEV) en una entidad:
    N_k      ~ Weibull(beta_lab, eta_lab) x factor_lab_a_vehiculo     ciclos equivalentes completos a 25 °C
    EFC_k    = km_k x consumo_k x fraccion_electrica_k / capacidad_k  ciclos equivalentes por año
    T_cic_k  = N_k / EFC_k / AF_k                                     años hasta 80% solo por ciclado
    T_cal_k  = vida_calendario_k / AF_k                               años hasta 80% solo por calendario
    T_bat_k  = 1 / (1/T_cic_k + 1/T_cal_k)                            pérdidas que se suman
    T_veh_k  ~ Weibull(beta_veh, eta_veh)                             el auto se desecha
    T_k      = min(T_bat_k, T_veh_k)                                  la batería sale del auto
HEV: T_k = T_veh_k (la batería híbrida no se retira por desgaste).

beta_lab y eta_lab se toman de réplicas bootstrap del ajuste de laboratorio, así que la incertidumbre del
ajuste también entra. Con las T_k se ajusta una Weibull de flota (años) por entidad y tipo.
"""
from __future__ import annotations

import numpy as np

from modelos.vida_util import weibull as W


def muestrear(spec: dict, n: int, rng: np.random.Generator) -> np.ndarray:
    d = spec["distribucion"]
    if d == "fija":
        return np.full(n, float(spec["valor"]))
    if d == "uniforme":
        return rng.uniform(spec["min"], spec["max"], n)
    if d == "triangular":
        return rng.triangular(spec["min"], spec["moda"], spec["max"], n)
    if d == "lognormal":
        sigma = np.log(spec["p90"] / spec["mediana"]) / 1.2815515655446004
        return spec["mediana"] * np.exp(sigma * rng.standard_normal(n))
    if d == "weibull":
        return spec["eta"] * rng.weibull(spec["beta"], n)
    raise ValueError(f"distribución desconocida: {d}")


def simular_vidas(tipo_cfg: dict, cfg: dict, temps_mensuales: np.ndarray, celda_bootstrap: dict,
                  n: int, rng: np.random.Generator) -> dict:
    """Devuelve vectores de vida (años) y la causa del retiro para n vehículos."""
    from modelos.vida_util.arrhenius import factor_efectivo

    t_veh = muestrear(cfg["vida_vehiculo_anios"], n, rng)
    if tipo_cfg["retiro_por"] == "vehiculo":
        return {"anios": t_veh, "por_bateria": np.zeros(n, bool)}

    idx = rng.integers(0, len(celda_bootstrap["beta"]), n)
    beta_lab, eta_lab = celda_bootstrap["beta"][idx], celda_bootstrap["eta"][idx]
    n_ciclos = eta_lab * rng.weibull(1.0, n) ** (1.0 / beta_lab)          # Weibull con beta, eta por vehículo
    n_ciclos *= muestrear(cfg["ciclos_lab_a_vehiculo"], n, rng)

    km = muestrear(cfg["km_anio"], n, rng)
    consumo = muestrear(tipo_cfg["consumo_kwh_km"], n, rng)
    frac = muestrear(tipo_cfg["fraccion_km_electricos"], n, rng)
    cap = muestrear(tipo_cfg["capacidad_kwh"], n, rng)
    efc_anio = km * consumo * frac / cap

    ea = muestrear(cfg["energia_activacion_kj_mol"], n, rng)
    af = factor_efectivo(temps_mensuales, ea, cfg["temperatura_referencia_c"])

    t_cic = n_ciclos / efc_anio / af
    t_cal = muestrear(cfg["vida_calendario_anios_25c"], n, rng) / af
    t_bat = 1.0 / (1.0 / t_cic + 1.0 / t_cal)
    return {"anios": np.minimum(t_bat, t_veh), "por_bateria": t_bat < t_veh,
            "t_bateria": t_bat, "efc_anio": efc_anio, "af": af}


def resumir(sim: dict) -> dict:
    t = sim["anios"]
    a = W.ajustar(t, np.ones_like(t, bool))
    q = np.quantile(t, [0.10, 0.50, 0.90])
    out = {"beta_flota": a.beta, "eta_flota_anios": a.eta, "p10_anios": q[0], "mediana_anios": q[1],
           "p90_anios": q[2], "pct_retiro_por_bateria": float(sim["por_bateria"].mean())}
    if "af" in sim:
        out.update(af_mediano=float(np.median(sim["af"])), efc_anio_mediano=float(np.median(sim["efc_anio"])),
                   mediana_bateria_sola_anios=float(np.median(sim["t_bateria"])))
    return out
