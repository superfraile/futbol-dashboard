import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.proveedores import descargar, COMPETICIONES


class ProveedoresTests(unittest.TestCase):
    def test_sin_clave_conserva_ligas_anteriores(self):
        anteriores = {liga: [{"local": "A", "visitante": "B"}]
                      for liga in ("GER", *COMPETICIONES)}
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "datos-origen.json"
            ruta.write_text(json.dumps({"ligas": anteriores}), encoding="utf-8")
            with patch("pathlib.Path", return_value=ruta), \
                 patch("scripts.proveedores.openligadb", side_effect=OSError("sin conexión")), \
                 patch.dict("os.environ", {"FOOTBALL_DATA_API_KEY": ""}):
                resultado = descargar()
        self.assertEqual(resultado["ligas"], anteriores)
        self.assertIn("copia anterior", resultado["fuente"])

    def test_sin_fuentes_ni_copia_no_publica_vacio(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "datos-origen.json"
            with patch("pathlib.Path", return_value=ruta), \
                 patch("scripts.proveedores.openligadb", side_effect=OSError("sin conexión")), \
                 patch.dict("os.environ", {"FOOTBALL_DATA_API_KEY": ""}):
                with self.assertRaises(ValueError):
                    descargar()


if __name__ == "__main__":
    unittest.main()
