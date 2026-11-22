"""Pruebas del adaptador de Football-Data.org sin usar la red ni secretos."""
import unittest
from scripts.proveedores import convertir_partidos

class ProveedorFootballDataTests(unittest.TestCase):
    def test_partidos_y_estados(self):
        partidos = [
            {"utcDate": "2026-11-20T20:00:00Z", "status": "FINISHED",
             "homeTeam": {"name": "Local"}, "awayTeam": {"name": "Visitante"},
             "score": {"fullTime": {"home": 2, "away": 1}}},
            {"utcDate": "2026-11-28T18:00:00Z", "status": "TIMED",
             "homeTeam": {"name": "Visitante"}, "awayTeam": {"name": "Local"},
             "score": {"fullTime": {"home": None, "away": None}}}
        ]
        salida = convertir_partidos({"matches": partidos})
        self.assertEqual(salida[0]["goles_local"], 2)
        self.assertEqual(salida[0]["estado"], "finalizado")
        self.assertEqual(salida[1]["estado"], "pendiente")
        self.assertEqual(salida[1]["fecha"], "2026-11-28T18:00:00Z")
        self.assertNotIn("goles_local", salida[1])

    def test_no_acepta_marcador_ausente(self):
        partido = {"utcDate": "2026-11-20T20:00:00Z", "status": "FINISHED",
                   "homeTeam": {"name": "A"}, "awayTeam": {"name": "B"},
                   "score": {"fullTime": {"home": None, "away": 0}}}
        with self.assertRaises(ValueError):
            convertir_partidos({"matches": [partido]})

    def test_no_acepta_lista_vacia(self):
        with self.assertRaises(ValueError):
            convertir_partidos({"matches": []})

if __name__ == "__main__":
    unittest.main()
