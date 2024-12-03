# create_db.py
from utils.config import create_db_connection
create_table_query = """
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    prompt TEXT NOT NULL,
    response TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    interaction_count INTEGER NOT NULL,
    duration INTERVAL NOT NULL
);
"""

def create_table():
    conn = create_db_connection()
    if conn is None:
        return
    try:
        with conn.cursor() as cursor:
            cursor.execute(create_table_query)
            conn.commit()
            print("Table 'conversations' created successfully.")
    except Exception as e:
        print(f"Error creating table: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    create_table()