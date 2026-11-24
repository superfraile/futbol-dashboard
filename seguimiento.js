"use strict";
async function cargarSeguimiento(){
 const zona=document.getElementById("resumen-seguimiento"),dest=document.getElementById("lista-seguimiento");
 const euro=n=>Number(n).toLocaleString("es-ES",{style:"currency",currency:"EUR"});
 const fecha=s=>new Date(s).toLocaleString("es-ES",{timeZone:"Europe/Madrid"});
 try{
  const respuesta=await fetch("https://raw.githubusercontent.com/superfraile/futbol-dashboard/main/seguimiento.json?actualizacion="+Date.now(),{cache:"no-store"});
  if(!respuesta.ok)throw Error("Sin registro");
  const d=await respuesta.json(),todos=d.dobles;
  if(!Array.isArray(todos))throw Error("Formato incorrecto");
  const liquidadas=todos.filter(x=>x.estado!=="pendiente");
  const ganadas=liquidadas.filter(x=>x.estado==="acertada").length;
  const perdidas=liquidadas.filter(x=>x.estado==="fallada").length;
  const anuladas=liquidadas.filter(x=>x.estado==="anulada").length;
  const beneficio=liquidadas.reduce((s,x)=>s+x.beneficio,0);
  const invertido=liquidadas.reduce((s,x)=>s+x.stake,0);
  const indicadores=[["Registradas",todos.length],["Pendientes",todos.length-liquidadas.length],
    ["Acertadas",ganadas],["Falladas",perdidas],["Anuladas",anuladas],
    ["Aciertos",(ganadas+perdidas)?(100*ganadas/(ganadas+perdidas)).toFixed(1)+" %":"—"],
    ["Importe liquidado",euro(invertido)],["Beneficio neto simulado",euro(beneficio)],
    ["ROI",invertido?(100*beneficio/invertido).toFixed(2)+" %":"—"]];
  zona.replaceChildren();
  for(const [titulo,valor] of indicadores){
    const card=document.createElement("div");card.className="tarjeta";
    const a=document.createElement("div");a.className="etiqueta";a.textContent=titulo;
    const b=document.createElement("div");b.className="numero";b.textContent=valor;
    if(titulo==="Beneficio neto simulado"&&beneficio<0)b.style.color="#f87171";
    card.append(a,b);zona.append(card);
  }
  const progreso=document.getElementById("progreso-seguimiento");
  progreso.textContent="Muestra inicial: "+(ganadas+perdidas)+" de 100 dobles con resultado. Última actualización: "+fecha(d.actualizado_en)+".";
  if(!todos.length){dest.textContent="Aún no se han registrado dobles válidas.";return}
  tabla(dest,["Registro","Selección 1","Selección 2","Cuota total","Importe","Estado","Beneficio"],[...todos].reverse().map(x=>[
   fecha(x.registrada_en),...x.partidos.map(p=>p.local+" – "+p.visitante+" | "+p.favorito+" ("+p.cuota.toFixed(2)+", "+p.casa_apuestas+") | "+fecha(p.fecha)+" | "+p.estado+(p.marcador?" "+p.marcador:"")),
   x.cuota.toFixed(2),euro(x.stake),x.estado,x.beneficio===null?"—":euro(x.beneficio)
  ]));
 }catch(e){dest.textContent="El seguimiento aún no está disponible. No hay resultados de simulación confirmados."}
}
cargarSeguimiento();
