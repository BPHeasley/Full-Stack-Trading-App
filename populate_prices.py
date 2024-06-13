from alpaca.data import StockBarsRequest, TimeFrame, StockHistoricalDataClient

import config
import sqlite3

# Create historical data client
stock_historical_client = StockHistoricalDataClient(config.API_KEY, config.SECRET_KEY)

# Open connection to DB
connection = sqlite3.connect(config.DATABASE)
cursor = connection.cursor()

# Get a list of our symbols
cursor.execute("""select symbol from stock""")
rows = cursor.fetchall()
symbols = [row[0] for row in rows]

# Create historical data request object
request_params = StockBarsRequest(
    symbol_or_symbols=(symbols[0], symbols[1], symbols[2]),
    timeframe=TimeFrame.Minute,
    feed='sip'
)

bars = stock_historical_client.get_stock_bars(request_params)
for bar in bars.data.values():
    for info in bar:
        print(info)
