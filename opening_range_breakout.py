import config
import datetime as date
import db_utils as db_utils
import time
from threading import Thread

from alpaca.data import StockBarsRequest, TimeFrame, StockHistoricalDataClient, StockLatestBarRequest, StockLatestQuoteRequest
from alpaca.trading import (MarketOrderRequest, TimeInForce, OrderSide, TakeProfitRequest, StopLossRequest, OrderClass,
                            OrderStatus)
from alpaca.trading.client import TradingClient

OPENING_HOUR = 13
OPENING_MINUTE = 30
CLOSE_MINUTE = 45

OPENING_RANGE_BREAKOUT = 'opening_range_breakout'

stock_historical_client = StockHistoricalDataClient(config.API_KEY, config.SECRET_KEY)
trading_client = TradingClient(config.API_KEY, config.SECRET_KEY, paper=True)

opening_ranges = {}
symbols = []
threads = []


def strategy_handler(symbol):
    (opening_range_high, opening_range_difference) = opening_ranges.get(symbol)

    market_is_open = trading_client.get_clock().is_open

    # Every minute that the market is open
    # Check if we have an open position on a symbol
    # if we do, wait another minute to see if the trade clears
    # if we don't, check if opening range breakout has occurred
    while market_is_open:
        if symbol in open_positions:
            print(f"An open position already exists for {symbol}")
            client_order_ids = db_utils.get_client_order_ids(symbol, OrderStatus.NEW.capitalize())
            for client_order_id in client_order_ids:
                response = trading_client.get_order_by_client_id(client_order_id[0])
                # Checks if the sell side of the trade was filled and removes the symbol from the list of open positions
                for leg in response.legs:
                    if leg.status == OrderStatus.FILLED and leg.side == OrderSide.SELL:
                        if symbol in open_positions:
                            open_positions.remove(symbol)
                        # update client_order_id to database for redundancy
                        db_utils.update_trade_status(client_order_id[0], OrderStatus.FILLED.capitalize(),)
        else:
            print(f"Getting latest {symbol} quote")
            request_params = StockLatestQuoteRequest(symbol_or_symbols=symbol)

            latest_quote = stock_historical_client.get_stock_latest_quote(request_params)
            ask_price = latest_quote.get(symbol).ask_price
            bid_price = latest_quote.get(symbol).bid_price

            if bid_price > opening_range_high:
                # create a market order with a stop loss at price minus difference and take profit at price plus difference
                take_profit_request = TakeProfitRequest(limit_price=round(ask_price + 0.10, 2))
                # take_profit_request = TakeProfitRequest(limit_price=round(ask_price + opening_range_difference, 2))
                stop_loss_request = StopLossRequest(stop_price=round(bid_price - opening_range_difference, 2))

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

                print("Created a bracket order" + str(bracket_order.client_order_id))
                client_order_id = bracket_order.client_order_id

                # add client_order_id to database for redundancy
                db_utils.insert_trade(symbol, client_order_id, OrderStatus.NEW.capitalize(), bracket_order.created_at)
        time.sleep(60)

        market_is_open = trading_client.get_clock().is_open


stocks = db_utils.get_stocks_for_strategy(OPENING_RANGE_BREAKOUT)

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