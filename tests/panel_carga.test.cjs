// Prueba de ejecución, además de sintaxis: evita regresiones de referencias no definidas.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

class Elemento {
  constructor(){this.children=[];this.parentElement=this;this.value="";this.textContent="";this.style={};this.classList={add(){},remove(){}};this.selectores=new Map();}
  append(...n){this.children.push(...n);}
  replaceChildren(...n){this.children=n;}
  createTHead(){const e=new Elemento();this.append(e);return e;}
  createTBody(){return this.createTHead();}
  insertRow(){const e=new Elemento();this.append(e);return e;}
  insertCell(){return this.insertRow();}
  querySelector(s){if(!this.selectores.has(s))this.selectores.set(s,new Elemento());return this.selectores.get(s);}
  addEventListener(){}
  setAttribute(k,v){this[k]=v;}
}
const elementos=new Map();
const obtener=s=>{if(!elementos.has(s))elementos.set(s,new Elemento());return elementos.get(s);};
const tarjetas=Array.from({length:4},()=>new Elemento());
const errores=[];
const datos=JSON.parse(fs.readFileSync("datos.json","utf8"));
const favoritos=JSON.parse(fs.readFileSync("equipos-favoritos.json","utf8"));
const partes=new Intl.DateTimeFormat("sv-SE",{timeZone:"Europe/Madrid",year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",hourCycle:"h23"}).formatToParts(new Date());
const fechaLocal=Object.fromEntries(partes.map(p=>[p.type,p.value]));
const martes=new Date(Date.UTC(+fechaLocal.year,+fechaLocal.month-1,+fechaLocal.day));
let distancia=(martes.getUTCDay()+5)%7;
if(distancia===0&&+fechaLocal.hour<20)distancia=7;
martes.setUTCDate(martes.getUTCDate()-distancia);
const semana=martes.toISOString().slice(0,10);
const partido=(local,visitante,fecha)=>({local,visitante,fecha,cuota:1.5,casa_apuestas:"MoviOdds"});
const registro={confirmaciones:{[semana]:{cantidad:1}},dobles:[{semana_confirmada:semana,cuota:2.25,partidos:[partido("Equipo A","Equipo B","2026-12-05T18:00:00Z"),partido("Equipo C","Equipo D","2026-12-06T18:00:00Z")]}]};
const contexto=vm.createContext({
  document:{getElementById:s=>obtener("#"+s),querySelector:obtener,
    querySelectorAll:s=>s==="main > .resumen > .tarjeta"?tarjetas:[],
    createElement:()=>new Elemento()},
  console:{log(){},error(...args){errores.push(args);}},
  fetch:async url=>({ok:true,json:async()=>url.includes("equipos-favoritos.json")?favoritos:url.includes("seguimiento.json")?registro:datos}),
  URL
});
(async()=>{
  vm.runInContext(fs.readFileSync("datos.js","utf8"),contexto);
  const codigo=fs.readFileSync("panel.js","utf8").replace(/iniciar\(\);\s*$/,"iniciar();");
  await vm.runInContext(codigo,contexto);
  assert.equal(errores.length,0,errores.map(e=>String(e[1])).join("; "));
  for(const s of ["#detalle-liga","#favoritos .aviso","#partidos .aviso","#lista-candidatos","#lista-dobles","#estadisticas .aviso"]){
    const e=obtener(s);
    assert.ok(e.children.length||e.textContent.length,"Sección no inicializada: "+s);
  }
  assert.equal(obtener("#favoritos .aviso").children[0].children[1].children.length,38);
  assert.equal(tarjetas[0].querySelector(".numero").textContent,Object.values(datos.ligas).filter(t=>t.length).length);
  const favoritosTabla=obtener("#favoritos .aviso").children[0];
  assert.equal(favoritosTabla.className,"fichas");
  assert.equal(favoritosTabla.children[1].children[0].children[1]["data-label"],"Equipo fijo");
  const doble=obtener("#lista-dobles").children[0].children[1].children[0].children;
  assert.equal(doble.length,7);
  assert.equal(doble[0].textContent,"Equipo A - Equipo B");
  assert.equal(doble[1]["data-label"],"Fecha 1");
  assert.match(doble[1].textContent,/05\/12\/2026/);
  assert.equal(doble[2].textContent,"1.50");
  assert.equal(doble[3].textContent,"Equipo C - Equipo D");
  assert.equal(doble[5].textContent,"1.50");
  assert.equal(doble[6].textContent,"2.25");
  assert.ok(doble.every(c=>!String(c.textContent).includes("MoviOdds")));
  console.log("Carga completa y formato móvil de dobles comprobados.");
})().catch(e=>{console.error(e);process.exitCode=1;});
