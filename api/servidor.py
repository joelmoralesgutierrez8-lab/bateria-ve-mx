"""API de solo lectura con los resultados del proyecto (JSON). Solo biblioteca estándar + pandas.

Uso, desde la raíz del proyecto:
    python -m api.servidor                 # escucha en 0.0.0.0:8000 (accesible desde tu hotspot)
    python -m api.servidor --local         # solo esta computadora (127.0.0.1)
    python -m api.servidor --puerto 8080

Rutas:  /  /resumen  /retiros  /ventas  /vida-flota  /co2  /escenarios-red  /sobol  /ndvi  /figuras/<archivo.png>
Filtros: /retiros?anio=2035&escenario=base&tipo=BEV   /vida-flota?entidad=Yucatán   (se pueden combinar)
Es solo lectura: sirve únicamente los archivos de resultados/ de la lista blanca de abajo.
"""
from __future__ import annotations

import argparse
import json
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
RES = RAIZ / "resultados"

# ruta -> (archivo, columnas por las que se puede filtrar)
TABLAS = {
    "/retiros": ("fase3/retiros_eol_anual.csv", ["escenario", "tipo", "anio"]),
    "/ventas": ("fase3/ventas_proyeccion_anual.csv", ["escenario", "tipo", "anio"]),
    "/vida-flota": ("fase3/vida_flota_entidad.csv", ["entidad", "tipo"]),
    "/co2": ("fase6/co2_monte_carlo_resumen.csv", ["variable"]),
    "/escenarios-red": ("fase6/escenarios_red.csv", []),
    "/sobol": ("fase6/sobol_indices.csv", ["entrada"]),
    "/ndvi": ("fase7/ndvi_tendencias.csv", ["zona"]),
}
LIMITE_FILAS = 2000


def _leer(archivo: str) -> pd.DataFrame:
    return pd.read_csv(RES / archivo)


def _json(df: pd.DataFrame) -> list:
    return json.loads(df.to_json(orient="records", force_ascii=False))


def resumen() -> dict:
    mc = _leer("fase6/co2_monte_carlo_resumen.csv").set_index("variable")
    re = _leer("fase3/retiros_eol_anual.csv")
    base = re[re.escenario == "base"]
    toneladas = {int(a): round(float(base[base.anio == a].toneladas_p50.sum()), 1) for a in (2025, 2030, 2035, 2040)}
    return {
        "proyecto": "Baterías de vehículos eléctricos en México, 2016-2040",
        "co2_g_km": {"electrico_p50": round(float(mc.loc["bev_g_km", "p50"]), 1),
                     "gasolina_p50": round(float(mc.loc["gas_g_km", "p50"]), 1),
                     "reduccion_pct_p50": round(float(mc.loc["reduccion_pct", "p50"]), 1),
                     "reduccion_pct_ic90": [round(float(mc.loc["reduccion_pct", "p5"]), 1),
                                            round(float(mc.loc["reduccion_pct", "p95"]), 1)]},
        "prob_electrico_mas_limpio": float(mc.loc["prob_bev_mas_limpio", "p50"]),
        "equilibrio_km_p50": round(float(mc.loc["equilibrio_km", "p50"])),
        "toneladas_retiradas_base_p50": toneladas,
        "nota": "Escenarios con bandas de incertidumbre, no pronósticos puntuales. Ver README.",
    }


def tabla(ruta: str, consulta: dict) -> list:
    archivo, filtros = TABLAS[ruta]
    df = _leer(archivo)
    for col in filtros:
        if col in consulta:
            val = consulta[col][0]
            df = df[df[col].astype(str).str.lower() == val.lower()]
    return _json(df.head(LIMITE_FILAS))


class Manejador(BaseHTTPRequestHandler):
    def _enviar(self, codigo: int, cuerpo: bytes, tipo: str = "application/json; charset=utf-8") -> None:
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(cuerpo)

    def _datos(self, codigo: int, obj) -> None:
        self._enviar(codigo, json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def do_GET(self) -> None:                                   # noqa: N802
        u = urlparse(self.path)
        ruta, consulta = u.path.rstrip("/") or "/", parse_qs(u.query)
        try:
            if ruta == "/":
                self._datos(200, {"rutas": ["/resumen", *TABLAS, "/figuras/<archivo.png>"],
                                  "filtros": {r: f for r, (_, f) in TABLAS.items() if f}})
            elif ruta == "/resumen":
                self._datos(200, resumen())
            elif ruta in TABLAS:
                self._datos(200, tabla(ruta, consulta))
            elif ruta.startswith("/figuras/"):
                nombre = Path(unquote(ruta[len("/figuras/"):])).name          # .name evita ../
                f = RES / "figuras" / nombre
                if f.suffix == ".png" and f.is_file():
                    self._enviar(200, f.read_bytes(), "image/png")
                else:
                    self._datos(404, {"error": "figura no encontrada"})
            else:
                self._datos(404, {"error": "ruta no encontrada", "ayuda": "GET /"})
        except FileNotFoundError:
            self._datos(404, {"error": "faltan resultados; corre primero los ejecutores (ver README)"})
        except Exception as e:                                   # noqa: BLE001
            self._datos(500, {"error": type(e).__name__})

    def log_message(self, fmt, *args) -> None:                   # un renglón por petición
        print(f"{self.address_string()} {fmt % args}")


def ip_local() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))                         # no envía nada; solo elige la interfaz
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--puerto", type=int, default=8000)
    ap.add_argument("--local", action="store_true", help="solo esta computadora")
    a = ap.parse_args()
    host = "127.0.0.1" if a.local else "0.0.0.0"
    srv = ThreadingHTTPServer((host, a.puerto), Manejador)
    print(f"API lista. En esta PC:        http://127.0.0.1:{a.puerto}/resumen")
    if not a.local:
        print(f"Desde otro equipo (hotspot): http://{ip_local()}:{a.puerto}/resumen")
    print("Ctrl+C para detener.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nDetenida.")


if __name__ == "__main__":
    main()
