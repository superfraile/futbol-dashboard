"""Comprobación de cobertura; no modifica datos.json ni publica partidos."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

PAISES = {"Denmark", "Scotland", "Greece", "Norway", "Sweden", "Switzerland",
          "Turkey", "Türkiye"}

def publicar(estado, ligas=None, motivo=None):
    resultado={"fecha":datetime.now(timezone.utc).isoformat(),
               "estado":estado,"ligas":ligas or []}
    if motivo:
        resultado["motivo"]=motivo
    Path("diagnostico-sportapi.json").write_text(
        json.dumps(resultado,ensure_ascii=False,indent=2),encoding="utf-8")

def main():
    clave = os.environ.get("SPORTAPI_API_KEY", "").strip()
    if not clave:
        publicar("sin_clave",motivo="SPORTAPI_API_KEY no configurada")
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
        cobertura=[]
        for pais in datos["data"]:
            if not isinstance(pais, dict) or pais.get("country") not in PAISES:
                continue
            for liga in pais.get("leagues", []):
                cobertura.append({"pais":pais["country"],**{k:liga.get(k) for k in ("id","name","has_standings","has_fixtures","fixtures_count","teams_count")}})
                lineas.append(
                    f"- {pais['country']}: {liga.get('name')} (ID {liga.get('id')}); "
                    f"clasificación={liga.get('has_standings')}, "
                    f"calendario={liga.get('has_fixtures')}, "
                    f"partidos={liga.get('fixtures_count')}, equipos={liga.get('teams_count')}"
                )
        publicar("consulta_correcta",cobertura)
        print("\n".join(lineas))
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as resumen:
                resumen.write("\n".join(lineas) + "\n")
        return 0
    except HTTPError as error:
        publicar("error",motivo=f"HTTP {error.code}")
        print("SportAPI: HTTP", error.code)
    except (URLError, TimeoutError, ValueError, TypeError, OSError):
        publicar("error",motivo="Error de conexión o formato")
        print("SportAPI: error de conexión o formato.")
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
