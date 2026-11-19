import unittest
from scripts.elo import elo
class TestElo(unittest.TestCase):
    def test_ganador(self):
        r=elo([dict(fecha="2026-01-01",local="A",visitante="B",goles_local=2,goles_visitante=0,estado="finalizado")])
        self.assertGreater(r["A"],1500)
        self.assertAlmostEqual(sum(r.values()),3000)
    def test_vacio(self):
        self.assertEqual(elo([]),{})
