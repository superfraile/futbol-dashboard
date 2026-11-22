# Fuente gratuita de cuotas bet365: MoviOdds

Documentación: https://moviodds.com/doc
Alta de clave gratuita: https://moviodds.com/account
Precios: https://moviodds.com/pricing/

## Condiciones verificadas en la documentación (22-11-2026)
- El proveedor declara que distribuye exclusivamente cuotas de bet365 y que es independiente de bet365.
- Plan gratuito anunciado: 5.000 solicitudes/mes, hasta 30/minuto, solo mercados principales y sin WebSocket cuando entren en vigor los límites publicados.
- Mercado de interés: Full Time Result, grupo 40 antes del inicio; 1777 es el grupo en directo y NO sirve.
- Endpoint: GET https://moviodds.com/odds?sport=soccer
- Autenticación: cabecera X-API-Key. Nunca incluir la clave en código público, HTML, datos.json o URL.
- No se ha probado todavía el acceso con una clave real. La procedencia de las cuotas es una afirmación del proveedor, no una verificación independiente.

## Requisitos antes de activar la importación
1. Crear una clave gratuita y guardarla como secreto GitHub Actions MOVIODDS_API_KEY.
2. Consultar una respuesta real y validar el esquema de fixtures, kickoff, mercado, selección, cuota y timestamp.
3. Emparejar por equipos, liga y fecha/hora; ante ambigüedad descartar.
4. Rechazar partidos en directo, mercados distintos de Full Time Result y cuotas suspendidas.
5. Importar solo victoria del favorito (1 o 2), cuota decimal 1.20–1.80.
6. Mantener hora de captura, ID de evento y fuente. No marcar una cuota verificada solo por existir un enlace.
7. Preservar el límite gratuito. Si la API falla, mantener las cuotas pendientes sin inventar valores.

El sitio público no debe llamar directamente a la API porque revelaría la clave. La actualización debe ejecutarse en GitHub Actions.
