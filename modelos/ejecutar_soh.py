"""Fase 5: red neuronal para predecir el SoH futuro y prueba de transferencia a temperatura alta.

Uso: python -m modelos.ejecutar_soh
Experimentos:
  A. Dentro de cada conjunto (CALCE, NASA 24 °C, Oxford): validación dejando una celda fuera
     (leave-one-cell-out, equivalente a GroupKFold con un grupo por celda): nunca hay mediciones de la celda
     de prueba en el entrenamiento.
  B. Transferencia por temperatura (NASA): entrena con las celdas a 24 °C y prueba con las de 43 °C.
Modelos: persistencia (el SoH no cambia), extrapolación lineal de la ventana y ensamble de 5 MLP (NumPy).
Salidas en resultados/fase5/: soh_validacion.csv (RMSE y MAE del SoH a h pasos) y soh_transferencia.csv.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from modelos.comun.semillas import fijar_semillas
from modelos.soh.datos import base_lineal, base_persistencia, curvas, ventanas
from modelos.soh.red import Ensamble

RAIZ = Path(__file__).resolve().parents[1]

# ventana (mediciones), horizonte h (mediciones), submuestreo y largo de referencia por conjunto
EXPERIMENTOS = {
    "calce": {"ventana": 10, "h": 10, "paso": 5, "largo_ref": 200},       # paso 5 ciclos -> h = 50 ciclos
    "nasa_pcoe": {"ventana": 10, "h": 5, "paso": 1, "largo_ref": 150},    # h = 5 ciclos
    "oxford": {"ventana": 8, "h": 5, "paso": 1, "largo_ref": 70},         # h = 500 ciclos de manejo
}


def metricas(real, pred):
    e = pred - real
    return {"rmse_soh_pp": float(np.sqrt(np.mean(e**2)) * 100), "mae_soh_pp": float(np.mean(np.abs(e)) * 100)}


def evaluar(X, y, ult, Xp, yp, ultp, e, semilla, epocas):
    """Devuelve métricas (en puntos porcentuales de SoH) de los tres modelos y la cobertura del ensamble."""
    ens = Ensamble(X.shape[1], miembros=5, semilla=semilla, epocas=epocas).fit(X, y)
    media, sd = ens.predict(Xp)
    real = ultp + yp
    out = {}
    for nombre, d in {"persistencia": base_persistencia(Xp, e["ventana"]),
                      "lineal": base_lineal(Xp, e["ventana"], e["h"]), "mlp_ensamble": media}.items():
        out[nombre] = metricas(real, ultp + d)
    out["mlp_ensamble"]["cobertura_2sd"] = float(np.mean(np.abs((ultp + media) - real) <= 2 * sd + 1e-12))
    return out


def main() -> None:
    cfg = yaml.safe_load(open(RAIZ / "modelos" / "config_fase3.yaml", encoding="utf-8"))
    semilla = cfg["semilla"]
    fijar_semillas(semilla)
    salida = RAIZ / "resultados" / "fase5"
    salida.mkdir(parents=True, exist_ok=True)
    eol = pd.read_csv(RAIZ / cfg["salidas"]["carpeta"] / "eol_celdas.csv")

    filas = []
    for conj, e in EXPERIMENTOS.items():
        df = pd.read_csv(RAIZ / cfg["conjuntos"][conj]["archivo"])
        celdas = eol[(eol.conjunto == conj) & eol.incluida].celda.tolist()
        if conj == "nasa_pcoe":
            celdas = [c for c in celdas if c in ("B0005", "B0006", "B0007", "B0018")]   # 24 °C, curvas largas
        cur = curvas(df, cfg["deteccion_eol"], celdas, e["paso"], cfg["conjuntos"][conj].get("temperatura_c", 25))
        X, y, g, ult = ventanas(cur, e["ventana"], e["h"], e["largo_ref"])
        for c in celdas:                                              # dejar una celda fuera
            tr, te = g != c, g == c
            if te.sum() == 0:
                continue
            res = evaluar(X[tr], y[tr], ult[tr], X[te], y[te], ult[te], e, semilla, epocas=400)
            for modelo, m in res.items():
                filas.append({"conjunto": conj, "celda_prueba": c, "modelo": modelo, "n_prueba": int(te.sum()), **m})
    val = pd.DataFrame(filas)
    val.to_csv(salida / "soh_validacion.csv", index=False)
    resumen = val.groupby(["conjunto", "modelo"])[["rmse_soh_pp", "mae_soh_pp"]].mean()
    print("A. Dejando una celda fuera (error del SoH a h pasos, en puntos porcentuales):")
    print(resumen.round(3).to_string())
    print("\nCobertura del ensamble (+-2 desv. est.):")
    print(val[val.modelo == "mlp_ensamble"].groupby("conjunto")["cobertura_2sd"].mean().round(3).to_string())

    # ---------- B. Transferencia por temperatura (NASA 24 °C -> 43 °C)
    e = {"ventana": 10, "h": 5, "paso": 1, "largo_ref": 150}
    df = pd.read_csv(RAIZ / cfg["conjuntos"]["nasa_pcoe"]["archivo"])
    fria = curvas(df, cfg["deteccion_eol"], ["B0005", "B0006", "B0007", "B0018"])
    caliente = curvas(df, cfg["deteccion_eol"], ["B0029", "B0030", "B0031", "B0032"])
    X, y, _, ult = ventanas(fria, e["ventana"], e["h"], e["largo_ref"])
    Xc, yc, _, ultc = ventanas(caliente, e["ventana"], e["h"], e["largo_ref"])
    tr = evaluar(X, y, ult, Xc, yc, ultc, e, semilla, epocas=400)
    trans = pd.DataFrame([{"entrena": "NASA 24 °C", "prueba": "NASA 43 °C", "modelo": k, "n_prueba": len(yc), **v}
                          for k, v in tr.items()])
    trans.to_csv(salida / "soh_transferencia.csv", index=False)
    print("\nB. Transferencia: entrena a 24 °C, prueba a 43 °C (puntos porcentuales de SoH):")
    print(trans.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
