"""Genera el JSON del panel desde un fichero de partidos previamente validado.
Uso: python -m scripts.construir_datos entrada.json salida.json
No descarga ni publica información por su cuenta.
"""
import json
import sys
from math import isfinite
from datetime import datetime, timezone, date
from pathlib import Path
from scripts.estadisticas import calcular, desglosar
from scripts.elo import elo
import unicodedata
from itertools import combinations
from urllib.parse import urlparse

LIGAS="GER DEN SCO ESP FRA GRE ENG ITA NOR NED POR SWE SUI TUR".split()

def clave_equipo(nombre):
    normal=unicodedata.normalize("NFKD",nombre.casefold())
    return "".join(c for c in normal if c.isalnum() and not unicodedata.combining(c))

def favoritos_configurados():
    archivo=Path(__file__).resolve().parent.parent/"equipos-favoritos.json"
    documento=json.loads(archivo.read_text(encoding="utf-8"))
    configuracion=documento["ligas"]
    if set(configuracion)!=set(LIGAS):
        raise ValueError("La lista fija debe contener las 14 ligas")
    if any(not isinstance(equipos,list) or len(equipos)>5 or len(equipos)!=len(set(equipos)) for equipos in configuracion.values()):
        raise ValueError("Lista fija inválida")
    if documento.get("validada") is True and sum(map(len,configuracion.values()))!=38:
        raise ValueError("La lista validada debe contener exactamente 38 favoritos")
    return configuracion


# Correspondencias exactas revisadas frente a los nombres reales de los proveedores.
ALIAS = {
 "GER":{"Bayern Munich":"FC Bayern München","Dortmund":"Borussia Dortmund","Bayer Leverkusen":"Bayer 04 Leverkusen"},
 "DEN":{"FC Copenhagen":"FC København"},
 "ESP":{"Barcelona":"FC Barcelona","Real Madrid":"Real Madrid CF","Betis":"Real Betis Balompié","Atl. Madrid":"Club Atlético de Madrid"},
 "FRA":{"PSG":"Paris Saint-Germain FC","Monaco":"AS Monaco FC","Marseille":"Olympique de Marseille"},
 "GRE":{"AEK Athens":"AEK Athens","Olympiacos Piraeus":"Olympiacos"},
 "ENG":{"Arsenal":"Arsenal FC","Manchester City":"Manchester City FC","Manchester Utd":"Manchester United FC","Liverpool":"Liverpool FC"},
 "ITA":{"Inter":"FC Internazionale Milano","Napoli":"SSC Napoli","AC Milan":"AC Milan","Juventus":"Juventus FC"},
 "NOR":{"Bodo/Glimt":"FK Bodø/Glimt"},
 "NED":{"Feyenoord":"Feyenoord Rotterdam","Ajax":"AFC Ajax"},
 "POR":{"FC Porto":"FC Porto","Sporting CP":"Sporting Clube de Portugal","Benfica":"Sport Lisboa e Benfica","Braga":"Sporting Clube de Braga"},
 "SWE":{"Malmo FF":"Malmö FF"},
 "TUR":{"Fenerbahce":"Fenerbahçe"}
}

def resolver_favoritos(liga, favoritos, tabla):
    disponibles={clave_equipo(t["equipo"]):t for t in tabla}
    resueltos={}
    for favorito in favoritos:
        nombre=ALIAS.get(liga,{}).get(favorito,favorito)
        equipo=disponibles.get(clave_equipo(nombre))
        if equipo:
            resueltos[equipo["equipo"]]=favorito
    return resueltos

def generar_dobles(candidatos, ahora=None):
    """Solo combina partidos futuros con cuotas verificadas y vigentes."""
    ahora=ahora or datetime.now(timezone.utc)
    def vigente(p):
        try:
            fecha=datetime.fromisoformat(p["fecha"].replace("Z","+00:00"))
            consulta=datetime.fromisoformat(p["consultada_en"].replace("Z","+00:00"))
            return (fecha.tzinfo is not None and fecha>ahora and
                    consulta.tzinfo is not None and 0<=(ahora-consulta).total_seconds()<=3600)
        except (KeyError,TypeError,ValueError,AttributeError):
            return False
    validos=[p for p in candidatos
             if vigente(p)
             if type(p.get("cuota")) in (int,float) and isfinite(p["cuota"]) and 1.20<=p["cuota"]<=1.80
             and p.get("cuota_verificada") is True
             and p.get("casa_apuestas")=="bet365"
             and p.get("mercado")=="1X2"
             and p.get("seleccion")==("1" if p.get("equipo_proveedor")==p.get("local") else "2" if p.get("equipo_proveedor")==p.get("visitante") else None)]
    dobles=[]
    for a,b in combinations(sorted(validos,key=lambda p:p["fecha"]),2):
        # Nunca repetir un partido; cada combinación contiene dos encuentros distintos.
        if (a["liga"],a["fecha"],a["local"],a["visitante"]) == (b["liga"],b["fecha"],b["local"],b["visitante"]):
            continue
        dobles.append(dict(partidos=[a,b],cuota_combinada=round(a["cuota"]*b["cuota"],3)))
    dobles.sort(key=lambda d:((date.fromisoformat(d["partidos"][1]["fecha"][:10])-date.fromisoformat(d["partidos"][0]["fecha"][:10])).days,d["partidos"][0]["fecha"],d["partidos"][1]["fecha"]))
    return dobles

