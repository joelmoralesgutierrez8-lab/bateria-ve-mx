"""Reciclaje retrasado: ¿cuándo llegan las baterías al reciclaje si pasan antes por segunda vida?

Uso (desde la raíz):  python -m modelos.ejecutar_reciclaje_retrasado     (después de ejecutar_segunda_vida)
Lee resultados/segunda_vida/{destino_nacional, celdas_80_70}.csv y resultados/fase3/{vida_flota_entidad, retiros_eol_entidad}.csv
Salidas en resultados/segunda_vida/:
  reciclaje_retrasado.csv          toneladas que llegan a reciclaje por año, tipo y escenario de adopción
  reciclaje_retrasado_resumen.csv  totales nacionales por año y escenario (+ lo que se pasa de 2040)

Supuestos (todos en config_fase3.yaml -> segunda_vida):
  - Duración de la segunda vida = margen (80 -> 70 % SoH, celdas de laboratorio aptas) x vida de la batería en la
    flota mexicana (mediana_bateria_sola_anios, ponderada por bajas de 2035). Se reparte uniforme entre los
    cuantiles 25 y 75 del margen. Es un SUPUESTO: el uso estacionario degrada distinto que el vehicular.
  - tipos_sin_segunda_vida: HEV (paquetes pequeños, sin vida de batería modelada) van directo a reciclaje.
  - adopcion_segunda_vida: fracción de baterías aptas que de verdad entra a segunda vida (palanca de política).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yaml

RAIZ = Path(__file__).resolve().parents[1]


def vida_bateria_nacional(flota: pd.DataFrame, entidad: pd.DataFrame, anio_peso: int) -> dict[str, float]:
    w = entidad[entidad["anio"] == anio_peso][["entidad", "tipo", "unidades_p50"]]
    x = flota[["entidad", "tipo", "mediana_bateria_sola_anios"]].merge(w, on=["entidad", "tipo"])
    return {t: float(np.average(g["mediana_bateria_sola_anios"], weights=g["unidades_p50"])) for t, g in x.groupby("tipo")}


def main() -> None:
    cfg = yaml.safe_load(open(RAIZ / "modelos" / "config_fase3.yaml", encoding="utf-8"))
    sv = cfg["segunda_vida"]
    carpeta = RAIZ / sv["carpeta"]
    nac = pd.read_csv(carpeta / "destino_nacional.csv")
    nac = nac[nac["margen_minimo"] == sv["margen_minimo"]]
    celdas = pd.read_csv(carpeta / "celdas_80_70.csv")
    margen = celdas.loc[celdas["clase"] == "apta", "margen"]
    q25, q75 = float(margen.quantile(0.25)), float(margen.quantile(0.75))
    flota = pd.read_csv(RAIZ / "resultados/fase3/vida_flota_entidad.csv")
    entidad = pd.read_csv(RAIZ / "resultados/fase3/retiros_eol_entidad.csv")
    vida = vida_bateria_nacional(flota.dropna(subset=["mediana_bateria_sola_anios"]), entidad, sv["anio_peso_vida"])
    anio_max = int(nac["anio"].max())

    filas = []
    for adop in sv["adopcion_segunda_vida"]:
        for tipo, g in nac.groupby("tipo"):
            sin_sv = tipo in sv.get("tipos_sin_segunda_vida", [])
            adop_t = 0.0 if sin_sv else adop
            d_bajo = 0 if sin_sv else max(1, int(round(q25 * vida[tipo])))
            d_alto = 0 if sin_sv else max(d_bajo, int(round(q75 * vida[tipo])))
            retrasos = np.arange(d_bajo, d_alto + 1)
            llegada: dict[int, float] = {}
            for r in g.itertuples():
                aptas = r.toneladas_sale_por_vehiculo_soh_mayor_80 + r.toneladas_segunda_vida_80_70
                inmediato = r.toneladas_reciclaje_directo + aptas * (1 - adop_t)
                llegada[r.anio] = llegada.get(r.anio, 0.0) + inmediato
                for d in (retrasos if adop_t > 0 else []):
                    llegada[r.anio + d] = llegada.get(r.anio + d, 0.0) + aptas * adop_t / len(retrasos)
            for anio, t in llegada.items():
                filas.append({"adopcion_segunda_vida": adop, "tipo": tipo, "anio": anio,
                              "retraso_anios": f"{d_bajo}-{d_alto}", "toneladas_a_reciclaje": t,
                              "despues_de_horizonte": anio > anio_max})
    det = pd.DataFrame(filas).sort_values(["adopcion_segunda_vida", "tipo", "anio"])
    det.to_csv(carpeta / "reciclaje_retrasado.csv", index=False)

    retiradas = nac.groupby("anio")["toneladas_p50"].sum()
    res = (det[~det["despues_de_horizonte"]].groupby(["adopcion_segunda_vida", "anio"])["toneladas_a_reciclaje"]
           .sum().unstack(0))
    res.columns = [f"reciclaje_adopcion_{c:g}" for c in res.columns]
    res.insert(0, "toneladas_retiradas", retiradas)
    fuera = det[det["despues_de_horizonte"]].groupby("adopcion_segunda_vida")["toneladas_a_reciclaje"].sum()
    res.to_csv(carpeta / "reciclaje_retrasado_resumen.csv")
    print(f"margen q25-q75 = {q25:.2f}-{q75:.2f}; vida batería (años) = { {k: round(v, 1) for k, v in vida.items()} }")
    print(res.loc[[2030, 2035, 2040]].round(0).to_string())
    print("toneladas que llegan a reciclaje después de", anio_max, ":", fuera.round(0).to_dict())


if __name__ == "__main__":
    main()
