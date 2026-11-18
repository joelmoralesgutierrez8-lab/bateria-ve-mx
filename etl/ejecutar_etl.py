"""Orquestador de la Fase 2.   Uso:  python -m etl.ejecutar_etl

Para cada dataset: si el crudo existe lo limpia y guarda en datos/procesado/; si no, lo anota como AUSENTE en la
tabla de datos faltantes (en vez de fallar). Al final genera las fichas (datos/fichas/*.md) y la cobertura por entidad."""
from __future__ import annotations

import pandas as pd
import yaml

from etl import limpieza as L
from etl.utils import (RAIZ, cargar_config, fijar_semilla, fila_dataset_ausente, logger, resumen_faltantes, ruta)

log = logger("etl")


def _guardar(df: pd.DataFrame, nombre: str, cfg: dict) -> pd.DataFrame:
    destino = ruta(cfg["rutas"]["procesado"]) / f"{nombre}.csv"
    destino.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(destino, index=False)
    log.info("Guardado %s (%d filas)", destino.relative_to(RAIZ), len(df))
    return df


def procesar_todo(cfg: dict) -> dict[str, dict]:
    """Devuelve {dataset: {'df': DataFrame|None, 'motivo': str}} y guarda los procesados."""
    res: dict[str, dict] = {}

    def intentar(nombre, existe, fn, motivo_ausente):
        if not existe:
            res[nombre] = {"df": None, "motivo": motivo_ausente}
            log.warning("AUSENTE %s: %s", nombre, motivo_ausente)
            return
        try:
            res[nombre] = {"df": _guardar(fn(), nombre, cfg), "motivo": ""}
        except Exception as e:  # un dataset roto no debe tumbar a los demás
            res[nombre] = {"df": None, "motivo": f"ERROR al procesar: {e}"}
            log.error("%s: %s", nombre, e)

    # --- INEGI
    p = ruta(cfg["inegi"]["archivo"])
    intentar("inegi_ventas_entidad_mes", p.exists(),
             lambda: L.normalizar_ventas_inegi(L.leer_csv_flexible(p)), f"no existe {cfg['inegi']['archivo']}")
    v = res["inegi_ventas_entidad_mes"]["df"]
    if v is not None:
        _guardar(L.agregar_nacional(v), "inegi_ventas_nacional_mes", cfg)
        cw = pd.read_csv(ruta(cfg["crosswalk_entidad_region"]), dtype=str).fillna("")
        _guardar(L.asignar_region(v, cw), "inegi_ventas_entidad_mes_con_region", cfg)

    # --- CENACE
    p = ruta(cfg["cenace"]["archivo"])
    pf = ruta(cfg["cenace"]["factores_tecnologia"])

    def cenace():
        gen = L.normalizar_generacion(L.leer_csv_flexible(p), cfg["cenace"]["columnas"],
                                      cfg["cenace"]["tecnologias_limpias"])
        _guardar(gen, "cenace_generacion_mensual", cfg)
        return L.factor_emision_implicito(gen, pd.read_csv(pf))

    intentar("cenace_factor_emision_regional", p.exists(), cenace, f"no existe {cfg['cenace']['archivo']}")

    # --- Baterías
    c = ruta(cfg["nasa_pcoe"]["carpeta"])
    intentar("bateria_nasa_pcoe", c.exists() and any(c.rglob("B*.mat")), lambda: L.leer_nasa_pcoe(c),
             "sin archivos B*.mat en datos/crudo/nasa_pcoe")
    c = ruta(cfg["calce"]["carpeta"])
    intentar("bateria_calce", c.exists() and any(c.rglob("*.xlsx")), lambda: L.leer_calce(c),
             "sin archivos .xlsx en datos/crudo/calce")
    p = ruta(cfg["oxford"]["archivo"])
    intentar("bateria_oxford", p.exists(), lambda: L.leer_oxford(p), f"no existe {cfg['oxford']['archivo']}")

    # --- Ciclo de vida, minerales, clima, vegetación
    p = ruta(cfg["greet_batpac"]["archivo"])
    intentar("greet_batpac_parametros", p.exists() and len(pd.read_csv(p)) > 0, lambda: L.leer_greet_batpac(p),
             "plantilla vacía: extrae a mano los parámetros de GREET/BatPaC (ver README)")
    c = ruta(cfg["usgs"]["carpeta"])
    intentar("usgs_minerales", c.exists() and any(c.glob("*.csv")),
             lambda: L.leer_usgs(c, cfg["usgs"]["minerales"]), "sin CSV en datos/crudo/usgs")
    p = ruta(cfg["power"]["salida"])
    intentar("nasa_power_temperatura", p.exists(), lambda: L.limpiar_power(pd.read_csv(p)),
             "ejecuta: python -m etl.descargas power (requiere config/puntos_interes.csv)")
    p = ruta(cfg["vegetacion"]["salida"])
    intentar("vegetacion_ndvi_zonas", p.exists(), lambda: L.limpiar_ndvi(pd.read_csv(p)),
             "ejecuta: python -m etl.descargas vegetacion (requiere config/zonas_mineras.csv)")
    return res


