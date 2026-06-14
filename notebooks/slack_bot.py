import os
import anthropic
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
from db_connector import AdventureWorksDB

load_dotenv()

# ── Clients ───────────────────────────────────────────────────────────────────

app = App(token=os.getenv("SLACK_BOT_TOKEN"))
claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
db = AdventureWorksDB()

# ── Schema context for Claude ─────────────────────────────────────────────────
# Tells Claude what tables and columns exist so it can write accurate SQL.
# Extend this as you add more tables to your analysis.

SCHEMA_CONTEXT = """
You are a SQL Server expert assistant for the AdventureWorks2025 database.
Your job is to convert natural language questions into valid T-SQL queries,
execute them, and return a clear, concise answer.

Here are the key tables available:

QUALITY & PRODUCTION:
- Production.WorkOrder (WorkOrderID, ProductID, OrderQty, ScrappedQty, ScrapReasonID, StartDate, EndDate)
- Production.ScrapReason (ScrapReasonID, Name)
- Production.Product (ProductID, Name, ProductNumber, StandardCost, ListPrice)
- Production.WorkOrderRouting (WorkOrderID, ProductID, ActualCost, ActualResourceHrs)

INVENTORY:
- Production.ProductInventory (ProductID, LocationID, Shelf, Bin, Quantity)
- Production.Location (LocationID, Name, CostRate, Availability)
- Production.TransactionHistory (TransactionID, ProductID, TransactionDate, TransactionType, Quantity)
- Production.BillOfMaterials (BillOfMaterialsID, ProductAssemblyID, ComponentID, PerAssemblyQty)

PURCHASING & LOGISTICS:
- Purchasing.Vendor (BusinessEntityID, Name, CreditRating, ActiveFlag)
- Purchasing.ProductVendor (ProductID, BusinessEntityID, AverageLeadTime, StandardPrice, MinOrderQty, MaxOrderQty, OnOrderQty, RejectedQty, ReceivedQty)
- Purchasing.PurchaseOrderHeader (PurchaseOrderID, VendorID, OrderDate, TotalDue, Freight)
- Purchasing.PurchaseOrderDetail (PurchaseOrderID, ProductID, OrderQty, ReceivedQty, RejectedQty, StockedQty, DueDate)
- Purchasing.ShipMethod (ShipMethodID, Name, ShipRate)

SALES:
- Sales.SalesOrderHeader (SalesOrderID, OrderDate, TotalDue, Freight, CustomerID)
- Sales.SalesOrderDetail (SalesOrderID, ProductID, OrderQty, UnitPrice, LineTotal)

Rules you must follow:
1. Only generate SELECT statements — never INSERT, UPDATE, DELETE, or DROP.
2. Always use schema prefixes (e.g. Production.WorkOrder, not just WorkOrder).
3. Use TOP 50 by default unless the user asks for more or fewer rows.
4. Return ONLY the SQL query with no explanation, no markdown, no backticks.
"""

# ── Core logic ────────────────────────────────────────────────────────────────

def ask_claude_for_sql(question: str) -> str:
    """Send a natural language question to Claude and get back a SQL query."""
    response = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=SCHEMA_CONTEXT,
        messages=[{"role": "user", "content": question}]
    )
    return response.content[0].text.strip()


def format_dataframe_for_slack(df) -> str:
    """Format a pandas DataFrame as a readable Slack message."""
    if df.empty:
        return "The query returned no results."

    # Cap output at 20 rows to keep Slack messages readable
    display_df = df.head(20)
    total_rows = len(df)

    # Build a simple text table
    col_widths = {
        col: max(len(str(col)), df[col].astype(str).str.len().max())
        for col in display_df.columns
    }

    header = "  ".join(str(col).ljust(col_widths[col]) for col in display_df.columns)
    divider = "  ".join("-" * col_widths[col] for col in display_df.columns)

    rows = []
    for _, row in display_df.iterrows():
        rows.append(
            "  ".join(str(row[col]).ljust(col_widths[col]) for col in display_df.columns)
        )

    table = "\n".join([header, divider] + rows)

    footer = ""
    if total_rows > 20:
        footer = f"\n\n_Showing 20 of {total_rows} rows._"

    return f"```\n{table}\n```{footer}"


def handle_question(question: str) -> str:
    """
    Full pipeline:
    1. Send question to Claude → get SQL
    2. Run SQL against SQL Server → get DataFrame
    3. Format DataFrame → return Slack message
    """
    try:
        # Step 1: Natural language → SQL
        sql = ask_claude_for_sql(question)

        # Step 2: Run the query
        df = db.query(sql)

        if df.empty:
            return f"Query ran successfully but returned no results.\n\n*SQL used:*\n```{sql}```"

        # Step 3: Format and return
        result = format_dataframe_for_slack(df)
        return f"*SQL used:*\n```{sql}```\n\n*Results:*\n{result}"

    except Exception as e:
        return f":warning: Something went wrong: {str(e)}"


# ── Slack event handlers ───────────────────────────────────────────────────────

@app.event("app_mention")
def handle_mention(event, say):
    """Triggered when someone @mentions the bot in a channel."""
    # Strip the bot mention from the message text
    text = event.get("text", "")
    question = text.split(">", 1)[-1].strip()

    if not question:
        say("Hi! Ask me anything about the AdventureWorks database. For example:\n"
            "_@AW Analytics Bot What are the top scrap reasons by quantity?_")
        return

    say(f":hourglass: Running your query...")
    answer = handle_question(question)
    say(answer)


@app.event("message")
def handle_message(event, say):
    """
    Catch-all for direct messages to the bot.
    Ignores bot messages to prevent feedback loops.
    """
    if event.get("bot_id"):
        return

    question = event.get("text", "").strip()
    if not question:
        return

    say(f":hourglass: Running your query...")
    answer = handle_question(question)
    say(answer)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Starting AW Analytics Slack Bot...")
    print(f"Connected to: {os.getenv('DB_NAME')} on {os.getenv('DB_SERVER')}")
    handler = SocketModeHandler(app, os.getenv("SLACK_APP_TOKEN"))
    handler.start()