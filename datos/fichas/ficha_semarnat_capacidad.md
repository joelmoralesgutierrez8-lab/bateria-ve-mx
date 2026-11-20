# Ficha de dataset: Directorios de empresas autorizadas para el manejo de residuos peligrosos, Rubros 1-14 (SEMARNAT, DGGIMAR), y tablas del Compendio DGEIA

- **Fuente oficial:** Directorios DGGIMAR (CSV, descarga manual nov 2026) y https://apps1.semarnat.gob.mx:8443/dgeia/compendio_2021/archivos/01_residuosp/d3_residuop01_05_d.pdf
- **Origen geográfico:** México; desglose por entidad federativa y modalidad (reciclaje, acopio, tratamiento, etc.)
- **Clima / condiciones:** No aplica
- **Periodo nominal:** Series anuales del Compendio DGEIA (último consultado: edición 2021); el Inventario Nacional de Residuos Peligrosos actualizado a 2025 está anunciado pero sin enlace de descarga localizado (por verificar)
- **Variables:** Número de autorizaciones, número de plantas, capacidad instalada autorizada (toneladas/año) por entidad, modalidad y año
- **Licencia:** Información pública de SEMARNAT (por verificar términos de uso)
- **Estado del procesamiento:** 937 filas procesadas. Columnas con faltantes (%): capacidad_t_anio 1.0%, municipio 0.1%, clave_entidad 0.1%, vigencia_inicio 0.1%, vigencia_termino 0.1%.

## Sesgos y limitaciones conocidos
- Capacidad AUTORIZADA, no volumen procesado: SEMARNAT advierte que las plantas no siempre operan a su capacidad total.
- Es capacidad para residuos peligrosos en general; no hay desglose para baterías de litio. La brecha calculada será una cota superior de la capacidad disponible.
- Las empresas autorizadas pueden atender residuos de todo el país, no solo de su entidad.
- Las baterías de litio suelen clasificarse como residuo de manejo especial (LGPGIR art. 19, NOM-161), cuyo manejo autorizan sobre todo las entidades federativas; ese canal no aparece en esta tabla.
- Clasificación de baterías de litio por texto libre (etl/semarnat.py, función es_litio): revisar resultados/brecha/litio_autorizaciones.csv.
- Rubro 14 no indica si es importación o exportación; solo el país de destino u origen.
