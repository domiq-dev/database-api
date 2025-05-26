# tools/db_tool.py
import os, psycopg2
from psycopg2.extras import Json

WRITE_LEAD_TOOL = {
    "type": "function",
    "function": {
        "name": "write_lead_record",
        "description": "Persist the lead into PostgreSQL",
        "parameters": {
            "type": "object",
            "properties": {
                "record": {
                    "type": "object",
                    "description": "Fields that map to public.leads"
                }
            },
            "required": ["record"]
        }
    }
}

# ----- real DB connection (unchanged) -----
_conn = psycopg2.connect(
    host=os.getenv("PG_HOST"),
    port=os.getenv("PG_PORT", 5432),
    dbname=os.getenv("PG_DB"),
    user=os.getenv("PG_USER"),
    password=os.getenv("PG_PASS"),
    sslmode="require"
)
_conn.autocommit = True

def write_lead_record(record: dict) -> None:
    with _conn.cursor() as cur:
        cur.execute("SELECT 1")  # placeholder or full UPSERT as before
