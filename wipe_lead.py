
import sqlite3

DB_PATH = "leads.db"
PHONE_TO_DELETE = "+14127264930"

def delete_lead():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if exists
        cursor.execute("SELECT * FROM conversations WHERE customer_phone = ?", (PHONE_TO_DELETE,))
        if not cursor.fetchone():
            print(f"Lead {PHONE_TO_DELETE} not found.")
            return

        # Delete
        cursor.execute("DELETE FROM conversations WHERE customer_phone = ?", (PHONE_TO_DELETE,))
        conn.commit()
        print(f"✅ Successfully deleted lead: {PHONE_TO_DELETE}")
        
    except Exception as e:
        print(f"❌ Error deleting lead: {e}")
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    delete_lead()
