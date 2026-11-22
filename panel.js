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
 try{datos=await cargarDatos(); if(!datos||typeof datos.ligas!=="object")throw Error("Formato incorrecto");
 const cards=document.querySelectorAll(".resumen .tarjeta");
 cards[0].querySelector(".numero").textContent=Object.values(datos.ligas).filter(t=>Array.isArray(t)&&t.length).length;
 cards[1].querySelector(".numero").textContent=datos.equipos_top?.length||"—";
 cards[2].querySelector(".numero").textContent=datos.partidos?.length||"—";
 cards[3].querySelector("p").textContent=datos.ultima_actualizacion?new Date(datos.ultima_actualizacion).toLocaleString("es-ES",{timeZone:"Europe/Madrid"}):"Sin datos verificados";
 liga();
 const nombreLiga=id=>CONFIG.ligas.find(l=>l.id===id)?.pais||id;
 if(datos.equipos_top?.length)tabla(document.querySelector("#favoritos .aviso"),["Liga","Equipo fijo","ELO estimado","Pts/PJ"],datos.equipos_top.map(r=>{const s=datos.ligas[r.liga]?.find(t=>t.equipo===r.equipo_proveedor);return [nombreLiga(r.liga),r.equipo,r.elo,s?.ppp??null]}));
 else document.querySelector("#favoritos .aviso").textContent="Sin equipos TOP calculados con datos verificados.";
 const hoy=new Intl.DateTimeFormat("sv-SE",{timeZone:"Europe/Madrid",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date());
 const proximos=(datos.partidos||[]).filter(r=>r.fecha.slice(0,10)>=hoy).sort((a,b)=>a.fecha.localeCompare(b.fecha));
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
 const candidatos=(datos.candidatos||[]).filter(r=>r.fecha.slice(0,10)>=hoy);
 const candidatosDest=document.getElementById("lista-candidatos");
 if(datos.favoritos_validados===false){
   candidatosDest.textContent="La lista de favoritos está pendiente de validación. No se generan selecciones.";
 }else if(candidatos.length){
   tabla(candidatosDest,["Liga","Fecha","Local","Visitante","Favorito fijo","Pts/PJ","Cuota"],candidatos.slice(0,100).map(r=>[
     nombreLiga(r.liga),r.fecha,r.local,r.visitante,r.favorito,r.ppp,"Pendiente"
   ]));
   const aviso=document.createElement("p");
   aviso.textContent=candidatos.length+" partidos preseleccionados. Ninguno es apuesta válida sin cuota comprobada.";
   candidatosDest.append(aviso);
 }else candidatosDest.textContent="No hay partidos preseleccionados con los filtros deportivos actuales.";
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
