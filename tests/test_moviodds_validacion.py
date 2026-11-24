import unittest
from datetime import datetime, timezone, timedelta
from scripts.moviodds_validacion import mercado_1x2, emparejar_candidatos, atribucion_bet365
from scripts.importar_moviodds import incorporar

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
        self.partido["quotes"]=[self.cuota(minutos=361)]
        self.assertEqual(mercado_1x2(self.partido,self.ahora),{})
        self.partido["quotes"]=[self.cuota()]
        self.partido["in_play"]=True
        self.assertEqual(mercado_1x2(self.partido,self.ahora),{})
    def test_antiguedad_variable(self):
        for horas,limite in ((5,60),(6,180),(23,180),(24,360),(48,360),(49,720)):
            with self.subTest(horas=horas):
                self.partido["kickoff_utc"]=(self.ahora+timedelta(hours=horas)).isoformat()
                self.partido["quotes"]=[self.cuota(minutos=limite)]
                self.assertIn("1",mercado_1x2(self.partido,self.ahora))
                self.partido["quotes"]=[self.cuota(minutos=limite+1)]
                self.assertEqual(mercado_1x2(self.partido,self.ahora),{})

    def test_rechaza_mercados_distintos_y_duplicados(self):
        self.partido["quotes"]=[self.cuota(grupo=1777)]
        self.assertEqual(mercado_1x2(self.partido,self.ahora),{})
        self.partido["quotes"]=[self.cuota(),self.cuota(valor=1.6),self.cuota(valor=1.7)]
        self.assertEqual(mercado_1x2(self.partido,self.ahora),{})
    def test_descarta_valores_no_finitos_y_booleanos(self):
        for valor in (float("nan"),float("inf"),float("-inf"),True):
            with self.subTest(valor=str(valor)):
                self.partido["quotes"]=[self.cuota(valor=valor)]
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

    def test_nombres_nulos_del_proveedor_no_interrumpen(self):
        candidato=dict(fecha=self.partido["kickoff_utc"],local="FC Barcelona",visitante="Sevilla FC")
        incompleto=dict(self.partido,home=None)
        self.assertEqual(len(emparejar_candidatos([candidato],[incompleto,self.partido])),1)

    def test_equivalencias_explicitas_no_similitud(self):
        candidato=dict(fecha=self.partido["kickoff_utc"],local="Barcelona",visitante="Sevilla")
        self.assertEqual(emparejar_candidatos([candidato],[self.partido]),[])
        aprobadas={"Barcelona":"FC Barcelona","Sevilla":"Sevilla FC"}
        self.assertEqual(len(emparejar_candidatos([candidato],[self.partido],aprobadas)),1)

    def test_atribucion_bet365_por_cuota(self):
        cuota=self.cuota()
        self.assertFalse(atribucion_bet365(self.partido,cuota))
        cuota["bookmaker"]="bet365"
        self.assertTrue(atribucion_bet365(self.partido,cuota))
        cuota["sportsbook"]="Otra casa"
        self.assertFalse(atribucion_bet365(self.partido,cuota))
        cuota.pop("sportsbook")
        self.partido["operator"]="Otra casa"
        self.assertFalse(atribucion_bet365(self.partido,cuota))

    def test_importa_cuotas_moviodds_y_genera_doble(self):
        ahora=self.ahora
        primero=dict(liga="ESP",fecha=self.partido["kickoff_utc"],
                     local="FC Barcelona",visitante="Sevilla FC",
                     equipo_proveedor="FC Barcelona",valoracion=2.1,cuota=None)
        segundo=dict(liga="ESP",fecha=(ahora+timedelta(days=2)).isoformat(),
                     local="Real Betis",visitante="Valencia CF",
                     equipo_proveedor="Real Betis",valoracion=1.7,cuota=None)
        p1=dict(self.partido,quotes=[self.cuota()])
        p2=dict(home="Real Betis",away="Valencia CF",in_play=False,
                kickoff_utc=segundo["fecha"],
                quotes=[self.cuota(label="Real Betis",valor=1.6)])
        datos=incorporar({"candidatos":[primero,segundo],"dobles":[]},[p1,p2],ahora)
        self.assertEqual(datos["candidatos"][0]["casa_apuestas"],"MoviOdds")
        self.assertEqual(datos["candidatos"][1]["cuota"],1.6)
        self.assertEqual(len(datos["dobles"]),1)
        self.assertEqual(datos["dobles"][0]["cuota_combinada"],2.4)

    def test_actualizacion_no_conserva_cuota_antigua(self):
        candidato=dict(liga="ESP",fecha=self.partido["kickoff_utc"],
                       local="FC Barcelona",visitante="Sevilla FC",
                       equipo_proveedor="FC Barcelona",cuota=1.5,
                       cuota_verificada=True,casa_apuestas="MoviOdds",
                       mercado="1X2",seleccion="1",
                       consultada_en=self.ahora.isoformat(),
                       url_fuente="https://moviodds.com/odds?sport=soccer")
        datos=incorporar({"candidatos":[candidato],"dobles":[]},[],self.ahora)
        self.assertIsNone(datos["candidatos"][0]["cuota"])
        self.assertEqual(datos["dobles"],[])
        actualizado=dict(self.partido,quotes=[self.cuota(valor=1.6)])
        datos=incorporar(datos,[actualizado],self.ahora)
        self.assertEqual(datos["candidatos"][0]["cuota"],1.6)
        self.assertEqual(datos["candidatos"][0]["casa_apuestas"],"MoviOdds")

    def test_importador_no_acepta_emparejamiento_ambiguo(self):
        candidato=dict(liga="ESP",fecha=self.partido["kickoff_utc"],
                       local="FC Barcelona",visitante="Sevilla FC",
                       equipo_proveedor="FC Barcelona",cuota=None)
        partido=dict(self.partido,quotes=[self.cuota()])
        datos=incorporar({"candidatos":[candidato],"dobles":[]},[partido,dict(partido)],self.ahora)
        self.assertIsNone(datos["candidatos"][0]["cuota"])
        self.assertEqual(datos["dobles"],[])

    def test_no_atribuye_bookmaker(self):
        self.partido["quotes"]=[self.cuota()]
        datos=mercado_1x2(self.partido,self.ahora)
        self.assertNotIn("casa_apuestas",datos["1"])
        self.assertNotIn("verificada",datos["1"])

if __name__=="__main__":
    unittest.main()
