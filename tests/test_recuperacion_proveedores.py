"""Prueba de recuperación ante indisponibilidad temporal de OpenLigaDB."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import proveedores

PARTIDO = {"fecha": "2026-11-21", "local": "Equipo A",
           "visitante": "Equipo B", "estado": "finalizado",
           "goles_local": 1, "goles_visitante": 0}

class RecuperacionProveedorTests(unittest.TestCase):
    def test_503_aleman_no_impide_descargar_otras_ligas(self):
        with tempfile.TemporaryDirectory() as carpeta:
            Path(carpeta, "datos-origen.json").write_text(
                json.dumps({"ligas": {"GER": [PARTIDO]}}), encoding="utf-8")
            directorio = os.getcwd()
            try:
                os.chdir(carpeta)
                with patch.dict(os.environ, {"FOOTBALL_DATA_API_KEY": "clave-de-prueba"}), \
                     patch.object(proveedores, "openligadb", side_effect=OSError("HTTP 503")), \
                     patch.object(proveedores, "football_data", return_value=[PARTIDO]):
                    resultado = proveedores.descargar()
            finally:
                os.chdir(directorio)
        self.assertEqual(resultado["ligas"]["GER"], [PARTIDO])
        self.assertIn("ESP", resultado["ligas"])
        self.assertIn("copia anterior", resultado["fuente"])

    def test_sin_datos_no_publica_vacio(self):
        with tempfile.TemporaryDirectory() as carpeta:
            directorio = os.getcwd()
            try:
                os.chdir(carpeta)
                with patch.dict(os.environ, {"FOOTBALL_DATA_API_KEY": ""}), \
                     patch.object(proveedores, "openligadb", side_effect=OSError("HTTP 503")):
                    with self.assertRaises(ValueError):
                        proveedores.descargar()
            finally:
                os.chdir(directorio)

if __name__ == "__main__":
    unittest.main()
