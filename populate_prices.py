from datetime import datetime

from alpaca.data import StockBarsRequest, TimeFrame, StockHistoricalDataClient

import config
import sqlite3

# Create historical data client
stock_historical_client = StockHistoricalDataClient(config.API_KEY, config.SECRET_KEY)

# Open connection to DB
connection = sqlite3.connect(config.DATABASE)
connection.row_factory = sqlite3.Row
cursor = connection.cursor()

# Get a list of our symbols
cursor.execute("""select symbol, id from stock""")
rows = cursor.fetchall()

# add the Symbol in each row to a new list named 'symbols'
symbols = [row[0] for row in rows]

stock_dict = {}
for row in rows:
    symbol = row['symbol']
    stock_dict[symbol] = row['id']

# for bar in bars.data.values():
#     for info in bar:
#         stock_id = stock_dict[info.symbol]
#         cursor.execute("""
#         insert into stock_price (stock_id, date, open, high, low, close, volume)
#         VALUES (?, ?, ?, ?, ?, ?, ?)""",
#                        (stock_id, info.timestamp, info.open, info.high, info.low, info.close, info.volume))
# connection.commit()

chunk_size = 200
for i in range(0, len(symbols), chunk_size):
    # Create a chunk of 200 symbols
    chunk = symbols[i:i + chunk_size]
    # start (Optional[datetime]): The beginning of the time interval for desired data. Timezone naive inputs assumed to be in UTC.
    # end (Optional[datetime]): The end of the time interval for desired data. Defaults to now. Timezone naive inputs assumed to be in UTC.

    # Create historical data request object for each chunk of 200 symbols
    request_params = StockBarsRequest(
        symbol_or_symbols=chunk,
        timeframe=TimeFrame.Day,
        start=datetime(2024, 6, 1),
        feed='sip'
    )

    bars = stock_historical_client.get_stock_bars(request_params)
    for bar in bars.data.values():
        for info in bar:
            stock_id = stock_dict[info.symbol]
            cursor.execute("""
            insert into stock_price (stock_id, date, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
                           (stock_id, info.timestamp.date().isoformat(), info.open, info.high, info.low, info.close, info.volume))

connection.commit()
