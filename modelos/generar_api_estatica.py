"""Genera la "API estática": archivos JSON en api-estatica/ a partir de resultados/ (para GitHub Pages, raw.githack, Netlify...).

Uso, desde la raíz del proyecto:   python -m modelos.generar_api_estatica
Salida: api-estatica/*.json  (se sirven como archivos; no hay servidor ni base de datos)
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
RES = RAIZ / "resultados"
SALIDA = RAIZ / "api-estatica"

TABLAS = {
    "retiros.json": "fase3/retiros_eol_anual.csv",
    "ventas.json": "fase3/ventas_proyeccion_anual.csv",
    "vida-flota.json": "fase3/vida_flota_entidad.csv",
    "weibull.json": "fase3/weibull_por_conjunto.csv",
    "co2.json": "fase6/co2_monte_carlo_resumen.csv",
    "escenarios-red.json": "fase6/escenarios_red.csv",
    "sobol.json": "fase6/sobol_indices.csv",
    "ndvi.json": "fase7/ndvi_tendencias.csv",
    "retiros-por-clima.json": "fase7/retiros_por_clima.csv",
    "segunda-vida.json": "segunda_vida/destino_nacional.csv",
    "segunda-vida-entidad.json": "segunda_vida/destino_entidad.csv",
    "reciclaje-retrasado.json": "segunda_vida/reciclaje_retrasado_resumen.csv",
    "brecha-reciclaje.json": "brecha/brecha_entidad.csv",
    "litio-autorizaciones.json": "brecha/litio_autorizaciones.csv",
    "sensibilidad-umbral-70.json": "sensibilidad_umbral_70/retiros_umbral_80_vs_70.csv",
}


def guardar(nombre: str, obj) -> None:
    (SALIDA / nombre).write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def resumen() -> dict:
    mc = pd.read_csv(RES / "fase6/co2_monte_carlo_resumen.csv").set_index("variable")
    re = pd.read_csv(RES / "fase3/retiros_eol_anual.csv")
    base = re[re.escenario == "base"]
    t = {str(a): round(float(base[base.anio == a].toneladas_p50.sum()), 1) for a in (2025, 2030, 2035, 2040)}
    t40 = {e: round(float(re[(re.escenario == e) & (re.anio == 2040)].toneladas_p50.sum()), 1) for e in ("bajo", "base", "alto")}
    return {
        "proyecto": "Baterías de vehículos eléctricos en México, 2016-2040",
        "co2_g_km": {"electrico_p50": round(float(mc.loc["bev_g_km", "p50"]), 1),
                     "gasolina_p50": round(float(mc.loc["gas_g_km", "p50"]), 1),
                     "reduccion_pct_p50": round(float(mc.loc["reduccion_pct", "p50"]), 1),
                     "reduccion_pct_ic90": [round(float(mc.loc["reduccion_pct", "p5"]), 1),
                                            round(float(mc.loc["reduccion_pct", "p95"]), 1)]},
        "prob_electrico_mas_limpio": float(mc.loc["prob_bev_mas_limpio", "p50"]),
        "equilibrio_km_p50": round(float(mc.loc["equilibrio_km", "p50"])),
        "toneladas_retiradas_base_p50": t,
        "toneladas_2040_por_escenario_p50": t40,
        "linea2_2035": linea2(),
        "nota": "Escenarios con bandas de incertidumbre, no pronósticos puntuales.",
    }


def linea2() -> dict:
    sv = json.loads((RES / "segunda_vida/resumen.json").read_text(encoding="utf-8"))["por_anio"]["2035"]
    br = json.loads((RES / "brecha/resumen.json").read_text(encoding="utf-8"))
    return {"pct_toneladas_aptas_reuso_o_segunda_vida": round(sv["pct_toneladas_aptas"], 1),
            "pct_toneladas_aptas_sin_hev": round(sv["pct_toneladas_aptas_sin_hev"], 1),
            "toneladas_reciclaje_directo": round(sv["toneladas_reciclaje_directo"], 1),
            "reciclaje_litio_autorizado_t_anio": br["reciclaje_litio_t_anio"],
            "reciclaje_plomo_autorizado_t_anio": br["reciclaje_plomo_t_anio"],
            "acopio_litio_autorizaciones": br["acopio_litio_autorizaciones"],
            "entidades_con_deficit": br["2035"]["entidades_con_deficit"]}


def main() -> None:
    SALIDA.mkdir(exist_ok=True)
    guardar("resumen.json", resumen())
    indice = {"resumen.json": "Cifras clave del proyecto"}
    for nombre, archivo in TABLAS.items():
        df = pd.read_csv(RES / archivo)
        guardar(nombre, json.loads(df.to_json(orient="records", force_ascii=False)))
        indice[nombre] = f"{len(df)} filas de resultados/{archivo}"
    guardar("index.json", indice)
    print(f"Listo: {len(indice)} archivos en {SALIDA.relative_to(RAIZ)}/")


if __name__ == "__main__":
    main()
