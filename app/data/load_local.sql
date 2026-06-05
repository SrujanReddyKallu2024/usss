-- Load CSVs into a LOCAL (non-Docker) Postgres using client-side \copy.
-- Run with: psql -d real_estate -f load_local.sql
\copy properties FROM 'D:/c/usssssssss/app/data/csv/properties.csv' CSV HEADER
\copy tenants FROM 'D:/c/usssssssss/app/data/csv/tenants.csv' CSV HEADER
\copy leases FROM 'D:/c/usssssssss/app/data/csv/leases.csv' CSV HEADER
\copy payments FROM 'D:/c/usssssssss/app/data/csv/payments.csv' CSV HEADER
\copy leads FROM 'D:/c/usssssssss/app/data/csv/leads.csv' CSV HEADER
\copy crm_activities FROM 'D:/c/usssssssss/app/data/csv/crm_activities.csv' CSV HEADER
\copy maintenance_requests FROM 'D:/c/usssssssss/app/data/csv/maintenance_requests.csv' CSV HEADER
\copy knowledge_base_documents (document_id, title, category, content) FROM 'D:/c/usssssssss/app/data/csv/knowledge_base_documents.csv' CSV HEADER

GRANT SELECT ON ALL TABLES IN SCHEMA public TO chatbot_ro;
