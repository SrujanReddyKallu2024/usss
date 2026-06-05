-- Database schema for the Real Estate chatbot.
-- Runs automatically the first time the db container starts.

-- Embeddings are stored as a plain float array and compared in Python (numpy),
-- so no database extension is required. Works on any PostgreSQL.

DROP TABLE IF EXISTS ai_usage_logs CASCADE;
DROP TABLE IF EXISTS maintenance_requests CASCADE;
DROP TABLE IF EXISTS crm_activities CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS leases CASCADE;
DROP TABLE IF EXISTS leads CASCADE;
DROP TABLE IF EXISTS tenants CASCADE;
DROP TABLE IF EXISTS properties CASCADE;
DROP TABLE IF EXISTS knowledge_base_documents CASCADE;

CREATE TABLE properties (
    property_id INT PRIMARY KEY,
    property_name VARCHAR(150),
    property_type VARCHAR(50),
    city VARCHAR(80),
    address TEXT,
    monthly_rent NUMERIC(10,2),
    status VARCHAR(40),
    bedrooms INT,
    bathrooms NUMERIC(3,1),
    sqft INT,
    amenities TEXT,
    latitude NUMERIC(10,6),
    longitude NUMERIC(10,6),
    created_at TIMESTAMP
);

CREATE TABLE tenants (
    tenant_id INT PRIMARY KEY,
    tenant_name VARCHAR(150),
    email VARCHAR(150),
    phone VARCHAR(50),
    tenant_status VARCHAR(50),
    created_at TIMESTAMP,
    credit_score INT
);

CREATE TABLE leases (
    lease_id INT PRIMARY KEY,
    tenant_id INT REFERENCES tenants(tenant_id),
    property_id INT REFERENCES properties(property_id),
    start_date DATE,
    end_date DATE,
    rent_amount NUMERIC(10,2),
    lease_status VARCHAR(50),
    signature_status VARCHAR(50)
);

CREATE TABLE payments (
    payment_id INT PRIMARY KEY,
    tenant_id INT REFERENCES tenants(tenant_id),
    lease_id INT REFERENCES leases(lease_id),
    property_id INT REFERENCES properties(property_id),
    due_date DATE,
    paid_date DATE,
    amount_due NUMERIC(10,2),
    amount_paid NUMERIC(10,2),
    status VARCHAR(50),
    days_late INT
);

CREATE TABLE leads (
    lead_id INT PRIMARY KEY,
    lead_name VARCHAR(150),
    email VARCHAR(150),
    source VARCHAR(80),
    inquiry_date DATE,
    status VARCHAR(80),
    converted INT,
    preferred_city VARCHAR(80),
    preferred_property_type VARCHAR(60),
    preferred_bedrooms INT,
    budget NUMERIC(10,2),
    followup_count INT,
    site_visits INT
);

CREATE TABLE crm_activities (
    activity_id INT PRIMARY KEY,
    lead_id INT REFERENCES leads(lead_id),
    activity_type VARCHAR(80),
    activity_date DATE,
    activity_status VARCHAR(80),
    notes TEXT
);

CREATE TABLE maintenance_requests (
    request_id INT PRIMARY KEY,
    property_id INT REFERENCES properties(property_id),
    issue_type VARCHAR(80),
    status VARCHAR(80),
    priority VARCHAR(50),
    created_date DATE,
    resolved_date DATE,
    estimated_cost NUMERIC(10,2)
);

-- Policy documents for the RAG feature. The embedding is filled in later by the ingest script.
CREATE TABLE knowledge_base_documents (
    document_id INT PRIMARY KEY,
    title VARCHAR(200),
    category VARCHAR(80),
    content TEXT,
    embedding double precision[]   -- 384-dim vector, compared in Python
);

-- One row per AI answer, so we can see what the bot did and how long it took.
CREATE TABLE ai_usage_logs (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(80),
    intent VARCHAR(40),
    user_prompt TEXT,
    ai_response TEXT,
    sql_text TEXT,
    sources TEXT,
    tokens_used INT,
    latency_ms INT,
    status VARCHAR(50),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_properties_city_status ON properties(city, status);
CREATE INDEX idx_properties_type_rent ON properties(property_type, monthly_rent);
CREATE INDEX idx_leases_end_date ON leases(end_date);
CREATE INDEX idx_payments_status_due_date ON payments(status, due_date);
CREATE INDEX idx_payments_property_due_date ON payments(property_id, due_date);
CREATE INDEX idx_leads_status_source ON leads(status, source);
CREATE INDEX idx_crm_lead_date ON crm_activities(lead_id, activity_date);
CREATE INDEX idx_maintenance_property_status ON maintenance_requests(property_id, status);

-- Read-only user. The chatbot connects as this user so generated SQL can never change data.
DROP ROLE IF EXISTS chatbot_ro;
CREATE ROLE chatbot_ro WITH LOGIN PASSWORD 'readonly';
GRANT CONNECT ON DATABASE real_estate TO chatbot_ro;
GRANT USAGE ON SCHEMA public TO chatbot_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO chatbot_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO chatbot_ro;
