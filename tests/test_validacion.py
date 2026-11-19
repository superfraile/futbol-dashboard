import unittest
from scripts.construir_datos import construir

class TestValidacion(unittest.TestCase):
    def test_calendario_duplicado(self):
        m=dict(fecha="2026-01-01",local="A",visitante="B",estado="pendiente")
        with self.assertRaises(ValueError):
            construir(dict(fuente="test",ligas={"ESP":[m,m]}))
    def test_liga_desconocida(self):
        with self.assertRaises(ValueError):
            construir(dict(fuente="test",ligas={"XXX":[]}))
    def test_fecha_invalida(self):
        m=dict(fecha="2026-02-30",local="A",visitante="B",estado="pendiente")
        with self.assertRaises(ValueError):
            construir(dict(fuente="test",ligas={"ESP":[m]}))
