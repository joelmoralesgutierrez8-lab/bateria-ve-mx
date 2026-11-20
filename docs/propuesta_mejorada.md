# Gestión inteligente de baterías de VE e híbridos en México

**Fecha:** 19 nov 2026 · **Integrante:** Joel Morales Gutierrez
**Título:** *¿Adónde van las baterías? Trazabilidad y gestión inteligente del fin de vida de baterías de VE e híbridos en México, 2016–2035*

> Las cifras salen de `resultados/` (escenario base, mediana P50; banda P5–P95 cuando se indica). Son escenarios, no
> pronósticos puntuales: en México no existen datos públicos de baterías retiradas. El repositorio proyecta hasta 2040;
> **2035 es el corte de este documento** y 2040 se cita solo como horizonte.

**En tres frases.** Entre 2026 y 2035 saldrán de los vehículos en México unas 400 mil baterías (39 mil t), y en 2035
serán 11,356 t al año, concentradas en CDMX, Estado de México, Jalisco y Nuevo León. Hoy el país tiene **0 t/año de
reciclaje autorizado para baterías de litio** y ninguna norma específica que obligue a registrarlas o a medir su salud.
Más de la mitad del peso podría reutilizarse antes de reciclarse, pero sin trazabilidad no hay forma de saber cuál.

## Línea temática y contexto

| Elemento | Definición |
|---|---|
| Línea de sustentabilidad | 2. Gestión inteligente de baterías (VE / híbridos) |
| Lugar | México, nivel nacional, con desglose por las 32 entidades |
| Periodo observado | 2016–2025 (INEGI RAIAVL: primer año con ventas por entidad y último año completo) |
| Periodo de proyección | 2026–2035 (horizonte del repositorio: 2040) |
| Baterías | Ion-litio y NiMH de tracción (BEV, PHEV, HEV); plomo-ácido solo como referencia del canal de acopio actual |
| Metodología | DMAIC (Six Sigma) |

**Por qué ahora.** Las ventas de híbridos y eléctricos pasaron de 8,265 unidades en 2016 a **149,031 en 2025**
(22,208 BEV, 13,722 PHEV y 113,101 HEV; INEGI, RAIAVL, datos abiertos con cifras revisadas a octubre de 2026,
`datos/crudo/inegi/conjunto_de_datos_raiavl_mensual_hibrido_csv.zip`). Según el modelo, las bajas pasan de unas 6 mil
baterías en 2026 a 103 mil en 2035 (banda 90 %: 90–124 mil): 16 veces más en una década.

## 1. Descripción de la causa

**Problemática.** En México nadie puede decir cuántas baterías de VE e híbridos salen de los vehículos, en qué estado de
salud y adónde van.

- No hay registro público del estado de salud (SoH) ni del destino de estas baterías: los planes de manejo de residuos de
  manejo especial solo se presentan a los estados "para efectos de su conocimiento" (LGPGIR art. 33).
- Sin ese dato, unas baterías se retiran antes de tiempo y otras terminan en acopio sin destino o en canales informales.
- Una batería no reutilizada ni reciclada obliga a extraer más litio, níquel y cobalto; mal manejada puede incendiarse.

**Pregunta guía.** ¿Cuántas baterías llegarán al final de su vida en cada estado entre 2026 y 2035, en qué condición, y
existe capacidad autorizada para reutilizarlas o reciclarlas?

**Hipótesis y resultado**

| Hipótesis | Resultado |
|---|---|
| 1. Las bajas se concentran en pocas entidades | **Confirmada.** En 2035, CDMX 3,131 t, Estado de México 1,114 t, Jalisco 1,102 t y Nuevo León 1,031 t: 56 % del total |
| 2. En estados calurosos la batería dura menos | **Confirmada en el modelo.** BEV: 9.7 años en estados ≥ 24 °C frente a 15.8 años en el resto (Arrhenius) |
| 3. La capacidad de reciclaje autorizada es menor que las bajas | **Confirmada y más grave de lo previsto.** 0 t/año autorizadas para litio en las 32 entidades (SEMARNAT) |

## 2. Análisis de causa raíz

