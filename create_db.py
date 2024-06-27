import config
import sqlite3

# Connect to the existing database or create it if it doesn't exist
connection = sqlite3.connect(config.DATABASE)

cursor = connection.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS stock (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    exchange TEXT NOT NULL
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
    volume NOT NULL,
    FOREIGN KEY (stock_id) REFERENCES stock (id)
    )
""")

cursor.execute("""CREATE TABLE IF NOT EXISTS strategy (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
    )
""")

cursor.execute("""CREATE TABLE IF NOT EXISTS stock_strategy (
    stock_id INTEGER NOT NULL,
    strategy_id INTEGER NOT NULL,
    FOREIGN KEY (stock_id) REFERENCES stock (id),
    FOREIGN KEY (strategy_id) REFERENCES strategy (id)
    )
""")

cursor.execute("""CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY,
    client_order_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    status TEXT NOT NULL,
    date datetime NOT NULL,
    FOREIGN KEY (id) REFERENCES stock (id)
    )
""")

# Commit the changes to the db
connection.commit()