import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from scripts.seguimiento import registrar

class SeguimientoSemanal(unittest.TestCase):
    def test_solo_martes_20_hora_madrid(self):
        for fecha,esperado in [
            ("2026-12-01T18:59:00+00:00",False),
            ("2026-12-01T19:00:00+00:00",True),
            ("2026-07-07T18:00:00+00:00",True),
            ("2026-07-07T19:00:00+00:00",False),
            ("2026-12-02T19:00:00+00:00",False),
        ]:
            with self.subTest(fecha=fecha),patch("scripts.seguimiento.generar_dobles",return_value=[]) as generar:
                cierres={}
                ahora=datetime.fromisoformat(fecha)
                registrar([],{},ahora,cierres)
                self.assertEqual(bool(cierres),esperado)
                registrar([],{},ahora,cierres)
                self.assertEqual(generar.call_count,int(esperado))

    def test_conserva_dobles_y_cuotas(self):
        def partido(local,visitante):
            return dict(liga="ESP",fecha="2026-12-05T18:00:00+00:00",local=local,
                visitante=visitante,favorito=local,equipo_proveedor=local,cuota=1.5,
                casa_apuestas="MoviOdds",seleccion="1",consultada_en="2026-12-01T18:30:00+00:00")
        a,b=partido("A","B"),partido("C","D")
        historial,cierres=[],{}
        ahora=datetime(2026,12,1,19,tzinfo=timezone.utc)
        with patch("scripts.seguimiento.generar_dobles",return_value=[{"partidos":[a,b]}]) as generar:
            registrar(historial,{},ahora,cierres)
            a["cuota"]=1.8
            registrar(historial,{},ahora,cierres)
            self.assertEqual(generar.call_count,1)
        self.assertEqual(len(historial),1)
        self.assertEqual(historial[0]["partidos"][0]["cuota"],1.5)
        self.assertEqual(historial[0]["semana_confirmada"],"2026-12-01")
        self.assertEqual(cierres["2026-12-01"]["cantidad"],1)
