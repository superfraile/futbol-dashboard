"""Comprobación de cobertura; no modifica datos.json ni publica partidos."""
import json
import os
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
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
        # Validar las competiciones concretas, sin publicar marcadores ni cuotas.
        ids={"DEN":19,"SCO":88,"GRE":10,"NOR":11,"SWE":21,"SUI":15,"TUR":16}
        def consultar(ruta):
            req=Request("https://sportapi.ai/api/"+ruta,
                        headers={"X-Api-Key":clave,"Accept":"application/json"})
            with urlopen(req,timeout=30) as respuesta:
                doc=json.load(respuesta)
            if doc.get("success") is not True:
                raise ValueError("Consulta no confirmada")
            return doc
        detalles={}
        for liga,identificador in ids.items():
            try:
                doc=consultar(f"standings/{identificador}")
                filas=doc.get("data")
                if isinstance(filas,dict):
                    filas=filas.get("standings")
                if not isinstance(filas,list) or not filas:
                    raise ValueError("Clasificación vacía o incompatible")
                detalles[liga]={"temporada":doc.get("season"),
                    "formato":doc.get("format"),
                    "equipos":len(filas),
                    "campos":sorted(filas[0]),
                    "nombres":[f.get("team",{}).get("name") if isinstance(f.get("team"),dict)
                               else f.get("team_name") for f in filas],
                    "partidos_proximos":0}
            except HTTPError as error:
                detalles[liga]={"error":f"HTTP {error.code}"}
            except (URLError,TimeoutError,ValueError,TypeError,KeyError):
                detalles[liga]={"error":"Clasificación no interpretable"}
        hoy=datetime.now(ZoneInfo("Europe/Madrid")).date()
        errores_fechas=[]
        for n in range(7):
            dia=(hoy+timedelta(days=n)).isoformat()
            try:
                doc=consultar(f"fixtures/date/{dia}")
                if not isinstance(doc.get("data"),list):
                    raise ValueError("Calendario no reconocido")
                for partido in doc["data"]:
                    liga=next((k for k,v in ids.items() if v==partido.get("league_id")),None)
                    if liga and "partidos_proximos" in detalles[liga] and partido.get("status")=="Scheduled":
                        detalles[liga]["partidos_proximos"]+=1
                        detalles[liga]["campos_partido"]=sorted(partido)
            except (HTTPError,URLError,TimeoutError,ValueError,TypeError):
                errores_fechas.append(dia)
        publicar("consulta_correcta",cobertura)
        ruta=Path("diagnostico-sportapi.json")
        informe=json.loads(ruta.read_text(encoding="utf-8"))
        informe.update(detalles=detalles,errores_fechas=errores_fechas)
        ruta.write_text(json.dumps(informe,ensure_ascii=False,indent=2),encoding="utf-8")
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