**Causa raíz:** falta de trazabilidad de la batería desde la venta hasta el desecho. (Diagrama de Ishikawa con seis
categorías: regulación, infraestructura, datos, economía, tecnología y sociedad.)

**5 porqués (con su fuente)**
1. ¿Por qué hay baterías sin destino claro? Porque no se sabe cuántas se retiran ni dónde.
2. ¿Por qué no se sabe? Porque no hay registro por batería ni por estado: los planes de manejo de residuos de manejo
   especial no se registran ante SEMARNAT (LGPGIR art. 33).
3. ¿Por qué no hay registro? Porque el litio está en una zona gris: es residuo de manejo especial (LGPGIR art. 19 IX;
   NOM-161, modificada en 2014) salvo que muestre características CRETIB (NOM-052), y no aparece en la lista de
   peligrosos con plan de manejo (LGPGIR art. 31, que sí nombra los acumuladores de plomo).
4. ¿Por qué no se ha corregido? Porque la infraestructura y las reglas se hicieron para plomo-ácido: hay 2.02 millones
   t/año de reciclaje autorizado para plomo y 0 para litio. La Ley General de Economía Circular (2026) creó la
   responsabilidad extendida del productor, pero sin acuerdo de implementación para baterías.
5. ¿Por qué sigue así? Porque sin datos no se ve el tamaño del problema ni hay presión para cambiar la norma.

> **Aporte del proyecto:** estimar ese tamaño con datos abiertos. Es la primera cuantificación abierta por estado.

## 3. Mapeo de la problemática

El punto crítico está después del acopio: nadie mide la salud, así que no se sabe si la batería va a segunda vida, a
reciclaje (fuera del país) o a un canal informal.

| Etapa | Quién participa | Dato disponible | Estado |
|---|---|---|---|
| Mina y fabricación | Proveedores extranjeros, armadoras | USGS (global) y GREET; 47 % de las emisiones del BEV ocurren al fabricarlo, casi siempre fuera de México | Parcial |
| Venta | Armadoras y agencias | INEGI RAIAVL por entidad y tipo | Cubierto |
| Uso | Particulares, flotillas, transporte | Temperatura por estado (NASA POWER); edad promedio del parque 16.2 años (IDF) | Parcial |
| Retiro y acopio | Refaccionarias, agencias, centros de acopio | SEMARNAT: 56 autorizaciones de acopio aceptan litio en 15 estados | Cubierto |
| Destino final | Recicladoras autorizadas, exportación, informal | SEMARNAT: 0 autorizaciones de reciclaje de litio; el reciclaje se hace en EE. UU. o Costa Rica; el canal informal no tiene datos | Cubierto (salvo informal) |

## 4. Línea temática: reto ambiental y aporte de ciencia de datos

| Reto ambiental | Aporte de ciencia de datos | Resultado |
|---|---|---|
| Se desconoce la salud y el destino de las baterías; el país no puede reciclarlas | Proyectar bajas por estado, estimar SoH, clasificar destino (reúso, segunda vida, reciclaje) y medir la brecha contra la capacidad autorizada | Bajas 2026–2035 por estado; KPI de segunda vida; reciclaje retrasado; brecha SEMARNAT; figura 9 |

**Destino de las 11,356 t retiradas en 2035**

| Destino | Toneladas | Criterio |
|---|---|---|
| Salen con SoH > 80 % porque el auto terminó su vida | 5,305 t | Modelo de flota (fase 3) |
| Segunda vida (SoH 80–70 %) | 4,711 t | Celdas de laboratorio aptas con margen ≥ 20 % |
| Reciclaje directo | 1,340 t | Híbridos (HEV): paquetes pequeños, diseñados para durar la vida del auto |
| **Aptas para reúso o segunda vida** | **88 %** (100 % sin contar HEV) | Con margen mínimo de 30 % baja a 81 % |

**Reciclaje retrasado.** La segunda vida no elimina el reciclaje, lo pospone 3–7 años. Si todas las aptas entraran a
segunda vida, el reciclaje necesario en 2035 bajaría de 11,356 t a 3,232 t (a 7,294 t con 50 % de adopción). En
2026–2035, la demanda acumulada de reciclaje bajaría de 39,223 t a 10,685 t; lo demás llega después de 2035.

