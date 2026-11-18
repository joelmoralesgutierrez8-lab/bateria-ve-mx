# Ficha de dataset: GREET (R&D GREET 1/2) y BatPaC, Argonne National Laboratory

- **Fuente oficial:** https://greet.anl.gov  |  https://www.anl.gov/cse/batpac-model-software
- **Origen geográfico:** Modelos con supuestos estadounidenses (mezcla eléctrica, cadenas de suministro, tecnologías)
- **Clima / condiciones:** No aplica
- **Periodo nominal:** Versión anual del modelo (anota la versión usada en cada fila)
- **Variables:** Parámetros de ciclo de vida (emisiones y energía de fabricación/reciclaje) y diseño/costo de baterías
- **Licencia:** GREET gratuito con registro y términos de uso (citar a Argonne; publicar resultados indicando que GREET fue desarrollado por Argonne). BatPaC de libre descarga en hoja de cálculo.
- **Estado del procesamiento:** 4 filas procesadas. Columnas con faltantes (%): celda 100.0%.

## Sesgos y limitaciones conocidos
- Valores por defecto basados en EE. UU.: hay que sustituir la mezcla eléctrica por la mexicana donde sea posible.
- GREET se ejecuta en Excel/.NET sobre Windows: no hay descarga automática ni API; la extracción es manual y trazable.
- Argonne advierte que no todas las rutas de R&D GREET sirven cuando se exige alta precisión cuantitativa.
- Los valores de parametros_ciclo_vida.csv NO salen de correr GREET: son cifras publicadas (Kelly, Dai y Wang 2020 con GREET2018; Llamas-Orozco et al. 2023, LCA propio). Ninguna refleja producción mexicana; México importa baterías, sobre todo de cadenas asiáticas (supuesto a documentar). Las cifras de Llamas-Orozco vienen de fuente secundaria y deben verificarse.
