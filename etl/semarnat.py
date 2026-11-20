"""Limpieza de los directorios de empresas autorizadas para el manejo de residuos peligrosos (SEMARNAT, DGGIMAR).

Archivos esperados en datos/crudo/semarnat/ (descarga manual, CSV en cp1252 o UTF-8):
  Rubro1_Reciclaje..., Rubro2_Aprovechamiento..., Rubro4_Reutilizacion..., Rubro5_Tratamiento...,
  Rubro6_Incineracion..., Rubro7_Confinamiento..., Rubro9_Almacenamiento_y_Acopio..., Rubro14_Exportacion-Importacion...

Salidas (vía etl.ejecutar_etl):
  semarnat_autorizaciones.csv   una fila por autorización: rubro, empresa, entidad (nombre INEGI), capacidad t/año,
                                vigencia y banderas de tipo de residuo (plomo-ácido, litio, níquel, pilas)
  semarnat_import_export.csv    movimientos transfronterizos (Rubro 14) con las mismas banderas

Criterios de clasificación del texto libre "Tipo de residuo" (documentados para poder auditarlos):
  - litio: menciona baterías/pilas/acumuladores/celdas de litio, ion-litio, polímero de litio o metal-litio.
    No cuenta "hidróxido de litio" ni palabras que solo contienen las letras (p. ej. "naftiltiourea").
  - plomo: menciona plomo (acumuladores plomo-ácido y sus residuos).
  - vehicular: menciona vehículo/automotor/automotriz.
La capacidad es la AUTORIZADA para toda la empresa y todos sus residuos, no solo para baterías.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd

# Claves de entidad del Marco Geoestadístico de INEGI, con los nombres que usa el RAIAVL en este repositorio.
ENTIDADES_INEGI = {
    1: "Aguascalientes", 2: "Baja California", 3: "Baja California Sur", 4: "Campeche",
    5: "Coahuila de Zaragoza", 6: "Colima", 7: "Chiapas", 8: "Chihuahua", 9: "Ciudad de México",
    10: "Durango", 11: "Guanajuato", 12: "Guerrero", 13: "Hidalgo", 14: "Jalisco", 15: "México",
    16: "Michoacán de Ocampo", 17: "Morelos", 18: "Nayarit", 19: "Nuevo León", 20: "Oaxaca", 21: "Puebla",
    22: "Querétaro", 23: "Quintana Roo", 24: "San Luis Potosí", 25: "Sinaloa", 26: "Sonora", 27: "Tabasco",
    28: "Tamaulipas", 29: "Tlaxcala", 30: "Veracruz de Ignacio de la Llave", 31: "Yucatán", 32: "Zacatecas",
}
_ALIAS = {"distrito federal": 9, "cdmx": 9, "estado de mexico": 15, "edo. de mexico": 15, "edomex": 15,
          "coahuila": 5, "michoacan": 16, "veracruz": 30, "queretaro de arteaga": 22}

RUBROS = {1: "reciclaje", 2: "aprovechamiento", 4: "reutilizacion", 5: "tratamiento", 6: "incineracion",
          7: "confinamiento", 9: "acopio", 14: "importacion_exportacion"}

_RE_LITIO = re.compile(
    r"(bater[ií]as?|pilas?|acumuladores?|celdas?)[^,;]{0,40}?\blitio\b"
    r"|\bion[\s-]*(de[\s-]+)?litio\b|\blitio[\s-]*ion\b|pol[ií]mero\s+de\s+litio|metal[\s-]*litio",
    re.IGNORECASE)
_RE_PLOMO = re.compile(r"\bplomo\b", re.IGNORECASE)
_RE_NIQUEL = re.compile(r"n[ií]quel", re.IGNORECASE)
_RE_PILAS = re.compile(r"\bpilas?\b", re.IGNORECASE)
_RE_VEHIC = re.compile(r"veh[ií]cul|automot", re.IGNORECASE)


def _sin_acentos(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


def clave_entidad(clave, nombre) -> int | None:
    """Clave INEGI a partir de la clave numérica del archivo; si falta o es inválida, por el nombre."""
    try:
        c = int(float(str(clave).strip()))
        if c in ENTIDADES_INEGI:
            return c
    except (TypeError, ValueError):
        pass
    if pd.isna(nombre):
        return None
    n = _sin_acentos(str(nombre))
    if n in _ALIAS:
        return _ALIAS[n]
    por_nombre = {_sin_acentos(v): k for k, v in ENTIDADES_INEGI.items()}
    if n == "mexico":
        return 15
    return por_nombre.get(n)


def numero(x) -> float:
    """'20,358' -> 20358.0; vacío o texto -> NaN."""
    if pd.isna(x):
        return float("nan")
    s = str(x).replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return float("nan")


_RE_BATERIA = re.compile(r"bater[ií]a|pilas?\b|acumulador|celdas?\b", re.IGNORECASE)
_RE_COMPUESTO = re.compile(r"(jab[oó]n|nitrato|hidr[oó]xido|carbonato|cloruro|[oó]xido|grasa|estearato|bromuro)"
                           r"\s+de\s*$", re.IGNORECASE)


def es_litio(texto) -> bool:
    """Batería de litio: patrón explícito, o 'litio' dentro de una lista que empezó con batería/pila/acumulador
    (hasta 160 caracteres antes, sin cruzar ';' ni '.'), excluyendo compuestos químicos (jabón, nitrato, etc.)."""
    if pd.isna(texto):
        return False
    s = str(texto).replace("\xa0", " ")
    if _RE_LITIO.search(s):
        return True
    for m in re.finditer(r"\blitio\b", s, flags=re.IGNORECASE):
        antes = s[max(0, m.start() - 160): m.start()]
        antes = re.split(r"[;.]", antes)[-1]
        if _RE_BATERIA.search(antes) and not _RE_COMPUESTO.search(antes):
            return True
    return False


def leer_csv(p: Path) -> pd.DataFrame:
    try:
        d = pd.read_csv(p, encoding="utf-8", dtype=str)
    except UnicodeDecodeError:
        d = pd.read_csv(p, encoding="cp1252", dtype=str)
    d = d.loc[:, ~d.columns.str.startswith("Unnamed")]
    d.columns = [re.sub(r"\s+", " ", c).strip() for c in d.columns]
    return d.dropna(how="all")


def _col(d: pd.DataFrame, *pistas: str) -> str:
    for c in d.columns:
        cl = _sin_acentos(c)
        if any(p in cl for p in pistas):
            return c
    raise KeyError(f"no se encontró columna con {pistas}; columnas: {list(d.columns)}")


def banderas(texto: pd.Series) -> pd.DataFrame:
    t = texto.fillna("").astype(str)
    return pd.DataFrame({"litio": t.map(es_litio), "plomo": t.str.contains(_RE_PLOMO),
                         "niquel": t.str.contains(_RE_NIQUEL), "pilas": t.str.contains(_RE_PILAS),
                         "vehicular": t.str.contains(_RE_VEHIC)}, index=texto.index)


def limpiar_directorios(carpeta: Path) -> pd.DataFrame:
    partes = []
    for p in sorted(carpeta.glob("Rubro*.csv")):
        rubro = int(re.match(r"Rubro(\d+)", p.name).group(1))
        if rubro == 14:
            continue
        d = leer_csv(p)
        empresa = _col(d, "empresa")
        d = d[d[empresa].notna() & d[empresa].str.strip().ne("")]
        res = _col(d, "tipo de residuo")
        f = pd.DataFrame({
            "rubro": rubro, "rubro_nombre": RUBROS.get(rubro, str(rubro)), "empresa": d[empresa].str.strip(),
            "municipio": d[_col(d, "municipio")].str.strip(),
            "clave_entidad": [clave_entidad(c, n) for c, n in zip(d[_col(d, "clave estado", "clave entidad",
                                                                            "clave del estado")], d[_col(d, "estado")])],
            "estado_original": d[_col(d, "estado")].str.strip(),
            "tipo_residuo": d[res].str.strip(),
            "autorizacion": d[_col(d, "autorizacion")].str.strip(),
            "vigencia_inicio": d[_col(d, "inicio")].str.strip(),
            "vigencia_termino": d[_col(d, "termino")].str.strip(),
            "capacidad_t_anio": d[_col(d, "capacidad")].map(numero),
            "archivo_origen": p.name,
        })
        f["entidad"] = f["clave_entidad"].map(ENTIDADES_INEGI)
        partes.append(pd.concat([f, banderas(f["tipo_residuo"])], axis=1))
    if not partes:
        raise FileNotFoundError(f"sin archivos Rubro*.csv en {carpeta}")
    return pd.concat(partes, ignore_index=True)


def limpiar_import_export(carpeta: Path) -> pd.DataFrame:
    ps = sorted(carpeta.glob("Rubro14*.csv"))
    if not ps:
        raise FileNotFoundError("sin Rubro14*.csv")
    d = leer_csv(ps[0])
    d = d[d[_col(d, "razon social")].notna()]
    f = pd.DataFrame({
        "numero": d[_col(d, "numero")].str.strip(), "fecha_entrada": d[_col(d, "entrada")].str.strip(),
        "empresa": d[_col(d, "razon social")].str.strip(), "toneladas": d[_col(d, "cantidad")].map(numero),
        "tipo_residuo": d[_col(d, "tipo de residuo")].str.strip(), "pais": d[_col(d, "pais")].str.strip(),
        "vigencia_inicio": d[_col(d, "inicio vigencia")].str.strip(),
        "vigencia_termino": d[_col(d, "fin vigencia")].str.strip(), "archivo_origen": ps[0].name})
    # El archivo no tiene una columna de sentido (importación o exportación); no se infiere del folio.
    return pd.concat([f, banderas(f["tipo_residuo"])], axis=1)
