import unittest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta
from scripts.construir_datos import construir, resolver_favoritos, generar_dobles, aplicar_cuotas_bet365

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
        base=dict(liga="ESP",fecha="2026-11-30",local="A",visitante="B",cuota=1.5,cuota_verificada=True,casa_apuestas="bet365",mercado="1X2",equipo_proveedor="A",seleccion="1")
        segundo=dict(base,fecha="2026-12-01",local="C",visitante="D",equipo_proveedor="C",cuota=1.8)
        tercero=dict(base,fecha="2026-12-02",local="E",visitante="F",equipo_proveedor="E",cuota=1.81)
        sin_verificar=dict(base,fecha="2026-12-03",local="G",visitante="H",equipo_proveedor="G",cuota_verificada=False)
        dobles=generar_dobles([base,segundo,tercero,sin_verificar])
        self.assertEqual(len(dobles),1)
        self.assertEqual(dobles[0]["cuota_combinada"],2.7)

    def test_todas_las_combinaciones_priorizando_proximidad(self):
        def p(dia,cuota=1.5):
            return dict(liga="ESP",fecha="2026-12-"+dia,local="A"+dia,visitante="B"+dia,cuota=cuota,cuota_verificada=True,casa_apuestas="bet365",mercado="1X2",equipo_proveedor="A"+dia,seleccion="1")
        dobles=generar_dobles([p("01"),p("02"),p("20")])
        self.assertEqual(len(dobles),3)
        self.assertEqual([x["fecha"] for x in dobles[0]["partidos"]],["2026-12-01","2026-12-02"])

    def test_descarta_cuotas_de_otras_casas(self):
        a=dict(liga="ESP",fecha="2026-12-01",local="A",visitante="B",cuota=1.5,cuota_verificada=True,casa_apuestas="bet365")
        b=dict(a,fecha="2026-12-02",local="C",visitante="D",equipo_proveedor="C",casa_apuestas="otra")
        self.assertEqual(generar_dobles([a,b]),[])

    def test_descarta_mercado_o_resultado_incorrecto(self):
        a=dict(liga="ESP",fecha="2026-12-01",local="A",visitante="B",equipo_proveedor="A",cuota=1.5,cuota_verificada=True,casa_apuestas="bet365",mercado="1X2",seleccion="1")
        b=dict(a,fecha="2026-12-02",local="C",visitante="D",equipo_proveedor="C",seleccion="2")
        self.assertEqual(generar_dobles([a,b]),[])
        b["seleccion"]="1"
        b["mercado"]="Doble oportunidad"
        self.assertEqual(generar_dobles([a,b]),[])

    def test_importador_bet365_verificacion_y_caducidad(self):
        def candidato():
            return dict(liga="ESP",fecha="2099-12-01",local="A",visitante="B",
                        equipo_proveedor="A",cuota=None)
        ahora=datetime.now(timezone.utc)
        base=dict(liga="ESP",fecha="2099-12-01",local="A",visitante="B",
                  seleccion="1",cuota=1.5,verificada=True,
                  consultada_en=ahora.isoformat(),url_fuente="https://www.bet365.com/")
        with tempfile.TemporaryDirectory() as carpeta:
            archivo=Path(carpeta)/"cuotas.json"
            def probar(registro):
                archivo.write_text(json.dumps(dict(casa_apuestas="bet365",mercado="1X2",
                                                  cuotas=[registro])),encoding="utf-8")
                lista=[candidato()]
                aplicar_cuotas_bet365(lista,archivo)
                return lista[0]
            valido=probar(base)
            self.assertEqual(valido["cuota"],1.5)
            self.assertEqual(valido["casa_apuestas"],"bet365")
            self.assertIsNone(probar(dict(base,verificada=False))["cuota"])
            self.assertIsNone(probar(dict(base,seleccion="2"))["cuota"])
            self.assertIsNone(probar(dict(base,cuota=1.9))["cuota"])
            antiguo=(ahora-timedelta(hours=2)).isoformat()
            self.assertIsNone(probar(dict(base,consultada_en=antiguo))["cuota"])

    def test_no_selecciona_con_pocos_puntos(self):
        datos=construir({"fuente":"prueba", "ligas":{"ESP":[
            partido("2026-08-10","FC Barcelona","Sevilla FC",a=0,b=2),
            partido("2026-11-30","FC Barcelona","Valencia CF","pendiente")
        ]}})
        self.assertEqual(datos["candidatos"],[])

if __name__=="__main__":
    unittest.main()
