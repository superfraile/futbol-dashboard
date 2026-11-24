"""Comprobación de cobertura; no modifica datos.json ni publica partidos."""
import json
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

PAISES = {"Denmark", "Scotland", "Greece", "Norway", "Sweden", "Switzerland",
          "Turkey", "Türkiye"}

def main():
    clave = os.environ.get("SPORTAPI_API_KEY", "").strip()
    if not clave:
        print("SportAPI pendiente de configurar; no se modifica el dashboard.")
        return 0
    try:
        req = Request("https://sportapi.ai/api/leagues",
                      headers={"X-Api-Key": clave, "Accept": "application/json"})
        with urlopen(req, timeout=30) as respuesta:
            datos = json.load(respuesta)
        if datos.get("success") is not True or not isinstance(datos.get("data"), list):
            raise ValueError("Esquema de ligas no reconocido")
        lineas = ["## Cobertura SportAPI (solo diagnóstico)"]
        for pais in datos["data"]:
            if not isinstance(pais, dict) or pais.get("country") not in PAISES:
                continue
            for liga in pais.get("leagues", []):
                lineas.append(
                    f"- {pais['country']}: {liga.get('name')} (ID {liga.get('id')}); "
                    f"clasificación={liga.get('has_standings')}, "
                    f"calendario={liga.get('has_fixtures')}, "
                    f"partidos={liga.get('fixtures_count')}, equipos={liga.get('teams_count')}"
                )
        print("\n".join(lineas))
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as resumen:
                resumen.write("\n".join(lineas) + "\n")
        return 0
    except HTTPError as error:
        print("SportAPI: HTTP", error.code)
    except (URLError, TimeoutError, ValueError, TypeError, OSError):
        print("SportAPI: error de conexión o formato.")
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
