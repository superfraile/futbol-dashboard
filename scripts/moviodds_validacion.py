"""Validaciones locales de datos MoviOdds. No consulta ni publica cuotas."""
from datetime import datetime, timezone
from math import isfinite
from scripts.construir_datos import clave_equipo, limite_antiguedad

def fecha_utc(valor):
    if not isinstance(valor,str):
        return None
    try:
        fecha=datetime.fromisoformat(valor.replace("Z","+00:00"))
    except ValueError:
        return None
    return fecha.astimezone(timezone.utc) if fecha.tzinfo else None

def fecha_comprobacion(partido, cuota, ahora):
    # ts registra cambios de precio; polled_at confirma lecturas del encuentro.
    cambio=fecha_utc(cuota.get("ts"))
    if cambio is None or cambio>ahora:
        return None
    # La lectura de otro mercado no confirma el 1X2.
    if "group_status" in partido:
        grupos=partido["group_status"]
        grupo=grupos.get(str(cuota.get("group_id"))) if isinstance(grupos,dict) else None
        if not isinstance(grupo,dict) or grupo.get("stale",False) is not False:
            return None
        lectura=fecha_utc(grupo.get("polled_at"))
        if lectura is None or lectura>ahora:
            return None
        return max(cambio,lectura)
    if "polled_at" not in partido:
        return cambio
    comprobacion=fecha_utc(partido.get("polled_at"))
    if comprobacion is None or comprobacion>ahora:
        return None
    return max(cambio,comprobacion)

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
        if q.get("suspended",False) is not False or q.get("phase","prematch")!="prematch":
            continue
        instante=fecha_comprobacion(partido,q,ahora)
        valor=q.get("odds_dec")
        if (instante is None or instante>ahora or (ahora-instante).total_seconds()>limite_antiguedad(inicio,ahora)
                or type(valor) not in (float,int) or not isfinite(valor) or valor<=1):
            continue
        # Duplicados para una misma selección son ambiguos: no escoger arbitrariamente.
        if signo in resultados:
            duplicados.add(signo)
        else:
            resultados[signo]={"cuota":valor,"consultada_en":instante.isoformat(),"ultimo_cambio":fecha_utc(q["ts"]).isoformat()}
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
        return {clave_equipo(valor),clave_equipo(equivalencias.get(valor,valor))} if isinstance(valor,str) else set()
    # Evaluar todas las relaciones antes de aceptar ninguna: el orden de entrada
    # no debe decidir a qué candidato se asigna un mismo partido.
    opciones_por_candidato={}
    candidatos_por_partido={}
    for indice_candidato,candidato in enumerate(candidatos):
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
        for indice_partido,partido in enumerate(partidos):
            if not isinstance(partido,dict) or partido.get("in_play") is not False:
                continue
            fecha=fecha_utc(partido.get("kickoff_utc"))
            if fecha is None or abs((fecha-inicio).total_seconds())>tolerancia_segundos:
                continue
            home=partido.get("home")
            away=partido.get("away")
            if (isinstance(home,str) and isinstance(away,str) and
                    clave_equipo(home) in local and clave_equipo(away) in visitante):
                opciones.append(indice_partido)
                candidatos_por_partido.setdefault(indice_partido,set()).add(indice_candidato)
        opciones_por_candidato[indice_candidato]=opciones
    return [(candidatos[i],partidos[opciones[0]])
            for i,opciones in opciones_por_candidato.items()
            if len(opciones)==1 and len(candidatos_por_partido[opciones[0]])==1]

CAMPOS_BOOKMAKER=("bookmaker","bookmaker_name","bookmaker_id",
                  "sportsbook","sportsbook_name","operator","operator_name","brand")

def atribucion_bet365(partido, cuota):
    """Exige identificación explícita y no contradictoria en el registro de cuota.

    La presencia de bet365 en otro partido o en otra selección no es suficiente.
    Si no hay atribución por selección, no se considera verificada.
    """
    if not isinstance(partido,dict) or not isinstance(cuota,dict):
        return False
    identificadores=[]
    for campo in CAMPOS_BOOKMAKER:
        if campo in cuota:
            valor=cuota[campo]
            if not isinstance(valor,str) or not valor.strip():
                return False
            identificadores.append(valor.casefold().replace(" ","").strip())
    # El origen del partido puede corroborar, pero nunca sustituir, el de la cuota.
    if not identificadores:
        return False
    if any(valor not in ("bet365","bet365.com","www.bet365.com","bet365.es",
                         "www.bet365.es") for valor in identificadores):
        return False
    for campo in CAMPOS_BOOKMAKER:
        if campo in partido:
            valor=partido[campo]
            if not isinstance(valor,str) or valor.casefold().replace(" ","").strip() not in (
                    "bet365","bet365.com","www.bet365.com","bet365.es","www.bet365.es"):
                return False
    return True
