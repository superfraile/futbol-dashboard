"use strict";
const lista=document.getElementById("lista-ligas");
let datos=null, seleccion="GER";
function tabla(dest,headers,rows){
 const t=document.createElement("table"), h=t.createTHead().insertRow();
 headers.forEach(v=>{const c=document.createElement("th");c.textContent=v;h.append(c)});
 const fichas=["Equipo fijo","Local","Favorito fijo","Partido 1","Registro"].some(k=>headers.includes(k));
 if(fichas){t.className="fichas";t.setAttribute("role","table");}
 const b=t.createTBody();rows.forEach(row=>{const r=b.insertRow();row.forEach((v,i)=>{const c=r.insertCell();c.textContent=v??"—";c.setAttribute("data-label",headers[i]||"");})});
 dest.replaceChildren(t);
}
function liga(){
 const dest=document.getElementById("detalle-liga"), rows=datos?.ligas?.[seleccion]||[];
 if(!rows.length){dest.textContent="Sin datos verificados para esta liga.";return}
 tabla(dest,["Pos.","Equipo","PJ","G","E","P","GF","GC","Pts","Pts/PJ"],rows.map(r=>[r.posicion,r.equipo,r.pj,r.g,r.e,r.p,r.gf,r.gc,r.puntos,r.pj>0?(r.puntos/r.pj).toFixed(2):null]));
}
CONFIG.ligas.forEach(l=>{const b=document.createElement("button");b.className="liga";b.textContent=l.pais+" - "+l.nombre;b.onclick=()=>{seleccion=l.id;liga()};lista.append(b)});
function mostrar(id,boton){document.querySelectorAll(".seccion").forEach(s=>s.classList.remove("visible"));document.querySelectorAll("nav button").forEach(b=>b.classList.remove("activo"));document.getElementById(id).classList.add("visible");boton.classList.add("activo")}
async function iniciar(){
 try{const [publicados,listaFija]=await Promise.all([cargarDatos(),cargarFavoritos()]); datos=publicados; if(!datos||typeof datos.ligas!=="object")throw Error("Formato incorrecto");
 const cards=document.querySelectorAll("main > .resumen > .tarjeta");
 cards[0].querySelector(".numero").textContent=Object.values(datos.ligas).filter(t=>Array.isArray(t)&&t.length).length;
 cards[1].querySelector(".numero").textContent=Object.values(listaFija.ligas).flat().length;
 cards[2].querySelector(".numero").textContent=datos.partidos?.length||"—";
 const actualizacion=datos.ultima_actualizacion?new Date(datos.ultima_actualizacion):null;
 const horasAntiguedad=actualizacion?(Date.now()-actualizacion.getTime())/3600000:Infinity;
 cards[3].querySelector("p").textContent=actualizacion?actualizacion.toLocaleString("es-ES",{timeZone:"Europe/Madrid"}):"Sin datos verificados";
 if(horasAntiguedad>36){
   const avisoAntiguedad=document.createElement("p");
   avisoAntiguedad.setAttribute("role","status");
   avisoAntiguedad.textContent="AVISO: los datos deportivos tienen más de 36 horas; las clasificaciones y los filtros pueden estar desactualizados.";
   avisoAntiguedad.style.fontWeight="bold";
   document.querySelector(".resumen").append(avisoAntiguedad);
 }
 liga();
 const nombreLiga=id=>CONFIG.ligas.find(l=>l.id===id)?.pais||id;
 const fechaStats=id=>{const fecha=datos.fecha_estadisticas_por_liga?.[id]||datos.ultima_actualizacion;return fecha?new Date(fecha).toLocaleDateString("es-ES",{timeZone:"Europe/Madrid"}):null};
 const topPublicados=datos.favoritos_validados===true&&datos.equipos_top?.length===38?datos.equipos_top:[];
 tabla(document.querySelector("#favoritos .aviso"),["Liga","Equipo fijo","ELO estimado","Fecha Elo","Pts/PJ"],Object.entries(listaFija.ligas).flatMap(([liga,equipos])=>equipos.map(equipo=>{
   const r=topPublicados.find(x=>x.liga===liga&&x.equipo===equipo);
   const s=r?datos.ligas[liga]?.find(t=>t.equipo===r.equipo_proveedor):null;
   return [nombreLiga(liga),equipo,r?.elo??null,r?.elo!=null?fechaStats(liga):null,s?.ppp??null];
 })));
 const hoy=new Intl.DateTimeFormat("sv-SE",{timeZone:"Europe/Madrid",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date());
 const diaEspana=valor=>valor.length>10
   ?new Intl.DateTimeFormat("sv-SE",{timeZone:"Europe/Madrid",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date(valor))
   :valor.slice(0,10);
 const fechaEspana=valor=>valor.length>10?new Date(valor).toLocaleString("es-ES",{timeZone:"Europe/Madrid",day:"2-digit",month:"2-digit",year:"numeric",hour:"2-digit",minute:"2-digit"}):valor;
 const proximos=(datos.partidos||[]).filter(r=>r.fecha.length>10?Date.parse(r.fecha)>Date.now():r.fecha>=hoy).sort((a,b)=>a.fecha.localeCompare(b.fecha));
 cards[2].querySelector(".numero").textContent=datos.ultima_actualizacion?proximos.length:"—";
 const partidosDest=document.querySelector("#partidos .aviso");
 const filtro=document.getElementById("filtro-partidos");
 for(const l of CONFIG.ligas.filter(l=>proximos.some(p=>p.liga===l.id))){
   const opcion=document.createElement("option");
   opcion.value=l.id;opcion.textContent=l.pais+" - "+l.nombre;
   filtro.append(opcion);
 }
 function dibujarPartidos(){
   const filtrados=proximos.filter(r=>!filtro.value||r.liga===filtro.value).slice(0,100);
   if(filtrados.length){
     tabla(partidosDest,["Liga","Fecha (España)","Local","Visitante"],filtrados.map(r=>{
       const fecha=r.fecha.length>10?new Date(r.fecha).toLocaleString("es-ES",{timeZone:"Europe/Madrid",day:"2-digit",month:"2-digit",year:"numeric",hour:"2-digit",minute:"2-digit"}):r.fecha;
       return [nombreLiga(r.liga),fecha,r.local,r.visitante];
     }));
     const nota=document.createElement("p");
     nota.textContent="Mostrando "+filtrados.length+" de "+proximos.filter(r=>!filtro.value||r.liga===filtro.value).length+" partidos futuros.";
     partidosDest.append(nota);
   }else partidosDest.textContent="Sin próximos partidos para esta liga.";
 }
 filtro.addEventListener("change",dibujarPartidos);
 dibujarPartidos();
 const ahora=Date.now();
 const esFuturo=r=>{
   if(r.fecha.length>10){
     const instante=Date.parse(r.fecha);
     return Number.isFinite(instante)&&instante>ahora;
   }
   return r.fecha>=hoy;
 };
 const cuotaVigente=p=>{
   if(!["bet365","MoviOdds"].includes(p.casa_apuestas)||p.mercado!=="1X2"||p.cuota_verificada!==true||
      typeof p.cuota!=="number"||!Number.isFinite(p.cuota)||
      p.cuota<1.20||p.cuota>1.80||
      typeof p.fecha!=="string"||p.fecha.length<=10||
      typeof p.consultada_en!=="string"||typeof p.url_fuente!=="string")return false;
   const inicio=Date.parse(p.fecha),consulta=Date.parse(p.consultada_en);
   if(!Number.isFinite(inicio)||inicio<=ahora||
      !Number.isFinite(consulta)||consulta>ahora||
      consulta>=inicio||ahora-consulta>3600000*((inicio-ahora)>48*3600000?12:(inicio-ahora)>=24*3600000?6:(inicio-ahora)>=6*3600000?3:1))return false;
   try{
     const fuente=new URL(p.url_fuente);
     if(fuente.protocol!=="https:")return false;
     const dominios=p.casa_apuestas==="bet365"?["bet365.com","www.bet365.com","bet365.es","www.bet365.es"]:["moviodds.com","www.moviodds.com"];
     if(!dominios.includes(fuente.hostname))return false;
   }catch(_){return false;}
   const signo=p.equipo_proveedor===p.local?"1":p.equipo_proveedor===p.visitante?"2":null;
   return signo!==null&&p.seleccion===signo;
 };
 const candidatos=(datos.candidatos||[]).filter(esFuturo);
 const candidatosDest=document.getElementById("lista-candidatos");
 const filtroCandidatos=document.getElementById("filtro-candidatos");
 const plazoCandidatos=document.getElementById("plazo-candidatos");
 for(const l of CONFIG.ligas.filter(l=>candidatos.some(p=>p.liga===l.id))){
   const opcion=document.createElement("option");opcion.value=l.id;opcion.textContent=l.pais+" - "+l.nombre;filtroCandidatos.append(opcion);
 }
 function dibujarCandidatos(){
   if(datos.favoritos_validados!==true || datos.equipos_top?.length!==38){
     candidatosDest.textContent="La lista publicada todavía no coincide con los 38 favoritos confirmados.";return;
   }
   const dias=plazoCandidatos.value;
   // Siete días significa hoy y los seis días siguientes, en calendario español.
   const inicio=Date.parse(hoy+"T12:00:00Z");
   const fechaLimite=new Date(inicio+(Number(dias==="all"?3650:dias)-1)*86400000).toISOString().slice(0,10);
   const filtrados=candidatos.filter(r=>(!filtroCandidatos.value||r.liga===filtroCandidatos.value)&&(dias==="all"||diaEspana(r.fecha)<=fechaLimite)).sort((a,b)=>Number(b.valoracion??-Infinity)-Number(a.valoracion??-Infinity)||Number(b.ppp)-Number(a.ppp)||a.fecha.localeCompare(b.fecha));
   if(!filtrados.length){candidatosDest.textContent="Sin partidos preseleccionados para esta liga.";return;}
   tabla(candidatosDest,["Liga","Fecha","Local","Visitante","Favorito fijo","Pts/PJ","Pts/PJ rival","Bonus local","Valoración","Cuota"],filtrados.slice(0,100).map(r=>[
     nombreLiga(r.liga),fechaEspana(r.fecha),r.local,r.visitante,r.favorito,r.ppp,r.ppp_rival??"Sin datos",r.bonus_local??0,r.valoracion??"Sin datos",cuotaVigente(r)?r.cuota.toFixed(2)+" ("+r.casa_apuestas+"; "+new Date(r.consultada_en).toLocaleString("es-ES",{timeZone:"Europe/Madrid"})+")":(r.cuota_verificada===true?"Cuota caducada":r.motivo_cuota_moviodds||"Pendiente de cuota")
   ]));
   const aviso=document.createElement("p");
   aviso.textContent="Mostrando "+Math.min(100,filtrados.length)+" de "+filtrados.length+" partidos preseleccionados, ordenados por valoración (diferencia Pts/PJ + 0,2 si el favorito juega en casa). Cuotas disponibles (fuente indicada): "+filtrados.filter(p=>cuotaVigente(p)).length+". Las cuotas MoviOdds no son cuotas verificadas de bet365.";
   candidatosDest.append(aviso);
 }
 filtroCandidatos.addEventListener("change",dibujarCandidatos);
 plazoCandidatos.addEventListener("change",dibujarCandidatos);
 dibujarCandidatos();
 const cuotasActualizadas=datos.ultima_actualizacion_cuotas?new Date(datos.ultima_actualizacion_cuotas):null;
 const avisoCuotas=document.createElement("p");
 avisoCuotas.setAttribute("role","status");
 avisoCuotas.textContent=cuotasActualizadas
   ?"Última consulta de cuotas MoviOdds: "+cuotasActualizadas.toLocaleString("es-ES",{timeZone:"Europe/Madrid"})+
     (Date.now()-cuotasActualizadas.getTime()>3600000?" (más de una hora; comprobar vigencia de cada cuota)":"")
   :"Sin actualización automática de cuotas MoviOdds confirmada.";
 candidatosDest.parentElement.append(avisoCuotas);
 if(datos.error_actualizacion_cuotas){
   const error=document.createElement("p");
   error.setAttribute("role","status");
   error.textContent="Error en la última actualización MoviOdds: "+datos.error_actualizacion_cuotas.motivo+" ("+new Date(datos.error_actualizacion_cuotas.fecha).toLocaleString("es-ES",{timeZone:"Europe/Madrid"})+").";
   candidatosDest.parentElement.append(error);
 }
 if(datos.diagnostico_cuotas){
   const diagnostico=datos.diagnostico_cuotas;
   const detalle=document.createElement("p");
   detalle.setAttribute("role","status");
   detalle.textContent="Diagnóstico de cuotas: "+diagnostico.candidatos+" candidatos, "+
     diagnostico.candidatos_sin_hora+" sin hora de inicio, "+
     (diagnostico.candidatos_con_nombres_exactos_en_proveedor??"—")+" coincidencias por nombres de equipos, "+
     diagnostico.emparejamientos_unicos+" partidos identificados con horario compatible, "+
     diagnostico.selecciones_en_rango+" selecciones con cuota válida. "+
     (diagnostico.emparejamientos_unicos===0
       ?"No se han podido relacionar los partidos entre ambas fuentes."
       :diagnostico.selecciones_en_rango===0
         ?"Los partidos encontrados no tienen cuotas utilizables dentro de 1,20–1,80."
         :"");
   if(Number.isFinite(diagnostico.antiguedad_comprobacion_maxima_minutos)){
     detalle.textContent+=" Últimas comprobaciones de precios: entre "+
       diagnostico.antiguedad_comprobacion_minima_minutos+" y "+
       diagnostico.antiguedad_comprobacion_maxima_minutos+" minutos de antigüedad.";
   }
   if(diagnostico.cuotas_fuera_de_1_20_a_1_80>0){
     detalle.textContent+=" Cuotas vigentes fuera de rango: "+diagnostico.cuotas_fuera_de_1_20_a_1_80+".";
   }
   candidatosDest.parentElement.append(detalle);
 }
 const doblesDest=document.getElementById("lista-dobles");
 let registro=null;
 try{
   const respuesta=await fetch("https://raw.githubusercontent.com/superfraile/futbol-dashboard/main/seguimiento.json?actualizacion="+Date.now(),{cache:"no-store"});
   if(respuesta.ok)registro=await respuesta.json();
 }catch(e){ /* No presentar una selección provisional como confirmada. */ }
 const partes=Object.fromEntries(new Intl.DateTimeFormat("en-CA",{timeZone:"Europe/Madrid",year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",hourCycle:"h23"}).formatToParts(new Date()).map(p=>[p.type,p.value]));
 const diaMadrid=new Date(Date.UTC(+partes.year,+partes.month-1,+partes.day));
 let diasDesdeMartes=(diaMadrid.getUTCDay()+5)%7;
 if(diasDesdeMartes===0&&+partes.hour<20)diasDesdeMartes=7;
 diaMadrid.setUTCDate(diaMadrid.getUTCDate()-diasDesdeMartes);
 const semana=diaMadrid.toISOString().slice(0,10);
 const confirmacion=registro?.confirmaciones?.[semana];
 const confirmados=Boolean(confirmacion)&&Array.isArray(registro?.dobles);
 const dobles=confirmados
   ?registro.dobles.filter(d=>d.semana_confirmada===semana).map(d=>({...d,cuota_combinada:d.cuota}))
   :(datos.dobles||[]).filter(d=>Array.isArray(d.partidos)&&d.partidos.length===2&&d.partidos.every(p=>esFuturo(p)&&cuotaVigente(p)));
 if(dobles.length){
   tabla(doblesDest,["Partido 1","Fecha 1","Cuota 1","Partido 2","Fecha 2","Cuota 2","Cuota combinada"],dobles.slice(0,5).map(d=>[
     d.partidos[0].local+" - "+d.partidos[0].visitante,
     fechaEspana(d.partidos[0].fecha),
     d.partidos[0].cuota.toFixed(2),
     d.partidos[1].local+" - "+d.partidos[1].visitante,
     fechaEspana(d.partidos[1].fecha),
     d.partidos[1].cuota.toFixed(2),
     Number(d.cuota_combinada).toFixed(2)
   ]));
   const nota=document.createElement("p");
   nota.textContent=confirmados?"CONFIRMADAS · "+semana+" · Cuotas de referencia bloqueadas; resultados en Seguimiento.":"PROVISIONALES · Pendientes de confirmación semanal (martes, 20:00, hora peninsular).";
   doblesDest.append(nota);
 }else doblesDest.textContent=confirmados?"CONFIRMADAS · "+semana+" · No había dobles válidas en el cierre semanal.":"PROVISIONALES · No hay dobles válidas o no consta aún la confirmación semanal.";
 const dest=document.querySelector("#estadisticas .aviso");
 const filas=[];
 for(const l of CONFIG.ligas){
   for(const [equipo,condiciones] of Object.entries(datos.estadisticas?.[l.id]||{})){
     for(const [condicion,s] of Object.entries(condiciones)){
       filas.push([l.pais,equipo,condicion,s.pj,s.g,s.e,s.p,s.gf,s.gc,s.puntos,s.ppp,s.victorias_pct,fechaStats(l.id)]);
     }
   }
 }
 if(filas.length)tabla(dest,["Liga","Equipo","Condición","PJ","G","E","P","GF","GC","Pts","Pts/PJ","Victorias %","Fecha datos"],filas);
 else dest.textContent="Sin estadísticas verificadas. Fuente: "+(datos.fuente||"pendiente de validación");
 const fuente=document.createElement("p");fuente.textContent="Fuente: "+(datos.fuente||"pendiente de validación");
 document.querySelector("footer").append(fuente);
 }catch(e){
   console.error("Error al cargar el panel:",e);
   for(const selector of ["#detalle-liga","#favoritos .aviso","#partidos .aviso","#lista-candidatos","#lista-dobles","#estadisticas .aviso"]){
     const dest=document.querySelector(selector);
     if(dest&&!dest.querySelector("table"))dest.textContent="No se pudieron cargar los datos de esta sección. Recarga la página.";
   }
 }
}
iniciar();
