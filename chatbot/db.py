import sqlite3
import pandas as pd
from config import DB_PATH, CSV_DIR, DATA_DIR

TABLES = {
    "properties": "properties.csv",
    "tenants": "tenants.csv",
    "leases": "leases.csv",
    "payments": "payments.csv",
    "leads": "leads.csv",
    "crm_activities": "crm_activities.csv",
    "maintenance_requests": "maintenance_requests.csv",
    "knowledge_base_documents": "knowledge_base_documents.csv",
}

def setup():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))

    for table, filename in TABLES.items():
        path = CSV_DIR / filename
        if not path.exists():
            print(f"  SKIP {table} — {filename} not found")
            continue
        df = pd.read_csv(str(path))
        df.to_sql(table, conn, if_exists="replace", index=False)
        print(f"  ✓ {table}: {len(df)} rows")

    cursor = conn.cursor()
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_prop_city ON properties(city)",
        "CREATE INDEX IF NOT EXISTS idx_prop_status ON properties(status)",
        "CREATE INDEX IF NOT EXISTS idx_tenant_status ON tenants(tenant_status)",
        "CREATE INDEX IF NOT EXISTS idx_lease_status ON leases(lease_status)",
        "CREATE INDEX IF NOT EXISTS idx_pay_status ON payments(status)",
        "CREATE INDEX IF NOT EXISTS idx_lead_status ON leads(status)",
        "CREATE INDEX IF NOT EXISTS idx_maint_status ON maintenance_requests(status)",
        "CREATE INDEX IF NOT EXISTS idx_maint_priority ON maintenance_requests(priority)",
        "CREATE INDEX IF NOT EXISTS idx_prop_type ON properties(property_type)",
        "CREATE INDEX IF NOT EXISTS idx_lead_city ON leads(preferred_city)",
    ]
    for sql in indexes:
        cursor.execute(sql)

    conn.commit()
    conn.close()
    print(f"\n  Database ready → {DB_PATH}")


if __name__ == "__main__":
    print("Loading CSVs into SQLite...")
    setup()
