import unittest
from datetime import datetime, timezone, timedelta
from scripts.moviodds_validacion import mercado_1x2, emparejar_candidatos

class MoviOddsValidacionTests(unittest.TestCase):
    def setUp(self):
        self.ahora=datetime(2026,11,22,20,0,tzinfo=timezone.utc)
        self.partido=dict(home="FC Barcelona",away="Sevilla FC",in_play=False,
            kickoff_utc=(self.ahora+timedelta(days=1)).isoformat(),quotes=[])
    def cuota(self,label="FC Barcelona",valor=1.5,grupo=40,minutos=5):
        return dict(group_id=grupo,label=label,odds_dec=valor,
                    ts=(self.ahora-timedelta(minutes=minutos)).isoformat())
    def test_mercado_prepartido(self):
        self.partido["quotes"]=[self.cuota(),self.cuota("Draw",3.2),
                                 self.cuota("Sevilla FC",5.0)]
        datos=mercado_1x2(self.partido,self.ahora)
        self.assertEqual(datos["1"]["cuota"],1.5)
        self.assertEqual(datos["X"]["cuota"],3.2)
        self.assertEqual(datos["2"]["cuota"],5.0)
    def test_rechaza_directo_y_cuotas_antiguas(self):
        self.partido["quotes"]=[self.cuota(minutos=90)]
        self.assertEqual(mercado_1x2(self.partido,self.ahora),{})
        self.partido["quotes"]=[self.cuota()]
        self.partido["in_play"]=True
        self.assertEqual(mercado_1x2(self.partido,self.ahora),{})
    def test_rechaza_mercados_distintos_y_duplicados(self):
        self.partido["quotes"]=[self.cuota(grupo=1777)]
        self.assertEqual(mercado_1x2(self.partido,self.ahora),{})
        self.partido["quotes"]=[self.cuota(),self.cuota(valor=1.6),self.cuota(valor=1.7)]
        self.assertEqual(mercado_1x2(self.partido,self.ahora),{})
    def test_empareja_solo_ambos_equipos_y_hora(self):
        candidato=dict(fecha=self.partido["kickoff_utc"],local="FC Barcelona",visitante="Sevilla FC")
        self.assertEqual(len(emparejar_candidatos([candidato],[self.partido])),1)
        incorrecto=dict(self.partido,away="Valencia CF")
        self.assertEqual(emparejar_candidatos([candidato],[incorrecto]),[])
        self.assertEqual(emparejar_candidatos([candidato],[self.partido,self.partido]),[])

    def test_no_asigna_mismo_partido_a_dos_candidatos(self):
        candidato=dict(fecha=self.partido["kickoff_utc"],local="FC Barcelona",visitante="Sevilla FC")
        self.assertEqual(emparejar_candidatos([candidato,dict(candidato)],[self.partido]),[])

    def test_equivalencias_explicitas_no_similitud(self):
        candidato=dict(fecha=self.partido["kickoff_utc"],local="Barcelona",visitante="Sevilla")
        self.assertEqual(emparejar_candidatos([candidato],[self.partido]),[])
        aprobadas={"Barcelona":"FC Barcelona","Sevilla":"Sevilla FC"}
        self.assertEqual(len(emparejar_candidatos([candidato],[self.partido],aprobadas)),1)

    def test_no_atribuye_bookmaker(self):
        self.partido["quotes"]=[self.cuota()]
        datos=mercado_1x2(self.partido,self.ahora)
        self.assertNotIn("casa_apuestas",datos["1"])
        self.assertNotIn("verificada",datos["1"])

if __name__=="__main__":
    unittest.main()
