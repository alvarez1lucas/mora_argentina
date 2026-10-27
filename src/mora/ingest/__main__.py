"""Ingesta completa: `python -m mora.ingest [--skip-entidades] [--max-months N]`.

Escribe en data/processed/ las series ya ordenadas y un manifest.json con la fecha de
corrida, el último dato de cada archivo y la cantidad de filas.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

import pandas as pd

from mora.config import path
from mora.ingest import bcra_anexo, bcra_api, datos_gob, entidades


def _summary(df: pd.DataFrame, date_col: str | None = None) -> dict:
    fechas = pd.to_datetime(df[date_col] if date_col else df.index)
    return {"filas": int(len(df)), "desde": str(fechas.min().date()), "hasta": str(fechas.max().date())}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-entidades", action="store_true", help="no actualizar el panel por entidad")
    parser.add_argument("--max-months", type=int, default=None, help="tope de meses nuevos del panel por corrida")
    parser.add_argument("--keep-archives", action="store_true", help="conservar los 7z en data/raw")
    parser.add_argument("--rebuild-entidades", action="store_true", help="reconstruir el panel por entidad desde cero")
    args = parser.parse_args(argv)

    out = path("processed")
    manifest_file = out / "manifest.json"
    previous = json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.exists() else {}
    manifest = {
        "corrida_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "archivos": previous.get("archivos", {}),
    }

    xlsx = bcra_anexo.download_anexo()
    anexo = bcra_anexo.read_anexo(xlsx)
    anexo.to_csv(out / "anexo_calidad_cartera.csv", index=False, date_format="%Y-%m-%d")
    manifest["archivos"]["anexo_calidad_cartera.csv"] = _summary(anexo, "fecha")
    familias = bcra_anexo.familias_por_linea(anexo)
    familias.to_csv(out / "familias_por_linea.csv", date_format="%Y-%m-%d")
    manifest["archivos"]["familias_por_linea.csv"] = _summary(familias)
    print("anexo: ok")

    bcra = bcra_api.build_panel()
    bcra.to_csv(out / "bcra_mensual.csv", date_format="%Y-%m-%d")
    manifest["archivos"]["bcra_mensual.csv"] = _summary(bcra)
    print("api bcra: ok")

    for freq, df in datos_gob.build_panel().items():
        name = f"macro_{freq}.csv"
        df.to_csv(out / name, date_format="%Y-%m-%d")
        manifest["archivos"][name] = _summary(df)
    print("datos.gob.ar: ok")

    if not args.skip_entidades:
        panel = entidades.update_panel(
            out,
            max_months=args.max_months,
            keep_archives=args.keep_archives or None,
            rebuild=args.rebuild_entidades,
        )
        manifest["archivos"]["entidades_panel.csv"] = _summary(panel, "fecha")

    with open(manifest_file, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
