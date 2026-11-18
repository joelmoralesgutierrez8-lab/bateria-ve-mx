"""Fase 3, paso 1: fin de vida por celda y ajuste de Weibull con censura.

Uso (desde la raíz del proyecto):  python -m modelos.ejecutar_vida_util
Salidas en resultados/fase3/:
  eol_celdas.csv           una fila por celda: tiempo a 80% SoH (o censura) y, si se excluyó, la razón
  weibull_por_conjunto.csv beta, eta, vida media, B10, mediana e intervalos bootstrap (90%)
  weibull_beta_comun.json  beta compartida, eta por conjunto y prueba de razón de verosimilitudes
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml

from modelos.comun.semillas import fijar_semillas
from modelos.vida_util import weibull as W
from modelos.vida_util.eol_celdas import eol_por_celda

RAIZ = Path(__file__).resolve().parents[1]


def main() -> None:
    cfg = yaml.safe_load(open(RAIZ / "modelos" / "config_fase3.yaml", encoding="utf-8"))
    rng = fijar_semillas(cfg["semilla"])
    salida = RAIZ / cfg["salidas"]["carpeta"]
    salida.mkdir(parents=True, exist_ok=True)
    umbral = cfg["umbrales_soh"]["eol_vehiculo"]

    tablas = []
    for nombre, c in cfg["conjuntos"].items():
        df = pd.read_csv(RAIZ / c["archivo"])
        tablas.append(eol_por_celda(df, nombre, c, cfg["deteccion_eol"], umbral))
    eol = pd.concat(tablas, ignore_index=True)
    eol.to_csv(salida / "eol_celdas.csv", index=False)

    usadas = eol[eol["incluida"]]
    filas, grupos = [], {}
    for nombre, g in usadas.groupby("conjunto"):
        t, ev = g["tiempo"].to_numpy(), g["evento"].astype(int).to_numpy()
        fila = {"conjunto": nombre, "unidad_tiempo": cfg["conjuntos"][nombre]["unidad_tiempo"],
                "celdas_usadas": len(g), "excluidas": int((eol["conjunto"] == nombre).sum() - len(g))}
        if ev.sum() == 0:
            fila["nota"] = "sin fines de vida observados: no identificable"
        else:
            fila.update(W.ajustar(t, ev).como_dict())
            bs = W.bootstrap(t, ev, cfg["weibull"]["bootstrap_repeticiones"], rng, cfg["weibull"]["nivel_intervalo"])
            fila.update(beta_ic_bajo=bs["beta_ic"][0], beta_ic_alto=bs["beta_ic"][1],
                        eta_ic_bajo=bs["eta_ic"][0], eta_ic_alto=bs["eta_ic"][1],
                        replicas_validas=bs["replicas_validas"], replicas_descartadas=bs["replicas_descartadas"])
            if nombre in cfg["weibull"]["conjuntos_para_beta_comun"]:
                grupos[nombre] = (t, ev)
        filas.append(fila)
    por_conjunto = pd.DataFrame(filas)
    por_conjunto.to_csv(salida / "weibull_por_conjunto.csv", index=False)

    comun = {}
    if len(grupos) >= 2:
        comun = W.ajustar_beta_comun(grupos)
        comun["prueba_lr"] = W.prueba_beta_comun(grupos)
    with open(salida / "weibull_beta_comun.json", "w", encoding="utf-8") as fh:
        json.dump(comun, fh, ensure_ascii=False, indent=2)

    print(eol[["conjunto", "celda", "incluida", "tiempo", "evento", "motivo_exclusion"]].to_string(index=False))
    print()
    cols = [c for c in ["conjunto", "celdas_usadas", "n_eventos", "beta", "beta_ic_bajo", "beta_ic_alto",
                        "eta", "eta_ic_bajo", "eta_ic_alto", "b10", "mediana"] if c in por_conjunto]
    print(por_conjunto[cols].round(3).to_string(index=False))
    print(json.dumps(comun, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
