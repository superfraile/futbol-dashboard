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
        # Muestra únicamente los nombres de campos y tipos de una cuota, nunca valores.
        partidos=datos.get("matches",[]) if isinstance(datos,dict) else []
        con_cuotas=[m for m in partidos if isinstance(m,dict) and isinstance(m.get("quotes"),list) and m["quotes"]]
        print("Partidos con quotes no vacías:",len(con_cuotas))
        if con_cuotas:
            print("Estructura de la primera quote (solo tipos):")
            print(json.dumps(estructura(con_cuotas[0]["quotes"][0]),ensure_ascii=False,indent=2))
        # Resumen acotado de mercados y selecciones, sin publicar cuotas ni equipos.
        from collections import Counter
        grupos=Counter()
        lados=Counter()
        fases=Counter()
        for partido in con_cuotas:
            if partido.get("in_play") is True:
                continue
            for q in partido["quotes"]:
                if not isinstance(q,dict):
                    continue
                if str(q.get("group_id","")) in ("40",):
                    grupos[(str(q.get("group_id")),str(q.get("group_name")))]+=1
                    lados[(str(q.get("side")),str(q.get("label")))]+=1
                    fases[str(q.get("phase"))]+=1
        print("Grupo 40, nombres y frecuencias:",grupos.most_common(5))
        print("Grupo 40, lados/etiquetas y frecuencias:",lados.most_common(12))
        print("Grupo 40, fases y frecuencias:",fases.most_common(8))
        # Comprobar si las etiquetas de victoria coinciden con los nombres de los equipos.
        # No muestra nombres, precios ni información privada.
        import unicodedata
        from datetime import datetime, timezone
        def normalizar(s):
            return "".join(x for x in unicodedata.normalize("NFKD",str(s).casefold())
                           if x.isalnum() and not unicodedata.combining(x))
        coincidencias=Counter()
        antiguedades=Counter()
        for m in con_cuotas:
            if m.get("in_play") is True:
                continue
            try:
                inicio=datetime.fromisoformat(m["kickoff_utc"].replace("Z","+00:00"))
                if inicio.tzinfo is None or inicio<=datetime.now(timezone.utc):
                    continue
            except (ValueError,TypeError,KeyError,AttributeError):
                continue
            etiquetas={normalizar(m.get("home")):"local",normalizar(m.get("away")):"visitante"}
            for q in m["quotes"]:
                if not isinstance(q,dict) or str(q.get("group_id"))!="40":
                    continue
                lado=etiquetas.get(normalizar(q.get("label")))
                coincidencias[lado or "sin coincidencia"]+=1
                try:
                    t=datetime.fromisoformat(q["ts"].replace("Z","+00:00"))
                    segundos=(datetime.now(timezone.utc)-t).total_seconds()
                    antiguedades["<=1h" if 0<=segundos<=3600 else ">1h o futuro"]+=1
                except (KeyError,ValueError,TypeError,AttributeError):
                    antiguedades["sin timestamp válido"]+=1
        print("Grupo 40 futuro: coincidencia exacta de etiquetas:",dict(coincidencias))
        print("Grupo 40 futuro: vigencia de registros:",dict(antiguedades))
        print("No se ha importado ninguna cuota; falta validar esquema y mercado.")
        return 0
    except HTTPError as error:
        print("ERROR HTTP",error.code,"en MoviOdds (sin imprimir cuerpo ni cabeceras).")
    except (URLError,TimeoutError,ValueError,OSError) as error:
        print("ERROR de conexión o formato:",type(error).__name__)
    return 1

if __name__=="__main__":
    sys.exit(main())
