-- Load the sample CSVs into the tables. Files are mounted at /csv inside the container.
COPY properties FROM '/csv/properties.csv' CSV HEADER;
COPY tenants FROM '/csv/tenants.csv' CSV HEADER;
COPY leases FROM '/csv/leases.csv' CSV HEADER;
COPY payments FROM '/csv/payments.csv' CSV HEADER;
COPY leads FROM '/csv/leads.csv' CSV HEADER;
COPY crm_activities FROM '/csv/crm_activities.csv' CSV HEADER;
COPY maintenance_requests FROM '/csv/maintenance_requests.csv' CSV HEADER;
COPY knowledge_base_documents (document_id, title, category, content) FROM '/csv/knowledge_base_documents.csv' CSV HEADER;

-- Read-only user needs SELECT on the freshly loaded tables too.
GRANT SELECT ON ALL TABLES IN SCHEMA public TO chatbot_ro;
