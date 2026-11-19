import unittest
from scripts.estadisticas import desglosar

class TestLocalVisitante(unittest.TestCase):
    def test_desglose(self):
        partidos=[
            dict(fecha="2026-01-01",local="A",visitante="B",goles_local=2,goles_visitante=0,estado="finalizado"),
            dict(fecha="2026-01-08",local="B",visitante="A",goles_local=1,goles_visitante=1,estado="finalizado")]
        r=desglosar(partidos)
        self.assertEqual(r["A"]["local"]["ppp"],3)
        self.assertEqual(r["A"]["visitante"]["ppp"],1)
        self.assertEqual(r["B"]["visitante"]["victorias_pct"],0)
