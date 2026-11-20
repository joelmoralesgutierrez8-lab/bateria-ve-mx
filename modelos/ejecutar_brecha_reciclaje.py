"""Brecha entre baterías retiradas y capacidad autorizada de manejo, por entidad (Línea 2).

Uso (desde la raíz):  python -m modelos.ejecutar_brecha_reciclaje
Necesita: datos/procesado/semarnat_autorizaciones.csv, datos/procesado/semarnat_import_export.csv (etl.ejecutar_etl),
          resultados/fase3/retiros_eol_entidad.csv y resultados/segunda_vida/destino_entidad.csv
Salidas en resultados/brecha/:
  brecha_entidad.csv     por entidad y año (2030, 2035, 2040): toneladas retiradas por destino y capacidades autorizadas
  litio_autorizaciones.csv  las autorizaciones que mencionan baterías de litio (para revisión manual)
  resumen.json           cifras nacionales clave

Tres capacidades, de más optimista a más realista:
  cap_reciclaje_rp_total   todo el reciclaje autorizado de residuos peligrosos (Rubro 1) en la entidad
  cap_reciclaje_baterias   reciclaje autorizado que menciona baterías/acumuladores (hoy, de plomo-ácido)
  cap_reciclaje_litio      reciclaje/aprovechamiento/reutilización (Rubros 1, 2 y 4) que menciona litio
El acopio de litio (Rubro 9) se reporta aparte: almacenar no es reciclar.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
RUBROS_RECICLAJE = {1, 2, 4}


def capacidades(aut: pd.DataFrame) -> pd.DataFrame:
    rec = aut[aut["rubro"] == 1]
    rec_lit = aut[aut["rubro"].isin(RUBROS_RECICLAJE) & aut["litio"]]
    aco_lit = aut[(aut["rubro"] == 9) & aut["litio"]]
    bat = rec[rec["plomo"] | rec["tipo_residuo"].str.contains("bater|acumulador", case=False, na=False)]
    g = lambda d, n: d.groupby("entidad")["capacidad_t_anio"].agg(**{f"cap_{n}": "sum", f"n_{n}": "count"})
    return pd.concat([g(rec, "reciclaje_rp_total"), g(bat, "reciclaje_baterias"), g(rec_lit, "reciclaje_litio"),
                      g(aco_lit, "acopio_litio")], axis=1).fillna(0)


def main() -> None:
    proc = RAIZ / "datos/procesado"
    aut = pd.read_csv(proc / "semarnat_autorizaciones.csv")
    imex = pd.read_csv(proc / "semarnat_import_export.csv")
    salida = RAIZ / "resultados/brecha"
    salida.mkdir(parents=True, exist_ok=True)

    sin_entidad = aut["entidad"].isna().sum()
    caps = capacidades(aut)

    dest = pd.read_csv(RAIZ / "resultados/segunda_vida/destino_entidad.csv")
    dest = dest[dest["entidad"] != "No especificado"]
    t = (dest.groupby(["entidad", "anio"])[["toneladas_p50", "toneladas_sale_por_vehiculo_soh_mayor_80",
                                             "toneladas_segunda_vida_80_70", "toneladas_reciclaje_directo"]]
         .sum().reset_index())
    b = t.merge(caps, left_on="entidad", right_index=True, how="left").fillna(0)
    b["brecha_litio_t"] = b["cap_reciclaje_litio"] - b["toneladas_p50"]          # negativo = déficit
    b["brecha_litio_inmediata_t"] = b["cap_reciclaje_litio"] - b["toneladas_reciclaje_directo"]
    b["retiro_vs_reciclaje_rp_pct"] = 100 * b["toneladas_p50"] / b["cap_reciclaje_rp_total"].where(b["cap_reciclaje_rp_total"] > 0)
    b = b.sort_values(["anio", "toneladas_p50"], ascending=[True, False])
    b.to_csv(salida / "brecha_entidad.csv", index=False)

    lit = aut[aut["litio"]][["rubro", "rubro_nombre", "empresa", "entidad", "municipio", "capacidad_t_anio",
                             "vehicular", "tipo_residuo", "autorizacion", "vigencia_termino"]]
    lit.to_csv(salida / "litio_autorizaciones.csv", index=False)

    n35 = b[b["anio"] == 2035]
    criticos = ["Ciudad de México", "México", "Jalisco", "Nuevo León"]
    resumen = {
        "autorizaciones_leidas": int(len(aut)), "autorizaciones_sin_entidad": int(sin_entidad),
        "por_rubro": aut.groupby("rubro_nombre").size().to_dict(),
        "reciclaje_rp_total_t_anio": float(aut.loc[aut["rubro"] == 1, "capacidad_t_anio"].sum()),
        "reciclaje_plomo_t_anio": float(aut.loc[(aut["rubro"] == 1) & aut["plomo"], "capacidad_t_anio"].sum()),
        "reciclaje_litio_autorizaciones": int((aut["rubro"].isin(RUBROS_RECICLAJE) & aut["litio"]).sum()),
        "reciclaje_litio_t_anio": float(aut.loc[aut["rubro"].isin(RUBROS_RECICLAJE) & aut["litio"], "capacidad_t_anio"].sum()),
        "acopio_litio_autorizaciones": int(((aut["rubro"] == 9) & aut["litio"]).sum()),
        "acopio_litio_entidades": int(aut.loc[(aut["rubro"] == 9) & aut["litio"], "entidad"].nunique()),
        "import_export_litio": imex.loc[imex["litio"], ["empresa", "toneladas", "tipo_residuo", "pais"]].to_dict("records"),
        "import_export_plomo_t": float(imex.loc[imex["plomo"] | imex["tipo_residuo"].str.contains("acumulador", case=False, na=False), "toneladas"].sum()),
        "2035": {"toneladas_retiradas": float(n35["toneladas_p50"].sum()),
                 "toneladas_reciclaje_directo": float(n35["toneladas_reciclaje_directo"].sum()),
                 "deficit_litio_t": float(-n35["brecha_litio_t"].clip(upper=0).sum()),
                 "entidades_con_deficit": int((n35["brecha_litio_t"] < 0).sum()),
                 "criticos": n35[n35["entidad"].isin(criticos)][["entidad", "toneladas_p50", "cap_reciclaje_litio",
                                                                   "n_acopio_litio"]].to_dict("records")},
    }
    (salida / "resumen.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in resumen.items() if k != "import_export_litio"}, indent=2, ensure_ascii=False))
    print("litio en Rubro 14:", resumen["import_export_litio"])


if __name__ == "__main__":
    main()
