"""Descargas auxiliares de la Fase 1 que el README marcaba como "manuales".

No modifica nada de etl/: solo deja los archivos crudos donde config/config.yaml los espera y registra
fuente, URL, fecha y sha256 en datos/manifiesto_descargas.csv (con etl.utils.registrar_descarga).

Uso (desde la raíz del repo, con el entorno activado):
    python -m herramientas.descargar_fuentes inegi        # INEGI RAIAVL_11 (PxWeb, todos los años/meses/entidades/tipos)
    python -m herramientas.descargar_fuentes capitales    # agrega capitales estatales (Wikidata) a config/puntos_interes.csv
    python -m herramientas.descargar_fuentes nasa         # NASA PCoE "5. Battery Data Set" (B00xx.mat)
    python -m herramientas.descargar_fuentes calce        # CALCE CS2_33 a CS2_38 (xlsx de Arbin)
    python -m herramientas.descargar_fuentes oxford       # Oxford Battery Degradation Dataset 1 (.mat, ~262 MB)
    python -m herramientas.descargar_fuentes usgs         # USGS MCS 2026 (ScienceBase; puede bloquearlo Cloudflare)
    python -m herramientas.descargar_fuentes todo
Cada paso es independiente: si uno falla, imprime el motivo y sigue con el siguiente.

URLs: tomadas de las páginas oficiales el 2026-11-17 (ver comentarios junto a cada una).
"""
from __future__ import annotations

import csv
import io
import sys
import unicodedata
import zipfile
from html.parser import HTMLParser
from pathlib import Path

import requests

from etl.utils import cargar_config, registrar_descarga, ruta

UA = {"User-Agent": "bateria_ve_mx/0.1 (proyecto escolar; Python requests)"}
CFG = cargar_config()
MANIFIESTO = ruta(CFG["rutas"]["manifiesto"])