## 5. Ficha analítica: auditoría de datasets (10 fuentes)

El sesgo principal: los datos de salud de batería vienen de laboratorios de EE. UU. y Reino Unido, no del clima ni del
manejo en México. Fichas completas en `datos/fichas/`; URL, fecha y SHA-256 en `datos/manifiesto_descargas.csv`.

| Fuente | Dataset | Uso | Limitación |
|---|---|---|---|
| INEGI | RAIAVL, ventas de híbridos y eléctricos por entidad | Entradas de baterías 2016–2025 | Subconteo: Chirey y Omoda dejaron de reportar en mayo de 2025 |
| SEMARNAT | Directorios de empresas autorizadas (Rubros 1–14) | Capacidad de reciclaje y acopio por estado | Es capacidad autorizada en papel, no toneladas realmente recicladas; clasificación de litio por texto libre |
| CENACE | Generación por tecnología | Intensidad de la red | Solo nacional; factores provisionales en 3 tecnologías |
| NASA PCoE | Battery Data Set | Vida útil y SoH | Celdas 18650; 12 usadas, 8 censuradas |
| CALCE (U. Maryland) | CS2 | Vida útil de referencia para la flota | Celdas de electrónica portátil |
| Oxford | Battery Degradation Dataset 1 | Manejo urbano | 8 celdas |
| NASA POWER | Temperatura mensual | Clima por estado | Reanálisis; suaviza picos de calor |
| USGS | Mineral Commodity Summaries 2026 | Minerales críticos | Nacional, anual |
| Landsat (Planetary Computer) | NDVI | Vegetación en zonas mineras | No prueba causalidad |
| GREET (Argonne) | Parámetros de ciclo de vida | Huella de fabricar la batería | Extracción manual |

Complemento: compilación de 7 actores de acopio, reúso y reciclaje de litio (`datos/crudo/plantas_litio/`).

## 6. Arquitectura de datos (pipeline)

Python reproducible: semilla 42, rutas relativas, SHA-256 por archivo, **47 pruebas unitarias**.

1. **Ingesta:** 10 fuentes con URL, fecha y SHA-256.
2. **Limpieza:** unificar unidades, entidades (claves INEGI) y años; tabla de faltantes; fichas por dataset.
3. **Modelos:**
   - Vida útil: Weibull con censura (MLE), bootstrap y Arrhenius de celda a flota por clima.
   - Ventas: curva S (Fisher–Pry) y modelos de corto plazo (SARIMA, LightGBM, LSTM) con validación de origen móvil.
   - Flujo: convolución de cohortes por entidad.
   - SoH: red neuronal MLP (ensamble) contra regresión lineal.
   - Riesgo: Monte Carlo (20,000) y Sobol (122,880 evaluaciones).
   - Línea 2: segunda vida, reciclaje retrasado y brecha contra SEMARNAT.
4. **Salidas:** 9 figuras, informe técnico HTML, API estática JSON.

**KPI**

| KPI | Valor |
|---|---|
| Baterías retiradas 2026 → 2035 | ~6 mil → ~103 mil (90–124 mil); 330 → 11,356 t |
| Acumulado 2026–2035 | ~400 mil baterías, 39,223 t |
| % apto para reúso o segunda vida (2035) | 88 % de las toneladas (100 % sin HEV) |
| Capacidad autorizada de reciclaje de litio | **0 t/año** (32 de 32 entidades en déficit) |
| Autorizaciones de acopio que aceptan litio | 56 en 15 estados |
| CO₂e por km, BEV vs. gasolina | 147 g vs. 276 g: 45 % menos (IC 90 %: 23–60 %) |
| Equilibrio de carbono de la batería | ~27 mil km (14–47 mil) |
| Error SoH fuera del rango de temperatura | RMSE 0.66 pp (lineal) vs. 1.16 pp (red) |

**Hallazgos honestos del modelado**
- **El modelo simple gana.** SARIMA supera a la LSTM en BEV (MASE 0.37) y HEV (0.29); de 24 a 43 °C, la regresión
  lineal supera a la red neuronal en SoH.
