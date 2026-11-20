"""KPI de segunda vida: % de baterías retiradas aptas para reúso o segunda vida, por año, tipo y entidad.

Uso (desde la raíz):  python -m modelos.ejecutar_segunda_vida
Necesita: datos/procesado/bateria_*.csv, resultados/fase3/{retiros_eol_anual, retiros_eol_entidad, vida_flota_entidad}.csv
Salidas en resultados/segunda_vida/:
  celdas_80_70.csv         t80, t70, margen y clase por celda de laboratorio
  p_apta.csv               fracción de celdas aptas (IC bootstrap) para el margen base y los de sensibilidad
  destino_nacional.csv     bajas por destino 2016-2040 (escenario base, P50), por tipo y margen
  destino_entidad.csv      lo mismo por entidad en 2030, 2035 y 2040 (margen base)
  resumen.json             cifras clave para el extenso y la API
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from modelos.comun.semillas import fijar_semillas
from modelos.segunda_vida import clasificacion as C
from modelos.vida_util.eol_celdas import eol_por_celda

RAIZ = Path(__file__).resolve().parents[1]


def pb_nacional(flota: pd.DataFrame, entidad: pd.DataFrame, anio: int) -> dict[str, float]:
    """Fracción de bajas causadas por la batería, ponderada por las bajas de cada entidad en el año de
    reporte más cercano (las bajas por entidad solo existen para 2030, 2035 y 2040)."""
    anios = sorted(entidad["anio"].unique())
    ref = min(anios, key=lambda a: abs(a - anio))
    w = entidad[entidad["anio"] == ref][["entidad", "tipo", "unidades_p50"]]
    x = flota[["entidad", "tipo", "pct_retiro_por_bateria"]].merge(w, on=["entidad", "tipo"])
    return {t: float(np.average(g["pct_retiro_por_bateria"], weights=g["unidades_p50"]))
            if g["unidades_p50"].sum() > 0 else float(g["pct_retiro_por_bateria"].mean())
            for t, g in x.groupby("tipo")}


def main() -> None:
    cfg = yaml.safe_load(open(RAIZ / "modelos" / "config_fase3.yaml", encoding="utf-8"))
    sv = cfg["segunda_vida"]
    rng = fijar_semillas(cfg["semilla"])
    salida = RAIZ / sv["carpeta"]
    salida.mkdir(parents=True, exist_ok=True)

    # 1) Celdas: tiempo a 80 % y a 70 %
    u80, u70 = cfg["umbrales_soh"]["eol_vehiculo"], cfg["umbrales_soh"]["fin_segunda_vida"]
    t80, t70 = [], []
    for nombre, c in cfg["conjuntos"].items():
        df = pd.read_csv(RAIZ / c["archivo"])
        t80.append(eol_por_celda(df, nombre, c, cfg["deteccion_eol"], u80))
        t70.append(eol_por_celda(df, nombre, c, cfg["deteccion_eol"], u70))
    t80, t70 = pd.concat(t80, ignore_index=True), pd.concat(t70, ignore_index=True)

    margenes = [sv["margen_minimo"], *sv["margen_sensibilidad"]]
    filas_p, celdas_base = [], None
    for mm in margenes:
        m = C.margen_por_celda(t80, t70, mm)
        if mm == sv["margen_minimo"]:
            celdas_base = m
        lo, hi = C.bootstrap_p_apta(m, sv["bootstrap"], rng, sv["nivel_intervalo"])
        filas_p.append({"margen_minimo": mm, "p_apta": C.p_apta(m["clase"].to_numpy()), "ic_bajo": lo, "ic_alto": hi,
                        "celdas": len(m), "aptas": int((m["clase"] == "apta").sum()),
                        "no_aptas": int((m["clase"] == "no_apta").sum()),
                        "indeterminadas": int((m["clase"] == "indeterminada").sum())})
    celdas_base.to_csv(salida / "celdas_80_70.csv", index=False)
    p_tab = pd.DataFrame(filas_p)
    p_tab.to_csv(salida / "p_apta.csv", index=False)

    # 2) Flota: destino de las bajas
    anual = pd.read_csv(RAIZ / "resultados/fase3/retiros_eol_anual.csv")
    anual = anual[anual["escenario"] == sv["escenario"]]
    entidad = pd.read_csv(RAIZ / "resultados/fase3/retiros_eol_entidad.csv")
    flota = pd.read_csv(RAIZ / "resultados/fase3/vida_flota_entidad.csv")

    filas = []
    for r in p_tab.itertuples():
        for (anio, tipo), g in anual.groupby(["anio", "tipo"]):
            pb = pb_nacional(flota, entidad, anio)[tipo]
            p_t = 0.0 if tipo in sv.get("tipos_sin_segunda_vida", []) else r.p_apta
            pb_t = 1.0 if tipo in sv.get("tipos_sin_segunda_vida", []) else pb
            fila = {"margen_minimo": r.margen_minimo, "anio": anio, "tipo": tipo, "proyectado": bool(g["proyectado"].iloc[0]),
                    "pb": pb, "unidades_p50": float(g["unidades_p50"].iloc[0]),
                    "toneladas_p50": float(g["toneladas_p50"].iloc[0])}
            fila.update(C.destinos(fila["unidades_p50"], fila["toneladas_p50"], pb_t, p_t))
            for etiqueta, p in (("ic_bajo", r.ic_bajo), ("ic_alto", r.ic_alto)):
                fila[f"pct_apto_{etiqueta}"] = C.destinos(1.0, 1.0, pb_t, 0.0 if pb_t == 1.0 and p_t == 0.0 else p)["pct_apto_reuso_o_segunda_vida"]
            filas.append(fila)
    nac = pd.DataFrame(filas)
    nac.to_csv(salida / "destino_nacional.csv", index=False)

    base = p_tab[p_tab["margen_minimo"] == sv["margen_minimo"]].iloc[0]
    ent = entidad.merge(flota[["entidad", "tipo", "pct_retiro_por_bateria"]], on=["entidad", "tipo"])
    filas = []
    for r in ent.itertuples():
        f = {"entidad": r.entidad, "tipo": r.tipo, "anio": r.anio, "pb": r.pct_retiro_por_bateria,
             "unidades_p50": r.unidades_p50, "toneladas_p50": r.toneladas_p50}
        sin_sv = r.tipo in sv.get("tipos_sin_segunda_vida", [])
        f.update(C.destinos(r.unidades_p50, r.toneladas_p50, 1.0 if sin_sv else r.pct_retiro_por_bateria,
                            0.0 if sin_sv else base.p_apta))
        filas.append(f)
    pd.DataFrame(filas).to_csv(salida / "destino_entidad.csv", index=False)

    # 3) Resumen
    b = nac[nac["margen_minimo"] == sv["margen_minimo"]]
    resumen = {"margen_minimo_base": sv["margen_minimo"],
               "p_apta_celdas": {"p50": base.p_apta, "ic": [base.ic_bajo, base.ic_alto],
                                 "celdas": int(base.celdas), "indeterminadas": int(base.indeterminadas)},
               "sensibilidad_p_apta": p_tab[["margen_minimo", "p_apta"]].to_dict("records"), "por_anio": {}}
    for anio in sv["anios_reporte"]:
        g = b[b["anio"] == anio]
        tot_u, tot_t = g["unidades_p50"].sum(), g["toneladas_p50"].sum()
        ok_t = g["toneladas_sale_por_vehiculo_soh_mayor_80"].sum() + g["toneladas_segunda_vida_80_70"].sum()
        sin_hev = g[g["tipo"] != "HEV"]
        ok_t_sh = (sin_hev["toneladas_sale_por_vehiculo_soh_mayor_80"].sum()
                   + sin_hev["toneladas_segunda_vida_80_70"].sum())
        resumen["por_anio"][str(anio)] = {
            "unidades": tot_u, "toneladas": tot_t,
            "pct_toneladas_aptas": 100 * ok_t / tot_t,
            "pct_toneladas_aptas_sin_hev": 100 * ok_t_sh / sin_hev["toneladas_p50"].sum(),
            "toneladas_reciclaje_directo": g["toneladas_reciclaje_directo"].sum()}
    (salida / "resumen.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
    print(p_tab.to_string(index=False))
    print(json.dumps(resumen["por_anio"], indent=2))


if __name__ == "__main__":
    main()
