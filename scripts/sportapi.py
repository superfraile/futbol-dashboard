"""Clasificaciones oficiales del proveedor y calendario, sin fabricar históricos."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from urllib.request import Request, urlopen
import json
from urllib.error import HTTPError

IDS={"DEN":19,"SCO":88,"GRE":10,"NOR":11,"SWE":21,"SUI":15,"TUR":16}
EQUIPOS={"DEN":12,"SCO":12,"GRE":14,"NOR":16,"SWE":16,"SUI":12,"TUR":18}

def temporada(liga,hoy):
    if liga in ("NOR","SWE"):
        return str(hoy.year)
    inicio=hoy.year if hoy.month>=7 else hoy.year-1
    return f"{inicio}/{str(inicio+1)[-2:]}"

def consultar(ruta,clave):
    req=Request("https://sportapi.ai/api/"+ruta,
                headers={"X-Api-Key":clave,"Accept":"application/json"})
    with urlopen(req,timeout=30) as respuesta:
        doc=json.load(respuesta)
    if not isinstance(doc,dict) or doc.get("success") is not True:
        raise ValueError("Respuesta SportAPI no confirmada")
    return doc

def convertir_tabla(doc,liga,hoy):
    if doc.get("season")!=temporada(liga,hoy) or doc.get("format")!="league":
        raise ValueError("Temporada o formato incompatible")
    filas=doc.get("data")
    if isinstance(filas,dict):
        filas=filas.get("standings")
    if not isinstance(filas,list) or len(filas)!=EQUIPOS[liga]:
        raise ValueError("Clasificación incompleta")
    tabla=[]
    for f in filas:
        equipo=f["team"]["name"] if isinstance(f["team"],dict) else f["team_name"]
        p=dict(equipo=equipo,posicion=f["position"],pj=f["played"],g=f["won"],
               e=f["draw"],p=f["lost"],gf=f["goals_for"],gc=f["goals_against"],puntos=f["points"])
        if not isinstance(equipo,str) or not equipo.strip() or equipo!=equipo.strip():
            raise ValueError("Nombre inválido")
        if any(type(v) is not int for k,v in p.items() if k!="equipo"):
            raise ValueError("Clasificación no numérica")
        if any(p[k]<0 for k in ("pj","g","e","p","gf","gc")) or p["pj"]!=p["g"]+p["e"]+p["p"]:
            raise ValueError("Balance de partidos incoherente")
        p["ppp"]=round(p["puntos"]/p["pj"],2) if p["pj"] else 0
        tabla.append(p)
    if len({p["equipo"] for p in tabla})!=len(tabla) or {p["posicion"] for p in tabla}!=set(range(1,len(tabla)+1)):
        raise ValueError("Equipos o posiciones duplicados")
    return sorted(tabla,key=lambda p:p["posicion"])

def descargar_sportapi(clave,hoy=None,diagnostico=None):
    diagnostico=diagnostico if diagnostico is not None else {}
    hoy=hoy or datetime.now(ZoneInfo("Europe/Madrid")).date()
    tablas={}
    partidos={}
    for liga,id_liga in IDS.items():
        try:
            tablas[liga]=convertir_tabla(consultar(f"standings/{id_liga}",clave),liga,hoy)
            partidos[liga]=[]
            diagnostico[liga]={"clasificacion":"correcta","equipos":len(tablas[liga])}
        except Exception as error:
            motivo=str(error) if isinstance(error,ValueError) else f"HTTP {error.code}" if isinstance(error,HTTPError) else type(error).__name__
            diagnostico[liga]={"clasificacion":"rechazada","motivo":motivo}
            print(f"AVISO SportAPI {liga}: {motivo}")
    if not tablas:
        return {},{}
    # La fecha del endpoint utiliza CET/CEST, igual que Europe/Madrid.
    calendario=[]
    for n in range(7):
        dia=(hoy+timedelta(days=n)).isoformat()
        doc=consultar(f"fixtures/date/{dia}",clave)
        if not isinstance(doc.get("data"),list):
            raise ValueError("Calendario SportAPI incompleto")
        calendario.extend(doc["data"])
    for liga,tabla in list(tablas.items()):
        try:
            nombres={p["equipo"] for p in tabla}
            vistos=set()
            for m in calendario:
                if m.get("league_id")!=IDS[liga] or m.get("status")!="Scheduled":
                    continue
                local,visitante=m["home_team"],m["away_team"]
                inicio=datetime.fromisoformat(m["kickoff_utc"].replace("Z","+00:00"))
                if inicio.tzinfo is None or local not in nombres or visitante not in nombres or local==visitante:
                    diagnostico[liga]["partido_no_conciliado"]={"local":local,"visitante":visitante,"hora_con_zona":inicio.tzinfo is not None,"local_en_tabla":local in nombres,"visitante_en_tabla":visitante in nombres}
                    raise ValueError("Partido no conciliado con tabla")
                inicio=inicio.astimezone(timezone.utc).isoformat()
                k=(inicio,local,visitante)
                if k in vistos:
                    continue
                vistos.add(k)
                partidos[liga].append(dict(fecha=inicio,local=local,visitante=visitante,estado="pendiente"))
            diagnostico[liga].update(calendario="correcto",partidos=len(partidos[liga]))
        except (KeyError,ValueError,TypeError,AttributeError) as error:
            diagnostico[liga].update(calendario="rechazado",motivo=str(error) if isinstance(error,ValueError) else type(error).__name__)
            print(f"AVISO SportAPI {liga}: calendario no conciliado")
            tablas.pop(liga)
            partidos.pop(liga)
    return tablas,partidos