- **Sensibilidad al umbral de retiro.** Si las baterías se retiran al 70 % de SoH (límite de las garantías) en vez de
  80 %, las toneladas de 2035 bajan 16 % (9,499 t). La brecha sigue siendo total.

## 7. Supuestos validados con fuentes

| Supuesto | Valor en el modelo | Fuente | Veredicto |
|---|---|---|---|
| Vida del auto | Mediana ~14 años | Edad promedio del parque: 16.2 años (IDF, 2025) | Conservador |
| Retiro de la batería | 80 % de SoH | Garantías al 70 % (8 años / 160,000 km); literatura: retiro con 70–80 % | Extremo alto; sensibilidad a 70 % |
| Duración de la segunda vida | 3–7 años | 5–10 años adicionales; Nissan Leaf retiradas con 60–67 %: 12–20 años | Conservador |
| HEV directo a reciclaje | Sí | Diseñadas para la vida del auto (Toyota: 10 años / 240,000 km); recolección por concesionarios y reacondicionamiento | Se sostiene |

## 8. Marco legal (resumen; detalle en `docs/marco_regulatorio.md`)

- **México:** marco general sí (LGPGIR última reforma DOF 19-01-2026; NOM-161 y su modificación de 2014; NOM-052), pero
  ninguna norma específica para baterías de tracción. La Ley General de Economía Circular (DOF 19-01-2026) crea la
  responsabilidad extendida del productor, aplicable solo mediante acuerdos sectoriales que aún no existen para baterías.
- **Unión Europea (Reglamento 2023/1542):** pasaporte de batería con SoH desde el 18 feb 2027 (art. 77, Anexo XIII);
  responsabilidad ampliada del productor (art. 56); recuperación de litio de 50 % en 2027 y 80 % en 2031 (Anexo XII C);
  contenido reciclado mínimo de 6 % de litio en 2031 (art. 8.2).
- **Iniciativas en el Congreso (2025):** tres propuestas para incluir el ion-litio; ninguna aparece en la ley vigente.

## 9. Plan de trabajo (DMAIC)

| Etapa | Qué se hace | Fases | Estado |
|---|---|---|---|
| Definir | Problemática, alcance, periodo | — | Hecho |
| Medir | Recolección y limpieza, 10 fuentes | 1–2 | Hecho |
| Analizar | Causa raíz y modelos | 3–6 | Hecho |
| Mejorar | Segunda vida, reciclaje retrasado, brecha, marco legal, propuesta | 7 | Hecho |
| Controlar | Repositorio, informe técnico, API, tablero | 8 | Se actualiza con `generar_extenso` y `generar_api_estatica` |

## 10. Propuesta de gestión

1. **Acuerdo de implementación de REP para baterías de tracción** bajo la Ley General de Economía Circular, con
   financiamiento de la recolección por armadoras e importadores.
2. **Pasaporte de batería mexicano** vinculado al NIV: química, kWh, SoH al retiro y destino (modelo: Anexo XIII de la UE).
3. **Incluir el ion-litio en el art. 31 de la LGPGIR** o en una NOM específica, para cerrar la zona gris.
4. **Capacidad de reciclaje de litio** priorizada en CDMX, Estado de México, Jalisco y Nuevo León (56 % de las toneladas
   de 2035).
5. **Segunda vida regulada** para baterías entre 80 % y 70 % de SoH: pospone 3–7 años la demanda de reciclaje y da
   tiempo para construir plantas.
6. **Plan para estados calurosos** (Sinaloa, Yucatán, etc.), donde las baterías se retiran antes.

## 11. Limitaciones

- Celdas de laboratorio de EE. UU. y Reino Unido, no paquetes automotrices ni clima mexicano.
- Weibull de NASA con solo 12 celdas (8 censuradas); con umbral de 70 % el ajuste de NASA y Oxford no es identificable.
- El intervalo de PHEV al 90 % cubre solo 57 % en validación: está subestimado.
- La capacidad de SEMARNAT es la autorizada en papel, no las toneladas realmente recicladas, y la detección de litio es por texto libre.
- No hay datos del canal informal ni de baterías importadas en autos usados.
- La duración de la segunda vida y su adopción son supuestos con rango, no datos medidos.
