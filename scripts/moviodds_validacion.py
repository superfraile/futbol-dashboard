"""Validaciones locales de datos MoviOdds. No consulta ni publica cuotas."""
from datetime import datetime, timezone
from scripts.construir_datos import clave_equipo

def fecha_utc(valor):
    if not isinstance(valor,str):
        return None
    try:
        fecha=datetime.fromisoformat(valor.replace("Z","+00:00"))
    except ValueError:
        return None
    return fecha.astimezone(timezone.utc) if fecha.tzinfo else None

def mercado_1x2(partido, ahora=None):
    """Extrae únicamente selecciones prepartido 1X2 inequívocas, sin atribuir bookmaker."""
    ahora=ahora or datetime.now(timezone.utc)
    if not isinstance(partido,dict) or partido.get("in_play") is not False:
        return {}
    inicio=fecha_utc(partido.get("kickoff_utc"))
    if inicio is None or inicio<=ahora:
        return {}
    local=partido.get("home")
    visitante=partido.get("away")
    if not isinstance(local,str) or not isinstance(visitante,str):
        return {}
    if not local.strip() or not visitante.strip() or clave_equipo(local)==clave_equipo(visitante):
        return {}
    cuotas=partido.get("quotes")
    if not isinstance(cuotas,list):
        return {}
    resultados={}
    duplicados=set()
    for q in cuotas:
        if not isinstance(q,dict) or str(q.get("group_id"))!="40":
            continue
        etiqueta=q.get("label")
        if not isinstance(etiqueta,str):
            continue
        signo=("1" if clave_equipo(etiqueta)==clave_equipo(local) else
               "2" if clave_equipo(etiqueta)==clave_equipo(visitante) else
               "X" if etiqueta.strip().casefold()=="draw" else None)
        if signo is None:
            continue
        instante=fecha_utc(q.get("ts"))
        valor=q.get("odds_dec")
        if (instante is None or instante>ahora or (ahora-instante).total_seconds()>3600
                or type(valor) not in (float,int) or valor<=1):
            continue
        # Duplicados para una misma selección son ambiguos: no escoger arbitrariamente.
        if signo in resultados:
            duplicados.add(signo)
        else:
            resultados[signo]={"cuota":valor,"consultada_en":instante.isoformat()}
    return {k:v for k,v in resultados.items() if k not in duplicados}

def emparejar_candidatos(candidatos, partidos, equivalencias=None, tolerancia_segundos=10800):
    """Relaciona partidos únicamente por ambos equipos y horario; descarta ambigüedades.

    equivalencias: mapeo explícitamente revisado de nombre del proveedor deportivo
    a nombre de MoviOdds. Nunca usa similitud aproximada.
    """
    equivalencias=equivalencias or {}
    if not isinstance(candidatos,list) or not isinstance(partidos,list):
        raise ValueError("Se requieren listas de partidos")
    if not isinstance(equivalencias,dict):
        raise ValueError("Equivalencias inválidas")
    def nombre(valor):
        return clave_equipo(equivalencias.get(valor,valor)) if isinstance(valor,str) else None
    resultado=[]
    usados=set()
    for candidato in candidatos:
        if not isinstance(candidato,dict):
            continue
        inicio=fecha_utc(candidato.get("fecha"))
        if inicio is None:
            continue
        local=nombre(candidato.get("local"))
        visitante=nombre(candidato.get("visitante"))
        if not local or not visitante or local==visitante:
            continue
        opciones=[]
        for indice,partido in enumerate(partidos):
            if not isinstance(partido,dict) or partido.get("in_play") is not False:
                continue
            fecha=fecha_utc(partido.get("kickoff_utc"))
            if fecha is None or abs((fecha-inicio).total_seconds())>tolerancia_segundos:
                continue
            if clave_equipo(partido.get("home",""))==local and clave_equipo(partido.get("away",""))==visitante:
                opciones.append((indice,partido))
        if len(opciones)==1:
            indice,partido=opciones[0]
            if indice not in usados:
                resultado.append((candidato,partido))
                usados.add(indice)
    return resultado
