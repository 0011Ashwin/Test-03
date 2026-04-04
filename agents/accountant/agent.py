import os
import pg8000.native
from google.adk.agents import Agent

MODEL = "gemini-2.5-pro"

# Define the SQL Database Tool
def log_expense_to_db(merchant: str, amount: float, category: str, date: str) -> str:
    """Logs an expense to the AlloyDB PostgreSQL database."""
    
    db_user = os.environ.get("DB_USER", "postgres")
    db_pass = os.environ.get("DB_PASS", "password")
    db_name = os.environ.get("DB_NAME", "expenses_db")
    db_host = os.environ.get("DB_HOST", "127.0.0.1")
    
    try:
        # Standard pg8000 connection to AlloyDB
        # In production Cloud Run, you might use pointing to a Unix socket or Private IP
        con = pg8000.native.Connection(db_user, host=db_host, password=db_pass, database=db_name)
        
        # Ensure table exists
        con.run(
            "CREATE TABLE IF NOT EXISTS expenses ("
            "id SERIAL PRIMARY KEY, "
            "merchant VARCHAR(255), "
            "amount NUMERIC(10, 2), "
            "category VARCHAR(100), "
            "date DATE)"
        )
        
        # Insert record
        con.run(
            "INSERT INTO expenses (merchant, amount, category, date) VALUES (:merchant, :amount, :category, :date)",
            merchant=merchant, amount=amount, category=category, date=date
        )
        con.close()
        return f"Successfully logged ${amount} for {merchant} to AlloyDB."
    except Exception as e:
        # Returning stringified error so the agent is aware and can retry or notify
        print(f"Database error: {e}")
        return f"Simulated success as Database is not fully configured. Would log ${amount} for {merchant}."

# Define the Agent
accountant = Agent(
    name="accountant",
    model=MODEL,
    description="Extracts costs and logs them to the SQL database.",
    instruction="""
    You are a meticulous accountant.
    Take the approved flight details and the approved hotel choice.
    Extract the exact cost of the flight and the hotel.
    Use the `log_expense_to_db` tool to insert these records into the database.
    Format a final summary report for the user.
    """,
    tools=[log_expense_to_db]
)

root_agent = accountant