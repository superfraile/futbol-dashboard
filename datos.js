"use strict";

const CONFIG = {
    version: "1.0",
    zonaHoraria: "Europe/Madrid",
    actualizacionHoras: 24,
    ligas: [
        { id: "GER", nombre: "Bundesliga", pais: "Alemania" },
        { id: "DEN", nombre: "Superliga", pais: "Dinamarca" },
        { id: "SCO", nombre: "Premiership", pais: "Escocia" },
        { id: "ESP", nombre: "La Liga", pais: "España" },
        { id: "FRA", nombre: "Ligue 1", pais: "Francia" },
        { id: "GRE", nombre: "Super League", pais: "Grecia" },
        { id: "ENG", nombre: "Premier League", pais: "Inglaterra" },
        { id: "ITA", nombre: "Serie A", pais: "Italia" },
        { id: "NOR", nombre: "Eliteserien", pais: "Noruega" },
        { id: "NED", nombre: "Eredivisie", pais: "Países Bajos" },
        { id: "POR", nombre: "Primeira Liga", pais: "Portugal" },
        { id: "SWE", nombre: "Allsvenskan", pais: "Suecia" },
        { id: "SUI", nombre: "Super League", pais: "Suiza" },
        { id: "TUR", nombre: "Süper Lig", pais: "Turquía" }
    ]
};

async function cargarDatos() {
    const respuesta = await fetch("./datos.json", {
        cache: "no-store"
    });

    if (!respuesta.ok) {
        throw new Error("Datos deportivos no disponibles");
    }

    return await respuesta.json();
}

function puntosPorPartido(puntos, partidos) {
    if (partidos <= 0) return null;
    return Number((puntos / partidos).toFixed(2));
}

function porcentajeVictorias(victorias, partidos) {
    if (partidos <= 0) return null;
    return Number((victorias / partidos * 100).toFixed(2));
}

function diferenciaGoles(favor, contra) {
    return favor - contra;
}

console.log("Fútbol Dashboard: módulo de datos cargado");
