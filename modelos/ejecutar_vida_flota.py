"""Fase 3, paso 2: vida de la batería en la flota mexicana (años) por entidad y tipo de vehículo.

Requiere el paso 1 (resultados/fase3/eol_celdas.csv). Uso:  python -m modelos.ejecutar_vida_flota
Salida: resultados/fase3/vida_flota_entidad.csv con la Weibull de flota (beta, eta en años), P10/mediana/P90,
el % de baterías que salen por desgaste (vs porque se desechó el auto) y el factor Arrhenius mediano.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from modelos.comun.semillas import fijar_semillas
from modelos.vida_util import weibull as W
from modelos.vida_util.arrhenius import temperaturas_por_entidad
from modelos.vida_util.flota import resumir, simular_vidas

RAIZ = Path(__file__).resolve().parents[1]


def main() -> None:
    cfg_total = yaml.safe_load(open(RAIZ / "modelos" / "config_fase3.yaml", encoding="utf-8"))
    cfg = cfg_total["vida_flota"]
    rng = fijar_semillas(cfg_total["semilla"])
    salida = RAIZ / cfg_total["salidas"]["carpeta"]

    eol = pd.read_csv(salida / "eol_celdas.csv")
    ref = eol[(eol["conjunto"] == cfg["conjunto_celda_referencia"]) & eol["incluida"]]
    bs = W.bootstrap(ref["tiempo"].to_numpy(), ref["evento"].astype(int).to_numpy(),
                     cfg_total["weibull"]["bootstrap_repeticiones"], rng, cfg_total["weibull"]["nivel_intervalo"])
    celda = bs["muestras"]

    power = pd.read_csv(RAIZ / "datos" / "procesado" / "nasa_power_temperatura.csv")
    temps = temperaturas_por_entidad(power, cfg["mapeo_capital_entidad"], tuple(cfg["periodo_temperatura"]))
    faltan = set(cfg["mapeo_capital_entidad"].values()) - set(temps)
    if faltan:
        raise ValueError(f"sin temperatura para: {sorted(faltan)}")

    filas = []
    for entidad, t in sorted(temps.items()):
        for tipo, tcfg in cfg["tipos"].items():
            sim = simular_vidas(tcfg, cfg, t, celda, cfg["vehiculos_simulados"], rng)
            filas.append({"entidad": entidad, "tipo": tipo, "temp_media_c": float(np.mean(t)), **resumir(sim)})
    out = pd.DataFrame(filas)
    out.to_csv(salida / "vida_flota_entidad.csv", index=False)

    cols = ["entidad", "temp_media_c", "af_mediano", "mediana_bateria_sola_anios", "mediana_anios",
            "beta_flota", "eta_flota_anios", "pct_retiro_por_bateria"]
    for tipo in cfg["tipos"]:
        print(f"\n== {tipo}")
        print(out[out["tipo"] == tipo][[c for c in cols if c in out]].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
