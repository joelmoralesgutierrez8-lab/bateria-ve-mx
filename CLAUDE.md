# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A collaborative (team) IPN project analyzing the **recycling system for electric-vehicle batteries in Mexico**,
2016–2040. The central question is how many batteries leave vehicles, when and where, and what that implies for
recycling and second-life capacity; the rest of the pipeline supports it: battery lifetime (Weibull), sales
projections, retired-battery flows by state, SoH neural net, CO₂e per km (Monte Carlo + Sobol), and "who pays"
(grid scenarios, NDVI near mines). Keep in mind that leaving the vehicle ≠ arriving at recycling (second life,
SoH 80% → 70% → recycling thresholds in `config_fase3.yaml`). Code, identifiers, comments, config keys, and outputs
are all in **Spanish** — keep new code consistent with that.

## Commands

All commands run from this directory (the repo root) as modules (`python -m ...`) — imports are package-relative
(`from etl.utils import ...`, `from modelos.vida_util import ...`), so running files directly breaks.
Windows / PowerShell; set `$env:PYTHONIOENCODING = "utf-8"` if console output with accents fails.

```powershell
.venv\Scripts\activate
pip install -r requirements.txt          # core ETL; phases 4/8 also need statsmodels, lightgbm, torch, matplotlib
                                         # NDVI download needs requirements-stac.txt

python -m unittest discover -s tests                              # all tests (unittest, not pytest)
python -m unittest tests.test_weibull                             # one file
python -m unittest tests.test_weibull.TestDistribucion.test_cdf_y_cuantil_son_inversas   # one test
```

Pipeline (order matters — later steps read CSV/NPZ outputs of earlier ones):

```powershell
python -m herramientas.descargar_fuentes todo   # download raw sources (inegi|capitales|nasa|calce|oxford|usgs|todo)
python -m etl.descargas power|vegetacion|verificar   # NASA POWER, Landsat NDVI, sha256 check of manual files
python -m etl.ejecutar_etl                      # raw -> datos/procesado/, missing-data table, data fichas

python -m modelos.ejecutar_vida_util            # -> resultados/fase3/ eol_celdas, weibull_*
python -m modelos.ejecutar_vida_flota           # needs vida_util  -> vida_flota_entidad.csv
python -m modelos.ejecutar_ventas               # -> ventas_simulaciones.npz, ventas_proyeccion_anual.csv
python -m modelos.ejecutar_flujo_eol            # needs vida_flota + ventas -> retiros_eol_*.csv
python -m modelos.ejecutar_series               # fase4
python -m modelos.ejecutar_soh                  # fase5
python -m modelos.ejecutar_riesgo               # fase6
python -m modelos.ejecutar_etica                # fase7
python -m modelos.ejecutar_figuras              # resultados/figuras/*.png
python -m modelos.generar_extenso               # docs/extenso_bateria_ve_mx.html (single self-contained file)
python -m modelos.generar_api_estatica          # api-estatica/*.json
python -m api.servidor [--local] [--puerto N]   # optional local read-only JSON API over resultados/
```

`herramientas/ejecutar_todo.bat` runs downloads + ETL + tests and logs to `herramientas/log_corrida.txt`.

## Architecture

- **Two config files.** `config/config.yaml` drives the ETL (paths, source settings, seed). `modelos/config_fase3.yaml`
  drives every model phase despite its name (Weibull, fleet, sales scenarios, EOL flow, risk inputs). Every modeling
  assumption lives there with its source or tagged `SUPUESTO`; do not hard-code parameters in Python.
- **Paths are always relative to the repo root**, resolved via `RAIZ = Path(__file__).resolve().parents[1]`
  (or `etl.utils.ruta()`). Never use absolute paths or cwd-relative paths.
- **Seeds:** ETL uses `etl.utils.fijar_semilla`; models use `modelos.comun.semillas.fijar_semillas(42)`, which also
  seeds torch and returns an `np.random.Generator` that should be passed explicitly (prefer it over global state).
- **ETL (`etl/`)**: `limpieza.py` holds the per-source cleaners; `ejecutar_etl.py` orchestrates. A missing or broken
  raw dataset is recorded as `AUSENTE`/`ERROR` in `datos/procesado/tabla_datos_faltantes.*` instead of failing the run.
  Data fichas (`datos/fichas/*.md`) are generated from `config/fichas.yaml`. Every raw file is registered with
  URL/date/sha256 in `datos/manifiesto_descargas.csv` via `registrar_descarga`.
- **Models (`modelos/`)**: `ejecutar_*.py` are thin per-phase entry points; the math lives in subpackages
  (`vida_util/` Weibull MLE with censoring + Arrhenius fleet scaling, `ventas/` S-curve + short-term models,
  `flujo_eol/` cohort convolution, `soh/` NumPy MLP, `riesgo/` life-cycle CO₂ + Sobol). Phases communicate only
  through files in `resultados/faseN/`.
- **Deliverables are generated, never hand-edited:** `docs/extenso_bateria_ve_mx.html` (from
  `docs/plantilla_extenso.html` + results, with figures and KaTeX embedded) and `api-estatica/*.json`. After changing
  any result, rerun the downstream executors, then `generar_extenso` and `generar_api_estatica`.
  `index.html` + `api-estatica/` are served as a static site (GitHub Pages / raw.githack); `.nojekyll` must stay.

## Project rules (from README)

- No invented data: every number traces to a source file or a documented, ranged assumption.
- Report uncertainty intervals for every result; when a simple model beats a complex one, say so.
- Raw/processed data, `*.mat`, `*.npz`, zips are gitignored (reproduced by the download + ETL steps); only
  `factores_emision_por_tecnologia.csv` and `parametros_ciclo_vida.csv` under `datos/crudo/` are tracked.
- `_to_delete/` holds superseded backups — not part of the pipeline; don't import from or edit it.
