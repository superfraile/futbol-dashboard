"""Genera el JSON del panel desde un fichero de partidos previamente validado.
Uso: python -m scripts.construir_datos entrada.json salida.json
No descarga ni publica información por su cuenta.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from scripts.estadisticas import calcular, desglosar
from scripts.elo import elo

LIGAS="GER DEN SCO ESP FRA GRE ENG ITA NOR NED POR SWE SUI TUR".split()

def construir(entrada):
    fuente=entrada["fuente"]
    if not isinstance(fuente,str) or not fuente.strip():
        raise ValueError("Fuente obligatoria")
    resultado=dict(version="1.1",ultima_actualizacion=datetime.now(timezone.utc).isoformat(),
                   fuente=fuente,ligas={},equipos_top=[],partidos=[],estadisticas={})
    for liga in LIGAS:
        partidos=entrada["ligas"].get(liga,[])
        tabla=calcular(partidos)
        rating=elo(partidos)
        resultado["ligas"][liga]=tabla
        resultado["estadisticas"][liga]=desglosar(partidos)
        for equipo,valor in sorted(rating.items(),key=lambda x:(-x[1],x[0]))[:5]:
            resultado["equipos_top"].append(dict(liga=liga,equipo=equipo,elo=round(valor,1)))
        for m in partidos:
            if m.get("estado")=="pendiente":
                resultado["partidos"].append(dict(liga=liga,fecha=m["fecha"],local=m["local"],visitante=m["visitante"]))
    resultado["partidos"].sort(key=lambda m:m["fecha"])
    return resultado

if __name__=="__main__":
    entrada=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    salida=Path(sys.argv[2])
    temporal=salida.with_suffix(".tmp")
    temporal.write_text(json.dumps(construir(entrada),ensure_ascii=False,indent=2),encoding="utf-8")
    temporal.replace(salida)
