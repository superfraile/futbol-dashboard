import unittest
from scripts.construir_datos import construir

class TestConstruir(unittest.TestCase):
    def test_integracion(self):
        datos=construir({"fuente":"prueba ficticia","ligas":{"ESP":[
            dict(fecha="2026-01-01",local="A",visitante="B",goles_local=2,goles_visitante=0,estado="finalizado"),
            dict(fecha="2026-01-08",local="B",visitante="A",estado="pendiente")]}})
        self.assertEqual(len(datos["ligas"]),14)
        self.assertEqual(datos["ligas"]["ESP"][0]["puntos"],3)
        self.assertEqual(datos["equipos_top"][0]["equipo"],"A")
        self.assertEqual(len(datos["partidos"]),1)
        self.assertEqual(datos["estadisticas"]["ESP"]["A"]["local"]["ppp"],3)
    def test_fuente(self):
        with self.assertRaises(ValueError): construir({"fuente":"","ligas":{}})
