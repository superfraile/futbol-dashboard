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
const contexto=vm.createContext({
  document:{getElementById:s=>obtener("#"+s),querySelector:obtener,
    querySelectorAll:s=>s==="main > .resumen > .tarjeta"?tarjetas:[],
    createElement:()=>new Elemento()},
  console:{log(){},error(...args){errores.push(args);}},
  fetch:async url=>({ok:true,json:async()=>url.includes("equipos-favoritos.json")?favoritos:datos}),
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
  console.log("Carga completa del panel y etiquetas móviles comprobadas.");
})().catch(e=>{console.error(e);process.exitCode=1;});