def tabla_faltantes(res: dict[str, dict], cfg: dict) -> pd.DataFrame:
    partes = [resumen_faltantes(r["df"], n) if r["df"] is not None else fila_dataset_ausente(n, r["motivo"])
              for n, r in res.items()]
    t = pd.concat(partes, ignore_index=True)
    destino = ruta(cfg["rutas"]["procesado"]) / "tabla_datos_faltantes.csv"
    t.to_csv(destino, index=False)
    (destino.with_suffix(".md")).write_text(t.fillna("").to_markdown(index=False)
                                            if _tiene_tabulate() else t.to_string(index=False), encoding="utf-8")
    return t


def _tiene_tabulate() -> bool:
    try:
        import tabulate  # noqa: F401
        return True
    except ImportError:
        return False


def cobertura_entidades(res: dict[str, dict], cfg: dict) -> pd.DataFrame | None:
    """¿Qué entidades tienen ventas y cuántos meses con dato? Detecta huecos geográficos."""
    v = res["inegi_ventas_entidad_mes"]["df"]
    if v is None:
        return None
    cw = pd.read_csv(ruta(cfg["crosswalk_entidad_region"]))
    c = (v.groupby("entidad").agg(meses_con_dato=("unidades", lambda s: int(s.notna().sum())),
                                  unidades_totales=("unidades", "sum")).reindex(cw["entidad"]).reset_index())
    c["sin_ventas_registradas"] = c["unidades_totales"].fillna(0).eq(0)
    _guardar(c, "cobertura_por_entidad", cfg)
    return c


def generar_fichas(res: dict[str, dict], cfg: dict) -> None:
    meta = yaml.safe_load(open(ruta("config/fichas.yaml"), encoding="utf-8"))
    carpeta = ruta(cfg["rutas"]["fichas"])
    carpeta.mkdir(parents=True, exist_ok=True)
    mapa = {"inegi_ventas": "inegi_ventas_entidad_mes", "cenace_generacion": "cenace_factor_emision_regional",
            "nasa_pcoe": "bateria_nasa_pcoe", "calce": "bateria_calce", "oxford": "bateria_oxford",
            "greet_batpac": "greet_batpac_parametros", "usgs_mcs": "usgs_minerales",
            "nasa_power": "nasa_power_temperatura", "vegetacion": "vegetacion_ndvi_zonas"}
    for clave, m in meta.items():
        r = res.get(mapa[clave], {"df": None, "motivo": "no ejecutado"})
        df = r["df"]
        if df is None:
            estado = f"**Sin datos procesados todavía.** {r['motivo']}"
        else:
            falt = df.isna().mean().mul(100).round(1)
            peores = falt[falt > 0].sort_values(ascending=False).head(5)
            estado = (f"{len(df):,} filas procesadas. Columnas con faltantes (%): "
                      f"{', '.join(f'{k} {v}%' for k, v in peores.items()) or 'ninguna'}.")
            for col in ("fecha", "anio"):
                if col in df.columns:
                    estado += f" Periodo observado: {str(df[col].min())[:10]} a {str(df[col].max())[:10]}."
                    break
        sesgos = "\n".join(f"- {s}" for s in m["sesgos_conocidos"])
        md = (f"# Ficha de dataset: {m['nombre']}\n\n- **Fuente oficial:** {m['url']}\n"
              f"- **Origen geográfico:** {m['origen_geografico']}\n- **Clima / condiciones:** {m['clima']}\n"
              f"- **Periodo nominal:** {m['periodo_nominal']}\n- **Variables:** {m['variables']}\n"
              f"- **Licencia:** {m['licencia']}\n- **Estado del procesamiento:** {estado}\n\n"
              f"## Sesgos y limitaciones conocidos\n{sesgos}\n")
        (carpeta / f"ficha_{clave}.md").write_text(md, encoding="utf-8")


if __name__ == "__main__":
    cfg = cargar_config()
    fijar_semilla(cfg["semilla"])
    resultados = procesar_todo(cfg)
    print(tabla_faltantes(resultados, cfg).to_string(index=False))
    cobertura_entidades(resultados, cfg)
    generar_fichas(resultados, cfg)
