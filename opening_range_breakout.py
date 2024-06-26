import sqlite3, config
import datetime as date
import time
from threading import Thread

from alpaca.data import StockBarsRequest, TimeFrame, StockHistoricalDataClient, StockLatestBarRequest
from alpaca.trading import (MarketOrderRequest, TimeInForce, OrderSide, TakeProfitRequest, StopLossRequest, OrderClass,
                            OrderStatus)
from alpaca.trading.client import TradingClient

OPENING_HOUR = 13
OPENING_MINUTE = 30
CLOSE_MINUTE = 45

opening_ranges = {}
symbols = []
threads = []


def strategy_handler(symbol):
    (opening_range_high, opening_range_difference) = opening_ranges.get(symbol)

    market_is_open = trading_client.get_clock().is_open
    symbol_cursor = connection.cursor()
    symbol_cursor.execute("""
        SELECT client_order_id FROM trades WHERE symbol = ? AND status = ?
        """, (symbol, OrderStatus.NEW.capitalize()))
    client_order_ids = symbol_cursor.fetchall()

    # Every minute that the market is open
    # Check if we have an open position on a symbol
    # if we do, wait another minute to see if the trade clears
    # if we don't, check if opening range breakout has occurred
    while market_is_open:
        if symbol in open_positions:
            print(f"An open position already exists for {symbol}")
            for client_order_id in client_order_ids:
                response = trading_client.get_order_by_client_id(client_order_id[0])
                # Checks if the sell side of the trade was filled and removes the symbol from the list of open positions
                print(response)
                for leg in response.legs:
                    print(leg)
                    if leg.status == OrderStatus.FILLED and leg.side == OrderSide.SELL:
                        if symbol in open_positions:
                            open_positions.remove(symbol)
                        # add client_order_id to database to recover from app crash
                        symbol_cursor.execute("""
                            UPDATE trades set status = ? where client_order_id = ?
                            """, (OrderStatus.FILLED.capitalize(), client_order_id[0]))
                        connection.commit()
        else:
            print(f"Getting latest {symbol} bar")
            request_params = StockLatestBarRequest(
                symbol_or_symbols=symbol,
                feed='iex'
            )
            latest_bar = stock_historical_client.get_stock_latest_bar(request_params)
            price = latest_bar.get(symbol).close
            if price > opening_range_high:
                # create a market order with a stop loss at price minus difference and take profit at price plus difference
                take_profit_request = TakeProfitRequest(limit_price=round(price + 0.05, 2))
                # take_profit_request = TakeProfitRequest(limit_price=round(price + opening_range_difference, 2))
                stop_loss_request = StopLossRequest(stop_price=round(price - opening_range_difference, 2))

                bracket_order_data = MarketOrderRequest(
                    symbol=symbol,
                    qty=1,
                    side=OrderSide.BUY,
                    time_in_force=TimeInForce.DAY,
                    order_class=OrderClass.BRACKET,
                    take_profit=take_profit_request,
                    stop_loss=stop_loss_request,
                )

                bracket_order = trading_client.submit_order(order_data=bracket_order_data)

                open_positions.append(symbol)

                print("Created a bracket order" + str(bracket_order))
                client_order_id = bracket_order.client_order_id

                # add client_order_id to database to recover from app crash
                symbol_cursor.execute("""
                    INSERT INTO trades (symbol, client_order_id, status) VALUES (?, ?, ?) 
                """, (symbol, client_order_id, OrderStatus.NEW.capitalize()))
                connection.commit()
        time.sleep(60)

        market_is_open = trading_client.get_clock().is_open


# connection = sqlite3.connect(config.DATABASE)
connection = sqlite3.connect(config.DATABASE, check_same_thread=False)
connection.row_factory = sqlite3.Row
cursor = connection.cursor()

cursor.execute("""
    SELECT id FROM strategy
    WHERE name = 'opening_range_breakout'
""")

strategy_id = cursor.fetchone()['id']

cursor.execute("""
    SELECT symbol, name FROM stock
    JOIN stock_strategy ON stock_strategy.stock_id = stock.id
    WHERE stock_strategy.strategy_id = ?
""", (strategy_id,))

stocks = cursor.fetchall()

stock_historical_client = StockHistoricalDataClient(config.API_KEY, config.SECRET_KEY)
trading_client = TradingClient(config.API_KEY, config.SECRET_KEY, paper=True)

year = date.datetime.today().year
month = date.datetime.today().month
day = date.datetime.today().day

start_time = date.datetime(year, month, day, OPENING_HOUR, OPENING_MINUTE)
end_time = date.datetime(year, month, day, OPENING_HOUR, CLOSE_MINUTE)

open_positions = []

positions = trading_client.get_all_positions()
orders = trading_client.get_orders()
for order in orders:
    if order.symbol not in open_positions:
        open_positions.append(order.symbol)
for position in positions:
    if position.symbol not in open_positions:
        open_positions.append(position.symbol)

for stock in stocks:
    symbol = str(stock['symbol'])
    symbols.append(symbol)
    # Create minute bar request for each stock that the ORB strategy exists for
    # Get the opening range of stocks to set the price
    request_params = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Minute,
        start=start_time,
        end=end_time,
        feed='iex'
    )

    opening_bars = stock_historical_client.get_stock_bars(request_params)

    opening_range_low = float('inf')
    opening_range_high = 0

    for bar in opening_bars.data.values():
        for info in bar:
            if info.low < opening_range_low:
                opening_range_low = info.low
            if info.high > opening_range_high:
                opening_range_high = info.high

    opening_range_difference = opening_range_high - opening_range_low
    opening_ranges.update({symbol: (opening_range_high, opening_range_difference)})

for symbol in symbols:
    thread = Thread(target=strategy_handler, args=(symbol,))
    thread.start()
    threads.append(thread)

for thread in threads:
    thread.join()