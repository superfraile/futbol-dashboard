import unittest
from scripts.estadisticas import calcular

def partido(a,b,estado="finalizado"):
    return dict(fecha="2026-01-01",local="A",visitante="B",goles_local=a,goles_visitante=b,estado=estado)

class TestEstadisticas(unittest.TestCase):
    def test_victoria(self):
        a,b=calcular([partido(3,1)])
        self.assertEqual((a["equipo"],a["puntos"],a["ppp"],b["puntos"]),( "A",3,3,0))
    def test_empate(self):
        self.assertEqual([x["puntos"] for x in calcular([partido(1,1)])],[1,1])
    def test_pendiente(self):
        self.assertEqual(calcular([partido(None,None,"pendiente")]),[])
    def test_duplicado(self):
        with self.assertRaises(ValueError): calcular([partido(1,0)]*2)
    def test_invalido(self):
        with self.assertRaises(ValueError): calcular([partido(-1,0)])

if __name__=="__main__":
    unittest.main()