def validar(entrada):
    ligas=entrada["ligas"]
    if not isinstance(ligas,dict) or set(ligas)-set(LIGAS):
        raise ValueError("Ligas no reconocidas")
    for partidos in ligas.values():
        if not isinstance(partidos,list):
            raise ValueError("Lista de partidos obligatoria")
        vistos=set()
        for m in partidos:
            fecha=m["fecha"]
            date.fromisoformat(fecha[:10])
            if len(fecha)>10:
                datetime.fromisoformat(fecha.replace("Z","+00:00"))
            a,b=m["local"],m["visitante"]
            if not all(isinstance(x,str) and x.strip() and x==x.strip() for x in (a,b)) or a==b:
                raise ValueError("Equipos invalidos")
            if m["estado"] not in ("finalizado","pendiente","aplazado","cancelado"):
                raise ValueError("Estado desconocido")
            clave=(fecha[:10],a,b)
            if clave in vistos:
                raise ValueError("Partido duplicado")
            vistos.add(clave)

def aplicar_cuotas_bet365(candidatos, archivo=None):
    """Importa solo cuotas 1X2 documentadas de bet365, nunca estimaciones."""
    ruta=archivo or Path(__file__).resolve().parent.parent/"cuotas-bet365.json"
    ruta=Path(ruta)
    if not ruta.is_file():
        return
    documento=json.loads(ruta.read_text(encoding="utf-8"))
    if documento.get("casa_apuestas")!="bet365" or documento.get("mercado")!="1X2":
        raise ValueError("La fuente de cuotas debe ser bet365, mercado 1X2")
    indices={(p["liga"],p["fecha"],p["local"],p["visitante"]):p for p in candidatos}
    ahora=datetime.now(timezone.utc)
    registros=documento.get("cuotas",[])
    if not isinstance(registros,list):
        raise ValueError("La lista de cuotas debe ser una lista")
    # Si hay varias entradas para un mismo encuentro, ninguna se aplica:
    # no es seguro escoger arbitrariamente una cuota o selección.
    from collections import Counter
    claves=[tuple(q.get(k) for k in ("liga","fecha","local","visitante"))
            for q in registros if isinstance(q,dict)]
    repeticiones=Counter(claves)
    for cuota in registros:
        if not isinstance(cuota,dict):
            continue
        clave=tuple(cuota.get(k) for k in ("liga","fecha","local","visitante"))
        if repeticiones[clave]!=1:
            continue
        partido=indices.get(clave)
        if partido is None:
            continue
        # Una cuota no es operativa sin hora de inicio inequívoca y futura.
        try:
            inicio=datetime.fromisoformat(partido["fecha"].replace("Z","+00:00"))
            if inicio.tzinfo is None or inicio<=ahora:
                continue
        except (KeyError,TypeError,ValueError,AttributeError):
            continue
        signo="1" if partido["equipo_proveedor"]==partido["local"] else "2"
        valor=cuota.get("cuota")
        fecha_consulta=cuota.get("consultada_en")
        url=cuota.get("url_fuente")
        if (cuota.get("verificada") is not True or cuota.get("seleccion")!=signo or type(valor) not in (float,int)
                or not isfinite(valor) or not 1.20<=valor<=1.80 or not isinstance(url,str)
                or not url.startswith("https://")
                or urlparse(url).hostname not in ("bet365.com","www.bet365.com","bet365.es","www.bet365.es")
                or not isinstance(fecha_consulta,str)):
            continue
        try:
            instante=datetime.fromisoformat(fecha_consulta.replace("Z","+00:00"))
        except ValueError:
            continue
        if (instante.tzinfo is None or instante>ahora
                or (ahora-instante).total_seconds()>3600
                or instante>=inicio):
            continue
        partido.update(cuota=valor,cuota_verificada=True,casa_apuestas="bet365",
                       mercado="1X2",seleccion=signo,consultada_en=fecha_consulta,
                       url_fuente=url,estado="Cuota bet365 documentada")

