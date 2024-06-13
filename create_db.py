import config
import sqlite3

# Connect to the existing database or create it if it doesn't exist
connection = sqlite3.connect(config.DATABASE)

cursor = connection.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS stock (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL
    )
""")

cursor.execute("""CREATE TABLE IF NOT EXISTS stock_price (
    id INTEGER PRIMARY KEY,
    stock_id INTEGER,
    date NOT NULL,
    open NOT NULL,
    high NOT NULL,
    low NOT NULL,
    close NOT NULL,
    adjusted_close NOT NULL,
    volume NOT NULL,
    FOREIGN KEY (stock_id) REFERENCES stock (id)
    )
""")

# Commit the changes to the db
connection.commit()