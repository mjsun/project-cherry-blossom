"""
mcp_loan_server.py

MCP server exposing three tools over the loans.db SQLite database.
Uses FastMCP for clean decorator-based tool definitions.

Install:
    pip install fastmcp

Run:
    python mcp_loan_server.py
"""

import json
import sqlite3
from typing import Optional
from fastmcp import FastMCP

DB_PATH = "./loans.db"

mcp = FastMCP("loan-data")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@mcp.tool()
def lookup_loan(deal_id: str, loan_no: str) -> str:
    """Look up a single CMBS loan by deal_id and loan_no.
    Returns all fields: balance, rate, LTV, DSCR, property type, city, state, etc."""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM loans WHERE deal_id = ? AND loan_no = ?",
        (deal_id, str(loan_no)),
    ).fetchone()
    conn.close()

    if row is None:
        return json.dumps({"error": f"No loan found for {deal_id}:{loan_no}"})
    return json.dumps(dict(row), default=str, indent=2)


@mcp.tool()
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
) -> str:
    """Search CMBS loans with filters. Returns up to 50 matching loans
    sorted by cut-off date balance descending."""
    clauses = []
    values = []

    if not include_subs:
        clauses.append("is_sub_property = 0")

    for col, val in [
        ("state", state),
        ("city", city),
        ("general_property_type", general_property_type),
        ("seller", seller),
        ("deal_id", deal_id),
    ]:
        if val:
            clauses.append(f"LOWER({col}) = LOWER(?)")
            values.append(val)

    if property_name:
        clauses.append("LOWER(property_name) LIKE LOWER(?)")
        values.append(f"%{property_name}%")

    range_filters = {
        "cutoff_balance": (min_balance, max_balance),
        "gross_rate": (min_rate, max_rate),
        "cutoff_ltv": (min_ltv, max_ltv),
        "uw_noi_dscr": (min_dscr, max_dscr),
    }
    for col, (lo, hi) in range_filters.items():
        if lo is not None:
            clauses.append(f"{col} >= ?")
            values.append(lo)
        if hi is not None:
            clauses.append(f"{col} <= ?")
            values.append(hi)

    where = " AND ".join(clauses) if clauses else "1=1"
    sql = f"SELECT * FROM loans WHERE {where} ORDER BY cutoff_balance DESC LIMIT 50"

    conn = get_conn()
    rows = conn.execute(sql, values).fetchall()
    conn.close()

    result = {"count": len(rows), "loans": [dict(r) for r in rows]}
    return json.dumps(result, default=str, indent=2)


@mcp.tool()
def aggregate(group_by: str, metric: str) -> str:
    """Aggregate loan data.
    group_by: state, city, general_property_type, seller, or deal_id.
    metric: count, sum_balance, avg_balance, avg_rate, avg_ltv, avg_dscr, sum_appraised."""
    ALLOWED_GROUPS = {"state", "city", "general_property_type", "seller", "deal_id"}
    METRIC_SQL = {
        "count": "COUNT(*)",
        "sum_balance": "SUM(cutoff_balance)",
        "avg_balance": "AVG(cutoff_balance)",
        "avg_rate": "AVG(gross_rate)",
        "avg_ltv": "AVG(cutoff_ltv)",
        "avg_dscr": "AVG(uw_noi_dscr)",
        "sum_appraised": "SUM(appraised_value)",
    }

    if group_by not in ALLOWED_GROUPS:
        return json.dumps({"error": f"group_by must be one of: {sorted(ALLOWED_GROUPS)}"})
    if metric not in METRIC_SQL:
        return json.dumps({"error": f"metric must be one of: {sorted(METRIC_SQL.keys())}"})

    agg_expr = METRIC_SQL[metric]
    sql = (
        f"SELECT {group_by}, {agg_expr} AS value "
        f"FROM loans WHERE is_sub_property = 0 AND {group_by} IS NOT NULL "
        f"GROUP BY {group_by} ORDER BY value DESC"
    )

    conn = get_conn()
    rows = conn.execute(sql).fetchall()
    conn.close()

    result = {
        "group_by": group_by,
        "metric": metric,
        "results": [{"group": r[0], "value": r[1]} for r in rows],
    }
    return json.dumps(result, default=str, indent=2)


if __name__ == "__main__":
    mcp.run()