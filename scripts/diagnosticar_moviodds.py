"""Diagnóstico seguro de la API MoviOdds: no publica cuotas ni credenciales."""
import json
import os
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

URL="https://moviodds.com/odds?sport=soccer"

def estructura(valor, profundidad=0):
    if profundidad>=3:
        return type(valor).__name__
    if isinstance(valor,dict):
        return {str(k):estructura(v,profundidad+1) for k,v in list(valor.items())[:20]}
    if isinstance(valor,list):
        return {"tipo":"lista","elementos":len(valor),
                "ejemplo_estructura":estructura(valor[0],profundidad+1) if valor else None}
    return type(valor).__name__

def main():
    clave=os.environ.get("MOVIODDS_API_KEY","").strip()
    if not clave:
        print("ERROR: falta el secreto MOVIODDS_API_KEY.")
        return 2
    try:
        solicitud=Request(URL,headers={"X-API-Key":clave,"Accept":"application/json",
                                      "User-Agent":"FutbolDashboard/1.0"})
        with urlopen(solicitud,timeout=25) as respuesta:
            datos=json.load(respuesta)
        print("Conexión HTTP correcta; estructura de la respuesta (sin valores):")
        print(json.dumps(estructura(datos),ensure_ascii=False,indent=2))
        print("No se ha importado ninguna cuota; falta validar esquema y mercado.")
        return 0
    except HTTPError as error:
        print("ERROR HTTP",error.code,"en MoviOdds (sin imprimir cuerpo ni cabeceras).")
    except (URLError,TimeoutError,ValueError,OSError) as error:
        print("ERROR de conexión o formato:",type(error).__name__)
    return 1

if __name__=="__main__":
    sys.exit(main())
