"""Descarga de partidos de fuentes gratuitas, sin exponer credenciales."""
import json
import os
from datetime import datetime
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

# Competiciones incluidas en el plan gratuito, sujetas a disponibilidad.
COMPETICIONES = {"ENG": "PL", "ESP": "PD", "ITA": "SA",
                 "FRA": "FL1", "POR": "PPL", "NED": "DED"}

def openligadb(temporada):
    url = f"https://api.openligadb.de/getmatchdata/bl1/{temporada}"
    with urlopen(url, timeout=30) as respuesta:
        datos = json.load(respuesta)
    partidos = []
    for m in datos:
        final = m["matchIsFinished"]
        p = dict(fecha=m["matchDateTime"][:10],
                 local=m["team1"]["teamName"],
                 visitante=m["team2"]["teamName"],
                 estado="finalizado" if final else "pendiente")
        if final:
            resultados = [r for r in m["matchResults"] if r["resultTypeID"] == 2]
            if len(resultados) != 1:
                raise ValueError("Resultado final ausente o ambiguo")
            p.update(goles_local=resultados[0]["pointsTeam1"],
                     goles_visitante=resultados[0]["pointsTeam2"])
        partidos.append(p)
    if len(partidos) != 306 or not any(p["estado"] == "finalizado" for p in partidos):
        raise ValueError("Temporada Bundesliga incompleta")
    return partidos

def convertir_partidos(datos):
    """Normaliza el esquema de football-data.org; excluye resultados incompletos."""
    partidos = []
    for m in datos["matches"]:
        estado_api = m["status"]
        if estado_api in ("CANCELLED", "POSTPONED", "SUSPENDED"):
            estado = "cancelado" if estado_api == "CANCELLED" else "aplazado"
        elif estado_api == "FINISHED":
            estado = "finalizado"
        else:
            estado = "pendiente"
        local = m["homeTeam"].get("name")
        visitante = m["awayTeam"].get("name")
        if not local or not visitante:
            continue
        partido = dict(fecha=m["utcDate"], local=local,
                       visitante=visitante, estado=estado)
        if estado == "finalizado":
            goles = m.get("score", {}).get("fullTime") or {}
            if not isinstance(goles.get("home"), int) or not isinstance(goles.get("away"), int):
                raise ValueError("Partido finalizado sin marcador válido")
            partido.update(goles_local=goles["home"], goles_visitante=goles["away"])
        partidos.append(partido)
    if not partidos or not any(p["estado"] == "finalizado" for p in partidos):
        raise ValueError("Proveedor sin resultados suficientes")
    return partidos

def football_data(codigo, clave):
    peticion = Request(
        f"https://api.football-data.org/v4/competitions/{codigo}/matches",
        headers={"X-Auth-Token": clave, "Accept": "application/json",
                 "User-Agent": "FutbolDashboard/1.0"})
    with urlopen(peticion, timeout=35) as respuesta:
        return convertir_partidos(json.load(respuesta))

def descargar():
    hoy = datetime.now(ZoneInfo("Europe/Madrid"))
    temporada = hoy.year if hoy.month >= 7 else hoy.year - 1
    anteriores = {}
    try:
        from pathlib import Path
        anterior = Path("datos-origen.json")
        if anterior.exists():
            anteriores = json.loads(anterior.read_text(encoding="utf-8")).get("ligas", {})
    except (OSError, ValueError, TypeError):
        print("AVISO: no se pudo leer la copia anterior")
    ligas = {}
    fuentes = []
    try:
        ligas["GER"] = openligadb(temporada)
        fuentes.append("OpenLigaDB (https://www.openligadb.de), ODbL 1.0; GER")
    except Exception as error:
        print(f"AVISO: GER no disponible: {type(error).__name__}: {error}")
        if anteriores.get("GER"):
            ligas["GER"] = anteriores["GER"]
            fuentes.append("OpenLigaDB (https://www.openligadb.de), ODbL 1.0; GER; copia anterior")
    clave = os.environ.get("FOOTBALL_DATA_API_KEY", "").strip()
    if clave:
        for liga, codigo in COMPETICIONES.items():
            try:
                ligas[liga] = football_data(codigo, clave)
                fuentes.append(f"football-data.org ({codigo}; {liga})")
                print(f"{liga}: {len(ligas[liga])} partidos descargados")
            except Exception as error:
                print(f"AVISO: {liga} no disponible: {type(error).__name__}: {error}")
                if anteriores.get(liga):
                    ligas[liga] = anteriores[liga]
                    fuentes.append(f"football-data.org ({codigo}; {liga}; copia anterior)")
    if not ligas:
        raise ValueError("Ninguna liga disponible; se conserva el JSON publicado")
    return {"fuente": "; ".join(fuentes), "ligas": ligas}

if __name__ == "__main__":
    from pathlib import Path
    Path("entrada.json").write_text(
        json.dumps(descargar(), ensure_ascii=False), encoding="utf-8")