def _bajar(url: str, destino: Path, timeout: int = 600) -> Path:
    """Descarga con streaming; no vuelve a bajar si el archivo ya existe."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and destino.stat().st_size > 0:
        print(f"  ya existe: {destino.relative_to(ruta(''))}")
        return destino
    print(f"  bajando {url}")
    with requests.get(url, stream=True, timeout=timeout, headers=UA) as r:
        r.raise_for_status()
        tmp = destino.with_suffix(destino.suffix + ".parcial")
        with open(tmp, "wb") as f:
            for bloque in r.iter_content(1 << 20):
                f.write(bloque)
    tmp.replace(destino)
    print(f"  guardado: {destino.relative_to(ruta(''))} ({destino.stat().st_size/1e6:.1f} MB)")
    return destino


def _extraer(zbytes: bytes, carpeta: Path, sufijos: tuple[str, ...], aplanar: bool = True) -> list[Path]:
    """Extrae del zip (y de zips anidados) solo los archivos con esos sufijos."""
    salida = []
    with zipfile.ZipFile(io.BytesIO(zbytes)) as z:
        for info in z.infolist():
            nombre = info.filename
            if nombre.lower().endswith(".zip"):
                salida += _extraer(z.read(info), carpeta, sufijos, aplanar)
            elif nombre.lower().endswith(sufijos) and not nombre.startswith("__MACOSX"):
                destino = carpeta / (Path(nombre).name if aplanar else nombre)
                destino.parent.mkdir(parents=True, exist_ok=True)
                destino.write_bytes(z.read(info))
                salida.append(destino)
    return salida


# ------------------------------------------------------------------------------------------- INEGI
URL_INEGI = "https://www.inegi.org.mx/app/tabulados/pxwebv2/pxweb/es/RAIAVL/RAIAVL/RAIAVL_11.px/"


class _FormularioAspNet(HTMLParser):
    """Lee los campos del formulario ASP.NET de PxWeb (inputs y selects con sus opciones)."""

    def __init__(self):
        super().__init__()
        self.inputs, self.selects, self._sel = [], {}, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "input" and a.get("name"):
            self.inputs.append(a)
        elif tag == "select" and a.get("name"):
            self._sel = a["name"]
            self.selects[self._sel] = {"multiple": "multiple" in a, "opciones": [], "elegida": None}
        elif tag == "option" and self._sel:
            self.selects[self._sel]["opciones"].append(a.get("value", ""))
            if "selected" in a:
                self.selects[self._sel]["elegida"] = a.get("value", "")

    def handle_endtag(self, tag):
        if tag == "select":
            self._sel = None


def descargar_inegi() -> None:
    destino = ruta(CFG["inegi"]["archivo"])
    s = requests.Session()
    s.headers.update(UA)
    r = s.get(URL_INEGI, timeout=120)
    r.raise_for_status()
    p = _FormularioAspNet()
    p.feed(r.text)
    datos: list[tuple[str, str]] = []
    boton = None
    for a in p.inputs:
        tipo = a.get("type", "text").lower()
        if tipo in ("hidden", "text"):
            datos.append((a["name"], a.get("value", "")))
        elif tipo == "submit" and a["name"].endswith("ButtonViewTable"):
            boton = (a["name"], a.get("value", "Continuar"))
    n_variables = 0
    for nombre, sel in p.selects.items():
        if nombre.endswith("ValuesListBox"):          # una lista por variable: Año, Mes, Entidad, Tipo
            n_variables += 1
            datos += [(nombre, v) for v in sel["opciones"]]   # = "Seleccionar todos"
        elif nombre.endswith("OutputFormatDropDownList"):
            datos.append((nombre, "FileTypeCsvWithHeadingAndComma"))   # "Delimitada por coma con encabezado"
        elif sel["elegida"] is not None:
            datos.append((nombre, sel["elegida"]))
    if boton is None or n_variables != 4:
        raise SystemExit(f"INEGI: la página cambió (botón={boton}, variables={n_variables}); descarga a mano.")
    datos.append(boton)
    r2 = s.post(URL_INEGI, data=datos, timeout=300)
    r2.raise_for_status()
    contenido = r2.content
    if b"<html" in contenido[:500].lower():
        raise SystemExit("INEGI devolvió HTML en lugar del CSV (posible límite de celdas o cambio en la página).")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(contenido)
    registrar_descarga(MANIFIESTO, destino, "INEGI RAIAVL", URL_INEGI,
                       "PxWeb: todos los años, meses, entidades y 3 tipos; 'Delimitada por coma con encabezado'")
    print(f"  INEGI guardado: {destino.relative_to(ruta(''))} ({len(contenido)/1e3:.0f} kB)")


# --------------------------------------------------------------- Capitales estatales para NASA POWER
SPARQL = """SELECT ?estado ?estadoLabel ?cap ?capLabel ?coord WHERE {
  ?estado wdt:P31 wd:Q15149663 ; wdt:P36 ?cap . ?cap wdt:P625 ?coord .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "es" } }"""


def _slug(t: str) -> str:
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return "_".join("".join(c if c.isalnum() else " " for c in t).split())


def agregar_capitales() -> None:
    """Agrega (sin duplicar) una fila por capital estatal + CDMX, con la coordenada P625 de Wikidata."""
    archivo = ruta(CFG["power"]["puntos"])
    r = requests.get("https://query.wikidata.org/sparql", params={"query": SPARQL, "format": "json"},
                     headers=UA, timeout=120)
    r.raise_for_status()
    filas = {}
    for b in r.json()["results"]["bindings"]:
        lon, lat = b["coord"]["value"].removeprefix("Point(").removesuffix(")").split()
        qid = b["cap"]["value"].rsplit("/", 1)[-1]
        estado = b["estadoLabel"]["value"]
        filas[estado] = {"id": f"cap_{_slug(estado)}", "nombre": f"{b['capLabel']['value']} (capital de {estado})",
                         "latitud": round(float(lat), 5), "longitud": round(float(lon), 5),
                         "fuente_coordenada": f"Wikidata {qid}, propiedad P625 (consulta SPARQL, estado con P36)"}
    # Ciudad de México no es "estado" (Q15149663) en Wikidata: se agrega su propio ítem (Q1489).
    if not any("Ciudad de M" in k for k in filas):
        r = requests.get("https://www.wikidata.org/wiki/Special:EntityData/Q1489.json", headers=UA, timeout=60)
        c = r.json()["entities"]["Q1489"]["claims"]["P625"][0]["mainsnak"]["datavalue"]["value"]
        filas["Ciudad de México"] = {"id": "cap_ciudad_de_mexico", "nombre": "Ciudad de México",
                                     "latitud": round(c["latitude"], 5), "longitud": round(c["longitude"], 5),
                                     "fuente_coordenada": "Wikidata Q1489, propiedad P625"}
    with open(archivo, encoding="utf-8") as f:
        existentes = list(csv.DictReader(f))
    ids = {e["id"] for e in existentes}
    nuevas = [v for v in sorted(filas.values(), key=lambda d: d["id"]) if v["id"] not in ids]
    with open(archivo, "a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=["id", "nombre", "latitud", "longitud", "fuente_coordenada"]).writerows(nuevas)
    print(f"  capitales: {len(filas)} encontradas en Wikidata, {len(nuevas)} agregadas a {archivo.name}")
    if len(filas) != 32:
        print("  OJO: se esperaban 32 (31 estados + CDMX); revisa el archivo.")


# --------------------------------------------------------------------------------- Baterías
# Página oficial: https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/
URL_NASA = "https://phm-datasets.s3.amazonaws.com/NASA/5.+Battery+Data+Set.zip"
# Página oficial: https://calce.umd.edu/battery-data (sección CS2)
URL_CALCE = "https://web.calce.umd.edu/batteries/data/{celda}.zip"
CELDAS_CALCE = ["CS2_33", "CS2_34", "CS2_35", "CS2_36", "CS2_37", "CS2_38"]
# Página oficial: https://ora.ox.ac.uk/objects/uuid:03ba4b01-cfed-46d3-9b1a-7d4a7bdf6fac (enlace del archivo .mat)
URL_OXFORD = ("https://ora.ox.ac.uk/objects/uuid:03ba4b01-cfed-46d3-9b1a-7d4a7bdf6fac/files/"
              "m5ac36a1e2073852e4f1f7dee647909a7")
# DOI 10.5066/P1WKQ63T resuelve a este ítem de ScienceBase
ID_USGS = "696a75d5d4be0228872d3bf8"


def descargar_nasa() -> None:
    carpeta = ruta(CFG["nasa_pcoe"]["carpeta"])
    zipf = _bajar(URL_NASA, carpeta / "_zip" / "5_Battery_Data_Set.zip")
    mats = _extraer(zipf.read_bytes(), carpeta, (".mat",))
    for m in mats:
        registrar_descarga(MANIFIESTO, m, "NASA PCoE Battery Data Set", URL_NASA, "extraído del zip oficial")
    print(f"  NASA: {len(mats)} archivos .mat en {carpeta.relative_to(ruta(''))}")


def descargar_calce() -> None:
    base = ruta(CFG["calce"]["carpeta"])
    for celda in CELDAS_CALCE:
        url = URL_CALCE.format(celda=celda)
        zipf = _bajar(url, base / "_zip" / f"{celda}.zip")
        xs = _extraer(zipf.read_bytes(), base / celda, (".xlsx", ".xls"))
        for x in xs:
            registrar_descarga(MANIFIESTO, x, f"CALCE {celda}", url, "extraído del zip oficial")
        print(f"  CALCE {celda}: {len(xs)} archivos")


def descargar_oxford() -> None:
    destino = ruta(CFG["oxford"]["archivo"])
    _bajar(URL_OXFORD, destino, timeout=1800)
    if destino.read_bytes()[:20].lower().startswith(b"<!doctype"):
        destino.unlink()
        raise SystemExit("Oxford devolvió una página HTML, no el .mat: descárgalo a mano desde ORA.")
    registrar_descarga(MANIFIESTO, destino, "Oxford Battery Degradation Dataset 1", URL_OXFORD, "ORA, ODbL 1.0")


def descargar_usgs() -> None:
    carpeta = ruta(CFG["usgs"]["carpeta"])
    r = requests.get(f"https://www.sciencebase.gov/catalog/item/{ID_USGS}", params={"format": "json"},
                     headers=UA, timeout=120)
    if r.status_code != 200 or "json" not in r.headers.get("content-type", ""):
        raise SystemExit(f"USGS/ScienceBase respondió {r.status_code} (verificación anti-bots). "
                         "Descarga los CSV a mano desde https://doi.org/10.5066/P1WKQ63T")
    item = r.json()
    archivos = item.get("files", []) + [f for fa in item.get("facets", []) for f in fa.get("files", [])]
    n = 0
    for f in archivos:
        nombre = f.get("name", "")
        if nombre.lower().endswith(".csv") or nombre.lower().endswith(".zip"):
            destino = _bajar(f["url"], carpeta / nombre)
            if nombre.lower().endswith(".zip"):
                for c in _extraer(destino.read_bytes(), carpeta, (".csv",)):
                    registrar_descarga(MANIFIESTO, c, "USGS MCS 2026", f["url"], "extraído del zip")
                    n += 1
            else:
                registrar_descarga(MANIFIESTO, destino, "USGS MCS 2026", f["url"])
                n += 1
    print(f"  USGS: {n} CSV")


PASOS = {"inegi": descargar_inegi, "capitales": agregar_capitales, "nasa": descargar_nasa,
         "calce": descargar_calce, "oxford": descargar_oxford, "usgs": descargar_usgs}

if __name__ == "__main__":
    pedidos = sys.argv[1:] or ["todo"]
    if "todo" in pedidos:
        pedidos = list(PASOS)
    for paso in pedidos:
        print(f"== {paso}")
        try:
            PASOS[paso]()
        except (SystemExit, Exception) as e:   # noqa: BLE001  - se reporta y se sigue con lo demás
            print(f"  FALLÓ {paso}: {e}")
