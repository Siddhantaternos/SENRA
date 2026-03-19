import sqlite3
from datetime import datetime

# Try importing matplotlib safely
try:
    import matplotlib.pyplot as plt
    GRAPH_AVAILABLE = True
except:
    GRAPH_AVAILABLE = False

DB_NAME = "pocket_manager.db"
TXT_BACKUP = "pocket_backup.txt"


# ---------- TABLE FORMATTER ----------
def print_table(headers, rows):
    col_widths = [len(h) for h in headers]

    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(val)))

    header = " | ".join(headers[i].ljust(col_widths[i]) for i in range(len(headers)))
    print("\n" + header)
    print("-" * len(header))

    for row in rows:
        print(" | ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(row))))


# ---------- TEXT BACKUP ----------
def save_backup(text):
    with open(TXT_BACKUP, "a", encoding="utf-8") as f:
        f.write(text + "\n")


# ---------- DATABASE ----------
def create_tables():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pocket_money(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL,
        timestamp TEXT,
        note TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS expenses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL,
        place TEXT,
        could_save TEXT,
        timestamp TEXT,
        note TEXT
    )
    """)

    conn.commit()
    conn.close()


# ---------- ADD POCKET MONEY ----------
def add_pocket_money():
    amount = float(input("Pocket Money Amount: "))
    note = input("Note: ")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO pocket_money(amount,timestamp,note) VALUES(?,?,?)",
        (amount, timestamp, note)
    )

    conn.commit()
    conn.close()

    save_backup(f"POCKET | {timestamp} | {amount} | {note}")
    print("Pocket money saved ✔")


# ---------- ADD EXPENSE ----------
def add_expense():
    amount = float(input("Spent Amount: "))
    place = input("Where spent: ")
    could_save = input("Could you have saved this? (YES/NO): ").upper()
    note = input("Note: ")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO expenses(amount,place,could_save,timestamp,note)
        VALUES(?,?,?,?,?)
    """, (amount, place, could_save, timestamp, note))

    conn.commit()
    conn.close()

    save_backup(f"EXPENSE | {timestamp} | {amount} | {place} | {could_save} | {note}")
    print("Expense saved ✔")


# ---------- VIEW EXPENSES ----------
def view_expenses():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, timestamp, amount, place, could_save, note
    FROM expenses
    ORDER BY timestamp DESC
    """)

    rows = cursor.fetchall()

    print_table(
        ["ID", "DATE TIME", "AMOUNT", "PLACE", "COULD SAVE", "NOTE"],
        rows
    )

    conn.close()


# ---------- MONTHLY SUMMARY ----------
def monthly_summary():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        p.month,
        p.total_money,
        IFNULL(e.total_spent,0),
        p.total_money - IFNULL(e.total_spent,0)
    FROM
    (SELECT strftime('%Y-%m',timestamp) month, SUM(amount) total_money 
     FROM pocket_money GROUP BY month) p
    LEFT JOIN
    (SELECT strftime('%Y-%m',timestamp) month, SUM(amount) total_spent 
     FROM expenses GROUP BY month) e
    ON p.month=e.month
    """)

    rows = cursor.fetchall()

    print_table(
        ["MONTH", "POCKET MONEY", "SPENT", "LEFT / SAVED"],
        rows
    )

    conn.close()


# ---------- GRAPH ----------
def expense_graph():
    if not GRAPH_AVAILABLE:
        print("Matplotlib not installed. Install using: pip install matplotlib")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT strftime('%Y-%m',timestamp), SUM(amount)
    FROM expenses
    GROUP BY 1
    """)

    data = cursor.fetchall()

    if not data:
        print("No data yet")
        return

    months = [x[0] for x in data]
    values = [x[1] for x in data]

    plt.plot(months, values)
    plt.title("Monthly Spending")
    plt.xlabel("Month")
    plt.ylabel("Amount")
    plt.show()

    conn.close()


# ---------- MENU ----------
def main():
    create_tables()

    while True:
        print("""
===== POCKET MONEY TRACKER =====

1 Add Pocket Money
2 Add Expense
3 View All Expenses (Table)
4 Monthly Summary (Table)
5 Spending Graph
6 Exit
""")

        choice = input("Choice: ")

        if choice == "1":
            add_pocket_money()
        elif choice == "2":
            add_expense()
        elif choice == "3":
            view_expenses()
        elif choice == "4":
            monthly_summary()
        elif choice == "5":
            expense_graph()
        elif choice == "6":
            break


if __name__ == "__main__":
    main()
