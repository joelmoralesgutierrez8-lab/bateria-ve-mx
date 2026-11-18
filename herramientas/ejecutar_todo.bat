@echo off
REM Corre todas las descargas, el ETL y las pruebas. Bitacora en herramientas\log_corrida.txt
cd /d "%~dp0.."
set LOG=herramientas\log_corrida.txt
set PYTHONIOENCODING=utf-8
echo ==== INICIO %date% %time% > %LOG%
call .venv\Scripts\activate.bat
echo ==== [1/8] descargas auxiliares (INEGI, capitales, NASA, CALCE, Oxford, USGS) >> %LOG%
python -m herramientas.descargar_fuentes todo >> %LOG% 2>&1
echo ==== [2/8] NASA POWER >> %LOG%
python -m etl.descargas power >> %LOG% 2>&1
echo ==== [3/8] verificar >> %LOG%
python -m etl.descargas verificar >> %LOG% 2>&1
echo ==== [4/8] ETL >> %LOG%
python -m etl.ejecutar_etl >> %LOG% 2>&1
echo ==== [5/8] pruebas >> %LOG%
python -m unittest discover -s tests -v >> %LOG% 2>&1
echo ==== [6/8] instalar dependencias de NDVI >> %LOG%
python -m pip install -r requirements-stac.txt >> %LOG% 2>&1
echo ==== [7/8] NDVI Landsat >> %LOG%
python -m etl.descargas vegetacion >> %LOG% 2>&1
echo ==== [8/8] ETL final >> %LOG%
python -m etl.ejecutar_etl >> %LOG% 2>&1
echo ==== FIN %date% %time% >> %LOG%
