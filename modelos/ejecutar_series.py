"""Fase 4: diagnóstico de las series de ventas y pronóstico de 12 meses con el modelo ganador.

Uso: python -m modelos.ejecutar_series     (requiere statsmodels; usa la validación del paso 3)
Salidas en resultados/fase4/:
  diagnosticos.csv              por tipo: fuerza de tendencia y estacionalidad (STL), ADF y KPSS en log y
                                en diferencia log, Ljung-Box de los residuos del SARIMA elegido
  cobertura_intervalos.csv      % de valores reales dentro del intervalo de 90% del SARIMA (origen móvil)
  pronostico_12_meses.csv       pronóstico mensual del modelo ganador por tipo, con intervalo de 90%
Lectura:
  ADF: H0 = raíz unitaria (no estacionaria). KPSS: H0 = estacionaria. Ambas en log suelen decir "no
  estacionaria" y en diferencia "estacionaria": eso justifica d = 1 en SARIMA.
  Ljung-Box: H0 = residuos sin autocorrelación; p > 0.05 indica que el modelo capturó la dinámica.
  Cobertura: si el intervalo de 90% cubre mucho menos del 90%, el modelo subestima su incertidumbre.
"""
from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from modelos.comun.semillas import fijar_semillas
from modelos.ventas import corto_plazo as CP
from modelos.ventas.preparar import TIPOS, serie_nacional_mensual

RAIZ = Path(__file__).resolve().parents[1]
ORDENES = [((0, 1, 1), (0, 1, 1, 12)), ((1, 1, 0), (0, 1, 1, 12)), ((1, 1, 1), (0, 1, 1, 12)),
           ((0, 1, 2), (0, 1, 1, 12)), ((0, 1, 1), (0, 0, 0, 12)), ((1, 1, 1), (0, 0, 0, 12))]


def sarima_mejor(l: pd.Series):
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    mejor, aic = None, np.inf
    for o, s in ORDENES:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                r = SARIMAX(l, order=o, seasonal_order=s, enforce_stationarity=False,
                            enforce_invertibility=False).fit(disp=False)
            except Exception:
                continue
        if r.aic < aic:
            mejor, aic = r, r.aic
    return mejor


def diagnostico(y: pd.Series) -> dict:
    from statsmodels.stats.diagnostic import acorr_ljungbox
    from statsmodels.tsa.seasonal import STL
    from statsmodels.tsa.stattools import adfuller, kpss

    l = np.log1p(y)
    stl = STL(l, period=12, robust=True).fit()
    var_r = np.var(stl.resid)
    fuerza_t = max(0.0, 1 - var_r / np.var(stl.trend + stl.resid))
    fuerza_s = max(0.0, 1 - var_r / np.var(stl.seasonal + stl.resid))
    d = l.diff().dropna()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = {"fuerza_tendencia_stl": fuerza_t, "fuerza_estacional_stl": fuerza_s,
               "adf_p_log": adfuller(l, autolag="AIC")[1], "kpss_p_log": kpss(l, nlags="auto")[1],
               "adf_p_dif": adfuller(d, autolag="AIC")[1], "kpss_p_dif": kpss(d, nlags="auto")[1]}
    r = sarima_mejor(l)
    lb = acorr_ljungbox(r.resid[13:], lags=[12], return_df=True)
    out.update(sarima_orden=str(r.model.order), sarima_estacional=str(r.model.seasonal_order),
               sarima_aic=r.aic, ljungbox_p_lag12=float(lb["lb_pvalue"].iloc[0]))
    return out


def cobertura_sarima(y: pd.Series, origenes: int, h: int, nivel: float = 0.90) -> dict:
    dentro, total, n = 0, 0, len(y)
    for o in range(n - origenes, n):
        real = y.iloc[o : o + h].to_numpy()
        if len(real) == 0:
            continue
        r = sarima_mejor(np.log1p(y.iloc[:o]))
        ic = np.expm1(np.asarray(r.get_forecast(len(real)).conf_int(alpha=1 - nivel)))
        dentro += int(((real >= ic[:, 0]) & (real <= ic[:, 1])).sum())
        total += len(real)
    return {"nivel_nominal": nivel, "cobertura_observada": dentro / total, "n": total}


def pronostico(y: pd.Series, modelo: str, h: int, semilla: int, nivel: float = 0.90) -> pd.DataFrame:
    """Pronóstico puntual del modelo ganador. El intervalo viene del SARIMA (el único con intervalo
    analítico); si el ganador no es SARIMA, se centra el ancho relativo del SARIMA en su pronóstico."""
    l = np.log1p(y)
    r = sarima_mejor(l)
    f = r.get_forecast(h)
    media_s = np.asarray(f.predicted_mean)
    ic = np.asarray(f.conf_int(alpha=1 - nivel))
    punto = np.log1p(np.asarray(CP.MODELOS[modelo](y, h, semilla)))
    bajo, alto = punto - (media_s - ic[:, 0]), punto + (ic[:, 1] - media_s)
    fechas = pd.date_range(y.index[-1] + pd.offsets.MonthBegin(1), periods=h, freq="MS")
    return pd.DataFrame({"fecha": fechas, "modelo": modelo, "pronostico": np.expm1(punto),
                         "ic90_bajo": np.expm1(bajo), "ic90_alto": np.expm1(alto)})


def main() -> None:
    cfg_total = yaml.safe_load(open(RAIZ / "modelos" / "config_fase3.yaml", encoding="utf-8"))
    cfg = cfg_total["ventas"]["validacion"]
    semilla = cfg_total["semilla"]
    fijar_semillas(semilla)
    salida = RAIZ / "resultados" / "fase4"
    salida.mkdir(parents=True, exist_ok=True)

    mensual = serie_nacional_mensual(pd.read_csv(RAIZ / "datos" / "procesado" / "inegi_ventas_entidad_mes.csv"))
    val = pd.read_csv(RAIZ / cfg_total["salidas"]["carpeta"] / "ventas_validacion_corto_plazo.csv")
    ganador = val.sort_values("MASE").groupby("tipo").first()["modelo"].to_dict()

    diag, cob, pron = [], [], []
    for t in TIPOS:
        diag.append({"tipo": t, **diagnostico(mensual[t])})
        cob.append({"tipo": t, **cobertura_sarima(mensual[t], cfg["origenes"], cfg["horizonte_meses"])})
        pron.append(pronostico(mensual[t], ganador[t], cfg["horizonte_meses"], semilla).assign(tipo=t))
    diag, cob, pron = pd.DataFrame(diag), pd.DataFrame(cob), pd.concat(pron)
    diag.to_csv(salida / "diagnosticos.csv", index=False)
    cob.to_csv(salida / "cobertura_intervalos.csv", index=False)
    pron.to_csv(salida / "pronostico_12_meses.csv", index=False)

    print("Diagnósticos (p-valores; ADF H0 = no estacionaria, KPSS H0 = estacionaria):")
    print(diag.round(3).to_string(index=False))
    print("\nCobertura del intervalo de 90% del SARIMA en el origen móvil:")
    print(cob.round(3).to_string(index=False))
    print("\nPronóstico de 12 meses (modelo ganador por tipo). Suma de los 12 meses; las columnas ic90 suman")
    print("los límites mensuales, así que son una banda conservadora, no el intervalo exacto del total:")
    print(pron.groupby(["tipo", "modelo"])[["pronostico", "ic90_bajo", "ic90_alto"]].sum().round(0).to_string())


if __name__ == "__main__":
    main()
