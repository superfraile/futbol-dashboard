"""Recupera resultados por fecha y publica únicamente estadísticas conciliadas."""
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.error import HTTPError

from scripts.sportapi import IDS, consultar, convertir_tabla, temporada
from scripts.estadisticas import calcular, desglosar
from scripts.elo import elo

def inicio_temporada(liga,hoy):
    return date(hoy.year,1,1) if liga in ("NOR","SWE") else date(hoy.year if hoy.month>=7 else hoy.year-1,7,1)

def conciliar(tabla,partidos):
    obtenida={p["equipo"]:p for p in calcular(partidos)}
    campos=("pj","g","e","p","gf","gc")
    diferencias=[]
    for fila in tabla:
        actual=obtenida.get(fila["equipo"],{})
        if any(actual.get(k,0)!=fila[k] for k in campos):
            diferencias.append(fila["equipo"])
    extras=set(obtenida)-{p["equipo"] for p in tabla}
    return sorted(set(diferencias)|extras)

def generar(clave,hoy):
    tablas={liga:convertir_tabla(consultar(f"standings/{identificador}",clave),liga,hoy)
            for liga,identificador in IDS.items()}
    inicio={liga:inicio_temporada(liga,hoy) for liga in IDS}
    registros={liga:{} for liga in IDS}
    errores={liga:[] for liga in IDS}
    ids={v:k for k,v in IDS.items()}
    dia=min(inicio.values())
    peticiones=7
    while dia<=hoy:
        # Límite absoluto: deja margen en el plan gratuito incluso en año bisiesto.
        if peticiones>=380:
            raise ValueError("Límite de consultas del histórico")
        peticiones+=1
        doc=consultar(f"fixtures/date/{dia.isoformat()}",clave)
        filas=doc.get("data")
        if not isinstance(filas,list):
            raise ValueError("Respuesta de calendario incompleta")
        for m in filas:
            liga=ids.get(m.get("league_id"))
            if not liga or dia<inicio[liga] or m.get("status")!="FT":
                continue
            try:
                a,b=m["home_score"],m["away_score"]
                local,visitante=m["home_team"],m["away_team"]
                instante=datetime.fromisoformat(m["kickoff_utc"].replace("Z","+00:00"))
                if instante.tzinfo is None or local==visitante or any(type(x) is not int or x<0 for x in (a,b)):
                    raise ValueError("Resultado inválido")
                partido=dict(fecha=instante.astimezone(timezone.utc).isoformat(),local=local,visitante=visitante,
                             goles_local=a,goles_visitante=b,estado="finalizado")
                id_partido=m["id"]
                anterior=registros[liga].get(id_partido)
                if anterior is not None and anterior!=partido:
                    raise ValueError("Identificador conflictivo")
                registros[liga][id_partido]=partido
            except (KeyError,TypeError,ValueError,AttributeError):
                errores[liga].append(dia.isoformat())
        dia+=timedelta(days=1)
    resultado={"fecha":datetime.now(timezone.utc).isoformat(),"consultas":peticiones,"ligas":{}}
    for liga,tabla in tablas.items():
        partidos=list(registros[liga].values())
        diferencias=conciliar(tabla,partidos)
        informe=dict(temporada=temporada(liga,hoy),partidos=len(partidos),
                     equipos_discrepantes=diferencias,fechas_invalidas=sorted(set(errores[liga])),
                     estado="validado" if not diferencias and not errores[liga] else "incompleto")
        if informe["estado"]=="validado":
            informe["estadisticas"]=desglosar(partidos)
            informe["elo"]={k:round(v,1) for k,v in elo(partidos).items()}
        resultado["ligas"][liga]=informe
    return resultado

def main():
    clave=os.environ.get("SPORTAPI_API_KEY","").strip()
    if not clave:
        print("Sin clave SportAPI")
        return 1
    try:
        informe=generar(clave,datetime.now(ZoneInfo("Europe/Madrid")).date())
    except HTTPError as error:
        print(f"SportAPI: HTTP {error.code}; no se reemplaza el histórico")
        return 1
    except Exception as error:
        print(f"Histórico no publicado: {type(error).__name__}")
        return 1
    Path("historico-sportapi.json").write_text(json.dumps(informe,ensure_ascii=False,indent=2),encoding="utf-8")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