def construir(entrada):
    validar(entrada)
    fuente=entrada["fuente"]
    if not isinstance(fuente,str) or not fuente.strip():
        raise ValueError("Fuente obligatoria")
    favoritos=favoritos_configurados()
    lista_validada=json.loads((Path(__file__).resolve().parent.parent/"equipos-favoritos.json").read_text(encoding="utf-8")).get("validada") is True
    resultado=dict(version="1.2",ultima_actualizacion=datetime.now(timezone.utc).isoformat(),
                   fuente=fuente,ligas={},equipos_top=[],partidos=[],estadisticas={},candidatos=[],dobles=[])
    for liga in LIGAS:
        partidos=entrada["ligas"].get(liga,[])
        tabla=calcular(partidos)
        rating=elo(partidos)
        resultado["ligas"][liga]=tabla
        resultado["estadisticas"][liga]=desglosar(partidos)
        resueltos=resolver_favoritos(liga,favoritos[liga],tabla) if lista_validada else {}
        # Un favorito puede no figurar en la clasificación si todavía no ha jugado.
        # Aun así, debe excluirse cualquier enfrentamiento entre dos favoritos.
        nombres_fijos={clave_equipo(ALIAS.get(liga,{}).get(nombre,nombre)) for nombre in favoritos[liga]} if lista_validada else set()
        def es_favorito_fijo(nombre):
            return clave_equipo(nombre) in nombres_fijos
        por_nombre={clave_equipo(nombre):(nombre,valor) for nombre,valor in rating.items()}
        por_equipo={t["equipo"]:t for t in tabla}
        for equipo in (favoritos[liga] if lista_validada else []):
            nombre=ALIAS.get(liga,{}).get(equipo,equipo)
            encontrado=por_nombre.get(clave_equipo(nombre))
            resultado["equipos_top"].append(dict(
                liga=liga,equipo=equipo,
                elo=round(encontrado[1],1) if encontrado else None,
                equipo_proveedor=encontrado[0] if encontrado else None))
        for m in partidos:
            if m.get("estado")!="pendiente":
                continue
            local,visitante=m["local"],m["visitante"]
            # Se excluyen enfrentamientos entre dos favoritos.
            if es_favorito_fijo(local) and es_favorito_fijo(visitante):
                continue
            favorito=local if local in resueltos else visitante if visitante in resueltos else None
            if favorito and por_equipo[favorito]["ppp"]>=2:
                resultado["candidatos"].append(dict(
                    liga=liga,fecha=m["fecha"],local=local,visitante=visitante,
                    favorito=resueltos[favorito],equipo_proveedor=favorito,
                    ppp=por_equipo[favorito]["ppp"],cuota=None,
                    estado="Pendiente de cuota verificada"))
        for m in partidos:
            if m.get("estado")=="pendiente":
                resultado["partidos"].append(dict(liga=liga,fecha=m["fecha"],local=m["local"],visitante=m["visitante"]))
    # No publicar como próximos partidos con hora de inicio ya transcurrida.
    ahora=datetime.now(timezone.utc)
    def futuro(m):
        fecha=m["fecha"]
        if len(fecha)>10:
            instante=datetime.fromisoformat(fecha.replace("Z","+00:00"))
            if instante.tzinfo is None:
                return fecha[:10]>=ahora.date().isoformat()
            return instante>ahora
        return fecha>=ahora.date().isoformat()
    resultado["partidos"]=[m for m in resultado["partidos"] if futuro(m)]
    resultado["candidatos"]=[m for m in resultado["candidatos"] if futuro(m)]
    resultado["partidos"].sort(key=lambda m:m["fecha"])
    resultado["candidatos"].sort(key=lambda m:m["fecha"])
    aplicar_cuotas_bet365(resultado["candidatos"])
    resultado["dobles"]=generar_dobles(resultado["candidatos"])
    resultado["favoritos_validados"]=lista_validada
    return resultado

if __name__=="__main__":
    entrada=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    salida=Path(sys.argv[2])
    temporal=salida.with_suffix(".tmp")
    temporal.write_text(json.dumps(construir(entrada),ensure_ascii=False,indent=2),encoding="utf-8")
    temporal.replace(salida)
