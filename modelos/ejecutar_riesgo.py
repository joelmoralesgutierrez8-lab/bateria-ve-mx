"""Fases 6 y 7: CO2 de ciclo de vida BEV vs gasolina (Monte Carlo + Sobol) y escenarios de red eléctrica.

Uso: python -m modelos.ejecutar_riesgo
Salidas en resultados/fase6/:
  co2_monte_carlo_resumen.csv   P5/P50/P95 de g CO2e/km (BEV y gasolina), reducción % y punto de equilibrio
  sobol_indices.csv             S1 y ST con intervalo de 90% para la diferencia gasolina - BEV (g/km)
  escenarios_red.csv            (Fase 7) misma comparación con red actual, fósil y limpia
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from modelos.comun.semillas import fijar_semillas
from modelos.riesgo.ciclo_vida import evaluar
from modelos.riesgo.sobol import indices
from modelos.ventas.preparar import participacion_entidad
from modelos.vida_util.arrhenius import temperaturas_por_entidad
from modelos.vida_util.flota import simular_vidas
from modelos.vida_util import weibull as W

RAIZ = Path(__file__).resolve().parents[1]

# Fase 7: intensidad media de la red durante la vida del auto (g CO2e/kWh). SUPUESTOS de escenario,
# anclados en el dato observado de CENACE (~420 g/kWh, ~20% de generación limpia en 2026).
ESCENARIOS_RED = {
    "actual (CENACE, últimos 24 meses)": None,
    "fósil (sin nuevas renovables, +15%)": 1.15,
    "limpia (la mitad de la intensidad actual)": 0.50,
    "muy limpia (75% limpia, ~120 g/kWh)": 0.28,
}


def cuantil_empirico(muestra):
    s = np.sort(np.asarray(muestra, float))
    return lambda u: np.quantile(s, np.clip(u, 0, 1))


def main() -> None:
    cfg_total = yaml.safe_load(open(RAIZ / "modelos" / "config_fase3.yaml", encoding="utf-8"))
    cfg, cfv = cfg_total["riesgo"], cfg_total["vida_flota"]
    rng = fijar_semillas(cfg_total["semilla"])
    salida = RAIZ / "resultados" / "fase6"
    salida.mkdir(parents=True, exist_ok=True)

    # --- vida de la batería BEV de la flota: mezcla nacional ponderada por ventas (Fase 3)
    eol = pd.read_csv(RAIZ / cfg_total["salidas"]["carpeta"] / "eol_celdas.csv")
    ref = eol[(eol.conjunto == cfv["conjunto_celda_referencia"]) & eol.incluida]
    celda = W.bootstrap(ref.tiempo.to_numpy(), ref.evento.astype(int).to_numpy(), 500, rng)["muestras"]
    temps = temperaturas_por_entidad(pd.read_csv(RAIZ / "datos/procesado/nasa_power_temperatura.csv"),
                                     cfv["mapeo_capital_entidad"], tuple(cfv["periodo_temperatura"]))
    pesos = participacion_entidad(pd.read_csv(RAIZ / "datos/procesado/inegi_ventas_entidad_mes.csv"))["BEV"]
    pesos = pesos[pesos.index.isin(temps)]
    pesos = pesos / pesos.sum()
    vidas = []
    for e, w in pesos.items():
        n = max(int(round(w * 40000)), 1)
        vidas.append(simular_vidas(cfv["tipos"]["BEV"], cfv, temps[e], celda, n, rng)["t_bateria"])
    vida_bat = np.concatenate(vidas)
    q_bat = cuantil_empirico(vida_bat)
    vv = cfv["vida_vehiculo_anios"]
    q_veh = lambda u: vv["eta"] * (-np.log1p(-np.clip(u, 0, 1 - 1e-12))) ** (1 / vv["beta"])

    red = pd.read_csv(RAIZ / "datos/procesado/cenace_factor_emision_regional.csv", parse_dates=["fecha"])
    red = red.sort_values("fecha").tail(cfg["meses_red"])["g_co2e_por_kwh"].to_numpy()
    q_red = cuantil_empirico(red)
    plomo = cfg["bateria_plomo_icev_t"]
    rangos = cfg["entradas"]

    def muestra(n):
        return {k: rng.uniform(v["min"], v["max"], n) for k, v in rangos.items()}

    # --- Monte Carlo
    r = evaluar(muestra(cfg["n_monte_carlo"]), q_bat, q_veh, q_red, plomo)
    filas = []
    for k in ["bev_g_km", "gas_g_km", "reduccion_pct", "uso_bev_g_km", "uso_gas_g_km", "equilibrio_km", "t_bat", "t_veh"]:
        q = np.quantile(r[k], [0.05, 0.5, 0.95])
        filas.append({"variable": k, "p5": q[0], "p50": q[1], "p95": q[2]})
    filas.append({"variable": "prob_bev_mas_limpio", "p50": float(np.mean(r["bev_g_km"] < r["gas_g_km"]))})
    mc = pd.DataFrame(filas)
    mc.to_csv(salida / "co2_monte_carlo_resumen.csv", index=False)
    print(f"Intensidad de la red (CENACE, {cfg['meses_red']} meses): {red.min():.0f}-{red.max():.0f} g/kWh")
    print("Monte Carlo (g CO2e/km salvo indicación):")
    print(mc.round(2).to_string(index=False))

    # --- Sobol sobre la diferencia gasolina - BEV
    f = lambda x: (lambda o: o["gas_g_km"] - o["bev_g_km"])(evaluar(x, q_bat, q_veh, q_red, plomo))
    s = indices(f, rangos, cfg["n_sobol"], rng, cfg["bootstrap_sobol"])
    sob = pd.DataFrame({"entrada": s["nombres"], "S1": s["S1"], "S1_p5": s["S1_ic"][0], "S1_p95": s["S1_ic"][1],
                        "ST": s["ST"], "ST_p5": s["ST_ic"][0], "ST_p95": s["ST_ic"][1]}).sort_values("ST", ascending=False)
    sob["fuente"] = sob["entrada"].map(lambda k: rangos[k]["fuente"])
    sob.to_csv(salida / "sobol_indices.csv", index=False)
    print("\nSobol (salida: ahorro gasolina - BEV en g/km); ordenado por efecto total ST:")
    print(sob.drop(columns="fuente").round(3).to_string(index=False))
    print(f"Suma S1 = {sob.S1.sum():.2f} (cerca de 1 = el modelo es casi aditivo)")

    # --- Fase 7: escenarios de red
    esc = []
    x = muestra(cfg["n_monte_carlo"])
    for nombre, factor in ESCENARIOS_RED.items():
        qr = q_red if factor is None else (lambda u, fct=factor: q_red(u) * fct)
        o = evaluar(x, q_bat, q_veh, qr, plomo)
        q = lambda k: np.quantile(o[k], [0.05, 0.5, 0.95])
        esc.append({"escenario_red": nombre, "i_red_p50": float(np.median(o["i_red"])),
                    **{f"bev_{p}": v for p, v in zip(["p5", "p50", "p95"], q("bev_g_km"))},
                    "gas_p50": float(np.median(o["gas_g_km"])),
                    **{f"reduccion_{p}": v for p, v in zip(["p5", "p50", "p95"], q("reduccion_pct"))},
                    "equilibrio_km_p50": float(np.median(o["equilibrio_km"])),
                    "prob_bev_mas_limpio": float(np.mean(o["bev_g_km"] < o["gas_g_km"]))})
    esc = pd.DataFrame(esc)
    esc.to_csv(salida / "escenarios_red.csv", index=False)
    print("\nFase 7 - escenarios de red:")
    print(esc.round(1).to_string(index=False))


if __name__ == "__main__":
    main()
