"use strict";
const lista=document.getElementById("lista-ligas");
let datos=null, seleccion="ESP";
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
 cards[1].querySelector(".numero").textContent=datos.equipos_top?.length||"—";
 cards[2].querySelector(".numero").textContent=datos.partidos?.length||"—";
 cards[3].querySelector("p").textContent=datos.ultima_actualizacion?new Date(datos.ultima_actualizacion).toLocaleString("es-ES",{timeZone:"Europe/Madrid"}):"Sin datos verificados";
 liga();
 if(datos.equipos_top?.length)tabla(document.querySelector("#favoritos .aviso"),["Liga","Equipo","ELO"],datos.equipos_top.map(r=>[r.liga,r.equipo,r.elo]));
 if(datos.partidos?.length)tabla(document.querySelector("#partidos .aviso"),["Liga","Fecha","Local","Visitante"],datos.partidos.map(r=>[r.liga,r.fecha,r.local,r.visitante]));
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
