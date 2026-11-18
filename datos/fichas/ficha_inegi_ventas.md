# Ficha de dataset: Ventas de vehículos híbridos y eléctricos por entidad federativa (INEGI, RAIAVL)

- **Fuente oficial:** https://www.inegi.org.mx/app/tabulados/pxwebv2/pxweb/es/RAIAVL/RAIAVL/RAIAVL_11.px/
- **Origen geográfico:** México; desglose por entidad federativa (32 + "No especificado")
- **Clima / condiciones:** No aplica
- **Periodo nominal:** 2016 - 2026 (último mes publicado = el que detecta el ETL)
- **Variables:** Unidades eléctricas, híbridas enchufables e híbridas, por año, mes y entidad
- **Licencia:** INEGI: términos de libre uso de la información (por verificar texto vigente). El tabulado declara Copyright = No.
- **Estado del procesamiento:** 12,870 filas procesadas. Columnas con faltantes (%): unidades 0.9%. Periodo observado: 2016-01-01 a 2026-10-01.

## Sesgos y limitaciones conocidos
- Ventas de vehículos NUEVOS reportadas por unidades económicas del registro; no incluye autos usados importados (por verificar el alcance exacto en la ficha metodológica del RAIAVL).
- Un boletín de 2026 indica que una marca no entregó datos de ventas de un mes: el registro depende de que cada empresa reporte.
- Las cifras del último mes son revisadas y pueden cambiar; pasan a definitivas cada febrero (nota al pie del tabulado).
- Entidad = lugar de comercialización según el registro (por verificar); no necesariamente donde circula el vehículo.
- Híbridos (HEV) llevan baterías mucho más pequeñas que BEV/PHEV: no sumar unidades como si fueran equivalentes.
- El tabulado no trae capacidad de batería (kWh) ni química: hay que cruzarlo con fichas de modelos.
