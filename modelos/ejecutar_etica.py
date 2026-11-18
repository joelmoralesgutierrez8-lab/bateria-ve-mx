"""Fase 7: ¿quién paga el costo ambiental?

Uso: python -m modelos.ejecutar_etica      (requiere la Fase 3 y la Fase 6)
Salidas en resultados/fase7/:
  ndvi_tendencias.csv       Mann-Kendall (tau de Kendall vs año, p-valor) y pendiente de Theil-Sen con IC 90%
                            del NDVI anual 2014-2025 por zona minera, más cambio 2014-16 vs 2023-25
  reparto_emisiones.csv     de dónde salen las emisiones de un BEV en México: batería (fabricada fuera),
                            carrocería y uso (red mexicana), en g/km y en %
  retiros_por_clima.csv     toneladas de baterías retiradas por entidad en 2035 junto a su temperatura
Limitación central del NDVI: sin zonas de control cercanas ni datos de lluvia, una tendencia NO prueba que la
mina la cause (sequía, incendios o cambio de uso de suelo pueden producir lo mismo).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

RAIZ = Path(__file__).resolve().parents[1]


def tendencia(anios, y, nivel: float = 0.90) -> dict:
    tau, p = stats.kendalltau(anios, y)
    pend, inter, bajo, alto = stats.theilslopes(y, anios, alpha=nivel)
    return {"tau_kendall": tau, "p_mann_kendall": p, "pendiente_por_anio": pend,
            "pendiente_ic_bajo": bajo, "pendiente_ic_alto": alto}


def main() -> None:
    salida = RAIZ / "resultados" / "fase7"
    salida.mkdir(parents=True, exist_ok=True)

    nd = pd.read_csv(RAIZ / "datos" / "procesado" / "vegetacion_ndvi_zonas.csv")
    filas = []
    for z, g in nd.groupby("zona"):
        g = g.sort_values("anio")
        ini = g[g.anio <= g.anio.min() + 2].ndvi_mediana.mean()
        fin = g[g.anio >= g.anio.max() - 2].ndvi_mediana.mean()
        filas.append({"zona": z, "anios": f"{g.anio.min()}-{g.anio.max()}", **tendencia(g.anio, g.ndvi_mediana),
                      "ndvi_inicio_3a": ini, "ndvi_fin_3a": fin, "cambio_pct": 100 * (fin / ini - 1)})
    t = pd.DataFrame(filas)
    t.to_csv(salida / "ndvi_tendencias.csv", index=False)
    print("Tendencia del NDVI en zonas mineras (Mann-Kendall y Theil-Sen):")
    print(t.round(4).to_string(index=False))

    mc = pd.read_csv(RAIZ / "resultados" / "fase6" / "co2_monte_carlo_resumen.csv").set_index("variable")
    bev, uso = mc.loc["bev_g_km", "p50"], mc.loc["uso_bev_g_km", "p50"]
    fab = bev - uso
    rep = pd.DataFrame([
        {"etapa": "fabricación (batería + carrocería)", "donde": "batería: casi siempre importada (minería y celdas fuera de México); carrocería: puede fabricarse en México",
         "g_km_p50": fab, "pct": 100 * fab / bev},
        {"etapa": "uso (electricidad)", "donde": "México (red CENACE)", "g_km_p50": uso, "pct": 100 * uso / bev}])
    rep.to_csv(salida / "reparto_emisiones.csv", index=False)
    print("\nReparto de las emisiones medianas de un BEV en México:")
    print(rep.round(1).to_string(index=False))

    ent = pd.read_csv(RAIZ / "resultados" / "fase3" / "retiros_eol_entidad.csv")
    vida = pd.read_csv(RAIZ / "resultados" / "fase3" / "vida_flota_entidad.csv")
    temp = vida.groupby("entidad").temp_media_c.first()
    bev = vida[vida.tipo == "BEV"].set_index("entidad")
    r = ent[ent.anio == 2035].groupby("entidad").toneladas_p50.sum().rename("toneladas_2035").to_frame()
    r = r.join(temp).join(bev[["mediana_bateria_sola_anios", "pct_retiro_por_bateria"]]).sort_values("toneladas_2035", ascending=False)
    r.to_csv(salida / "retiros_por_clima.csv")
    cal = r[r.temp_media_c >= 24]
    print(f"\nEntidades calurosas (>= 24 °C): {len(cal)}; vida mediana BEV {cal.mediana_bateria_sola_anios.mean():.1f} años "
          f"vs {r[r.temp_media_c < 24].mediana_bateria_sola_anios.mean():.1f} en el resto.")


if __name__ == "__main__":
    main()
