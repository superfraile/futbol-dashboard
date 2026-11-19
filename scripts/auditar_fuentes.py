import json
import unittest
from datetime import date
from urllib.request import urlopen
from pathlib import Path

CODES = dict(GER="de", ESP="es", FRA="fr", ENG="en", ITA="it", NED="nl", POR="pt")
SOURCE = "https://raw.githubusercontent.com/openfootball/football.json/master"

def audit(matches, today):
    played = [m for m in matches if isinstance(m.get("score", {}).get("ft"), list)]
    missing = [m for m in matches if m.get("date", "") < today and m not in played]
    return {"total": len(matches), "resultados": len(played),
            "ultimo_resultado": max((m["date"] for m in played), default=None),
            "pasados_sin_resultado": len(missing)}

def main():
    today = date.today().isoformat()
    year = date.today().year - (date.today().month < 7)
    season = f"{year}-{(year+1)%100:02d}"
    report = {}
    for league, code in CODES.items():
        try:
            with urlopen(f"{SOURCE}/{season}/{code}.1.json", timeout=25) as response:
                report[league] = audit(json.load(response)["matches"], today)
        except Exception as exc:
            report[league] = {"error": str(exc)}
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
