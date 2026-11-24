# Ampliación de cobertura — 24/11/2026

El panel tiene siete ligas operativas. No modificar las fuentes existentes ni las reglas de selección mientras se valida una nueva fuente.

## open-matchday

Fuente: https://github.com/oladeeayo/open-matchday
Resumen consultado: https://github.com/oladeeayo/open-matchday/blob/master/build_summary.json
Actualización declarada: 2026-11-24 09:12 UTC.

| Liga | Resultados | Próximos |
|---|---:|---:|
| SCO | 81 | 117 |
| TUR | 108 | 198 |
| GRE | 76 | 106 |
| SUI | 84 | 48 |
| DEN | 90 | 42 |
| SWE | 106 | 9 |
| NOR | 108 | 24 |

Son recuentos declarados, no una validación independiente de los partidos. En particular, SWE y NOR no parecen abarcar una temporada completa. No usar un histórico parcial para calcular Pts/PJ.

El README autoriza usos no comerciales con atribución, pero el aviso de derechos indica que siguen vigentes las condiciones de los proveedores originales: https://github.com/oladeeayo/open-matchday/blob/master/DISCLAIMER.md . Fixture Download restringe la redistribución pública: https://fixturedownload.com/terms . No incorporar automáticamente estos CSV al repositorio público sin resolver los derechos de las fuentes subyacentes.

## Alternativas

- OpenFootball: los archivos concretos de temporada buscados en football.json y europe devolvieron 404. Buscar rutas publicadas y comprobar cobertura antes de descartar todo el proyecto.
- football-data.co.uk: resultados históricos de las siete ligas; comprobar condiciones, cobertura y calendarios futuros por separado. https://football-data.co.uk/data.php y https://football-data.co.uk/all_new_data.php
- MoviOdds: dispone de resultados; el plan gratuito anuncia histórico limitado. No dar por disponible una temporada completa. https://moviodds.com/doc y https://moviodds.com/pricing/

## Requisitos para habilitar cada liga

1. Permiso de publicación de datos en el panel público.
2. Temporada correcta (año natural para NOR/SWE), equipos completos, marcadores finales y ausencia de duplicados.
3. Comparar Pts/PJ con clasificación fiable y considerar fases de liga y sanciones.
4. Horas inequívocas y correspondencias de equipos verificadas con MoviOdds.
5. Pruebas de regresión y conservación de las siete ligas operativas si falla la fuente nueva.

No se activa ninguna liga basándose únicamente en estos recuentos.
