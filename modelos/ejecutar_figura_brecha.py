"""Figura 9: baterías retiradas en 2035 por destino en las 10 entidades con más toneladas, frente a la capacidad
autorizada de reciclaje de litio (SEMARNAT).

Uso:  python -m modelos.ejecutar_figura_brecha   (después de ejecutar_brecha_reciclaje)
Salida: resultados/figuras/9_brecha_reciclaje_estatal.png
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from modelos.ejecutar_figuras import AQUA, AZUL, FONDO, GRIS, NARANJA, REJILLA, TINTA, TINTA2

RAIZ = Path(__file__).resolve().parents[1]
CORTOS = {"México": "Estado de México", "Coahuila de Zaragoza": "Coahuila", "Michoacán de Ocampo": "Michoacán",
          "Veracruz de Ignacio de la Llave": "Veracruz"}


def main() -> None:
    b = pd.read_csv(RAIZ / "resultados/brecha/brecha_entidad.csv")
    d = b[b["anio"] == 2035].nlargest(10, "toneladas_p50").iloc[::-1]
    nombres = [CORTOS.get(e, e) for e in d["entidad"]]
    fig, ax = plt.subplots(figsize=(8.4, 5.2), facecolor=FONDO)
    ax.set_facecolor(FONDO)
    izq = 0
    for col, color, etiqueta in [("toneladas_sale_por_vehiculo_soh_mayor_80", AZUL, "Sale con SoH > 80 % (fin del auto)"),
                                 ("toneladas_segunda_vida_80_70", AQUA, "Segunda vida (SoH 80-70 %)"),
                                 ("toneladas_reciclaje_directo", NARANJA, "Reciclaje directo (incluye HEV)")]:
        ax.barh(nombres, d[col], left=izq, color=color, label=etiqueta, height=0.62)
        izq = izq + d[col].to_numpy()
    for y, (tot, cap, n_aco) in enumerate(zip(d["toneladas_p50"], d["cap_reciclaje_litio"], d["n_acopio_litio"])):
        ax.text(tot + 40, y, f"{tot:,.0f} t · reciclaje Li autorizado: {cap:,.0f} t · acopio Li: {int(n_aco)}",
                va="center", fontsize=8, color=TINTA2)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    for s in ["left", "bottom"]:
        ax.spines[s].set_color(REJILLA)
    ax.tick_params(colors=TINTA2, labelsize=9)
    ax.grid(axis="x", color=REJILLA, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_xlim(0, d["toneladas_p50"].max() * 1.9)
    ax.set_xlabel("toneladas retiradas en 2035 (escenario base, mediana)", color=TINTA2, fontsize=9)
    ax.set_title("Ninguna entidad tiene reciclaje de litio autorizado (2035)",
                 loc="left", fontsize=12, color=TINTA, fontweight="bold", pad=22)
    ax.text(0, 1.02, "Fuente: modelo del repo (fase 3 y segunda vida) y directorios SEMARNAT de empresas autorizadas",
            transform=ax.transAxes, fontsize=8.5, color=GRIS)
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    fig.tight_layout()
    salida = RAIZ / "resultados/figuras/9_brecha_reciclaje_estatal.png"
    fig.savefig(salida, dpi=200, facecolor=FONDO)
    print("guardada", salida.relative_to(RAIZ))


if __name__ == "__main__":
    main()
