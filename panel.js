"use strict";
const lista=document.getElementById("lista-ligas");
let datos=null, seleccion="GER";
function tabla(dest,headers,rows){
 const t=document.createElement("table"), h=t.createTHead().insertRow();
 headers.forEach(v=>{const c=document.createElement("th");c.textContent=v;h.append(c)});
 const b=t.createTBody();rows.forEach(row=>{const r=b.insertRow();row.forEach(v=>{r.insertCell().textContent=v??"—"})});
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
 const cards=document.querySelectorAll(".resumen .tarjeta");
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
 const topPublicados=datos.favoritos_validados===true&&datos.equipos_top?.length===38?datos.equipos_top:[];
 tabla(document.querySelector("#favoritos .aviso"),["Liga","Equipo fijo","ELO estimado","Pts/PJ"],Object.entries(listaFija.ligas).flatMap(([liga,equipos])=>equipos.map(equipo=>{
   const r=topPublicados.find(x=>x.liga===liga&&x.equipo===equipo);
   const s=r?datos.ligas[liga]?.find(t=>t.equipo===r.equipo_proveedor):null;
   return [nombreLiga(liga),equipo,r?.elo??null,s?.ppp??null];
 })));
 const hoy=new Intl.DateTimeFormat("sv-SE",{timeZone:"Europe/Madrid",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date());
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
   const filtrados=candidatos.filter(r=>(!filtroCandidatos.value||r.liga===filtroCandidatos.value)&&(dias==="all"||r.fecha.slice(0,10)<=fechaLimite)).sort((a,b)=>Number(b.ppp)-Number(a.ppp)||a.fecha.localeCompare(b.fecha));
   if(!filtrados.length){candidatosDest.textContent="Sin partidos preseleccionados para esta liga.";return;}
   tabla(candidatosDest,["Liga","Fecha","Local","Visitante","Favorito fijo","Pts/PJ","Cuota"],filtrados.slice(0,100).map(r=>[
     nombreLiga(r.liga),r.fecha,r.local,r.visitante,r.favorito,r.ppp,r.casa_apuestas==="bet365"&&r.cuota_verificada===true&&typeof r.cuota==="number"&&r.cuota>=1.20&&r.cuota<=1.80?r.cuota.toFixed(2):"Pendiente bet365"
   ]));
   const aviso=document.createElement("p");
   aviso.textContent="Mostrando "+Math.min(100,filtrados.length)+" de "+filtrados.length+" partidos preseleccionados, ordenados por Pts/PJ (mayor a menor). Cuotas verificadas: "+filtrados.filter(p=>p.casa_apuestas==="bet365"&&p.casa_apuestas==="bet365"&&p.cuota_verificada===true&&typeof p.cuota==="number"&&p.cuota>=1.20&&p.cuota<=1.80).length+". No son apuestas válidas sin cuotas verificadas.";
   candidatosDest.append(aviso);
 }
 filtroCandidatos.addEventListener("change",dibujarCandidatos);
 plazoCandidatos.addEventListener("change",dibujarCandidatos);
 dibujarCandidatos();
 const doblesDest=document.getElementById("lista-dobles");
 const dobles=(datos.dobles||[]).filter(d=>Array.isArray(d.partidos)&&d.partidos.length===2&&d.partidos.every(p=>esFuturo(p)&&p.cuota_verificada===true&&typeof p.cuota==="number"&&p.cuota>=1.20&&p.cuota<=1.80));
 if(dobles.length){
   tabla(doblesDest,["Partido 1","Cuota 1","Partido 2","Cuota 2","Cuota combinada"],dobles.slice(0,100).map(d=>[
     d.partidos[0].local+" - "+d.partidos[0].visitante+" ("+d.partidos[0].fecha.slice(0,10)+")",
     d.partidos[0].cuota,
     d.partidos[1].local+" - "+d.partidos[1].visitante+" ("+d.partidos[1].fecha.slice(0,10)+")",
     d.partidos[1].cuota,
     d.cuota_combinada
   ]));
   const nota=document.createElement("p");nota.textContent="Mostrando "+Math.min(100,dobles.length)+" de "+dobles.length+" combinaciones verificadas.";doblesDest.append(nota);
 }else doblesDest.textContent="Todavía no hay dobles con dos cuotas verificadas entre 1,20 y 1,80. No se muestran apuestas inventadas.";
 const dest=document.querySelector("#estadisticas .aviso");
 const filas=[];
 for(const l of CONFIG.ligas){
   for(const [equipo,condiciones] of Object.entries(datos.estadisticas?.[l.id]||{})){
     for(const [condicion,s] of Object.entries(condiciones)){
       filas.push([l.pais,equipo,condicion,s.pj,s.g,s.e,s.p,s.gf,s.gc,s.puntos,s.ppp,s.victorias_pct]);
     }
   }
 }
 if(filas.length)tabla(dest,["Liga","Equipo","Condición","PJ","G","E","P","GF","GC","Pts","Pts/PJ","Victorias %"],filas);
 else dest.textContent="Sin estadísticas verificadas. Fuente: "+(datos.fuente||"pendiente de validación");
 const fuente=document.createElement("p");fuente.textContent="Fuente: "+(datos.fuente||"pendiente de validación");
 document.querySelector("footer").append(fuente);
 }catch(e){document.getElementById("detalle-liga").textContent="No se pudieron cargar los datos. Recarga la página más tarde."}
}
iniciar();
