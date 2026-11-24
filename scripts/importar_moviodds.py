"""Importa cuotas MoviOdds 1X2 prepartido sin atribuirlas a bet365."""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from scripts.moviodds_validacion import emparejar_candidatos, mercado_1x2, fecha_utc
from scripts.construir_datos import generar_dobles, clave_equipo, limite_antiguedad

URL="https://moviodds.com/odds?sport=soccer"

# Equivalencias explícitas observadas en el feed con horarios compatibles.
EQUIVALENCIAS={
    "Real Betis Balompié":"Real Betis",
    "Rayo Vallecano de Madrid":"Rayo Vallecano",
    "Hamburger SV":"Hamburg",
    "FC Bayern München":"Bayern Munich",
    "Elche CF":"Elche",
    "Club Atlético de Madrid":"Atletico Madrid",
    "FC Internazionale Milano":"Inter Milan",
    "Genoa CFC":"Genoa",
    "Real Madrid CF":"Real Madrid",
    "Deportivo Alavés":"CD Alaves",
    "RC Deportivo La Coruña":"Deportivo A Coruna",
    "FC Barcelona":"Barcelona",
    "Cagliari Calcio":"Cagliari",
    "Sport Lisboa e Benfica":"Benfica",
    "FC Famalicão":"Famalicao",
}


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
    for candidato, partido in emparejar_candidatos(candidatos,partidos,EQUIVALENCIAS):
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
    emparejados=emparejar_candidatos(candidatos,partidos,EQUIVALENCIAS)
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
    diagnostico={
        "partidos_proveedor":len(partidos),
        "candidatos":len(candidatos),
        "candidatos_sin_hora":sin_hora,
        "emparejamientos_unicos":len(emparejados),
        "emparejados_con_mercado_1x2_vigente":con_mercado,
        "selecciones_en_rango":elegibles,
        "emparejados_con_favorito_identificado":con_signo,
        "sin_cuota_vigente_del_favorito":sin_cuota_favorito,
        "cuotas_fuera_de_1_20_a_1_80":fuera_rango
    }
    # Medir coincidencias de equipos sin relajar la regla estricta de publicación.
    pares_proveedor=set()
    for partido in partidos:
        if not isinstance(partido,dict):
            continue
        local,visitante=partido.get("home"),partido.get("away")
        if isinstance(local,str) and isinstance(visitante,str):
            pares_proveedor.add((clave_equipo(local),clave_equipo(visitante)))
    pares_identicos=0
    for candidato in candidatos:
        local,visitante=candidato.get("local"),candidato.get("visitante")
        if isinstance(local,str) and isinstance(visitante,str):
            if (clave_equipo(local),clave_equipo(visitante)) in pares_proveedor:
                pares_identicos+=1
    diagnostico["candidatos_con_nombres_exactos_en_proveedor"]=pares_identicos
    diagnostico["coincidencias_nombres_sin_horario_compatible"]=max(0,pares_identicos-len(emparejar_candidatos(candidatos,partidos)))
    # Diferencias horarias agregadas para coincidencias exactas por equipos.
    # No relajar el umbral de 3 horas: solo diagnóstico.
    horarios_proveedor={}
    for partido in partidos:
        if not isinstance(partido,dict):
            continue
        local,visitante=partido.get("home"),partido.get("away")
        inicio=fecha_utc(partido.get("kickoff_utc"))
        if isinstance(local,str) and isinstance(visitante,str) and inicio is not None:
            horarios_proveedor.setdefault((clave_equipo(local),clave_equipo(visitante)),[]).append(inicio)
    diferencias=[]
    for candidato in candidatos:
        local,visitante=candidato.get("local"),candidato.get("visitante")
        inicio=fecha_utc(candidato.get("fecha"))
        if not isinstance(local,str) or not isinstance(visitante,str) or inicio is None:
            continue
        opciones=horarios_proveedor.get((clave_equipo(local),clave_equipo(visitante)),[])
        if opciones:
            diferencias.append(min(abs((fecha-inicio).total_seconds()) for fecha in opciones))
    diagnostico["nombres_coincidentes_con_horario_mas_de_3h"]=sum(delta>10800 for delta in diferencias)
    diagnostico["nombres_coincidentes_sin_hora_proveedor"]=max(0,pares_identicos-len(diferencias))
    # Distinguir mercados ausentes, marcas temporales caducadas y etiquetas no reconocidas.
    from collections import Counter
    motivos=Counter()
    for candidato,partido in emparejados:
        cuotas=partido.get("quotes",[])
        if not isinstance(cuotas,list):
            motivos["sin_lista_cuotas"]+=1
            continue
        grupo=[q for q in cuotas if isinstance(q,dict) and str(q.get("group_id"))=="40"]
        if not grupo:
            motivos["sin_grupo_1x2"]+=1
            continue
        motivos["con_grupo_1x2"]+=1
        recientes=[q for q in grupo if (lambda t:t is not None and
                   0<=(ahora-t).total_seconds()<=limite_antiguedad(fecha_utc(partido["kickoff_utc"]),ahora))(fecha_utc(q.get("ts")))]
        if not recientes:
            motivos["grupo_1x2_sin_cotizaciones_recientes"]+=1
        else:
            motivos["grupo_1x2_con_cotizaciones_recientes"]+=1
        if not mercado_1x2(partido,ahora):
            motivos["grupo_1x2_no_interpretable"]+=1
    diagnostico["detalle_mercado_1x2"]=dict(motivos)
    # Identificar el formato real de las marcas de tiempo, sin publicar sus valores.
    tipos_ts={}
    campos_temporales=("ts","timestamp","updated_at","last_update","last_updated")
    for candidato,partido in emparejados:
        for cuota in partido.get("quotes",[]) if isinstance(partido.get("quotes"),list) else []:
            if not isinstance(cuota,dict) or str(cuota.get("group_id"))!="40":
                continue
            for campo in campos_temporales:
                if campo in cuota:
                    valor=cuota[campo]
                    formato=("iso_con_zona" if fecha_utc(valor) is not None else
                             "texto_sin_zona_o_invalido" if isinstance(valor,str) else
                             "numero" if isinstance(valor,(float,int)) and not isinstance(valor,bool) else
                             type(valor).__name__)
                    etiqueta=campo+":"+formato
                    tipos_ts[etiqueta]=tipos_ts.get(etiqueta,0)+1
    diagnostico["formatos_fechas_cuotas"]=tipos_ts
    # Propuestas para revisión manual: nunca se usan para publicar cuotas.
    from difflib import SequenceMatcher
    propuestas=[]
    for candidato in candidatos:
        inicio=fecha_utc(candidato.get("fecha"))
        if inicio is None or any(candidato is x for x,_ in emparejados):
            continue
        opciones=[]
        for partido in partidos:
            if not isinstance(partido,dict) or partido.get("in_play") is not False:
                continue
            fecha=fecha_utc(partido.get("kickoff_utc"))
            home,away=partido.get("home"),partido.get("away")
            if fecha is None or abs((fecha-inicio).total_seconds())>10800:
                continue
            if not isinstance(home,str) or not isinstance(away,str):
                continue
            a=SequenceMatcher(None,clave_equipo(candidato["local"]),clave_equipo(home)).ratio()
            b=SequenceMatcher(None,clave_equipo(candidato["visitante"]),clave_equipo(away)).ratio()
            if min(a,b)>=0.45 and (a+b)/2>=0.65:
                opciones.append((round((a+b)/2,3),home,away))
        if opciones:
            propuestas.append({"local":candidato["local"],"visitante":candidato["visitante"],
                               "posibles":sorted(opciones,reverse=True)[:3]})
    diagnostico["propuestas_equivalencias_no_validadas"]=propuestas

    # Antigüedad agregada, sin exponer precios ni nombres de partidos.
    edades=[]
    for _,partido in emparejados:
        for cuota in partido.get("quotes",[]) if isinstance(partido.get("quotes"),list) else []:
            if not isinstance(cuota,dict) or str(cuota.get("group_id"))!="40":
                continue
            instante=fecha_utc(cuota.get("ts"))
            if instante is not None:
                edades.append((ahora-instante).total_seconds())
    if edades:
        diagnostico["antiguedad_1x2_minima_minutos"]=round(min(edades)/60,1)
        diagnostico["antiguedad_1x2_maxima_minutos"]=round(max(edades)/60,1)
        diagnostico["cotizaciones_1x2_futuras"]=sum(edad<0 for edad in edades)
        diagnostico["cotizaciones_1x2_mas_de_60_minutos"]=sum(edad>3600 for edad in edades)




    print("Diagnóstico MoviOdds:",json.dumps(diagnostico,ensure_ascii=False))
    incorporar(datos,partidos,ahora)
    datos["diagnostico_cuotas"]=diagnostico
    datos.pop("error_actualizacion_cuotas",None)
    temporal=ruta.with_suffix(".tmp")
    temporal.write_text(json.dumps(datos,ensure_ascii=False,indent=2),encoding="utf-8")
    temporal.replace(ruta)
    print("Cuotas MoviOdds importadas:",sum(p.get("casa_apuestas")=="MoviOdds" for p in datos["candidatos"]))
    print("Dobles publicadas:",len(datos["dobles"]))
    return 0

def registrar_fallo(motivo):
    ruta=Path(sys.argv[1] if len(sys.argv)>1 else "datos.json")
    datos=json.loads(ruta.read_text(encoding="utf-8"))
    datos["error_actualizacion_cuotas"]={
        "fecha":datetime.now(timezone.utc).isoformat(),
        "motivo":motivo
    }
    temporal=ruta.with_suffix(".tmp")
    temporal.write_text(json.dumps(datos,ensure_ascii=False,indent=2),encoding="utf-8")
    temporal.replace(ruta)
    print("ERROR MoviOdds:",motivo)

def ejecutar():
    try:
        resultado=main()
        if resultado:
            registrar_fallo("Clave API no configurada")
        return resultado
    except HTTPError as error:
        motivo=f"HTTP {error.code}"
    except (URLError,TimeoutError):
        motivo="Error de conexión o tiempo de espera"
    except (ValueError,TypeError,KeyError):
        motivo="Respuesta inválida o datos incompatibles"
    except Exception as error:
        motivo="Error interno: "+type(error).__name__
    registrar_fallo(motivo)
    return 2

if __name__=="__main__":
    sys.exit(ejecutar())
