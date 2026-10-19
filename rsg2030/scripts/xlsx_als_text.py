"""Excel-Mappe als Text ausgeben, damit `git diff` Änderungen an den Eingaben (manuell.xlsx, freigabe.xlsx) zeigt.

Je Blatt eine Überschrift, je Zeile die Zellwerte mit Tab getrennt (Formeln als Formel, nicht als Ergebnis).
Einmal je Klon einrichten (die Zuordnung *.xlsx → xlsx steht in .gitattributes):

    git config diff.xlsx.textconv ".venv/bin/python -m rsg2030.scripts.xlsx_als_text"
"""

from __future__ import annotations

import sys
from pathlib import Path

import openpyxl


def als_text(pfad: Path) -> str:
    wb = openpyxl.load_workbook(pfad)
    teile: list[str] = []
    for ws in wb.worksheets:
        teile.append(f"## {ws.title}")
        for zeile in ws.iter_rows(values_only=True):
            werte = ["" if v is None else str(v) for v in zeile]
            while werte and not werte[-1]:
                werte.pop()
            teile.append("\t".join(werte))
    return "\n".join(teile) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("Aufruf: python -m rsg2030.scripts.xlsx_als_text DATEI.xlsx", file=sys.stderr)
        return 1
    sys.stdout.write(als_text(Path(args[0])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
