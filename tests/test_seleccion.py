import unittest
from scripts.construir_datos import construir, resolver_favoritos, generar_dobles

def partido(fecha,local,visitante,estado="finalizado",a=2,b=0):
    p=dict(fecha=fecha,local=local,visitante=visitante,estado=estado)
    if estado=="finalizado": p.update(goles_local=a,goles_visitante=b)
    return p

class SeleccionTests(unittest.TestCase):
    def test_alias_real(self):
        tabla=[{"equipo":"FC Barcelona","ppp":2.5}]
        self.assertEqual(resolver_favoritos("ESP",["Barcelona"],tabla),{"FC Barcelona":"Barcelona"})

    def test_candidato_y_duelo_entre_favoritos(self):
        datos=construir({"fuente":"prueba", "ligas":{"ESP":[
            partido("2026-08-10","FC Barcelona","Sevilla FC"),
            partido("2026-08-17","FC Barcelona","Valencia CF"),
            partido("2026-11-30","FC Barcelona","Sevilla FC","pendiente"),
            partido("2026-12-01","FC Barcelona","Real Madrid CF","pendiente")
        ]}})
        self.assertEqual(len(datos["candidatos"]),1)
        self.assertEqual(datos["candidatos"][0]["favorito"],"Barcelona")
        self.assertIsNone(datos["candidatos"][0]["cuota"])

    def test_dobles_solo_con_cuotas_verificadas(self):
        base=dict(liga="ESP",fecha="2026-11-30",local="A",visitante="B",cuota=1.5,cuota_verificada=True)
        segundo=dict(base,fecha="2026-12-01",local="C",visitante="D",cuota=1.8)
        tercero=dict(base,fecha="2026-12-02",local="E",visitante="F",cuota=1.81)
        sin_verificar=dict(base,fecha="2026-12-03",local="G",visitante="H",cuota_verificada=False)
        dobles=generar_dobles([base,segundo,tercero,sin_verificar])
        self.assertEqual(len(dobles),1)
        self.assertEqual(dobles[0]["cuota_combinada"],2.7)

    def test_no_selecciona_con_pocos_puntos(self):
        datos=construir({"fuente":"prueba", "ligas":{"ESP":[
            partido("2026-08-10","FC Barcelona","Sevilla FC",a=0,b=2),
            partido("2026-11-30","FC Barcelona","Valencia CF","pendiente")
        ]}})
        self.assertEqual(datos["candidatos"],[])

if __name__=="__main__":
    unittest.main()
