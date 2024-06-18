import sqlite3
import config

connection = sqlite3.connect(config.DATABASE)

cursor = connection.cursor()

strategies = ['opening_range_breakout', 'opening_range_breakdown']

for strategy in strategies:
    cursor.execute("""INSERT INTO strategy (name) VALUES (?)""", (strategy,))

connection.commit()
