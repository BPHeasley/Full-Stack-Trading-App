from datetime import datetime

import config, sqlite3, threading


def get_stocks_for_strategy(strategy: str):
    cursor.execute("""
        SELECT id FROM strategy
        WHERE name = ?
    """, (strategy,))

    strategy_id = cursor.fetchone()['id']

    cursor.execute("""
        SELECT symbol, name FROM stock
        JOIN stock_strategy ON stock_strategy.stock_id = stock.id
        WHERE stock_strategy.strategy_id = ?
    """, (strategy_id,))

    return cursor.fetchall()


def get_client_order_ids(symbol: str, status: str):
    cursor.execute("""
        SELECT client_order_id FROM trades WHERE symbol = ? AND status = ?
        """, (symbol, status))
    return cursor.fetchall()

def update_trade_status(client_order_id: str, status: str):
    while True:
        try:
            lock.acquire(True)
            cursor.execute("""
                                    UPDATE trades set status = ? where client_order_id = ?
                                    """, (status, client_order_id))
            connection.commit()
        except sqlite3.IntegrityError:
            print(f"Error attepmting to update trade {client_order_id}")
        finally:
            lock.release()
        break


def insert_trade(symbol: str, client_order_id: str, status: str, date: datetime):
    # add client_order_id to database to recover from app crash
    while True:
        try:
            lock.acquire(True)
            cursor.execute("""
                            INSERT INTO trades (symbol, client_order_id, status, date) VALUES (?, ?, ?, ?) 
                        """, (symbol, client_order_id, status, date))
            connection.commit()
        except sqlite3.IntegrityError:
            print(f"Error attempting to insert trade on {symbol}")
        finally:
            lock.release()
        break


connection = sqlite3.connect(config.DATABASE, check_same_thread=False)
connection.row_factory = sqlite3.Row
cursor = connection.cursor()
lock = threading.Lock()
