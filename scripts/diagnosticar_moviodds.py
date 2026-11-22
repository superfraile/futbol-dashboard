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
        # Verificar si el proveedor identifica explícitamente la casa de apuestas.
        # Nunca inferir que una cuota es de bet365 por pertenecer al mercado 1X2.
        campos_casa=("bookmaker","bookmaker_name","bookmaker_id","sportsbook",
                     "sportsbook_name","operator","operator_name","brand","source")
        campos_presentes=set()
        valores_casa=set()
        for m in con_cuotas:
            for objeto in (m,):
                for campo in campos_casa:
                    if campo in objeto:
                        campos_presentes.add("partido."+campo)
                        if isinstance(objeto[campo],str):
                            valores_casa.add(objeto[campo].strip().casefold())
            for q in m.get("quotes",[]):
                if not isinstance(q,dict):
                    continue
                for campo in campos_casa:
                    if campo in q:
                        campos_presentes.add("quote."+campo)
                        if isinstance(q[campo],str):
                            valores_casa.add(q[campo].strip().casefold())
        print("Campos de atribución de casa de apuestas:",sorted(campos_presentes))
        print("Referencia explícita a bet365 en campos de casa:",any(
            "bet365" in v for v in valores_casa))
        if not campos_presentes:
            print("AVISO: no hay atribución de bookmaker en los campos examinados; prohibido publicar como bet365.")
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
        # Diagnóstico de emparejamiento con la preselección publicada.
        # Exige coincidencia de ambos equipos y fecha de inicio dentro de 3 horas;
        # no importa cuotas ni publica los nombres de los partidos.
        from pathlib import Path
        ruta=Path(__file__).resolve().parent.parent/"datos.json"
        if ruta.is_file():
            candidatos=json.loads(ruta.read_text(encoding="utf-8")).get("candidatos",[])
            encontrados=0
            ambiguos=0
            sin_hora=0
            for p in candidatos:
                try:
                    if len(p["fecha"])<=10:
                        sin_hora+=1
                        continue
                    inicio=datetime.fromisoformat(p["fecha"].replace("Z","+00:00"))
                    if inicio.tzinfo is None:
                        sin_hora+=1
                        continue
                    opciones=[]
                    for m in partidos:
                        if not isinstance(m,dict) or m.get("in_play") is True:
                            continue
                        if normalizar(m.get("home"))!=normalizar(p["local"]) or normalizar(m.get("away"))!=normalizar(p["visitante"]):
                            continue
                        fecha=datetime.fromisoformat(m["kickoff_utc"].replace("Z","+00:00"))
                        if fecha.tzinfo is not None and abs((fecha-inicio).total_seconds())<=10800:
                            opciones.append(m)
                    if len(opciones)==1:
                        encontrados+=1
                    elif len(opciones)>1:
                        ambiguos+=1
                except (ValueError,TypeError,KeyError,AttributeError):
                    continue
            print("Candidatos del dashboard:",len(candidatos))
            print("Emparejados exactamente con MoviOdds:",encontrados)
            print("Emparejamientos ambiguos descartados:",ambiguos)
            print("Candidatos sin hora precisa:",sin_hora)
            # Distinguir ausencia de partido, diferencia horaria y variación de nombres.
            # Solo se imprimen contadores agregados, nunca nombres ni cuotas.
            coincidencia_equipos=0
            coincidencia_hora=0
            solo_un_equipo=0
            candidatos_validos=0
            for p in candidatos:
                try:
                    if len(p["fecha"])<=10:
                        continue
                    inicio=datetime.fromisoformat(p["fecha"].replace("Z","+00:00"))
                    if inicio.tzinfo is None:
                        continue
                    candidatos_validos+=1
                    local=normalizar(p["local"])
                    visitante=normalizar(p["visitante"])
                    ambos=False
                    hora=False
                    uno=False
                    for m in partidos:
                        if not isinstance(m,dict) or m.get("in_play") is True:
                            continue
                        ml=normalizar(m.get("home"))
                        mv=normalizar(m.get("away"))
                        equipos=(ml==local and mv==visitante)
                        if ml==local or mv==visitante:
                            uno=True
                        if equipos:
                            ambos=True
                        try:
                            fecha=datetime.fromisoformat(m["kickoff_utc"].replace("Z","+00:00"))
                            if fecha.tzinfo is not None and abs((fecha-inicio).total_seconds())<=10800:
                                hora=True
                        except (ValueError,TypeError,KeyError,AttributeError):
                            pass
                    coincidencia_equipos+=int(ambos)
                    coincidencia_hora+=int(hora)
                    solo_un_equipo+=int(uno)
                except (ValueError,TypeError,KeyError,AttributeError):
                    continue
            print("Candidatos con hora válida analizados:",candidatos_validos)
            print("Ambos nombres exactos (independiente de fecha):",coincidencia_equipos)
            print("Hora coincidente (independiente de equipos):",coincidencia_hora)
            print("Al menos un equipo exacto:",solo_un_equipo)
            # Diagnóstico por fecha: similitud orientativa, sin emparejar ni publicar cuotas.
            from difflib import SequenceMatcher
            proximos=0
            nombres_parecidos=0
            alta_confianza=0
            ambiguedad=0
            for p in candidatos:
                try:
                    if len(p["fecha"])<=10:
                        continue
                    inicio=datetime.fromisoformat(p["fecha"].replace("Z","+00:00"))
                    if inicio.tzinfo is None:
                        continue
                    opciones=[]
                    for m in partidos:
                        if not isinstance(m,dict) or m.get("in_play") is True:
                            continue
                        t=datetime.fromisoformat(m["kickoff_utc"].replace("Z","+00:00"))
                        if t.tzinfo is None or abs((t-inicio).total_seconds())>10800:
                            continue
                        a=SequenceMatcher(None,normalizar(p["local"]),normalizar(m.get("home"))).ratio()
                        b=SequenceMatcher(None,normalizar(p["visitante"]),normalizar(m.get("away"))).ratio()
                        opciones.append((min(a,b),a,b))
                    if opciones:
                        proximos+=1
                        compatibles=[o for o in opciones if o[1]>=0.65 and o[2]>=0.65]
                        if compatibles:
                            nombres_parecidos+=1
                        fuertes=[o for o in opciones if o[1]>=0.85 and o[2]>=0.85]
                        if len(fuertes)==1:
                            alta_confianza+=1
                        elif len(fuertes)>1:
                            ambiguedad+=1
                except (ValueError,TypeError,KeyError,AttributeError):
                    continue
            print("Candidatos con al menos un partido a ±3h:",proximos)
            print("Similitud >=65% en ambos equipos:",nombres_parecidos)
            print("Similitud >=85% en ambos, coincidencia única:",alta_confianza)
            print("Coincidencias fuertes ambiguas:",ambiguedad)
            print("Estas similitudes son diagnósticas: no autorizan importar cuotas.")
            # Resumen limitado a los próximos siete días: es la ventana operativa del panel.
            from datetime import timedelta
            ahora=datetime.now(timezone.utc)
            fin=ahora+timedelta(days=7)
            ventana=[]
            for p in candidatos:
                try:
                    fecha=datetime.fromisoformat(p["fecha"].replace("Z","+00:00"))
                    if fecha.tzinfo is not None and ahora<fecha<=fin:
                        ventana.append(p)
                except (ValueError,TypeError,KeyError,AttributeError):
                    pass
            exactos_7=0
            similares_7=0
            vigentes_7=0
            for p in ventana:
                inicio=datetime.fromisoformat(p["fecha"].replace("Z","+00:00"))
                coincidencias=[]
                for m in partidos:
                    try:
                        if not isinstance(m,dict) or m.get("in_play") is True:
                            continue
                        fecha=datetime.fromisoformat(m["kickoff_utc"].replace("Z","+00:00"))
                        if fecha.tzinfo is None or abs((fecha-inicio).total_seconds())>10800:
                            continue
                        local=SequenceMatcher(None,normalizar(p["local"]),normalizar(m.get("home"))).ratio()
                        visitante=SequenceMatcher(None,normalizar(p["visitante"]),normalizar(m.get("away"))).ratio()
                        if local>=0.85 and visitante>=0.85:
                            coincidencias.append(m)
                    except (ValueError,TypeError,KeyError,AttributeError):
                        continue
                if len(coincidencias)==1:
                    similares_7+=1
                    m=coincidencias[0]
                    if normalizar(p["local"])==normalizar(m["home"]) and normalizar(p["visitante"])==normalizar(m["away"]):
                        exactos_7+=1
                    favorito=normalizar(p.get("equipo_proveedor"))
                    nombre=m["home"] if favorito==normalizar(p["local"]) else m["away"] if favorito==normalizar(p["visitante"]) else None
                    if nombre:
                        for q in m.get("quotes",[]):
                            try:
                                t=datetime.fromisoformat(q["ts"].replace("Z","+00:00"))
                                if (str(q.get("group_id"))=="40" and normalizar(q.get("label"))==normalizar(nombre)
                                    and t.tzinfo is not None and 0<=(ahora-t).total_seconds()<=3600
                                    and isinstance(q.get("odds_dec"),(int,float))
                                    and not isinstance(q.get("odds_dec"),bool)
                                    and 1.2<=q["odds_dec"]<=1.8):
                                    vigentes_7+=1
                                    break
                            except (ValueError,TypeError,KeyError,AttributeError):
                                continue
            # Ejecutar también el motor de emparejamiento estricto que se usará
            # para la futura integración, sin autorizar la publicación de cuotas.
            from scripts.moviodds_validacion import emparejar_candidatos, mercado_1x2
            emparejados=emparejar_candidatos(ventana,partidos)
            from scripts.moviodds_validacion import atribucion_bet365, fecha_utc
            cuotas_estrictas=0
            cuotas_bet365_atribuidas=0
            for candidato,partido in emparejados:
                signo=("1" if candidato.get("equipo_proveedor")==candidato.get("local")
                       else "2" if candidato.get("equipo_proveedor")==candidato.get("visitante")
                       else None)
                seleccion=mercado_1x2(partido,ahora).get(signo)
                if not seleccion or not 1.20<=seleccion["cuota"]<=1.80:
                    continue
                cuotas_estrictas+=1
                # Corroborar la atribución en la misma selección y timestamp,
                # no en otra cuota del mismo partido.
                nombre=partido["home"] if signo=="1" else partido["away"] if signo=="2" else None
                coincidencias=[
                    q for q in partido.get("quotes",[])
                    if isinstance(q,dict) and str(q.get("group_id"))=="40"
                    and normalizar(q.get("label"))==normalizar(nombre)
                    and q.get("odds_dec")==seleccion["cuota"]
                    and fecha_utc(q.get("ts"))==fecha_utc(seleccion["consultada_en"])
                ]
                if len(coincidencias)==1 and atribucion_bet365(partido,coincidencias[0]):
                    cuotas_bet365_atribuidas+=1
            print("Motor estricto: partidos únicos emparejados:",len(emparejados))
            print("Motor estricto: cuotas vigentes en rango (bookmaker no verificado):",cuotas_estrictas)
            print("Motor estricto: cuotas atribuidas explícitamente a bet365:",cuotas_bet365_atribuidas)
            print("Próximos 7 días: candidatos con hora:",len(ventana))
            print("Próximos 7 días: emparejamientos exactos:",exactos_7)
            print("Próximos 7 días: coincidencias únicas con similitud >=85%:",similares_7)
            print("Próximos 7 días: coincidencias con cuota candidata vigente 1.20-1.80:",vigentes_7)
            print("Las coincidencias aproximadas no se importan sin validación adicional.")
            print("Los no emparejados requerirán equivalencias de nombres verificadas.")
        print("No se ha importado ninguna cuota; falta validar esquema y mercado.")
        # Resumen permanente en la vista principal de cada ejecución de GitHub Actions.
        # No incluye cuotas, credenciales ni datos de partidos.
        resumen=os.environ.get("GITHUB_STEP_SUMMARY")
        if resumen:
            with open(resumen,"a",encoding="utf-8") as salida:
                salida.write("## Diagnóstico MoviOdds\n\n")
                salida.write(f"- Partidos recibidos: **{len(partidos)}**\n")
                salida.write(f"- Partidos con cuotas: **{len(con_cuotas)}**\n")
                salida.write(f"- Atribución explícita a bet365: **{'Sí' if any('bet365' in v for v in valores_casa) else 'No verificada'}**\n")
                if ruta.is_file():
                    salida.write(f"- Candidatos próximos 7 días con hora: **{len(ventana)}**\n")
                    salida.write(f"- Coincidencias exactas: **{exactos_7}**\n")
                    salida.write(f"- Emparejamientos únicos del motor estricto: **{len(emparejados)}**\n")
                    salida.write(f"- Cuotas en rango del motor estricto (bookmaker no verificado): **{cuotas_estrictas}**\n")
                    salida.write(f"- Cuotas atribuidas expresamente a bet365: **{cuotas_bet365_atribuidas}**\n")
                    salida.write(f"- Coincidencias únicas aproximadas (no importables): **{similares_7}**\n")
                    salida.write(f"- Cuotas candidatas vigentes 1,20–1,80 (sin verificar casa): **{vigentes_7}**\n")
                salida.write("\n**Estado:** solo diagnóstico; no se han publicado cuotas ni generado dobles.\n")

        return 0
    except HTTPError as error:
        print("ERROR HTTP",error.code,"en MoviOdds (sin imprimir cuerpo ni cabeceras).")
    except (URLError,TimeoutError,ValueError,OSError) as error:
        print("ERROR de conexión o formato:",type(error).__name__)
    return 1

if __name__=="__main__":
    sys.exit(main())
