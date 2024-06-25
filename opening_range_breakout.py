import sqlite3, config
import datetime as date
import time
from threading import Thread

from alpaca.data import StockBarsRequest, TimeFrame, StockHistoricalDataClient, DataFeed, Bar
from alpaca.trading import MarketOrderRequest, TimeInForce, OrderSide, TakeProfitRequest, StopLossRequest
from alpaca.trading.client import TradingClient

OPENING_HOUR = 14
OPENING_MINUTE = 30
CLOSE_MINUTE = 45

opening_ranges = {}
symbols = []
threads = []


def strategy_handler(symbol):
    (opening_range_high, opening_range_difference) = opening_ranges.get(symbol)

    trade_time = end_time
    market_is_open = trading_client.get_clock().is_open

    # Every minute that the market is open
    # Check if we have an open position on a symbol
    # if we do, wait another minute to see if the trade clears
    # if we don't, check if opening range breakout has occurred
    while market_is_open:
        if symbol in open_positions:
            print(f"An open position already exists for {symbol}")
        else:
            request_params = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Minute,
                start=trade_time,
                feed='sip'
            )

            single_symbol_bars = stock_historical_client.get_stock_bars(request_params)
            for bar in single_symbol_bars.data.values():
                for info in bar:
                    if info.close > opening_range_high and symbol not in open_positions:
                        # create a market order with a stop loss at high minus difference and take profit at high plus difference
                        take_profit_request = TakeProfitRequest(limit_price=opening_range_high + opening_range_difference)
                        stop_loss_request = StopLossRequest(stop_price=opening_range_high - opening_range_difference)

                        market_order_data = MarketOrderRequest(
                            symbol=symbol,
                            qty=1,
                            side=OrderSide.BUY,
                            time_in_force=TimeInForce.DAY,
                            take_profit=take_profit_request,
                            stop_loss=stop_loss_request,
                        )

                        market_order = trading_client.submit_order(order_data=market_order_data)
                        trade_time = market_order.created_at.time()

                        open_positions.append(symbol)

                        print("Created a market order" + str(market_order))
        time.sleep(60)

        market_is_open = trading_client.get_clock().is_open


connection = sqlite3.connect(config.DATABASE)
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
        feed='sip'
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