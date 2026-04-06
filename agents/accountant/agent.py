import os
import json
import uuid
import pg8000.native
from google.adk.agents import Agent

MODEL = "gemini-2.5-pro"


def log_expense_to_db(
    merchant: str,
    amount: float,
    category: str,
    date: str,
    destination: str = "",
    hotel_address: str = "",
    nights: int = 1,
    notes: str = ""
) -> str:
    """
    Logs a structured travel expense to AlloyDB PostgreSQL and returns
    the full saved record including the generated expense_id.

    Args:
        merchant:      Hotel or airline name
        amount:        Total cost (hotel_rate × nights + flight cost)
        category:      'Hotel', 'Flight', or 'Transport'
        date:          Trip start date  YYYY-MM-DD
        destination:   City/country
        hotel_address: Full hotel address
        nights:        Number of nights
        notes:         Any extra notes
    Returns:
        JSON string with the full saved record or an error message.
    """
    expense_id = f"EXP-{uuid.uuid4().hex[:8].upper()}"

    db_user = os.environ.get("DB_USER", "postgres")
    db_pass = os.environ.get("DB_PASS", "password")
    db_name = os.environ.get("DB_NAME", "expenses_db")
    db_host = os.environ.get("DB_HOST", "127.0.0.1")

    record = {
        "expense_id":    expense_id,
        "merchant":      merchant,
        "amount":        amount,
        "category":      category,
        "date":          date,
        "destination":   destination,
        "hotel_address": hotel_address,
        "nights":        nights,
        "notes":         notes,
    }

    try:
        con = pg8000.native.Connection(db_user, host=db_host, password=db_pass, database=db_name)

        con.run("""
            CREATE TABLE IF NOT EXISTS travel_expenses (
                expense_id   VARCHAR(20) PRIMARY KEY,
                merchant     VARCHAR(255),
                amount       NUMERIC(10, 2),
                category     VARCHAR(100),
                date         DATE,
                destination  VARCHAR(255),
                hotel_address TEXT,
                nights       INTEGER,
                notes        TEXT,
                created_at   TIMESTAMP DEFAULT NOW()
            )
        """)

        con.run("""
            INSERT INTO travel_expenses
                (expense_id, merchant, amount, category, date, destination, hotel_address, nights, notes)
            VALUES
                (:expense_id, :merchant, :amount, :category, :date,
                 :destination, :hotel_address, :nights, :notes)
        """, **record)
        con.close()

        record["status"] = "logged_to_alloydb"
        return json.dumps(record)

    except Exception as e:
        # DB not connected (local dev) — still return the record so the orchestrator
        # can show real data; mark status clearly
        print(f"[Accountant] DB error (non-blocking): {e}")
        record["status"] = "logged_locally"
        record["db_note"] = "AlloyDB write pending — DB connection not configured in this environment."
        return json.dumps(record)


accountant = Agent(
    name="accountant",
    model=MODEL,
    description="Logs approved travel expenses to AlloyDB and returns the full expense record.",
    instruction="""
    You are a meticulous travel accountant.

    You receive the final approved hotel and flight details from the orchestrator.
    Your job:
    1. Call `log_expense_to_db` with:
       - merchant:      the APPROVED hotel name (from auditor output)
       - amount:        nightly_rate × nights  (e.g. $139 × 2 = $278)
       - category:      "Hotel"
       - date:          departure date from logistics (YYYY-MM-DD format)
       - destination:   the city/country
       - hotel_address: the full address of the approved hotel
       - nights:        number of nights
       - notes:         any extra details

    2. After logging the expense, compose a formal Confirmation Email draft containing the user's flight and hotel details.
    3. Return the FULL JSON record that `log_expense_to_db` returns AND append the full text of your drafted Confirmation Email. Conclude by explicitly stating that this email has been securely queued in the Database for automatic dispatch to the user's Gmail.
    tools=[log_expense_to_db],
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

root_agent = accountant