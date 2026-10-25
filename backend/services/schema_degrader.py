"""
schema_degrader.py
Implements the D0–D4 schema degradation pipeline defined in Section IV
of the Talking Rabbitt research paper.

Levels:
  - D0: Clean baseline schema (standardized names, native numeric/date types).
  - D1: Syntactic noise (abbreviated headers, casing changes, underscores removed).
  - D2: Type and format inconsistency (numbers with currency/units/commas, mixed dates, string tokens for nulls).
  - D3: Semantic ambiguity & decoy columns (shadowing metrics like rev vs rev_adj, qty vs qty_returned).
  - D4: Compound degradation (D1-D3 plus cryptic undocumented header codes c01..cN, scrambled order).
"""
import copy
import random
import re
import numpy as np
import pandas as pd


# Dictionary of realistic abbreviations for D1
ABBREVIATION_MAP = {
    # Sales
    "order_id": "ord_id",
    "date": "dt",
    "region": "reg",
    "category": "cat",
    "product": "prod",
    "revenue": "tot_rev",
    "profit": "net_pft",
    "quantity": "qty",
    "customer_id": "cust_id",
    # Inventory
    "sku": "sku_no",
    "warehouse": "whse_loc",
    "stock_level": "stk_lvl",
    "reorder_point": "reord_pt",
    "unit_cost": "u_cst",
    "last_restock_date": "lst_rstk_dt",
    # Finance
    "transaction_id": "txn_id",
    "account": "acct_nm",
    "type": "txn_typ",
    "amount": "amt",
    "department": "dept",
    "vendor": "vndr",
    "status": "stat_cd",
    # Customer
    "name": "c_name",
    "segment": "seg",
    "total_spend": "tot_spnd",
    "last_order_date": "lst_ord_dt",
    "orders_count": "ord_cnt",
    "churn_risk": "chn_rsk",
    # Operations
    "task_id": "tsk_id",
    "duration": "dur_hrs",
    "priority": "pri_lvl",
    "assigned_to": "asgn_user",
    "completion_rate": "comp_pct",
}


def _abbreviate_col(col_name: str) -> str:
    cleaned = str(col_name).strip().lower().replace(" ", "_")
    if cleaned in ABBREVIATION_MAP:
        return ABBREVIATION_MAP[cleaned]
    # Fallback heuristic abbreviation
    words = cleaned.split("_")
    short_words = [w[:3] if len(w) > 3 else w for w in words]
    return "_".join(short_words)


