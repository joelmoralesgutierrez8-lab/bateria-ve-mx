"""Fase 1 - Recolección.

Qué se descarga solo (con red):   NASA POWER (temperatura) y Landsat/Planetary Computer (NDVI).
Qué se descarga A MANO:           INEGI, CENACE, NASA PCoE, CALCE, Oxford, GREET/BatPaC, USGS (ver README).
`verificar_manuales` revisa que los archivos estén, registra su sha256 y avisa de lo que falta.

Uso:  python -m etl.descargas power | vegetacion | verificar
"""
from __future__ import annotations

import sys
import time

import numpy as np
import pandas as pd
import requests

from etl.utils import cargar_config, logger, registrar_descarga, ruta

log = logger("descargas")

URL_POWER_MENSUAL = "https://power.larc.nasa.gov/api/temporal/monthly/point"
URL_STAC_PC = "https://planetarycomputer.microsoft.com/api/stac/v1"


# ---------------------------------------------------------------- NASA POWER (temperatura)
def parsear_power_json(respuesta: dict, punto_id: str) -> pd.DataFrame:
    """Convierte la respuesta JSON mensual de POWER en tabla larga (id, fecha, variable, valor).

    Supuesto de estructura (a confirmar en tu primera corrida): properties.parameter.<VAR>.<YYYYMM>.
    Las claves YYYY13 son el promedio anual y se descartan; -999 es el valor de "sin dato".
    """
    try:
        parametros = respuesta["properties"]["parameter"]
    except KeyError as e:  # falla ruidoso si la API cambia de formato
        raise ValueError(f"Estructura inesperada en la respuesta de NASA POWER (falta {e}).") from e
    filas = []
    for variable, serie in parametros.items():
        for clave, valor in serie.items():
            if clave.endswith("13"):
                continue
            filas.append({"id": punto_id, "fecha": pd.Timestamp(f"{clave[:4]}-{clave[4:6]}-01"),
                          "variable": variable, "valor": np.nan if valor == -999 else float(valor)})
    return pd.DataFrame(filas)


def descargar_power(cfg: dict) -> pd.DataFrame:
    p = cfg["power"]
    puntos = pd.read_csv(ruta(p["puntos"]))
    if puntos.empty:
        raise SystemExit("config/puntos_interes.csv está vacío: agrega id, nombre, latitud, longitud "
                         "(con la fuente de cada coordenada).")
    tablas = []
    for _, fila in puntos.iterrows():
        params = {"parameters": ",".join(p["parametros"]), "community": p["comunidad"],
                  "latitude": fila["latitud"], "longitude": fila["longitud"],
                  "start": p["anio_inicio"], "end": p["anio_fin"], "format": "JSON"}
        r = requests.get(URL_POWER_MENSUAL, params=params, timeout=120)
        r.raise_for_status()
        tablas.append(parsear_power_json(r.json(), str(fila["id"])))
        time.sleep(1)  # cortesía con el servicio
    salida = ruta(p["salida"])
    out = pd.concat(tablas, ignore_index=True)
    out.to_csv(salida, index=False)
    registrar_descarga(ruta(cfg["rutas"]["manifiesto"]), salida, "NASA POWER",
                       URL_POWER_MENSUAL, f"{p['anio_inicio']}-{p['anio_fin']}; {len(puntos)} puntos")
    return out


# ---------------------------------------------------------------- Cobertura vegetal (NDVI Landsat)
def ndvi_mediana_anual(bbox: list[float], anio: int, cfg_veg: dict) -> float | None:
    """NDVI mediano de la temporada del año para un bbox [oeste, sur, este, norte].

    Landsat 8/9 Collection 2 Level-2: reflectancia = DN*0.0000275 - 0.2 (constantes de USGS).
    Máscara de nubes con QA_PIXEL (bits 1 dilatada, 2 cirro, 3 nube, 4 sombra).
    Requiere: pip install -r requirements-stac.txt  (NO probado con red en la sesión donde se escribió).
    """
    import odc.stac
    import planetary_computer
    import pystac_client

    cat = pystac_client.Client.open(URL_STAC_PC, modifier=planetary_computer.sign_inplace)
    busqueda = cat.search(
        collections=[cfg_veg["coleccion"]], bbox=bbox, datetime=f"{anio}-01-01/{anio}-12-31",
        query={"eo:cloud_cover": {"lt": cfg_veg["nubes_max"]}, "platform": {"in": ["landsat-8", "landsat-9"]}},
    )
    items = list(busqueda.items())
    if not items:
        log.warning("Sin escenas Landsat 8/9 para %s en %s", bbox, anio)
        return None
    ds = odc.stac.load(items, bands=["red", "nir08", "qa_pixel"], bbox=bbox, crs="EPSG:4326",
                       resolution=cfg_veg["resolucion_grados"], groupby="solar_day",
                       fail_on_error=False)  # escenas dañadas en el servidor (p. ej. LC09_034039_20220801) se tratan como sin dato
    malo = ((ds.qa_pixel & 0b11110) != 0) | (ds.red == 0) | (ds.nir08 == 0)
    red = (ds.red * 0.0000275 - 0.2).where(~malo)
    nir = (ds.nir08 * 0.0000275 - 0.2).where(~malo)
    ndvi = (nir - red) / (nir + red)
    mediana = float(ndvi.median(skipna=True).compute())
    if not -1.0 <= mediana <= 1.0:  # chequeo de cordura contra errores de escala
        raise ValueError(f"NDVI fuera de rango ({mediana}); revisa escala/offset.")
    return mediana


