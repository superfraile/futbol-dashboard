"""Importa cuotas MoviOdds 1X2 prepartido sin atribuirlas a bet365."""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from scripts.moviodds_validacion import emparejar_candidatos, mercado_1x2
from scripts.construir_datos import generar_dobles

URL="https://moviodds.com/odds?sport=soccer"

def incorporar(datos, partidos, ahora=None):
    ahora=ahora or datetime.now(timezone.utc)
    candidatos=datos.get("candidatos",[])
    for candidato, partido in emparejar_candidatos(candidatos,partidos):
        signo=("1" if candidato["equipo_proveedor"]==candidato["local"] else
               "2" if candidato["equipo_proveedor"]==candidato["visitante"] else None)
        cuota=mercado_1x2(partido,ahora).get(signo)
        if not cuota or not 1.20<=cuota["cuota"]<=1.80:
            continue
        # Mantener cuotas bet365 previamente documentadas; no confundir proveedores.
        if candidato.get("cuota_verificada") is True:
            continue
        candidato.update(cuota=cuota["cuota"],consultada_en=cuota["consultada_en"],
                         cuota_verificada=True,casa_apuestas="MoviOdds",
                         mercado="1X2",seleccion=signo,url_fuente=URL,
                         estado="Cuota MoviOdds; no verificada en bet365")
    datos["dobles"]=generar_dobles(candidatos,ahora)
    return datos

def main():
    clave=os.environ.get("MOVIODDS_API_KEY","").strip()
    if not clave:
        print("Sin clave MoviOdds: no se importan cuotas.")
        return 0
    ruta=Path(sys.argv[1] if len(sys.argv)>1 else "datos.json")
    datos=json.loads(ruta.read_text(encoding="utf-8"))
    solicitud=Request(URL,headers={"X-API-Key":clave,"Accept":"application/json",
                                    "User-Agent":"FutbolDashboard/1.0"})
    with urlopen(solicitud,timeout=25) as respuesta:
        documento=json.load(respuesta)
    partidos=documento.get("matches",[]) if isinstance(documento,dict) else []
    if not isinstance(partidos,list):
        raise ValueError("Formato MoviOdds no reconocido")
    incorporar(datos,partidos)
    temporal=ruta.with_suffix(".tmp")
    temporal.write_text(json.dumps(datos,ensure_ascii=False,indent=2),encoding="utf-8")
    temporal.replace(ruta)
    print("Cuotas MoviOdds importadas:",sum(p.get("casa_apuestas")=="MoviOdds" for p in datos["candidatos"]))
    print("Dobles publicadas:",len(datos["dobles"]))
    return 0

if __name__=="__main__":
    sys.exit(main())
