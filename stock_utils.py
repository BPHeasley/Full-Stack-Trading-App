from datetime import datetime

from alpaca.common import APIError
from alpaca.data import StockBarsRequest, TimeFrame, StockHistoricalDataClient, StockLatestQuoteRequest
from alpaca.trading import TakeProfitRequest, StopLossRequest, MarketOrderRequest, OrderSide, TimeInForce, \
    TradingClient, OrderClass, GetOrdersRequest, QueryOrderStatus

import config

trading_client = TradingClient(config.API_KEY, config.SECRET_KEY, paper=True)
stock_historical_client = StockHistoricalDataClient(config.API_KEY, config.SECRET_KEY)

date = datetime.today().strftime('%Y-%m-%d')


def submit_trade(bid_price: float, trade_side: str, symbol: str, id: int):
    # preparing bracket order
    side, take_profit_request, stop_loss_request = None, None, None
    if trade_side == "BUY":
        side = OrderSide.BUY
        take_profit_request = TakeProfitRequest(limit_price=round(bid_price + 0.30, 2))
        stop_loss_request = StopLossRequest(stop_price=round(bid_price - 0.50, 2))
    elif trade_side == "SELL":
        side = OrderSide.SELL
        take_profit_request = TakeProfitRequest(limit_price=round(bid_price - 0.30, 2))
        stop_loss_request = StopLossRequest(stop_price=round(bid_price + 0.50, 2))
    bracket_order_data = MarketOrderRequest(
        symbol=symbol,
        qty=1,
        side=side,
        time_in_force=TimeInForce.GTC,
        order_class=OrderClass.BRACKET,
        take_profit=take_profit_request,
        stop_loss=stop_loss_request,
        client_order_id=f"{symbol}_{date}_{id}"
    )

    try_number = 1
    while try_number <= config.RETRY_LIMIT:
        try:
            bracket_order = trading_client.submit_order(order_data=bracket_order_data)
            print("Created a bracket order" + str(bracket_order.client_order_id))
            return bracket_order
        except APIError as e:
            print(e)
            print(
                f"Unable to submit order for {symbol} at {bid_price}, attempt {try_number} out of {config.RETRY_LIMIT}")
            try_number += 1
    # return None in the event the trade was unable to be completed
    return None


def get_bars(symbol: str, start_time: datetime.date = None, end_time: datetime.date = None):
    request_params = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Minute,
        start=start_time,
        end=end_time
    )

    return stock_historical_client.get_stock_bars(request_params)


def get_bid_price(symbol: str):
    request_params = StockLatestQuoteRequest(symbol_or_symbols=symbol)

    return stock_historical_client.get_stock_latest_quote(request_params).get(symbol).bid_price


def get_open_orders(symbols: list):
    get_orders_data = GetOrdersRequest(
        symbols=symbols,
        status=QueryOrderStatus.OPEN,
        limit=100,
        nested=True
    )

    return trading_client.get_orders(get_orders_data)

def get_order_by_client_id(client_id: str):
    return trading_client.get_order_by_client_id(client_id)

def is_market_open():
    return trading_client.get_clock().is_open


def get_all_open_positions():
    response = trading_client.get_all_positions()
    return [data.symbol for data in response]