def degrade_d1(df: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """
    D1: Abbreviate column headers, introduce inconsistent capitalization
    and minor punctuation differences.
    """
    rng = random.Random(seed)
    df_out = df.copy()
    new_cols = []
    for c in df_out.columns:
        abbr = _abbreviate_col(c)
        choice = rng.choice(["lower", "upper", "title", "dot"])
        if choice == "upper":
            abbr = abbr.upper()
        elif choice == "title":
            abbr = abbr.title()
        elif choice == "dot":
            abbr = abbr.replace("_", ".")
        new_cols.append(abbr)
    df_out.columns = new_cols
    return df_out


def degrade_d2(df: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """
    D2: D1 plus type inconsistencies:
      - Numbers formatted as string text with commas, $, %, or unit suffix.
      - Date formats randomized across rows (YYYY-MM-DD, DD/MM/YYYY, MM-DD-YYYY).
      - Sporadic non-standard missing indicators ('N/A', '-', 'missing', 'NULL').
    """
    df_out = degrade_d1(df, seed=seed)
    rng = np.random.RandomState(seed)

    for col in df_out.columns:
        col_lower = str(col).lower()

        # Date handling: format inconsistently across rows
        if "dt" in col_lower or "date" in col_lower:
            parsed = pd.to_datetime(df_out[col], errors="coerce")
            formatted = []
            for dt in parsed:
                if pd.isna(dt):
                    formatted.append(rng.choice(["N/A", "-", "missing", ""]))
                    continue
                fmt_choice = rng.choice(["iso", "slash_dmy", "slash_mdy", "dash_mdy"])
                if fmt_choice == "iso":
                    formatted.append(dt.strftime("%Y-%m-%d"))
                elif fmt_choice == "slash_dmy":
                    formatted.append(dt.strftime("%d/%m/%Y"))
                elif fmt_choice == "slash_mdy":
                    formatted.append(dt.strftime("%m/%d/%Y"))
                else:
                    formatted.append(dt.strftime("%m-%d-%Y"))
            df_out[col] = formatted

        # Numeric handling: stringify with commas, currency or unit suffixes
        elif pd.api.types.is_numeric_dtype(df_out[col]):
            series = df_out[col].copy()
            vals = []
            is_currency = any(w in col_lower for w in ["rev", "amt", "cst", "spnd", "pft"])
            is_pct = any(w in col_lower for w in ["pct", "rate", "comp"])

            for v in series:
                if pd.isna(v):
                    vals.append(rng.choice(["N/A", "-", "NULL"]))
                    continue
                if rng.rand() < 0.4:  # 40% formatted
                    if is_currency:
                        vals.append(f"${v:,.2f}")
                    elif is_pct:
                        vals.append(f"{v * (100 if v <= 1 else 1):.1f}%")
                    elif float(v).is_integer():
                        vals.append(f"{int(v):,d} units" if rng.rand() < 0.3 else f"{int(v):,d}")
                    else:
                        vals.append(f"{v:,.2f}")
                else:
                    vals.append(str(v))
            df_out[col] = vals

    return df_out


def degrade_d3(df: pd.DataFrame, dataset_name: str = "sales", seed: int = 42) -> pd.DataFrame:
    """
    D3: D2 plus decoy columns and semantic shadowing.
    Decoy columns create multiple plausible choices (e.g., rev vs rev_adj,
    qty vs qty_returned, amount vs gross_amount).
    """
    df_out = degrade_d2(df, seed=seed)
    rng = np.random.RandomState(seed)
    n = len(df_out)

    dataset_name = dataset_name.lower()

    if "sales" in dataset_name:
        rev_col = next((c for c in df_out.columns if "rev" in c.lower()), None)
        qty_col = next((c for c in df_out.columns if "qty" in c.lower()), None)
        if rev_col:
            noise = rng.uniform(0.85, 0.98, n)
            df_out["rev_adj"] = [f"${val:,.2f}" for val in (noise * 5000)]
        if qty_col:
            df_out["qty_returned"] = rng.randint(0, 5, n)

    elif "inventory" in dataset_name:
        stk_col = next((c for c in df_out.columns if "stk" in c.lower() or "stock" in c.lower()), None)
        cst_col = next((c for c in df_out.columns if "cst" in c.lower() or "cost" in c.lower()), None)
        if stk_col:
            df_out["stk_rsrvd"] = rng.randint(5, 50, n)
        if cst_col:
            df_out["repl_cst"] = [f"${v:.2f}" for v in rng.uniform(10, 150, n)]

    elif "finance" in dataset_name:
        amt_col = next((c for c in df_out.columns if "amt" in c.lower() or "amount" in c.lower()), None)
        if amt_col:
            df_out["gross_amt"] = [f"${v:,.2f}" for v in rng.uniform(100, 12000, n)]
            df_out["tax_ded"] = [f"${v:,.2f}" for v in rng.uniform(10, 1200, n)]

    elif "customer" in dataset_name:
        spnd_col = next((c for c in df_out.columns if "spnd" in c.lower() or "spend" in c.lower()), None)
        if spnd_col:
            df_out["life_spnd_gross"] = [f"${v:,.2f}" for v in rng.uniform(500, 35000, n)]
            df_out["rtn_cnt"] = rng.randint(0, 3, n)

    elif "operations" in dataset_name:
        dur_col = next((c for c in df_out.columns if "dur" in c.lower() or "hrs" in c.lower()), None)
        if dur_col:
            df_out["logged_raw_hrs"] = [f"{v:.1f}h" for v in rng.uniform(1, 40, n)]
            df_out["raw_progress"] = [f"{v:.1f}%" for v in rng.uniform(10, 100, n)]

    df_out["audit_flag"] = rng.choice(["OK", "VERIFIED", "PENDING", "FLAGGED"], n)

    return df_out


def degrade_d4(df: pd.DataFrame, dataset_name: str = "sales", seed: int = 42) -> pd.DataFrame:
    """
    D4: Compound degradation (D3) plus undocumented cryptic column codes,
    meaningless column names (c01..cN, amt2), and scrambled column ordering.
    """
    df_out = degrade_d3(df, dataset_name=dataset_name, seed=seed)
    rng = random.Random(seed)

    cols = list(df_out.columns)
    rng.shuffle(cols)
    df_out = df_out[cols]

    new_names = {}
    code_counter = 10
    for idx, col in enumerate(df_out.columns):
        if idx % 2 == 0 or idx == len(df_out.columns) - 1:
            new_names[col] = f"c{code_counter}"
            code_counter += 1
        elif idx == 1:
            new_names[col] = "amt_code_2"
        elif idx == 3:
            new_names[col] = "fld_09x"

    df_out = df_out.rename(columns=new_names)
    return df_out


def apply_degradation(df: pd.DataFrame, level: str, dataset_name: str = "sales", seed: int = 42) -> pd.DataFrame:
    """
    Unified entry point to apply schema degradation level D0, D1, D2, D3, or D4.
    """
    lvl = str(level).strip().upper()
    if lvl == "D0":
        return df.copy()
    elif lvl == "D1":
        return degrade_d1(df, seed=seed)
    elif lvl == "D2":
        return degrade_d2(df, seed=seed)
    elif lvl == "D3":
        return degrade_d3(df, dataset_name=dataset_name, seed=seed)
    elif lvl == "D4":
        return degrade_d4(df, dataset_name=dataset_name, seed=seed)
    else:
        raise ValueError(f"Unknown degradation level: {level}. Valid levels are D0, D1, D2, D3, D4.")
