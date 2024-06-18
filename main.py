# import socket
from datetime import datetime
# import pandas as pd
# from alpaca.trading.client import TradingClient
# from alpaca.trading.requests import GetAssetsRequest, MarketOrderRequest, LimitOrderRequest, TakeProfitRequest, \
#     StopLossRequest, GetOrdersRequest
# from alpaca.trading.enums import AssetClass, OrderSide, TimeInForce, OrderClass, QueryOrderStatus
# from alpaca.trading.stream import TradingStream
# from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
# from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
# from alpaca.data.timeframe import TimeFrame

# import config
# import create_db

# public_key = config.API_KEY
# private_key = config.SECRET_KEY
# trading_client = TradingClient(public_key, private_key, paper=True)
# stock_historical_client = StockHistoricalDataClient(public_key, private_key)
# crypto_historical_client = CryptoHistoricalDataClient(public_key, private_key)

import sqlite3, config
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory="templates")

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
        """, (datetime.today().date().isoformat(),))
    elif stock_filter == 'new_closing_lows':
        cursor.execute("""
            SELECT * FROM (
                SELECT symbol, name, stock_id, min(close), date
                FROM stock_price JOIN stock ON stock.id = stock_price.stock_id
                GROUP BY stock_id
                ORDER BY symbol
            ) WHERE date = ?
        """, (datetime.today().date().isoformat(),))
    elif stock_filter == 'new_intraday_highs':
        cursor.execute("""
            SELECT * FROM (
                SELECT symbol, name, stock_id, max(high), date
                FROM stock_price JOIN stock ON stock.id = stock_price.stock_id
                GROUP BY stock_id
                ORDER BY symbol
            ) WHERE date = ?
        """, (datetime.today().date().isoformat(),))
    elif stock_filter == 'new_intraday_lows':
        cursor.execute("""
            SELECT * FROM (
                SELECT symbol, name, stock_id, min(high), date
                FROM stock_price JOIN stock ON stock.id = stock_price.stock_id
                GROUP BY stock_id
                ORDER BY symbol
            ) WHERE date = ?
        """, (datetime.today().date().isoformat(),))
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

# # create historical data request object
# request_params = StockBarsRequest(
#     symbol_or_symbols='SPY',
#     timeframe=TimeFrame.Minute
# )
#
# spy_bars = stock_historical_client.get_stock_bars(request_params)
#
# btc_request_params = CryptoBarsRequest(
#     symbol_or_symbols='BTC/USD',
#     timeframe=TimeFrame.Day,
#     start="2024-06-09",
#     end="2024-06-10"
# )
#
# btc_bars = crypto_historical_client.get_crypto_bars(btc_request_params)
#
# # Convert to dataframe
# print(spy_bars.df)
# print(btc_bars.df)

# # Get our account information
# account = trading_client.get_account()
#
# # Check if our account is restricted from trading
# if account.trading_blocked:
#     print("Account is currently blocked")
#
# # Check how much money we can use to open new positions
# print("${} is available as buying power.".format(account.buying_power))
#
# # Check balance vs last market close balance
# balance_change = float(account.equity) - float(account.last_equity)
# print(f'Today\'s balance change is {balance_change:.2f}')
#
# # search for US equities
# search_params = GetAssetsRequest(asset_class=AssetClass.US_EQUITY)
#
# assets = trading_client.get_all_assets(search_params)
# asset = trading_client.get_asset("SPY")
#
# # for asset in assets:
# #     if asset.tradable:
# #         print(f"We can trade {asset.symbol}")
#
# # preparing market order
# market_order_data = MarketOrderRequest(
#                     symbol="SPY",
#                     qty=1,
#                     side=OrderSide.BUY,
#                     time_in_force=TimeInForce.DAY,
#                     client_order_id='SPY_order'
#                     )
#
# # Market order
# # market_order = trading_client.submit_order(order_data=market_order_data)
#
# # preparing limit order
# limit_order_data = LimitOrderRequest(
#                     symbol="BTC/USD",
#                     limit_price=17000,
#                     notional=4000,
#                     side=OrderSide.BUY,
#                     time_in_force=TimeInForce.IOC
#                     )
#
# # Limit order
# limit_order = trading_client.submit_order(order_data=limit_order_data)
#
# # preparing short
# # preparing market order
# market_order_data = MarketOrderRequest(
#                     symbol="AAPL",
#                     qty=1,
#                     side=OrderSide.SELL,
#                     time_in_force=TimeInForce.GTC
#                     )
#
# market_order = trading_client.submit_order(order_data=market_order_data)
#
# # Get our order using its client order ID
# my_order = trading_client.get_order_by_client_id('SPY_order')
# print("Got order #{}".format(my_order.id))
#
# # preparing bracket order with both stop loss and take profit
# bracket_order_data = MarketOrderRequest(
#                     symbol="SPY",
#                     qty=5,
#                     side=OrderSide.BUY,
#                     time_in_force=TimeInForce.DAY,
#                     order_class=OrderClass.BRACKET,
#                     take_profit=TakeProfitRequest(limit_price=540),
#                     stop_loss=StopLossRequest(stop_price=530)
#                     )
#
# bracket_order = trading_client.submit_order(order_data=bracket_order_data)
#
# # preparing oto order with stop loss
# oto_order_data = LimitOrderRequest(
#                 symbol="SPY",
#                 qty=5,
#                 limit_price=540,
#                 side=OrderSide.BUY,
#                 time_in_force=TimeInForce.DAY,
#                 stop_loss=StopLossRequest(stop_price=520),
#                 order_class=OrderClass.OTO
#                 )
# oto_order = trading_client.submit_order(order_data=oto_order_data)
#
# # Get the last 100 closed orders
# get_orders_request = GetOrdersRequest(
#                     status=QueryOrderStatus.CLOSED,
#                     limit=100,
#                     nested=True
#                     )
#
# # print(trading_client.get_orders(get_orders_request))
#
# stream = TradingStream(public_key, private_key, paper=True)
#
# # @conn.on(client_order_id)
# # async def on_msg(data):
# #     # Print the update to the console
# #     print("Update for {}. Event: {}.".format(data.event))
# #
# # stream.subscribe_trade_updates(on_msg)
# # #start listening for updates
# # stream.run()
#
# # Get my position on SPY
# # spy_position = trading_client.get_open_position("SPY")
#
# # Get a list of all positions
# portfolio = trading_client.get_all_positions()
#
# for position in portfolio:
#     print("{} shares of {}".format(position.qty, position.symbol))