import sqlite3, config
import datetime as date

from alpaca.data import StockBarsRequest, TimeFrame, StockHistoricalDataClient, DataFeed
from alpaca.trading.client import TradingClient
from alpaca.data.live.stock import StockDataStream

OPENING_HOUR = 14
OPENING_MINUTE = 30
CLOSE_MINUTE = 45

# async handler
async def bar_data_handler(data):
    # bar data will arrive here
    print(data)

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
stream = StockDataStream(config.API_KEY, config.SECRET_KEY)

year = date.datetime.today().year
month = date.datetime.today().month
day = date.datetime.today().day

start_time = date.datetime(year, month, day, OPENING_HOUR, OPENING_MINUTE)
end_time = date.datetime(year, month, day, OPENING_HOUR, CLOSE_MINUTE)

open_positions = []

positions = trading_client.get_all_positions()
for position in positions:
    open_positions.append(position.symbol)

for stock in stocks:
    # Create minute bar request for each stock that the ORB strategy exists for
    # Get the opening range of stocks to set the price
    request_params = StockBarsRequest(
        symbol_or_symbols=stock['symbol'],
        timeframe=TimeFrame.Minute,
        start=start_time,
        end=end_time,
        feed='sip'
    )

    opening_bars = stock_historical_client.get_stock_bars(request_params)

    opening_range_low = float('inf')
    opening_range_high = 0

    symbol = ''

    for bar in opening_bars.data.values():
        for info in bar:
            symbol = info.symbol
            if info.low < opening_range_low:
                opening_range_low = info.low
            if info.high > opening_range_high:
                opening_range_high = info.high

    print(opening_range_high - opening_range_low, opening_range_high)

    # Get the minute value of stocks after the opening range
    request_params = StockBarsRequest(
        symbol_or_symbols=stock['symbol'],
        timeframe=TimeFrame.Minute,
        start=end_time,
        feed='sip'
    )

    bars = stock_historical_client.get_stock_bars(request_params)

    stream.subscribe_bars(bar_data_handler, symbol)

    stream.run()