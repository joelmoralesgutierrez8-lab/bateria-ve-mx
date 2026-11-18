"""Fase 2 - Limpieza. Cada dataset tiene (a) una función de lectura de archivo y (b) una función PURA que
normaliza el DataFrame. La parte pura se prueba con datos sintéticos (tests/); la lectura de archivos reales
debe revisarse en tu primera corrida (el log avisa de cualquier columna o estructura inesperada)."""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from etl.utils import logger, sin_acentos

log = logger("limpieza")

# ============================================================== INEGI / RAIAVL (ventas por entidad)
MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
         "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
TIPOS = {"unidades vehiculares electricas": "BEV",          # eléctrico puro
         "unidades vehiculares hibridas plugin": "PHEV",    # híbrido enchufable
         "unidades vehiculares hibridas": "HEV"}            # híbrido no enchufable (batería pequeña)
SIN_DATO = {"-", "..", "...", "", "nan", "n.d.", "nd", "x"}


def _a_numero(serie: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Convierte texto a número. Devuelve (valor, sin_reporte) donde sin_reporte marca '-', '..' o vacío."""
    txt = serie.astype(str).str.strip()
    sin_reporte = txt.str.lower().isin(SIN_DATO)
    limpio = txt.str.replace(r"(?<=\d),(?=\d{3}\b)", "", regex=True).str.replace(" ", "", regex=False)
    return pd.to_numeric(limpio.where(~sin_reporte), errors="coerce"), sin_reporte


def leer_csv_flexible(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(path, encoding=enc, dtype=str)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"No pude decodificar {path}")


def normalizar_ventas_inegi(df: pd.DataFrame) -> pd.DataFrame:
    """Tabla larga: fecha, anio, mes, entidad, tipo (BEV/PHEV/HEV), unidades, sin_reporte.

    Acepta el CSV de PxWeb en formato largo (columna 'Unidades vehiculares' + una columna de valores) o ancho
    (una columna por tipo de vehículo). Quita los meses aún no publicados (todo '-' al final de la serie)."""
    df = df.copy()
    norm = {c: sin_acentos(c) for c in df.columns}
    col_anio = next((c for c, n in norm.items() if n in ("ano", "anio", "year")), None)
    col_mes = next((c for c, n in norm.items() if n == "mes"), None)
    col_ent = next((c for c, n in norm.items() if "entidad" in n), None)
    if not (col_anio and col_mes and col_ent):
        raise ValueError(f"No encuentro Año/Mes/Entidad en las columnas {list(df.columns)}. "
                         "Exporta el tabulado como 'Delimitada por coma con encabezado'.")
    col_tipo = next((c for c, n in norm.items() if n == "unidades vehiculares"), None)
    columnas_tipo = [c for c, n in norm.items() if n in TIPOS]
    if col_tipo:                                   # formato largo
        col_val = next((c for c in df.columns if c not in (col_anio, col_mes, col_ent, col_tipo)), None)
        if col_val is None:
            raise ValueError("Formato largo sin columna de valores.")
        largo = df.rename(columns={col_tipo: "tipo_raw", col_val: "valor_raw"})
    elif columnas_tipo:                            # formato ancho
        largo = df.melt(id_vars=[col_anio, col_mes, col_ent], value_vars=columnas_tipo,
                        var_name="tipo_raw", value_name="valor_raw")
    else:
        raise ValueError(f"No encuentro columnas de tipo de vehículo en {list(df.columns)}.")
    largo = largo.rename(columns={col_anio: "anio", col_mes: "mes_raw", col_ent: "entidad"})
    largo["tipo"] = largo["tipo_raw"].map(lambda t: TIPOS.get(sin_acentos(t)))
    if largo["tipo"].isna().any():
        raro = largo.loc[largo["tipo"].isna(), "tipo_raw"].unique()
        raise ValueError(f"Tipos de vehículo no reconocidos: {raro}")
    largo["mes"] = largo["mes_raw"].map(lambda m: MESES.get(sin_acentos(m)))
    if largo["mes"].isna().any():
        raise ValueError(f"Meses no reconocidos: {largo.loc[largo['mes'].isna(), 'mes_raw'].unique()}")
    largo["anio"] = pd.to_numeric(largo["anio"]).astype(int)
    largo["unidades"], largo["sin_reporte"] = _a_numero(largo["valor_raw"])
    largo["entidad"] = largo["entidad"].str.strip()
    largo["fecha"] = pd.to_datetime(dict(year=largo["anio"], month=largo["mes"].astype(int), day=1))
    if (largo["unidades"] < 0).any():
        raise ValueError("Hay ventas negativas: revisa el archivo.")
    # meses no publicados: posteriores al último mes con algún dato
    ultimo = largo.loc[largo["unidades"].notna(), "fecha"].max()
    antes = len(largo)
    largo = largo[largo["fecha"] <= ultimo]
    log.info("INEGI: último mes con datos = %s; descarté %d filas posteriores (aún no publicadas)",
             ultimo.strftime("%Y-%m"), antes - len(largo))
    cols = ["fecha", "anio", "mes", "entidad", "tipo", "unidades", "sin_reporte"]
    return largo[cols].sort_values(["fecha", "entidad", "tipo"]).reset_index(drop=True)


def agregar_nacional(ventas: pd.DataFrame) -> pd.DataFrame:
    """Ventas mensuales nacionales por tipo. Incluye 'No especificado'. min_count=1 evita convertir NaN en 0."""
    return (ventas.groupby(["fecha", "tipo"], as_index=False)["unidades"]
            .sum(min_count=1).sort_values(["fecha", "tipo"]).reset_index(drop=True))


def asignar_region(ventas: pd.DataFrame, crosswalk: pd.DataFrame) -> pd.DataFrame:
    """Agrega region_cenace según el mapeo entidad->región que TÚ llenas en config/ (no lo adivino).
    Entidades sin región quedan en NaN y se reportan."""
    cw = crosswalk.copy()
    cw["_k"] = cw["entidad"].map(sin_acentos)
    cw["region_cenace"] = cw["region_cenace"].replace("", np.nan)
    out = ventas.assign(_k=ventas["entidad"].map(sin_acentos)).merge(
        cw[["_k", "region_cenace"]], on="_k", how="left").drop(columns="_k")
    faltan = sorted(out.loc[out["region_cenace"].isna(), "entidad"].unique())
    if faltan:
        log.warning("Entidades sin región CENACE (llena config/crosswalk_entidad_region.csv): %s", faltan)
    return out


# ============================================================== CENACE: generación por tecnología
def normalizar_generacion(df: pd.DataFrame, columnas: dict, claves_limpias: list[str]) -> pd.DataFrame:
    faltan = [v for v in columnas.values() if v not in df.columns]
    if faltan:
        raise ValueError(f"Columnas {faltan} no están en el archivo de CENACE (tiene {list(df.columns)}). "
                         "Ajusta cenace.columnas en config/config.yaml.")
    inv = {v: k for k, v in columnas.items()}
    g = df.rename(columns=inv)[["fecha", "region", "tecnologia", "energia_mwh"]].copy()
    g["fecha"] = pd.to_datetime(g["fecha"], errors="coerce")
    g["energia_mwh"], _ = _a_numero(g["energia_mwh"])
    g["tecnologia"] = g["tecnologia"].map(sin_acentos)
    g["region"] = g["region"].astype(str).str.strip()
    malas = g["fecha"].isna().sum()
    if malas:
        log.warning("CENACE: %d filas con fecha ilegible descartadas", malas)
    g = g.dropna(subset=["fecha"]).drop_duplicates()
    g["fecha"] = g["fecha"].dt.to_period("M").dt.to_timestamp()
    g = g.groupby(["fecha", "region", "tecnologia"], as_index=False)["energia_mwh"].sum(min_count=1)
    g["limpia"] = g["tecnologia"].map(lambda t: any(k in t for k in claves_limpias))
    return g


def factor_emision_implicito(gen: pd.DataFrame, factores: pd.DataFrame) -> pd.DataFrame:
    """gCO2e/kWh de la mezcla = sum(E_tec * f_tec) / sum(E_tec), por mes y región.
    OJO: es un factor de CICLO DE VIDA construido con los factores por tecnología que tú aportas; NO es el
    factor oficial FESEN de SEMARNAT (un solo número nacional por año). Úsalo para comparar regiones."""
    f = factores.copy()
    if f.empty:
        raise ValueError("Falta datos/crudo/cenace/factores_emision_por_tecnologia.csv (tecnologia, g_co2e_por_kwh, fuente).")
    f["tecnologia"] = f["tecnologia"].map(sin_acentos)
    m = gen.merge(f[["tecnologia", "g_co2e_por_kwh"]], on="tecnologia", how="left")
    sin_f = sorted(m.loc[m["g_co2e_por_kwh"].isna() & m["energia_mwh"].gt(0), "tecnologia"].unique())
    if sin_f:
        raise ValueError(f"Tecnologías sin factor de emisión: {sin_f}. Agrégalas al CSV de factores.")
    m["emisiones"] = m["energia_mwh"] * m["g_co2e_por_kwh"]
    r = m.groupby(["fecha", "region"]).apply(
        lambda d: pd.Series({"energia_mwh": d["energia_mwh"].sum(),
                             "g_co2e_por_kwh": d["emisiones"].sum() / d["energia_mwh"].sum(),
                             "pct_limpia": 100 * d.loc[d["limpia"], "energia_mwh"].sum() / d["energia_mwh"].sum()}),
        include_groups=False).reset_index()
    return r


# ============================================================== Baterías: degradación
def soh_desde_capacidad(df: pd.DataFrame, col_id: str = "bateria", col_ciclo: str = "ciclo",
                        col_cap: str = "capacidad_ah") -> pd.DataFrame:
    """SoH = capacidad / capacidad del primer ciclo de esa celda (definición operativa; la referencia
    correcta sería la capacidad nominal del fabricante cuando se conozca)."""
    d = df.sort_values([col_id, col_ciclo]).copy()
    d["capacidad_ref_ah"] = d.groupby(col_id)[col_cap].transform("first")
    d["soh"] = d[col_cap] / d["capacidad_ref_ah"]
    return d


def extraer_descargas_nasa(ciclos, bateria: str) -> pd.DataFrame:
    """Recibe la lista de ciclos (objetos con .type, .ambient_temperature, .data.Capacity). Solo 'discharge'."""
    filas, n = [], 0
    for c in np.atleast_1d(ciclos):
        if str(c.type) == "discharge":
            cap = np.atleast_1d(c.data.Capacity)
            if cap.size == 0:
                log.warning("NASA PCoE (%s): ciclo discharge con Capacity vacío omitido", bateria)
                continue
            n += 1
            filas.append({"bateria": bateria, "ciclo": n,
                          "capacidad_ah": float(cap[0]),
                          "temp_ambiente_c": float(c.ambient_temperature)})
    return pd.DataFrame(filas)


def leer_nasa_pcoe(carpeta: Path) -> pd.DataFrame:
    from scipy.io import loadmat
    tablas = []
    for f in sorted(carpeta.rglob("B*.mat")):
        m = loadmat(f, struct_as_record=False, squeeze_me=True)
        clave = next(k for k in m if not k.startswith("__"))
        tablas.append(extraer_descargas_nasa(m[clave].cycle, clave))
    if not tablas:
        return pd.DataFrame(columns=["bateria", "ciclo", "capacidad_ah", "temp_ambiente_c"])
    out = soh_desde_capacidad(pd.concat(tablas, ignore_index=True))
    out["fuente"] = "NASA PCoE"
    return out


def capacidad_calce(frames: list[pd.DataFrame], celda: str) -> pd.DataFrame:
    """frames: un DataFrame por archivo de Arbin con Cycle_Index, Discharge_Capacity(Ah), Date_Time.
    Ordena archivos por fecha, encadena los índices de ciclo (reinician en cada archivo) y toma la capacidad
    de descarga de cada ciclo.

    OJO: en los .xlsx de Arbin de CALCE, Discharge_Capacity(Ah) es ACUMULADA a lo largo del archivo
    (p. ej. 52.7 Ah en el ciclo 50 de una celda de 1.1 Ah). La capacidad de un ciclo es max - min dentro
    del ciclo; eso también funciona si el contador reinicia en cada ciclo (min = 0). Corregido 2026-11-18."""
    orden = sorted(frames, key=lambda d: pd.to_datetime(d["Date_Time"], errors="coerce").min())
    filas, offset = [], 0
    for d in orden:
        g = d.groupby("Cycle_Index")["Discharge_Capacity(Ah)"]
        cap = g.max() - g.min()
        cap.index = cap.index + offset
        filas.append(cap)
        offset = int(cap.index.max())
    s = pd.concat(filas)
    s = s[~s.index.duplicated(keep="last")]
    out = s.rename("capacidad_ah").rename_axis("ciclo").reset_index()
    out = out[out["capacidad_ah"] > 0]
    out.insert(0, "bateria", celda)
    return out


def leer_calce(carpeta: Path) -> pd.DataFrame:
    """Arbin .xlsx (hojas 'Channel_*'). Los .txt de CADEX (CS2_8, CS2_21) se omiten y se avisa."""
    tablas = []
    for sub in sorted(p for p in carpeta.iterdir() if p.is_dir()) or [carpeta]:
        frames = []
        for x in sorted(sub.glob("*.xlsx")):
            hojas = pd.read_excel(x, sheet_name=None)
            for nombre, h in hojas.items():
                if nombre.lower().startswith("channel") and "Cycle_Index" in h.columns:
                    frames.append(h[["Cycle_Index", "Discharge_Capacity(Ah)", "Date_Time"]])
        if frames:
            tablas.append(capacidad_calce(frames, sub.name))
    omitidos = [p.name for p in carpeta.rglob("*.txt")]
    if omitidos:
        log.warning("CALCE: omití %d archivos .txt (formato CADEX): %s", len(omitidos), omitidos[:5])
    if not tablas:
        return pd.DataFrame(columns=["bateria", "ciclo", "capacidad_ah", "soh"])
    out = soh_desde_capacidad(pd.concat(tablas, ignore_index=True))
    out["fuente"] = "CALCE"
    return out


def _campos(obj) -> dict:
    if hasattr(obj, "_fieldnames"):
        return {n: getattr(obj, n) for n in obj._fieldnames}
    if isinstance(obj, dict):
        return obj
    raise TypeError(f"Estructura MATLAB inesperada: {type(obj)}")


def extraer_oxford(datos: dict) -> pd.DataFrame:
    """datos: {'Cell1': {'cyc0000': {'C1dc': {'q': array, ...}}, ...}, ...}. Capacidad = |último q| de la
    descarga a 1C. UNIDAD SUPUESTA mAh (confírmala en readme.txt del dataset) -> se divide entre 1000 para Ah."""
    filas = []
    for celda, ciclos in datos.items():
        if not str(celda).lower().startswith("cell"):
            continue
        for nombre, contenido in _campos(ciclos).items():
            if not str(nombre).startswith("cyc"):
                continue
            c1dc = _campos(_campos(contenido)["C1dc"])
            q = np.atleast_1d(c1dc["q"]).astype(float)
            filas.append({"bateria": str(celda), "ciclo": int(str(nombre)[3:]),
                          "capacidad_ah": abs(q[-1]) / 1000.0, "temp_ambiente_c": 40.0})
    return pd.DataFrame(filas)


def leer_oxford(path: Path) -> pd.DataFrame:
    try:
        from scipy.io import loadmat
        m = loadmat(path, struct_as_record=False, squeeze_me=True)
    except NotImplementedError:      # MATLAB v7.3 (HDF5)
        import mat73                  # pip install mat73
        m = mat73.loadmat(str(path))
    datos = {k: v for k, v in m.items() if not k.startswith("__")}
    if len(datos) == 1:               # a veces todo viene bajo una sola llave
        unico = next(iter(datos.values()))
        datos = _campos(unico)
    out = soh_desde_capacidad(extraer_oxford(datos))
    out["fuente"] = "Oxford"
    return out


# ============================================================== USGS, GREET/BatPaC, POWER, NDVI
def leer_usgs(carpeta: Path, minerales: list[str]) -> pd.DataFrame:
    """Carga los CSV del data release y se queda con los minerales de interés. No conozco de antemano el
    nombre exacto de las columnas: busca una columna que contenga 'commodity'; si no la hay, avisa."""
    tablas = []
    for f in sorted(carpeta.glob("*.csv")):
        d = leer_csv_flexible(f)
        d.columns = [sin_acentos(c).replace(" ", "_") for c in d.columns]
        col = next((c for c in d.columns if "commodity" in c), None)
        if col is None:
            log.warning("USGS: %s no tiene columna 'commodity' (columnas: %s)", f.name, list(d.columns))
            continue
        mascara = d[col].map(sin_acentos).map(lambda t: any(m in t for m in minerales))
        if mascara.any():
            tablas.append(d[mascara].assign(archivo_origen=f.name))
    return pd.concat(tablas, ignore_index=True) if tablas else pd.DataFrame()


def leer_greet_batpac(path: Path) -> pd.DataFrame:
    """Plantilla llenada a mano desde GREET (Excel/.NET) y BatPaC. Exige trazabilidad por fila."""
    d = pd.read_csv(path) if path.exists() else pd.DataFrame()
    if d.empty:
        return d
    obligatorias = ["parametro", "valor", "unidad", "modelo_y_version", "hoja_o_tabla", "fecha_extraccion"]
    vacias = d[obligatorias].isna().any(axis=1)
    if vacias.any():
        raise ValueError(f"GREET/BatPaC: filas sin trazabilidad (faltan {obligatorias}): {list(d.index[vacias])}")
    d["valor"] = pd.to_numeric(d["valor"], errors="raise")
    return d


def limpiar_power(df: pd.DataFrame) -> pd.DataFrame:
    """Largo -> ancho (T2M, T2M_MAX, T2M_MIN por id y mes) con chequeo de rango físico."""
    d = df.copy()
    d["fecha"] = pd.to_datetime(d["fecha"])
    ancho = d.pivot_table(index=["id", "fecha"], columns="variable", values="valor").reset_index()
    ancho.columns.name = None
    for c in [c for c in ancho.columns if c.startswith("T2M")]:
        fuera = ~ancho[c].dropna().between(-60, 60)
        if fuera.any():
            raise ValueError(f"{c}: valores fuera de [-60, 60] °C")
    return ancho


def limpiar_ndvi(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    fuera = d["ndvi_mediana"].dropna().pipe(lambda s: ~s.between(-1, 1))
    if fuera.any():
        raise ValueError("NDVI fuera de [-1, 1]")
    return d
