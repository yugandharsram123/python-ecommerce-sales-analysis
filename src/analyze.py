from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_DIR / "data"
OUTPUT_DIR = PROJECT_DIR / "outputs"


def load_data():
    """Load project CSV files and parse date columns."""
    files = {name: pd.read_csv(DATA_DIR / f"{name}.csv") for name in ["customers", "products", "orders", "order_items", "payments"]}
    files["orders"]["order_date"] = pd.to_datetime(files["orders"]["order_date"])
    files["customers"]["signup_date"] = pd.to_datetime(files["customers"]["signup_date"])
    files["payments"]["payment_date"] = pd.to_datetime(files["payments"]["payment_date"])
    return files


def run_analysis():
    OUTPUT_DIR.mkdir(exist_ok=True)
    sns.set_theme(context="notebook", style="whitegrid")
    data = load_data()
    orders, items, products, customers, payments = (data[k] for k in ["orders", "order_items", "products", "customers", "payments"])

    # Validate key relationships before analysis.
    assert orders["order_id"].is_unique, "order_id must be unique"
    assert customers["customer_id"].is_unique, "customer_id must be unique"
    assert items["order_id"].isin(orders["order_id"]).all(), "Orphan order items found"
    assert items["product_id"].isin(products["product_id"]).all(), "Unknown product IDs found"

    line_items = items.merge(products[["product_id", "product_name", "category"]], on="product_id", validate="many_to_one")
    line_items["net_sales"] = line_items["quantity"] * line_items["unit_price"] * (1 - line_items["discount_pct"])
    sales = line_items.merge(orders[["order_id", "customer_id", "order_date", "status"]], on="order_id", validate="many_to_one")
    sales = sales[sales["status"].isin(["delivered", "shipped"])].copy()
    sales["month"] = sales["order_date"].dt.to_period("M").dt.to_timestamp()

    total_revenue = sales["net_sales"].sum()
    total_orders = sales["order_id"].nunique()
    aov = total_revenue / total_orders if total_orders else 0
    monthly = sales.groupby("month", as_index=False)["net_sales"].sum().rename(columns={"net_sales": "revenue"})
    category = sales.groupby("category", as_index=False)["net_sales"].sum().sort_values("net_sales", ascending=False)
    top_products = sales.groupby("product_name", as_index=False)["net_sales"].sum().nlargest(10, "net_sales")
    top_customers = sales.groupby("customer_id", as_index=False)["net_sales"].sum().merge(customers[["customer_id", "full_name", "city"]], on="customer_id").nlargest(10, "net_sales")
    monthly.to_csv(OUTPUT_DIR / "monthly_revenue.csv", index=False)
    category.to_csv(OUTPUT_DIR / "category_revenue.csv", index=False)
    top_products.to_csv(OUTPUT_DIR / "top_products.csv", index=False)
    top_customers.to_csv(OUTPUT_DIR / "top_customers.csv", index=False)

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.lineplot(data=monthly, x="month", y="revenue", marker="o", ax=ax)
    ax.set(title="Monthly Net Sales Revenue", xlabel="Month", ylabel="Revenue")
    fig.tight_layout(); fig.savefig(OUTPUT_DIR / "monthly_revenue.png", dpi=160); plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5))
    sns.barplot(data=category, x="net_sales", y="category", color="C0", ax=ax)
    ax.set(title="Revenue by Product Category", xlabel="Net sales", ylabel="Category")
    fig.tight_layout(); fig.savefig(OUTPUT_DIR / "category_revenue.png", dpi=160); plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(data=top_products, x="net_sales", y="product_name", color="C0", ax=ax)
    ax.set(title="Top 10 Products by Revenue", xlabel="Net sales", ylabel="Product")
    fig.tight_layout(); fig.savefig(OUTPUT_DIR / "top_products.png", dpi=160); plt.close(fig)

    summary = (f"E-commerce sales analysis\n=========================\n"
               f"Revenue from delivered/shipped orders: {total_revenue:,.2f}\n"
               f"Number of delivered/shipped orders: {total_orders:,}\n"
               f"Average order value: {aov:,.2f}\n"
               f"Unique customers represented in sales: {sales['customer_id'].nunique():,}\n"
               f"Top category: {category.iloc[0]['category']}\n")
    (OUTPUT_DIR / "summary.txt").write_text(summary, encoding="utf-8")
    print(summary)
    print(f"Outputs saved to: {OUTPUT_DIR}")
    return {"revenue": total_revenue, "orders": total_orders, "average_order_value": aov}


if __name__ == "__main__":
    run_analysis()
