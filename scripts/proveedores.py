"""Adaptadores gratuitos. Solo se activa OpenLigaDB; el resto requiere validar derechos y cobertura."""
import json
from urllib.request import urlopen
from datetime import datetime
from zoneinfo import ZoneInfo

def openligadb(temporada):
    url=f"https://api.openligadb.de/getmatchdata/bl1/{temporada}"
    with urlopen(url, timeout=30) as r:
        datos=json.load(r)
    partidos=[]
    for m in datos:
        final=m["matchIsFinished"]
        p=dict(fecha=m["matchDateTime"][:10],local=m["team1"]["teamName"],
               visitante=m["team2"]["teamName"],estado="finalizado" if final else "pendiente")
        if final:
            resultados=[r for r in m["matchResults"] if r["resultTypeID"]==2]
            if len(resultados)!=1:
                raise ValueError("Resultado final ausente o ambiguo")
            p.update(goles_local=resultados[0]["pointsTeam1"],goles_visitante=resultados[0]["pointsTeam2"])
        partidos.append(p)
    if len(partidos)!=306 or sum(p["estado"]=="finalizado" for p in partidos)==0:
        raise ValueError("Temporada Bundesliga incompleta")
    return partidos

def descargar():
    hoy=datetime.now(ZoneInfo("Europe/Madrid"))
    temporada=hoy.year if hoy.month>=7 else hoy.year-1
    return {"fuente":"OpenLigaDB (https://www.openligadb.de), ODbL 1.0; cobertura GER",
            "ligas":{"GER":openligadb(temporada)}}

if __name__=="__main__":
    from pathlib import Path
    Path("entrada.json").write_text(json.dumps(descargar(),ensure_ascii=False),encoding="utf-8")
