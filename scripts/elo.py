"""Elo experimental por liga; no es ClubElo ni una probabilidad calibrada."""
from collections import defaultdict
def elo(partidos, inicial=1500, k=20, ventaja_local=60):
    ratings=defaultdict(lambda: float(inicial))
    for m in sorted(partidos,key=lambda x:x["fecha"]):
        if m.get("estado")!="finalizado": continue
        a,b=m["local"],m["visitante"]
        x,y=m["goles_local"],m["goles_visitante"]
        esperado=1/(1+10**((ratings[b]-ratings[a]-ventaja_local)/400))
        real=1 if x>y else .5 if x==y else 0
        delta=k*(real-esperado)
        ratings[a]+=delta
        ratings[b]-=delta
    return dict(ratings)
