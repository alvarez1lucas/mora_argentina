"""Crédito de los proveedores no financieros (PNFC): saldo e irregularidad, informes semestrales del BCRA.

`python -m mora.ingest.pnfc [--verificar]` escribe data/processed/pnfc_informes.csv.

Las cifras están transcriptas en config/settings.yaml (pnfc.informes) con la cita textual de cada
una, porque los informes son PDF sin series y cada edición las redacta distinto. Con --verificar
se baja cada PDF y se comprueba que las citas estén en el texto y que digan el número cargado.
Son datos agregados del BCRA (no se consulta la Central de Deudores por CUIT).
"""

from __future__ import annotations

import argparse
import re
import tempfile
from pathlib import Path

import pandas as pd
import pypdf

from mora.config import path, settings
from mora.ingest.http import download


def tabla() -> pd.DataFrame:
    df = pd.DataFrame(settings()["pnfc"]["informes"])
    df["fecha"] = pd.to_datetime(df["fecha"])
    return df[["fecha", "saldo_billones", "irregularidad_pct", "url"]]


def _numero(cita: str) -> float:
    return float(re.search(r"\d+(?:,\d+)?", cita.replace("$", "")).group(0).replace(",", "."))


def _normalizar(texto: str) -> str:
    return re.sub(r"\s+", "", texto)  # pypdf a veces parte palabras con espacios


def verificar() -> None:
    for inf in settings()["pnfc"]["informes"]:
        with tempfile.TemporaryDirectory() as tmp:
            pdf = download(inf["url"], Path(tmp) / "informe.pdf")
            texto = _normalizar("\n".join(p.extract_text() or "" for p in pypdf.PdfReader(pdf).pages))
        for cita, valor in ((inf["cita_saldo"], inf["saldo_billones"]), (inf["cita_irregularidad"], inf["irregularidad_pct"])):
            assert _normalizar(cita) in texto, f"{inf['fecha']}: no está la cita «{cita}»"
            assert abs(_numero(cita) - valor) < 1e-9, f"{inf['fecha']}: la cita «{cita}» no dice {valor}"
        print(f"pnfc {inf['fecha']}: ok")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verificar", action="store_true", help="comprobar las citas contra los PDF del BCRA")
    args = parser.parse_args(argv)
    if args.verificar:
        verificar()
    out = path("processed") / "pnfc_informes.csv"
    tabla().to_csv(out, index=False, date_format="%Y-%m-%d")
    print(f"pnfc: {out}")


if __name__ == "__main__":
    main()
