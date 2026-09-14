# Snowflake and BigQuery

The analytics service is designed to receive normalised member, transaction, and entitlement records. In production, use one warehouse as the source of truth:

- **Snowflake**: configure account, warehouse, database, schema, role, and key-pair/OAuth authentication through environment variables.
- **BigQuery**: configure `GOOGLE_APPLICATION_CREDENTIALS`, project ID, dataset, and service-account permissions.

Never commit credentials. Use AWS Secrets Manager or GCP Secret Manager and provide the resulting values as runtime environment variables.
