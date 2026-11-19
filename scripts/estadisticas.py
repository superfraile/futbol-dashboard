"""Calcula estadísticas a partir de partidos finalizados y validados.
No representa clasificación oficial: no incorpora sanciones ni desempates especiales.
"""
from collections import defaultdict

def calcular(partidos):
    equipos = defaultdict(lambda: {"pj":0,"g":0,"e":0,"p":0,"gf":0,"gc":0,"puntos":0})
    vistos=set()
    for m in partidos:
        if m.get("estado") != "finalizado":
            continue
        local, visitante = m["local"], m["visitante"]
        a,b=m["goles_local"],m["goles_visitante"]
        if local==visitante or any(type(x) is not int or x<0 for x in (a,b)):
            raise ValueError("Resultado inválido")
        clave=(m["fecha"],local,visitante)
        if clave in vistos:
            raise ValueError("Partido duplicado")
        vistos.add(clave)
        for nombre,gf,gc in [(local,a,b),(visitante,b,a)]:
            s=equipos[nombre]
            s["pj"]+=1
            s["gf"]+=gf
            s["gc"]+=gc
            s["g"]+=int(gf>gc)
            s["e"]+=int(gf==gc)
            s["p"]+=int(gf<gc)
            s["puntos"]+=3 if gf>gc else int(gf==gc)
    rows=[dict(equipo=n,**s) for n,s in equipos.items()]
    rows.sort(key=lambda s:(-s["puntos"],s["gc"]-s["gf"],-s["gf"],s["equipo"]))
    for i,s in enumerate(rows,1):
        s["posicion"]=i
        s["ppp"]=round(s["puntos"]/s["pj"],2)
    return rows
