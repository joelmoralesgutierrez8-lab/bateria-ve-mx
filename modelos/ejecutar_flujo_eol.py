"""Fase 3, paso 4: baterías que salen de los vehículos en México, 2016-2040.

Requiere los pasos 2 y 3 (vida_flota_entidad.csv y ventas_simulaciones.npz). Uso:
    python -m modelos.ejecutar_flujo_eol
Salidas en resultados/fase3/:
  retiros_eol_anual.csv      P5/P50/P95 por escenario, tipo y año: unidades, MWh y toneladas que salen
  retiros_eol_entidad.csv    mediana por entidad (escenario base) en los años de reporte
Notas:
  - Ventas 2016-2025 observadas (INEGI); 2026 = observado + resto del año proyectado; 2027+ proyectado.
  - Las ventas nacionales se reparten entre entidades con su participación de los últimos 24 meses.
    'No especificado' usa la Weibull nacional (mezcla ponderada por ventas).
  - Salir del vehículo no es lo mismo que llegar al reciclaje: buena parte puede ir a segunda vida.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from modelos.comun.semillas import fijar_semillas
from modelos.flujo_eol.convolucion import retiros
from modelos.ventas.preparar import TIPOS, participacion_entidad, serie_nacional_mensual
from modelos.vida_util.flota import muestrear

RAIZ = Path(__file__).resolve().parents[1]


def media_spec(spec: dict) -> float:
    d = spec["distribucion"]
    return {"fija": lambda s: s["valor"], "uniforme": lambda s: (s["min"] + s["max"]) / 2,
            "triangular": lambda s: (s["min"] + s["moda"] + s["max"]) / 3}[d](spec)


def main() -> None:
    cfg_total = yaml.safe_load(open(RAIZ / "modelos" / "config_fase3.yaml", encoding="utf-8"))
    cfg, cfv = cfg_total["flujo_eol"], cfg_total["vida_flota"]
    rng = fijar_semillas(cfg_total["semilla"])
    salida = RAIZ / cfg_total["salidas"]["carpeta"]

    inegi = pd.read_csv(RAIZ / "datos" / "procesado" / "inegi_ventas_entidad_mes.csv")
    hist = serie_nacional_mensual(inegi)
    hist_anual = hist.groupby(hist.index.year).sum()
    part = participacion_entidad(inegi, cfg["meses_participacion_entidad"])
    vida = pd.read_csv(salida / "vida_flota_entidad.csv")
    sims = np.load(salida / "ventas_simulaciones.npz")
    anios_proy = sims["anios"]
    primer_proy = int(anios_proy[0])                       # año parcial (observado + proyectado)
    anios = np.arange(int(hist_anual.index.min()), int(anios_proy[-1]) + 1)
    n_obs = primer_proy - anios[0]                         # años completos observados antes del parcial

    filas, filas_ent = [], []
    for esc in cfg_total["ventas"]["escenarios_s_max"]:
        for t in TIPOS:
            proy = sims[f"{esc}__{t}"]                         # (B, años desde primer_proy)
            B = proy.shape[0]
            ventas_nac = np.concatenate([np.tile(hist_anual[t].to_numpy()[:n_obs], (B, 1)), proy], axis=1)
            v = vida[vida["tipo"] == t].set_index("entidad")
            pesos = part[t]
            # Weibull nacional para 'No especificado': mezcla -> se aproxima convolucionando por entidad
            ret_total = np.zeros_like(ventas_nac)
            por_ent = {}
            ent_validas = [e for e in pesos.index if e in v.index]
            w_validas = pesos[ent_validas] / pesos[ent_validas].sum()
            for e, w in pesos.items():
                if e in v.index:
                    r = retiros(ventas_nac * w, v.loc[e, "beta_flota"], v.loc[e, "eta_flota_anios"])
                else:                                       # sin entidad: mezcla nacional
                    r = sum(retiros(ventas_nac * w * we, v.loc[ee, "beta_flota"], v.loc[ee, "eta_flota_anios"])
                            for ee, we in w_validas.items())
                ret_total += r
                por_ent[e] = r
            cap = muestrear(cfv["tipos"][t]["capacidad_kwh"], B, rng)[:, None]
            dens = muestrear(cfg["densidad_paquete_wh_kg"][t], B, rng)[:, None]
            mwh = ret_total * cap / 1000.0
            ton = ret_total * cap / dens                    # kWh / (Wh/kg) = toneladas
            for j, anio in enumerate(anios):
                q = {k: np.quantile(x[:, j], [0.05, 0.5, 0.95]) for k, x in
                     {"unidades": ret_total, "mwh": mwh, "toneladas": ton, "ventas": ventas_nac}.items()}
                filas.append({"escenario": esc, "tipo": t, "anio": int(anio), "proyectado": bool(anio >= primer_proy),
                              **{f"{k}_{p}": q[k][i] for k in q for i, p in enumerate(["p5", "p50", "p95"])}})
            if esc == "base":
                for e, r in por_ent.items():
                    for anio in cfg["anios_reporte"]:
                        j = int(anio - anios[0])
                        filas_ent.append({"entidad": e, "tipo": t, "anio": anio,
                                          "unidades_p50": float(np.median(r[:, j])),
                                          "toneladas_p50": float(np.median(r[:, j] * cap[:, 0] / dens[:, 0]))})
    out = pd.DataFrame(filas)
    out.to_csv(salida / "retiros_eol_anual.csv", index=False)
    ent = pd.DataFrame(filas_ent)
    ent.to_csv(salida / "retiros_eol_entidad.csv", index=False)

    tot = (out.groupby(["escenario", "anio"])[["unidades_p50", "toneladas_p50", "mwh_p50"]].sum().reset_index())
    print("Baterías que salen de vehículos (suma de medianas por tipo; BEV+PHEV+HEV):")
    print(tot[tot.anio.isin([2025, 2030, 2035, 2040])].round(0).to_string(index=False))
    print("\nToneladas por tipo, escenario base (P5 - P50 - P95):")
    b = out[(out.escenario == "base") & out.anio.isin([2030, 2035, 2040])]
    print(b[["tipo", "anio", "toneladas_p5", "toneladas_p50", "toneladas_p95"]].round(0).to_string(index=False))
    top = ent[(ent.anio == 2035)].groupby("entidad")["toneladas_p50"].sum().sort_values(ascending=False).head(8)
    print("\nEntidades con más toneladas en 2035 (base):")
    print(top.round(0).to_string())


if __name__ == "__main__":
    main()