def descargar_vegetacion(cfg: dict) -> pd.DataFrame:
    v = cfg["vegetacion"]
    zonas = pd.read_csv(ruta(v["zonas"]))
    if zonas.empty:
        raise SystemExit("config/zonas_mineras.csv está vacío: agrega nombre, oeste, sur, este, norte "
                         "(y la fuente del bbox, p.ej. el título de concesión o el polígono del proyecto).")
    filas = [{"zona": z["nombre"], "anio": a,
              "ndvi_mediana": ndvi_mediana_anual([z["oeste"], z["sur"], z["este"], z["norte"]], a, v)}
             for _, z in zonas.iterrows() for a in v["anios"]]
    out = pd.DataFrame(filas)
    salida = ruta(v["salida"])
    out.to_csv(salida, index=False)
    registrar_descarga(ruta(cfg["rutas"]["manifiesto"]), salida, "Landsat C2 L2 (Planetary Computer)",
                       URL_STAC_PC, "NDVI mediano anual por bbox; sin escenas = NaN")
    return out


# ---------------------------------------------------------------- Verificación de descargas manuales
MANUALES = {
    "INEGI RAIAVL (híbridos y eléctricos por entidad)": ("inegi.archivo", "https://www.inegi.org.mx/app/tabulados/pxwebv2/pxweb/es/RAIAVL/RAIAVL/RAIAVL_11.px/"),
    "CENACE generación por tecnología": ("cenace.archivo", "https://www.cenace.gob.mx/Paginas/SIM/Reportes/EnergiaGeneradaTipoTec.aspx"),
    "Oxford Battery Degradation Dataset 1": ("oxford.archivo", "https://ora.ox.ac.uk/objects/uuid:03ba4b01-cfed-46d3-9b1a-7d4a7bdf6fac"),
    "GREET/BatPaC (plantilla extraída a mano)": ("greet_batpac.archivo", "https://greet.anl.gov  |  https://www.anl.gov/cse/batpac-model-software"),
}
CARPETAS = {
    "NASA PCoE (B00xx.mat)": ("nasa_pcoe.carpeta", "*.mat", "https://www.nasa.gov/content/prognostics-center-of-excellence-data-set-repository"),
    "CALCE (xlsx por celda)": ("calce.carpeta", "*.xlsx", "https://calce.umd.edu/data"),
    "USGS MCS 2026 (CSV)": ("usgs.carpeta", "*.csv", "https://doi.org/10.5066/P1WKQ63T"),
}


def _get(cfg: dict, punto: str):
    a, b = punto.split(".")
    return cfg[a][b]


def verificar_manuales(cfg: dict) -> pd.DataFrame:
    """Revisa existencia, registra sha256 y devuelve una tabla de estado."""
    estado = []
    manifiesto = ruta(cfg["rutas"]["manifiesto"])
    for nombre, (clave, url) in MANUALES.items():
        p = ruta(_get(cfg, clave))
        ok = p.exists() and p.stat().st_size > 0
        if ok and p.suffix == ".csv":          # una plantilla con solo encabezado cuenta como "falta"
            ok = len(pd.read_csv(p)) > 0
        if ok:
            registrar_descarga(manifiesto, p, nombre, url)
        estado.append({"fuente": nombre, "ruta": str(p.relative_to(ruta("."))), "presente": ok, "url_oficial": url})
    for nombre, (clave, patron, url) in CARPETAS.items():
        carpeta = ruta(_get(cfg, clave))
        archivos = sorted(carpeta.rglob(patron)) if carpeta.exists() else []
        for a in archivos:
            registrar_descarga(manifiesto, a, nombre, url)
        estado.append({"fuente": nombre, "ruta": f"{carpeta.relative_to(ruta('.'))} ({len(archivos)} archivos)",
                       "presente": len(archivos) > 0, "url_oficial": url})
    tabla = pd.DataFrame(estado)
    for _, f in tabla[~tabla["presente"]].iterrows():
        log.warning("FALTA: %s -> descárgalo de %s y guárdalo en %s", f["fuente"], f["url_oficial"], f["ruta"])
    return tabla


if __name__ == "__main__":
    cfg = cargar_config()
    orden = sys.argv[1] if len(sys.argv) > 1 else "verificar"
    if orden == "power":
        descargar_power(cfg)
    elif orden == "vegetacion":
        descargar_vegetacion(cfg)
    elif orden == "verificar":
        print(verificar_manuales(cfg).to_string(index=False))
    else:
        raise SystemExit("Uso: python -m etl.descargas [power|vegetacion|verificar]")
