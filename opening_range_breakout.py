#!/usr/bin/python
import datetime as date
import db_utils as db_utils
import time
from threading import Thread

import stock_utils

OPENING_HOUR = 13
OPENING_MINUTE = 30
CLOSE_MINUTE = 45

OPENING_RANGE_BREAKOUT = 'opening_range_breakout'
BUY = "BUY"
SELL = "SELL"

symbols = []
threads = []
open_positions = stock_utils.get_all_open_positions()


def strategy_handler(symbol, range_low, range_high):
    # Every minute that the market is open
    # Check if we have an open position on a symbol
    # if we do, wait another minute to see if the trade clears
    # if we don't, check if opening range breakout has occurred
    order_id = 1

    while stock_utils.is_market_open():
        if symbol in open_positions:
            # Check if the position is still open
            print(f"An open position already exists for {symbol}")
            response = stock_utils.get_open_orders([symbol])
            symbols = [data.symbol for data in response]
            if symbol not in symbols:
                print(f"Updating {symbol} trades in database")
                open_positions.remove(symbol)
                client_order_ids = db_utils.get_all_client_order_ids_by_symbol(symbol)
                for client_id in client_order_ids:
                    # get the status of the order
                    response = stock_utils.get_order_by_client_id(client_id)
                    db_utils.update_trade_status(client_id[0], response.status.capitalize())
        else:
            print(f"Getting latest {symbol} quote")
            bid_price = stock_utils.get_bid_price(symbol)

            bracket_order, side = None, None

            if bid_price > range_high:
                side = BUY

            # Short the stock
            elif bid_price <= range_low:
                side = SELL
            else:
                # no bid exists, wait for next bar
                time.sleep(60)
                continue

            # create the bracket order
            bracket_order = stock_utils.submit_trade(bid_price, side, symbol, order_id)

            # add client_order_id to database for redundancy
            if bracket_order is not None:
                db_utils.insert_trade(symbol, bracket_order.client_order_id, bracket_order.status.capitalize(),
                                      bracket_order.created_at)
                open_positions.append(symbol)
                order_id += 1

        time.sleep(60)


def start():
    stocks = db_utils.get_stocks_for_strategy(OPENING_RANGE_BREAKOUT)

    year = date.datetime.today().year
    month = date.datetime.today().month
    day = date.datetime.today().day

    start_time = date.datetime(year, month, day, OPENING_HOUR, OPENING_MINUTE)
    end_time = date.datetime(year, month, day, OPENING_HOUR, CLOSE_MINUTE)

    for stock in stocks:
        symbol = str(stock['symbol'])
        symbols.append(symbol)
        # Create minute bar request for each stock that the ORB strategy exists for
        # Get the opening range of stocks to set the price
        opening_bars = stock_utils.get_bars(symbol, start_time, end_time)

        opening_range_low = float('inf')
        opening_range_high = 0

        for bar in opening_bars.data.values():
            for info in bar:
                if info.low < opening_range_low:
                    opening_range_low = info.low
                if info.high > opening_range_high:
                    opening_range_high = info.high

        thread = Thread(target=strategy_handler, args=(symbol, opening_range_low, opening_range_high))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()
