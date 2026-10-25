"""
generate_sme_benchmark.py
Generates the 5 SME datasets, their D0-D4 degraded variants,
and computes ground truth answers for the 30 benchmark questions + 15 ambiguous probes.
"""
import json
import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from services.schema_degrader import apply_degradation


def generate_datasets():
    np.random.seed(42)
    output_dir = BASE_DIR / "benchmark" / "datasets"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Sales Data (1000 rows)
    n_sales = 1000
    dates = pd.date_range("2024-01-01", "2024-12-31", periods=n_sales).strftime("%Y-%m-%d")
    regions = ["North", "South", "East", "West"]
    categories = ["Electronics", "Office Supplies", "Furniture", "Apparel"]
    products = ["Quantum Laptop", "Ergo Chair", "Smart Desk", "Cloud Router", "Wireless Headset", "Ultra Monitor"]
    
    cat_choices = np.random.choice(categories, n_sales)
    prod_choices = np.random.choice(products, n_sales)
    reg_choices = np.random.choice(regions, n_sales, p=[0.3, 0.25, 0.25, 0.2])
    quantities = np.random.randint(1, 15, n_sales)
    prices = {"Quantum Laptop": 1200.0, "Ergo Chair": 350.0, "Smart Desk": 550.0, "Cloud Router": 180.0, "Wireless Headset": 95.0, "Ultra Monitor": 420.0}
    unit_costs = {"Quantum Laptop": 800.0, "Ergo Chair": 200.0, "Smart Desk": 310.0, "Cloud Router": 95.0, "Wireless Headset": 40.0, "Ultra Monitor": 230.0}
    
    revs = [quantities[i] * prices[prod_choices[i]] * np.random.uniform(0.95, 1.05) for i in range(n_sales)]
    profits = [revs[i] - (quantities[i] * unit_costs[prod_choices[i]]) for i in range(n_sales)]
    
    sales_df = pd.DataFrame({
        "Order_ID": [f"ORD-{10000 + i}" for i in range(n_sales)],
        "Date": dates,
        "Region": reg_choices,
        "Category": cat_choices,
        "Product": prod_choices,
        "Revenue": np.round(revs, 2),
        "Profit": np.round(profits, 2),
        "Quantity": quantities,
        "Customer_ID": [f"CUST-{np.random.randint(100, 350)}" for _ in range(n_sales)],
    })

    # 2. Inventory Data (600 rows)
    n_inv = 600
    warehouses = ["WH-East", "WH-West", "WH-Central", "WH-South"]
    inv_skus = [f"SKU-{20000 + i}" for i in range(n_inv)]
    inv_prods = np.random.choice(products, n_inv)
    inv_wh = np.random.choice(warehouses, n_inv)
    stock_levels = np.random.randint(10, 500, n_inv)
    reorder_pts = np.random.randint(20, 100, n_inv)
    unit_csts = [unit_costs[p] * np.random.uniform(0.9, 1.1) for p in inv_prods]
    restock_dates = pd.date_range("2024-03-01", "2024-11-30", periods=n_inv).strftime("%Y-%m-%d")

    inv_df = pd.DataFrame({
        "SKU": inv_skus,
        "Product": inv_prods,
        "Warehouse": inv_wh,
        "Stock_Level": stock_levels,
        "Reorder_Point": reorder_pts,
        "Unit_Cost": np.round(unit_csts, 2),
        "Last_Restock_Date": restock_dates,
    })

    # 3. Finance Data (800 rows)
    n_fin = 800
    fin_dates = pd.date_range("2024-01-01", "2024-12-31", periods=n_fin).strftime("%Y-%m-%d")
    depts = ["Marketing", "Engineering", "Sales", "Operations", "HR", "Finance"]
    vendors = ["AWS Cloud", "Google Ads", "Slack Tech", "WeWork Office", "Stripe Processing", "Salesforce"]
    types = ["Expense", "Revenue", "Accounts Payable", "Payroll"]
    statuses = ["Completed", "Pending", "Approved", "Audited"]

    fin_types = np.random.choice(types, n_fin, p=[0.45, 0.30, 0.15, 0.10])
    fin_amounts = [np.random.uniform(250, 15000) if t != "Payroll" else np.random.uniform(15000, 45000) for t in fin_types]

    finance_df = pd.DataFrame({
        "Transaction_ID": [f"TXN-{30000 + i}" for i in range(n_fin)],
        "Date": fin_dates,
        "Account": np.random.choice(["Operating Account", "Payroll Reserve", "Merchant Clearing", "Capital Fund"], n_fin),
        "Type": fin_types,
        "Amount": np.round(fin_amounts, 2),
        "Department": np.random.choice(depts, n_fin),
        "Vendor": np.random.choice(vendors, n_fin),
        "Status": np.random.choice(statuses, n_fin, p=[0.7, 0.1, 0.15, 0.05]),
    })

    # 4. Customer Data (700 rows)
    n_cust = 700
    cust_ids = [f"CUST-{100 + i}" for i in range(n_cust)]
    first_names = ["James", "Emma", "Liam", "Olivia", "Noah", "Sophia", "Lucas", "Mia", "Ethan", "Ava", "William", "Isabella"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
    names = [f"{np.random.choice(first_names)} {np.random.choice(last_names)}" for _ in range(n_cust)]
    segments = ["Enterprise", "Mid-Market", "Small Business", "Startup"]
    total_spends = np.random.exponential(scale=6500, size=n_cust) + 400
    orders_counts = np.random.randint(1, 45, n_cust)
    churn_risks = np.random.choice(["Low", "Medium", "High"], n_cust, p=[0.55, 0.30, 0.15])
    last_orders = pd.date_range("2024-06-01", "2024-12-31", periods=n_cust).strftime("%Y-%m-%d")

    cust_df = pd.DataFrame({
        "Customer_ID": cust_ids,
        "Name": names,
        "Segment": np.random.choice(segments, n_cust, p=[0.25, 0.35, 0.25, 0.15]),
        "Region": np.random.choice(regions, n_cust),
        "Total_Spend": np.round(total_spends, 2),
        "Last_Order_Date": last_orders,
        "Orders_Count": orders_counts,
        "Churn_Risk": churn_risks,
    })

    # 5. Operations Data (750 rows)
    n_ops = 750
    ops_dates = pd.date_range("2024-01-01", "2024-12-31", periods=n_ops).strftime("%Y-%m-%d")
    ops_statuses = ["Completed", "In Progress", "Blocked", "Review"]
    durations = np.random.uniform(0.5, 48.0, n_ops)
    priorities = ["Critical", "High", "Medium", "Low"]
    assignees = ["Alex Mercer", "Jordan Lee", "Taylor Swift", "Sam Chen", "Dana White", "Morgan Riley"]
    comp_rates = [100.0 if s == "Completed" else np.random.uniform(10.0, 95.0) for s in np.random.choice(ops_statuses, n_ops, p=[0.65, 0.2, 0.05, 0.1])]

    ops_df = pd.DataFrame({
        "Task_ID": [f"TSK-{50000 + i}" for i in range(n_ops)],
        "Date": ops_dates,
        "Department": np.random.choice(depts, n_ops),
        "Status": np.random.choice(ops_statuses, n_ops, p=[0.65, 0.2, 0.05, 0.1]),
        "Duration": np.round(durations, 1),
        "Priority": np.random.choice(priorities, n_ops, p=[0.15, 0.35, 0.35, 0.15]),
        "Assigned_To": np.random.choice(assignees, n_ops),
        "Completion_Rate": np.round(comp_rates, 1),
    })

    datasets = {
        "sales": sales_df,
        "inventory": inv_df,
        "finance": finance_df,
        "customer": cust_df,
        "operations": ops_df,
    }

    # Save clean baseline D0 in benchmark/datasets/ and workspace
    for name, df in datasets.items():
        clean_file = output_dir / f"{name}_data.csv"
        df.to_csv(clean_file, index=False)
        print(f"Saved {clean_file} ({len(df)} rows)")

    # Also save D0 to D4 variants for all datasets
    for name, df in datasets.items():
        for level in ["D0", "D1", "D2", "D3", "D4"]:
            degraded = apply_degradation(df, level=level, dataset_name=name, seed=42)
            deg_path = output_dir / f"{name}_{level.lower()}.csv"
            degraded.to_csv(deg_path, index=False)
            print(f"Generated {deg_path} (columns: {list(degraded.columns[:4])}...)")

    return datasets


def build_questions_and_ground_truth(datasets):
    sales_df = datasets["sales"]
    inv_df = datasets["inventory"]
    fin_df = datasets["finance"]
    cust_df = datasets["customer"]
    ops_df = datasets["operations"]

    questions = []
    ground_truth = {}

    def add_q(qid, dataset, qtype, text, gt_val, val_type="numeric", unit=None, explanation=""):
        questions.append({
            "id": qid,
            "dataset": dataset,
            "type": qtype,
            "question": text,
            "value_type": val_type,
            "unit": unit,
        })
        ground_truth[qid] = {
            "value": gt_val,
            "value_type": val_type,
            "unit": unit,
            "explanation": explanation,
        }

    # --- Sales (6 questions) ---
    tot_rev = float(np.round(sales_df["Revenue"].sum(), 2))
    add_q("SALES-01", "sales", "descriptive", "What is the total revenue across all sales orders?",
          tot_rev, "numeric", "USD", f"Sum of Revenue column is {tot_rev}")

    north_pft = float(np.round(sales_df[sales_df["Region"] == "North"]["Profit"].sum(), 2))
    add_q("SALES-02", "sales", "diagnostic", "What is the total profit generated by the North region?",
          north_pft, "numeric", "USD", f"Sum of Profit where Region == 'North' is {north_pft}")

    avg_qty_elect = float(np.round(sales_df[sales_df["Category"] == "Electronics"]["Quantity"].mean(), 2))
    add_q("SALES-03", "sales", "descriptive", "What is the average order quantity for Electronics?",
          avg_qty_elect, "numeric", "units", f"Mean of Quantity for Electronics category is {avg_qty_elect}")

    best_cat = sales_df.groupby("Category")["Revenue"].sum().idxmax()
    add_q("SALES-04", "sales", "comparative", "Which product category generated the highest total revenue?",
          best_cat, "string", None, f"Category with maximum total revenue is {best_cat}")

    total_orders = int(len(sales_df))
    add_q("SALES-05", "sales", "descriptive", "How many total sales orders were recorded in the dataset?",
          total_orders, "integer", "orders", f"Total row count is {total_orders}")

    south_rev = float(np.round(sales_df[sales_df["Region"] == "South"]["Revenue"].sum(), 2))
    west_rev = float(np.round(sales_df[sales_df["Region"] == "West"]["Revenue"].sum(), 2))
    diff_sw = float(np.round(south_rev - west_rev, 2))
    add_q("SALES-06", "sales", "comparative", "What is the difference in total revenue between South region and West region?",
          diff_sw, "numeric", "USD", f"South revenue ({south_rev}) minus West revenue ({west_rev}) = {diff_sw}")

    # --- Inventory (6 questions) ---
    tot_stock = int(inv_df["Stock_Level"].sum())
    add_q("INV-01", "inventory", "descriptive", "What is the total stock level across all inventory items?",
          tot_stock, "integer", "units", f"Sum of Stock_Level is {tot_stock}")

    items_reorder = int((inv_df["Stock_Level"] < inv_df["Reorder_Point"]).sum())
    add_q("INV-02", "inventory", "diagnostic", "How many items currently have stock levels below their reorder point?",
          items_reorder, "integer", "items", f"Count of rows where Stock_Level < Reorder_Point is {items_reorder}")

    avg_unit_cost = float(np.round(inv_df["Unit_Cost"].mean(), 2))
    add_q("INV-03", "inventory", "descriptive", "What is the overall average unit cost across all SKUs?",
          avg_unit_cost, "numeric", "USD", f"Mean of Unit_Cost is {avg_unit_cost}")

    wh_most_stock = inv_df.groupby("Warehouse")["Stock_Level"].sum().idxmax()
    add_q("INV-04", "inventory", "comparative", "Which warehouse holds the largest total number of stock units?",
          wh_most_stock, "string", None, f"Warehouse with highest sum of Stock_Level is {wh_most_stock}")

    inv_value = float(np.round((inv_df["Stock_Level"] * inv_df["Unit_Cost"]).sum(), 2))
    add_q("INV-05", "inventory", "descriptive", "What is the total valuation of all inventory in stock (Stock_Level * Unit_Cost)?",
          inv_value, "numeric", "USD", f"Total inventory valuation is {inv_value}")

    wh_east_items = int((inv_df["Warehouse"] == "WH-East").sum())
    add_q("INV-06", "inventory", "comparative", "How many distinct SKU records are managed in the WH-East warehouse?",
          wh_east_items, "integer", "SKUs", f"SKUs in WH-East is {wh_east_items}")

    # --- Finance (6 questions) ---
    tot_expense = float(np.round(fin_df[fin_df["Type"] == "Expense"]["Amount"].sum(), 2))
    add_q("FIN-01", "finance", "descriptive", "What is the total amount spent on Expense transactions?",
          tot_expense, "numeric", "USD", f"Sum of Amount where Type == 'Expense' is {tot_expense}")

    marketing_amt = float(np.round(fin_df[fin_df["Department"] == "Marketing"]["Amount"].sum(), 2))
    add_q("FIN-02", "finance", "diagnostic", "What is the total financial transaction volume for the Marketing department?",
          marketing_amt, "numeric", "USD", f"Sum of Amount for Marketing department is {marketing_amt}")

    tot_payroll = float(np.round(fin_df[fin_df["Type"] == "Payroll"]["Amount"].sum(), 2))
    add_q("FIN-03", "finance", "descriptive", "What is the total payout disbursed under Payroll type?",
          tot_payroll, "numeric", "USD", f"Sum of Payroll amounts is {tot_payroll}")

    dept_max_spend = fin_df.groupby("Department")["Amount"].sum().idxmax()
    add_q("FIN-04", "finance", "comparative", "Which department accounts for the highest cumulative financial outflow?",
          dept_max_spend, "string", None, f"Department with max total Amount is {dept_max_spend}")

    pending_txns = int((fin_df["Status"] == "Pending").sum())
    add_q("FIN-05", "finance", "diagnostic", "How many transactions are currently marked with Pending status?",
          pending_txns, "integer", "transactions", f"Count of Status == 'Pending' is {pending_txns}")

    top_vendor = fin_df.groupby("Vendor")["Amount"].sum().idxmax()
    add_q("FIN-06", "finance", "comparative", "Which vendor has received the highest total transaction payments?",
          top_vendor, "string", None, f"Vendor with highest total sum is {top_vendor}")

    # --- Customer (6 questions) ---
    tot_cust_spend = float(np.round(cust_df["Total_Spend"].sum(), 2))
    add_q("CUST-01", "customer", "descriptive", "What is the cumulative total spend across all customers?",
          tot_cust_spend, "numeric", "USD", f"Sum of Total_Spend is {tot_cust_spend}")

    high_risk_custs = int((cust_df["Churn_Risk"] == "High").sum())
    add_q("CUST-02", "customer", "diagnostic", "How many customers are flagged with a High Churn Risk?",
          high_risk_custs, "integer", "customers", f"Count of Churn_Risk == 'High' is {high_risk_custs}")

    avg_spend_enterprise = float(np.round(cust_df[cust_df["Segment"] == "Enterprise"]["Total_Spend"].mean(), 2))
    add_q("CUST-03", "customer", "descriptive", "What is the average total spend for Enterprise segment customers?",
          avg_spend_enterprise, "numeric", "USD", f"Mean Total_Spend for Enterprise is {avg_spend_enterprise}")

    seg_highest_spend = cust_df.groupby("Segment")["Total_Spend"].sum().idxmax()
    add_q("CUST-04", "customer", "comparative", "Which customer segment accounts for the highest total spend?",
          seg_highest_spend, "string", None, f"Segment with highest spend is {seg_highest_spend}")

    avg_orders_per_cust = float(np.round(cust_df["Orders_Count"].mean(), 2))
    add_q("CUST-05", "customer", "descriptive", "What is the average number of orders per customer across the base?",
          avg_orders_per_cust, "numeric", "orders", f"Mean of Orders_Count is {avg_orders_per_cust}")

    loyal_custs = int((cust_df["Orders_Count"] > 25).sum())
    add_q("CUST-06", "customer", "diagnostic", "How many high-frequency customers have placed more than 25 orders?",
          loyal_custs, "integer", "customers", f"Count of Orders_Count > 25 is {loyal_custs}")

    # --- Operations (6 questions) ---
    avg_task_duration = float(np.round(ops_df["Duration"].mean(), 2))
    add_q("OPS-01", "operations", "descriptive", "What is the average duration in hours across all operational tasks?",
          avg_task_duration, "numeric", "hours", f"Mean Duration is {avg_task_duration}")

    blocked_tasks = int((ops_df["Status"] == "Blocked").sum())
    add_q("OPS-02", "operations", "diagnostic", "How many operational tasks are currently recorded as Blocked?",
          blocked_tasks, "integer", "tasks", f"Count where Status == 'Blocked' is {blocked_tasks}")

    crit_tasks = int((ops_df["Priority"] == "Critical").sum())
    add_q("OPS-03", "operations", "descriptive", "What is the total number of Critical priority tasks in the system?",
          crit_tasks, "integer", "tasks", f"Count where Priority == 'Critical' is {crit_tasks}")

    dept_longest_dur = ops_df.groupby("Department")["Duration"].mean().idxmax()
    add_q("OPS-04", "operations", "comparative", "Which department exhibits the highest average task duration?",
          dept_longest_dur, "string", None, f"Department with highest average duration is {dept_longest_dur}")

    avg_comp_rate = float(np.round(ops_df["Completion_Rate"].mean(), 2))
    add_q("OPS-05", "operations", "descriptive", "What is the overall average completion rate across all operational tasks?",
          avg_comp_rate, "numeric", "%", f"Mean Completion_Rate is {avg_comp_rate}%")

    top_assignee = ops_df["Assigned_To"].value_counts().idxmax()
    add_q("OPS-06", "operations", "comparative", "Which team member has been assigned the largest volume of tasks?",
          top_assignee, "string", None, f"Assignee with most task rows is {top_assignee}")

    # --- Ambiguous Probes (15 questions: 3 per dataset) ---
    ambiguous_questions = [
        # Sales
        {
            "id": "AMB-SALES-01",
            "dataset": "sales",
            "question": "What is the total revenue?",
            "ambiguity_type": "decoy_column_conflict",
            "d0_expected_behavior": "Straightforwardly sums Revenue ($2.4M)",
            "d3_expected_behavior": "Subject to Confident-But-Wrong (CBW) choice between tot_rev and rev_adj decoy without clarification"
        },
        {
            "id": "AMB-SALES-02",
            "dataset": "sales",
            "question": "How many units were sold?",
            "ambiguity_type": "decoy_column_conflict",
            "d0_expected_behavior": "Sums Quantity column",
            "d3_expected_behavior": "Confuses gross quantity with qty_returned decoy column"
        },
        {
            "id": "AMB-SALES-03",
            "dataset": "sales",
            "question": "Show performance of top category",
            "ambiguity_type": "underspecified_metric",
            "d0_expected_behavior": "Clarifies or ranks by revenue by default",
            "d3_expected_behavior": "Selects arbitrary decoy metric (e.g. rev_adj) with false confidence"
        },
        # Inventory
        {
            "id": "AMB-INV-01",
            "dataset": "inventory",
            "question": "What is our current available inventory?",
            "ambiguity_type": "decoy_column_conflict",
            "d0_expected_behavior": "Reports Stock_Level",
            "d3_expected_behavior": "CBW conflation with stk_rsrvd (reserved stock) without hedging"
        },
        {
            "id": "AMB-INV-02",
            "dataset": "inventory",
            "question": "What is the cost of our stock?",
            "ambiguity_type": "semantic_multiplicity",
            "d0_expected_behavior": "Uses Unit_Cost or Unit_Cost * Stock_Level",
            "d3_expected_behavior": "Mistakes replacement cost (repl_cst) for historical cost"
        },
        {
            "id": "AMB-INV-03",
            "dataset": "inventory",
            "question": "Which warehouse needs restocking?",
            "ambiguity_type": "threshold_ambiguity",
            "d0_expected_behavior": "Evaluates stock < reorder_point per warehouse",
            "d3_expected_behavior": "Fails due to format noise or misidentifies warehouse by string codes"
        },
        # Finance
        {
            "id": "AMB-FIN-01",
            "dataset": "finance",
            "question": "What was the total expenditure?",
            "ambiguity_type": "decoy_column_conflict",
            "d0_expected_behavior": "Filters Amount for Type == 'Expense'",
            "d3_expected_behavior": "Sums gross_amt decoy instead of net amount"
        },
        {
            "id": "AMB-FIN-02",
            "dataset": "finance",
            "question": "What are our total tax deductions?",
            "ambiguity_type": "decoy_column_conflict",
            "d0_expected_behavior": "Explicitly states no tax column exists in clean schema",
            "d3_expected_behavior": "Hallucinates or uses injected decoy column tax_ded confidently"
        },
        {
            "id": "AMB-FIN-03",
            "dataset": "finance",
            "question": "Summarize pending vendor balances",
            "ambiguity_type": "status_semantic_split",
            "d0_expected_behavior": "Filters Status == 'Pending' and groups by Vendor",
            "d3_expected_behavior": "Fails to match formatted currency strings or corrupted status codes"
        },
        # Customer
        {
            "id": "AMB-CUST-01",
            "dataset": "customer",
            "question": "What is the lifetime value of our customers?",
            "ambiguity_type": "decoy_column_conflict",
            "d0_expected_behavior": "Uses Total_Spend",
            "d3_expected_behavior": "Confuses Total_Spend with life_spnd_gross decoy"
        },
        {
            "id": "AMB-CUST-02",
            "dataset": "customer",
            "question": "How many customer returns did we process?",
            "ambiguity_type": "decoy_column_conflict",
            "d0_expected_behavior": "Identifies that return counts are not present in original D0 schema",
            "d3_expected_behavior": "Takes decoy rtn_cnt column without flagging uncertainty"
        },
        {
            "id": "AMB-CUST-03",
            "dataset": "customer",
            "question": "Identify at-risk accounts",
            "ambiguity_type": "label_noise",
            "d0_expected_behavior": "Filters Churn_Risk == 'High'",
            "d3_expected_behavior": "Drops rows due to string casing or corrupted abbreviation tokens"
        },
        # Operations
        {
            "id": "AMB-OPS-01",
            "dataset": "operations",
            "question": "What is our team's total logged time?",
            "ambiguity_type": "decoy_column_conflict",
            "d0_expected_behavior": "Sums Duration in hours",
            "d3_expected_behavior": "Sums logged_raw_hrs decoy containing unparsed 'h' suffixes"
        },
        {
            "id": "AMB-OPS-02",
            "dataset": "operations",
            "question": "What is the average task completion progress?",
            "ambiguity_type": "decoy_column_conflict",
            "d0_expected_behavior": "Averages Completion_Rate",
            "d3_expected_behavior": "Mistakes raw_progress decoy for official completion rate"
        },
        {
            "id": "AMB-OPS-03",
            "dataset": "operations",
            "question": "Show critical path bottlenecks",
            "ambiguity_type": "semantic_multiplicity",
            "d0_expected_behavior": "Filters Priority == 'Critical' and Status == 'Blocked'",
            "d3_expected_behavior": "Generates incorrect SQL/tool calls due to fragmented column headers"
        },
    ]

    benchmark_dir = BASE_DIR / "benchmark"
    with open(benchmark_dir / "questions.json", "w") as f:
        json.dump({"questions": questions, "ambiguous_probes": ambiguous_questions}, f, indent=2)
    print(f"Saved {benchmark_dir / 'questions.json'} ({len(questions)} core + {len(ambiguous_questions)} ambiguous)")

    with open(benchmark_dir / "ground_truth.json", "w") as f:
        json.dump(ground_truth, f, indent=2)
    print(f"Saved {benchmark_dir / 'ground_truth.json'} ({len(ground_truth)} ground truth entries)")


if __name__ == "__main__":
    datasets = generate_datasets()
    build_questions_and_ground_truth(datasets)
    print("Phase 2 dataset generation and ground truth calculation completed successfully!")
