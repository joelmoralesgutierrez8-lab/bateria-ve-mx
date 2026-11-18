"""Fase 3, paso 3: proyección de ventas de BEV, PHEV y HEV en México hasta 2040.

Uso: python -m modelos.ejecutar_ventas            (todo)
     python -m modelos.ejecutar_ventas --rapido   (omite LSTM y LightGBM en la validación)
Salidas en resultados/fase3/:
  ventas_validacion_corto_plazo.csv   MAE, RMSE, MAPE, MASE por tipo y modelo (origen móvil, h = 12 meses)
  curva_s_parametros.csv              k, t0 por escenario y tipo
  curva_s_backtest.csv                ajuste hasta 2022, predicción 2023-2025 vs real y vs crecimiento ingenuo
  ventas_proyeccion_anual.csv         P5 / P50 / P95 de unidades por escenario, tipo y año
  ventas_simulaciones.npz             trayectorias anuales simuladas (para la convolución de retiros)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from modelos.comun.semillas import fijar_semillas
from modelos.ventas import corto_plazo as CP
from modelos.ventas import curva_s as CS
from modelos.ventas.preparar import TIPOS, anual, serie_nacional_mensual
from modelos.vida_util.flota import muestrear

RAIZ = Path(__file__).resolve().parents[1]


def main(rapido: bool = False) -> None:
    cfg_total = yaml.safe_load(open(RAIZ / "modelos" / "config_fase3.yaml", encoding="utf-8"))
    cfg = cfg_total["ventas"]
    semilla = cfg_total["semilla"]
    rng = fijar_semillas(semilla)
    salida = RAIZ / cfg_total["salidas"]["carpeta"]
    salida.mkdir(parents=True, exist_ok=True)

    inegi = pd.read_csv(RAIZ / "datos" / "procesado" / "inegi_ventas_entidad_mes.csv")
    mensual = serie_nacional_mensual(inegi)
    a = anual(mensual, cfg["mercado_total_anual"], cfg["anio_parcial"])
    print("Participación anual en el mercado total (%):")
    print((a[[f"s_{t}" for t in TIPOS]] * 100).round(2).to_string())

    # ---------- 1. Validación de corto plazo (mensual, origen móvil)
    modelos = dict(CP.MODELOS)
    if rapido:
        modelos.pop("lstm"), modelos.pop("lightgbm")
    tablas = []
    for t in TIPOS:
        err = CP.origen_movil(mensual[t], modelos, cfg["validacion"]["origenes"],
                              cfg["validacion"]["horizonte_meses"], semilla)
        tablas.append(CP.resumen(err).assign(tipo=t).reset_index())
    val = pd.concat(tablas)[["tipo", "modelo", "MASE", "MAE", "RMSE", "MAPE", "n"]]
    val.to_csv(salida / "ventas_validacion_corto_plazo.csv", index=False)
    print("\nValidación de origen móvil (h = 12 meses; MASE < 1 = mejor que el naive estacional):")
    print(val.round(3).to_string(index=False))

    # ---------- 2. Curva S: backtest anual y ajuste final
    completos = a[a["meses"] == 12]
    ultimo = int(completos.index.max())
    corte = ultimo - cfg["validacion"]["anios_prueba_curva_s"]
    bt, params, sims = [], [], {}
    anios_fut = np.arange(int(a.index.max()), cfg["horizonte"] + 1)
    mercado = muestrear(cfg["mercado_futuro"], cfg["bootstrap_curva_s"], rng)
    for esc, smax in cfg["escenarios_s_max"].items():
        for t in TIPOS:
            ent = completos.loc[:corte]
            aj = CS.ajustar(ent.index, ent[f"s_{t}"], smax[t], pesos=ent[t])
            prueba = completos.loc[corte + 1 :]
            pred = CS.predecir(prueba.index, aj["k"], aj["t0"], smax[t]) * prueba["mercado_total"]
            g = ent[t].iloc[-1] / ent[t].iloc[-2]                       # crecimiento ingenuo: repite el último
            ingenuo = ent[t].iloc[-1] * g ** np.arange(1, len(prueba) + 1)
            for (anio, real), p, i in zip(prueba[t].items(), pred, ingenuo):
                bt.append({"escenario": esc, "tipo": t, "anio": anio, "real": real, "curva_s": p, "ingenuo": i})

            aj = CS.ajustar(a.index, a[f"s_{t}"], smax[t], pesos=a[t])   # ajuste final con todos los años
            boot = CS.bootstrap(aj, cfg["bootstrap_curva_s"], rng)
            params.append({"escenario": esc, "tipo": t, "s_max": smax[t], "k": aj["k"], "t0": aj["t0"],
                           "k_p5": np.quantile(boot[:, 0], .05), "k_p95": np.quantile(boot[:, 0], .95)})
            s = smax[t] / (1 + np.exp(-boot[:, [0]] * (anios_fut[None, :] - boot[:, [1]])))
            unidades = s * mercado[:, None]
            # año parcial: lo observado + lo que falta del año según la curva
            obs = mensual[t][mensual.index.year == anios_fut[0]]
            unidades[:, 0] = obs.sum() + unidades[:, 0] * (12 - len(obs)) / 12
            sims[f"{esc}|{t}"] = unidades
    bt = pd.DataFrame(bt)
    bt.to_csv(salida / "curva_s_backtest.csv", index=False)
    pd.DataFrame(params).to_csv(salida / "curva_s_parametros.csv", index=False)
    mape = bt.assign(e_cs=lambda d: abs(d.curva_s - d.real) / d.real, e_ing=lambda d: abs(d.ingenuo - d.real) / d.real)
    print(f"\nBacktest curva S (ajusta hasta {corte}, predice {corte+1}-{ultimo}); MAPE por escenario y tipo:")
    print(mape.groupby(["escenario", "tipo"])[["e_cs", "e_ing"]].mean().mul(100).round(1)
          .rename(columns={"e_cs": "MAPE_curva_s_%", "e_ing": "MAPE_ingenuo_%"}).to_string())

    # ---------- 3. Proyección
    filas = []
    for clave, u in sims.items():
        esc, t = clave.split("|")
        q = np.quantile(u, [0.05, 0.5, 0.95], axis=0)
        for j, anio in enumerate(anios_fut):
            filas.append({"escenario": esc, "tipo": t, "anio": int(anio), "p5": q[0, j], "p50": q[1, j], "p95": q[2, j]})
    proy = pd.DataFrame(filas)
    proy.to_csv(salida / "ventas_proyeccion_anual.csv", index=False)
    np.savez_compressed(salida / "ventas_simulaciones.npz", anios=anios_fut, **{k.replace("|", "__"): v for k, v in sims.items()})
    print("\nProyección (mediana, unidades/año) en años clave:")
    print(proy[proy.anio.isin([anios_fut[0], 2030, 2035, 2040])].pivot_table(index=["escenario", "anio"], columns="tipo",
          values="p50").round(0).astype(int).to_string())


if __name__ == "__main__":
    main(rapido="--rapido" in sys.argv)
