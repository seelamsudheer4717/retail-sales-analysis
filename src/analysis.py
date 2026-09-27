"""Run business questions against the cleaned retail database."""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import pandas as pd

QUERIES = {
    "monthly_sales": """
        SELECT substr(InvoiceDate, 1, 7) AS month,
               ROUND(SUM(Revenue), 2) AS revenue,
               COUNT(DISTINCT InvoiceNo) AS orders
        FROM transactions GROUP BY month ORDER BY month
    """,
    "top_products": """
        SELECT StockCode AS stock_code, COALESCE(NULLIF(Description, ''), '[missing description]') AS product,
               SUM(Quantity) AS units, ROUND(SUM(Revenue), 2) AS revenue
        FROM transactions GROUP BY StockCode, Description ORDER BY revenue DESC LIMIT 10
    """,
    "country_sales": """
        SELECT Country AS country, COUNT(DISTINCT InvoiceNo) AS orders,
               ROUND(SUM(Revenue), 2) AS revenue
        FROM transactions GROUP BY Country ORDER BY revenue DESC
    """,
    "customer_summary": """
        SELECT COUNT(DISTINCT CustomerID) AS identified_customers,
               COUNT(DISTINCT InvoiceNo) AS orders,
               ROUND(SUM(Revenue), 2) AS gross_sales_value,
               ROUND(1.0 * SUM(Revenue) / NULLIF(COUNT(DISTINCT InvoiceNo), 0), 2) AS average_order_value
        FROM transactions
    """,
    "repeat_customers": """
        SELECT COUNT(*) AS repeat_customers FROM (
            SELECT CustomerID FROM transactions WHERE CustomerID IS NOT NULL
            GROUP BY CustomerID HAVING COUNT(DISTINCT InvoiceNo) > 1
        )
    """,
}


def run(db: Path, output: Path) -> None:
    if not db.is_file():
        raise FileNotFoundError(f"Database not found: {db}. Run src/prepare.py first.")
    output.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db) as conn:
        for name, query in QUERIES.items():
            result = pd.read_sql_query(query, conn)
            result.to_csv(output / f"{name}.csv", index=False)
            print(f"{name}: {len(result)} row(s)")
    print(f"Reports: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("output/retail.db"))
    parser.add_argument("--output", type=Path, default=Path("output/reports"))
    args = parser.parse_args()
    run(args.db, args.output)
