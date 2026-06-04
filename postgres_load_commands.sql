
-- Load CSVs after creating schema.
-- Update '/path/to/csv/' to your local folder path before running in PostgreSQL.

\copy properties FROM '/path/to/csv/properties.csv' CSV HEADER;
\copy tenants FROM '/path/to/csv/tenants.csv' CSV HEADER;
\copy leases FROM '/path/to/csv/leases.csv' CSV HEADER;
\copy payments FROM '/path/to/csv/payments.csv' CSV HEADER;
\copy leads FROM '/path/to/csv/leads.csv' CSV HEADER;
\copy crm_activities FROM '/path/to/csv/crm_activities.csv' CSV HEADER;
\copy maintenance_requests FROM '/path/to/csv/maintenance_requests.csv' CSV HEADER;
\copy knowledge_base_documents FROM '/path/to/csv/knowledge_base_documents.csv' CSV HEADER;
