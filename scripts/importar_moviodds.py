"""Importa cuotas MoviOdds 1X2 prepartido sin atribuirlas a bet365."""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from scripts.moviodds_validacion import emparejar_candidatos, mercado_1x2, fecha_utc
from scripts.construir_datos import generar_dobles

URL="https://moviodds.com/odds?sport=soccer"

def incorporar(datos, partidos, ahora=None):
    ahora=ahora or datetime.now(timezone.utc)
    candidatos=datos.get("candidatos",[])
    # Las cuotas MoviOdds anteriores no se conservan si el proveedor deja de devolverlas.
    for candidato in candidatos:
        if candidato.get("casa_apuestas")=="MoviOdds":
            for campo in ("cuota","consultada_en","cuota_verificada","casa_apuestas","mercado","seleccion","url_fuente"):
                candidato.pop(campo,None)
            candidato["cuota"]=None
            candidato["estado"]="Pendiente de cuota actualizada"
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
    datos["ultima_actualizacion_cuotas"]=ahora.isoformat()
    datos["dobles"]=generar_dobles(candidatos,ahora)
    return datos

def main():
    clave=os.environ.get("MOVIODDS_API_KEY","").strip()
    if not clave:
        print("ERROR: falta MOVIODDS_API_KEY; cuotas sin actualizar.")
        return 2
    ruta=Path(sys.argv[1] if len(sys.argv)>1 else "datos.json")
    datos=json.loads(ruta.read_text(encoding="utf-8"))
    solicitud=Request(URL,headers={"X-API-Key":clave,"Accept":"application/json",
                                    "User-Agent":"FutbolDashboard/1.0"})
    with urlopen(solicitud,timeout=25) as respuesta:
        documento=json.load(respuesta)
    if not isinstance(documento,dict) or "matches" not in documento:
        raise ValueError("Respuesta MoviOdds sin campo matches: no se publican cambios")
    partidos=documento["matches"]
    if not isinstance(partidos,list):
        raise ValueError("Formato MoviOdds no reconocido: matches debe ser lista")
    # Diagnóstico sin mostrar equipos, cuotas ni credenciales.
    ahora=datetime.now(timezone.utc)
    candidatos=datos.get("candidatos",[])
    emparejados=emparejar_candidatos(candidatos,partidos)
    sin_hora=sum(fecha_utc(p.get("fecha")) is None for p in candidatos)
    con_mercado=sum(bool(mercado_1x2(m,ahora)) for _,m in emparejados)
    elegibles=0
    for candidato,partido in emparejados:
        signo=("1" if candidato.get("equipo_proveedor")==candidato.get("local") else
               "2" if candidato.get("equipo_proveedor")==candidato.get("visitante") else None)
        q=mercado_1x2(partido,ahora).get(signo)
        if q and 1.20<=q["cuota"]<=1.80:
            elegibles+=1
    # Desglosar por causa, sin revelar nombres ni precios.
    con_signo=0
    con_mercado_favorito=0
    fuera_rango=0
    sin_cuota_favorito=0
    for candidato,partido in emparejados:
        signo=("1" if candidato.get("equipo_proveedor")==candidato.get("local") else
               "2" if candidato.get("equipo_proveedor")==candidato.get("visitante") else None)
        if signo is None:
            continue
        con_signo+=1
        cuota_favorito=mercado_1x2(partido,ahora).get(signo)
        if cuota_favorito is None:
            sin_cuota_favorito+=1
        else:
            con_mercado_favorito+=1
            if not 1.20<=cuota_favorito["cuota"]<=1.80:
                fuera_rango+=1
    print("Diagnóstico MoviOdds:",json.dumps({
        "partidos_proveedor":len(partidos),
        "candidatos":len(candidatos),
        "candidatos_sin_hora":sin_hora,
        "emparejamientos_unicos":len(emparejados),
        "emparejados_con_mercado_1x2_vigente":con_mercado,
        "selecciones_en_rango":elegibles,
        "emparejados_con_favorito_identificado":con_signo,
        "sin_cuota_vigente_del_favorito":sin_cuota_favorito,
        "cuotas_fuera_de_1_20_a_1_80":fuera_rango
    },ensure_ascii=False))
    incorporar(datos,partidos,ahora)
    temporal=ruta.with_suffix(".tmp")
    temporal.write_text(json.dumps(datos,ensure_ascii=False,indent=2),encoding="utf-8")
    temporal.replace(ruta)
    print("Cuotas MoviOdds importadas:",sum(p.get("casa_apuestas")=="MoviOdds" for p in datos["candidatos"]))
    print("Dobles publicadas:",len(datos["dobles"]))
    return 0

if __name__=="__main__":
    sys.exit(main())
