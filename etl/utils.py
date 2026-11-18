"""Utilidades comunes del ETL. Sin dependencias fuera de pandas, numpy y pyyaml."""
from __future__ import annotations

import hashlib
import logging
import random
import unicodedata
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

RAIZ = Path(__file__).resolve().parents[1]  # raíz del repo; todas las rutas salen de aquí (relativas)

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")


def logger(nombre: str) -> logging.Logger:
    return logging.getLogger(nombre)


def cargar_config(ruta: str = "config/config.yaml") -> dict:
    with open(RAIZ / ruta, encoding="utf-8") as f:
        return yaml.safe_load(f)


def fijar_semilla(semilla: int) -> None:
    """Semilla global (random y numpy). Los modelos de fases posteriores la reutilizan."""
    random.seed(semilla)
    np.random.seed(semilla)


def ruta(rel: str) -> Path:
    """Convierte una ruta relativa del config en absoluta, anclada a la raíz del repo."""
    return RAIZ / rel


def sin_acentos(texto: str) -> str:
    """minúsculas, sin acentos ni espacios sobrantes: 'Híbridas  Plugin' -> 'hibridas plugin'."""
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return " ".join(t.lower().split())


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def registrar_descarga(manifiesto: Path, archivo: Path, fuente: str, url: str, nota: str = "") -> None:
    """Deja constancia (fuente, URL, fecha, sha256) de cada archivo crudo -> reproducibilidad."""
    fila = pd.DataFrame([{
        "archivo": str(archivo.relative_to(RAIZ)), "fuente": fuente, "url": url,
        "fecha_registro": date.today().isoformat(), "sha256": sha256(archivo), "nota": nota,
    }])
    if manifiesto.exists():
        previo = pd.read_csv(manifiesto)
        fila = pd.concat([previo[previo["archivo"] != fila.loc[0, "archivo"]], fila])
    manifiesto.parent.mkdir(parents=True, exist_ok=True)
    fila.to_csv(manifiesto, index=False)


def resumen_faltantes(df: pd.DataFrame, dataset: str) -> pd.DataFrame:
    """Una fila por columna: cuántos valores faltan y qué porcentaje."""
    n = len(df)
    out = pd.DataFrame({
        "dataset": dataset,
        "columna": df.columns,
        "n_filas": n,
        "n_faltantes": df.isna().sum().values,
    })
    out["pct_faltantes"] = (100 * out["n_faltantes"] / max(n, 1)).round(2)
    return out


def fila_dataset_ausente(dataset: str, motivo: str) -> pd.DataFrame:
    """Para la tabla de faltantes: deja constancia de que un dataset completo no está disponible."""
    return pd.DataFrame([{"dataset": dataset, "columna": "(dataset completo)", "n_filas": 0,
                          "n_faltantes": np.nan, "pct_faltantes": np.nan, "motivo": motivo}])
