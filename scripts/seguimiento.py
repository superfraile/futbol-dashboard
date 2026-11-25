"""Seguimiento prospectivo, sin apuestas reales ni modificación de las cuotas."""
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from scripts.construir_datos import generar_dobles, clave_equipo
from scripts.sportapi import IDS, consultar

STAKE=5
ZONA=ZoneInfo("Europe/Madrid")
RUTA=Path("seguimiento.json")

def instante(s):
    d=datetime.fromisoformat(s.replace("Z","+00:00"))
    if d.tzinfo is None:
        raise ValueError("Fecha sin zona")
    return d

def clave(p):
    return (p["liga"],clave_equipo(p["local"]),clave_equipo(p["visitante"]),
            instante(p["fecha"]).astimezone(ZONA).date().isoformat())

def registrar(historial,datos,ahora,confirmaciones):
    # Una única selección semanal, incluso si no existen dobles válidas.
    local=ahora.astimezone(ZONA)
    if local.weekday()!=1 or local.hour!=20:
        return
    dia=local.date().isoformat()
    if dia in confirmaciones:
        return
    usados={clave(p) for d in historial for p in d["partidos"]}
    candidatos=[p for p in datos.get("candidatos",[]) if clave(p) not in usados]
    cantidad=0
    for doble in generar_dobles(candidatos,ahora):
        partidos=doble["partidos"]
        claves={clave(p) for p in partidos}
        if len(claves)!=2 or claves & usados:
            continue
        historial.append(dict(dia=dia,semana_confirmada=dia,registrada_en=ahora.isoformat(),
            stake=STAKE,cuota=round(partidos[0]["cuota"]*partidos[1]["cuota"],4),
            estado="pendiente",beneficio=None,partidos=[
                {**{k:p[k] for k in ("liga","fecha","local","visitante","favorito",
                  "equipo_proveedor","cuota","casa_apuestas","seleccion","consultada_en")},
                 "estado":"pendiente"} for p in partidos]))
        usados.update(claves)
        cantidad+=1
    confirmaciones[dia]=dict(confirmada_en=ahora.isoformat(),cantidad=cantidad)

def resultado(p,filas):
    coincidencias=[]
    for m in filas:
        try:
            if (clave_equipo(m["local"])!=clave_equipo(p["local"]) or
                clave_equipo(m["visitante"])!=clave_equipo(p["visitante"])):
                continue
            if abs((instante(m["fecha"])-instante(p["fecha"])).total_seconds())>3*3600:
                continue
            coincidencias.append(m)
        except (KeyError,ValueError,TypeError,AttributeError):
            continue
    if len(coincidencias)!=1:
        return
    m=coincidencias[0]
    if m["estado"]=="cancelado":
        p.update(estado="anulado",fuente_resultado=m.get("fuente_resultado"))
    elif m["estado"]=="finalizado":
        a,b=m.get("goles_local"),m.get("goles_visitante")
        if any(type(v) is not int or v<0 for v in (a,b)):
            return
        gana=(a>b and p["seleccion"]=="1") or (b>a and p["seleccion"]=="2")
        p.update(estado="acertado" if gana else "fallado",marcador=f"{a}-{b}",
                 fuente_resultado=m.get("fuente_resultado"))

def liquidar(d,ahora):
    estados=[p["estado"] for p in d["partidos"]]
    # Esperar a ambos resultados, incluso cuando una selección ya ha fallado.
    if "pendiente" in estados:
        return
    if "fallado" in estados:
        estado,beneficio="fallada",-d["stake"]
    elif all(e=="anulado" for e in estados):
        estado,beneficio="anulada",0
    else:
        cuota=1
        for p in d["partidos"]:
            if p["estado"]=="acertado":
                cuota*=p["cuota"]
        estado,beneficio="acertada",round(d["stake"]*(cuota-1),2)
    d.update(estado=estado,beneficio=beneficio,liquidada_en=ahora.isoformat())

def actualizar(historial,origen,ahora,clave_api):
    cache={}
    for d in historial:
        if d["estado"]!="pendiente":
            continue
        for p in d["partidos"]:
            if p["estado"]!="pendiente" or instante(p["fecha"])>=ahora:
                continue
            liga=p["liga"]
            if liga not in IDS:
                fuente="OpenLigaDB" if liga=="GER" else "football-data.org"
                filas=[dict(m,fuente_resultado=fuente) for m in origen.get("ligas",{}).get(liga,[])]
            else:
                dia=clave(p)[3]
                if dia not in cache:
                    if not clave_api or len(cache)>=30:
                        continue
                    try:
                        doc=consultar(f"fixtures/date/{dia}",clave_api)
                        cache[dia]=doc["data"] if isinstance(doc.get("data"),list) else []
                    except Exception:
                        cache[dia]=[]
                filas=[]
                for m in cache[dia]:
                    if m.get("league_id")!=IDS[liga] or m.get("status")!="FT":
                        continue
                    filas.append(dict(fecha=m.get("kickoff_utc"),local=m.get("home_team"),
                        visitante=m.get("away_team"),estado="finalizado",
                        goles_local=m.get("home_score"),goles_visitante=m.get("away_score"),
                        fuente_resultado="SportAPI.ai"))
            resultado(p,filas)
        liquidar(d,ahora)

def main():
    ahora=datetime.now(timezone.utc)
    doc=json.loads(RUTA.read_text(encoding="utf-8")) if RUTA.exists() else {"dobles":[]}
    historial=doc["dobles"]
    datos=json.loads(Path("datos.json").read_text(encoding="utf-8"))
    origen=json.loads(Path("datos-origen.json").read_text(encoding="utf-8"))
    actualizar(historial,origen,ahora,os.environ.get("SPORTAPI_API_KEY","").strip())
    registrar(historial,datos,ahora,doc.setdefault("confirmaciones",{}))
    doc.update(version=2,actualizado_en=ahora.isoformat(),stake_simulado=STAKE)
    tmp=RUTA.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding="utf-8")
    tmp.replace(RUTA)

if __name__=="__main__":
    main()
