#!/usr/bin/python
from threading import Thread

import opening_range_breakout

import datetime as date
import sqlite3, config


from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates


OPENING_HOUR = 13
OPENING_MINUTE = 30
CLOSE_MINUTE = 45

app = FastAPI()
templates = Jinja2Templates(directory="templates")
strategy_threads = []
strategies = [opening_range_breakout]

@app.get("/")
def index(request: Request):
    stock_filter = request.query_params.get('filter', False)
    connection = sqlite3.connect(config.DATABASE)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    # selects stocks based on the filter given
    if stock_filter == 'new_closing_highs':
        cursor.execute("""
            SELECT * FROM (
                SELECT symbol, name, stock_id, max(close), date
                FROM stock_price JOIN stock ON stock.id = stock_price.stock_id
                GROUP BY stock_id
                ORDER BY symbol
            ) WHERE date = ?
        """, (date.datetime.today().date().isoformat(),))
    elif stock_filter == 'new_closing_lows':
        cursor.execute("""
            SELECT * FROM (
                SELECT symbol, name, stock_id, min(close), date
                FROM stock_price JOIN stock ON stock.id = stock_price.stock_id
                GROUP BY stock_id
                ORDER BY symbol
            ) WHERE date = ?
        """, (date.datetime.today().date().isoformat(),))
    elif stock_filter == 'new_intraday_highs':
        cursor.execute("""
            SELECT * FROM (
                SELECT symbol, name, stock_id, max(high), date
                FROM stock_price JOIN stock ON stock.id = stock_price.stock_id
                GROUP BY stock_id
                ORDER BY symbol
            ) WHERE date = ?
        """, (date.datetime.today().date().isoformat(),))
    elif stock_filter == 'new_intraday_lows':
        cursor.execute("""
            SELECT * FROM (
                SELECT symbol, name, stock_id, min(high), date
                FROM stock_price JOIN stock ON stock.id = stock_price.stock_id
                GROUP BY stock_id
                ORDER BY symbol
            ) WHERE date = ?
        """, (date.datetime.today().date().isoformat(),))
    else:
        cursor.execute("""
             SELECT id, symbol, name FROM stock ORDER BY symbol
            """)

    rows = cursor.fetchall()

    return templates.TemplateResponse("index.html", {"request": request, "stocks": rows})

@app.get("/stock/{symbol}")
def stock_detail(request: Request, symbol: str):
    connection = sqlite3.connect(config.DATABASE)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, symbol, name, exchange FROM stock where symbol = ?
    """, (symbol,))
    row = cursor.fetchone()

    cursor.execute("""
        SELECT * from stock_price where stock_id = ?
        """, (row['id'],))
    prices = cursor.fetchall()

    cursor.execute("""
        SELECT * FROM strategy
    """)
    strategies = cursor.fetchall()
    return templates.TemplateResponse("stock_detail.html", {"request": request, "stock": row, "bars": prices,
                                                            "strategies": strategies})

@app.post("/apply_strategy")
def apply_strategy(strategy_id: int = Form(), stock_id: int = Form()):
    connection = sqlite3.connect(config.DATABASE)
    cursor = connection.cursor()

    cursor.execute("""
    INSERT INTO stock_strategy (stock_id, strategy_id) VALUES (?, ?)
    """, (stock_id, strategy_id))

    connection.commit()

    return RedirectResponse(url=f"/strategy/{strategy_id}", status_code=303)

@app.get("/strategy/{strategy_id}")
def strategy_detail(request: Request, strategy_id: int):
    connection = sqlite3.connect(config.DATABASE)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    cursor.execute("""
    SELECT id, name
    FROM strategy
    where id = ?
    """, (strategy_id,))

    strategy = cursor.fetchone()

    cursor.execute("""
    SELECT symbol, name
    FROM stock JOIN stock_strategy ON stock.id = stock_strategy.stock_id
    where strategy_id = ?
    """, (strategy_id,))

    stocks = cursor.fetchall()

    return templates.TemplateResponse("strategy.html", {"request": request, "stocks": stocks, "strategy": strategy})


for strategy in strategies:
    worker = getattr(strategy, 'start')
    thread = Thread(target=worker)
    thread.start()
