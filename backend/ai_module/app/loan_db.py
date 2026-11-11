"""
loan_db.py

Direct Python interface to loans.db — same logic as the MCP tools
but callable without MCP protocol overhead.
"""

import sqlite3
import json
from typing import Optional

DB_PATH = "./loans.db"


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def lookup_loan(deal_id: str, loan_no: str) -> dict:
    conn = _conn()
    row = conn.execute(
        "SELECT * FROM loans WHERE deal_id = ? AND loan_no = ?",
        (deal_id, str(loan_no)),
    ).fetchone()
    conn.close()
    return dict(row) if row else {}


def search_loans(
    state: Optional[str] = None,
    city: Optional[str] = None,
    general_property_type: Optional[str] = None,
    seller: Optional[str] = None,
    deal_id: Optional[str] = None,
    property_name: Optional[str] = None,
    min_balance: Optional[float] = None,
    max_balance: Optional[float] = None,
    min_rate: Optional[float] = None,
    max_rate: Optional[float] = None,
    min_ltv: Optional[float] = None,
    max_ltv: Optional[float] = None,
    min_dscr: Optional[float] = None,
    max_dscr: Optional[float] = None,
    include_subs: bool = False,
) -> list[dict]:
    clauses, values = [], []

    if not include_subs:
        clauses.append("is_sub_property = 0")

    for col, val in [("state", state), ("city", city),
                     ("general_property_type", general_property_type),
                     ("seller", seller), ("deal_id", deal_id)]:
        if val:
            clauses.append(f"LOWER({col}) = LOWER(?)")
            values.append(val)

    if property_name:
        clauses.append("LOWER(property_name) LIKE LOWER(?)")
        values.append(f"%{property_name}%")

    for col, lo, hi in [
        ("cutoff_balance", min_balance, max_balance),
        ("gross_rate", min_rate, max_rate),
        ("cutoff_ltv", min_ltv, max_ltv),
        ("uw_noi_dscr", min_dscr, max_dscr),
    ]:
        if lo is not None:
            clauses.append(f"{col} >= ?"); values.append(lo)
        if hi is not None:
            clauses.append(f"{col} <= ?"); values.append(hi)

    where = " AND ".join(clauses) if clauses else "1=1"
    conn = _conn()
    rows = conn.execute(
        f"SELECT * FROM loans WHERE {where} ORDER BY cutoff_balance DESC LIMIT 50",
        values,
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def aggregate(group_by: str, metric: str) -> list[dict]:
    ALLOWED = {"state", "city", "general_property_type", "seller", "deal_id"}
    METRICS = {
        "count": "COUNT(*)", "sum_balance": "SUM(cutoff_balance)",
        "avg_balance": "AVG(cutoff_balance)", "avg_rate": "AVG(gross_rate)",
        "avg_ltv": "AVG(cutoff_ltv)", "avg_dscr": "AVG(uw_noi_dscr)",
        "sum_appraised": "SUM(appraised_value)",
    }
    if group_by not in ALLOWED or metric not in METRICS:
        return []

    conn = _conn()
    rows = conn.execute(
        f"SELECT {group_by}, {METRICS[metric]} AS value "
        f"FROM loans WHERE is_sub_property = 0 AND {group_by} IS NOT NULL "
        f"GROUP BY {group_by} ORDER BY value DESC"
    ).fetchall()
    conn.close()
    return [{"group": r[0], "value": r[1]} for r in rows]
