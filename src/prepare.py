"""Clean UCI Online Retail transactions and load a reproducible SQLite database."""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import pandas as pd

REQUIRED = {"InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice", "CustomerID", "Country"}


def clean_transactions(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    missing = REQUIRED - set(frame.columns)
    if missing:
        raise ValueError(f"Missing columns: {', '.join(sorted(missing))}")
    data = frame[list(REQUIRED)].copy()
    data["InvoiceNo"] = data["InvoiceNo"].astype("string").str.strip()
    data["StockCode"] = data["StockCode"].astype("string").str.strip()
    data["Description"] = data["Description"].astype("string").str.strip()
    data["Country"] = data["Country"].astype("string").str.strip()
    data["InvoiceDate"] = pd.to_datetime(data["InvoiceDate"], errors="coerce")
    for col in ("Quantity", "UnitPrice", "CustomerID"):
        data[col] = pd.to_numeric(data[col], errors="coerce")
    rows_input = len(data)
    # Explicit scope: completed, positive-value product sales only.
    valid = (
        data["InvoiceNo"].notna() & ~data["InvoiceNo"].str.upper().str.startswith("C", na=False)
        & data["InvoiceDate"].notna() & data["StockCode"].notna()
        & (data["Quantity"] > 0) & (data["UnitPrice"] > 0)
    )
    data = data.loc[valid].drop_duplicates().copy()
    data["Revenue"] = (data["Quantity"] * data["UnitPrice"]).round(2)
    data["CustomerID"] = data["CustomerID"].astype("Int64").astype("string")
    data["InvoiceDate"] = data["InvoiceDate"].dt.strftime("%Y-%m-%d %H:%M:%S")
    columns = ["InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice", "CustomerID", "Country", "Revenue"]
    return data[columns], {"rows_input": rows_input, "rows_clean": len(data), "rows_excluded_or_deduplicated": rows_input - len(data)}


def load_data(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".xlsx":
        return pd.read_excel(path, engine="openpyxl")
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, dtype={"InvoiceNo": "string", "StockCode": "string"})
    raise ValueError("Input must be a .csv or .xlsx file")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="UCI Online Retail .xlsx or .csv")
    parser.add_argument("--db", type=Path, default=Path("output/retail.db"))
    args = parser.parse_args()
    if not args.input.is_file():
        parser.error(f"Input not found: {args.input}")
    cleaned, audit = clean_transactions(load_data(args.input))
    args.db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(args.db) as conn:
        cleaned.to_sql("transactions", conn, if_exists="replace", index=False, chunksize=10000)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_date ON transactions(InvoiceDate)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_invoice ON transactions(InvoiceNo)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_customer ON transactions(CustomerID)")
    (args.db.parent / "cleaning_summary.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit, indent=2))
    print(f"Database: {args.db}")


if __name__ == "__main__":
    main()
