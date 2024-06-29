from datetime import datetime

from alpaca.data import StockBarsRequest, TimeFrame, StockHistoricalDataClient, StockLatestQuoteRequest
from alpaca.trading import TakeProfitRequest, StopLossRequest, MarketOrderRequest, OrderSide, TimeInForce, TradingClient

import config

trading_client = TradingClient(config.API_KEY, config.SECRET_KEY, paper=True)
stock_historical_client = StockHistoricalDataClient(config.API_KEY, config.SECRET_KEY)


def submit_trade(bid_price: float, trade_side: str, symbol: str, ):
    # preparing bracket order
    global side, take_profit_request, stop_loss_request
    if trade_side == "BUY":
        side = OrderSide.BUY
        take_profit_request = TakeProfitRequest(limit_price=round(bid_price * 1.03, 2))
        stop_loss_request = StopLossRequest(stop_price=round(bid_price * 0.99, 2))
    elif trade_side == "SELL":
        side = OrderSide.SELL
        take_profit_request = TakeProfitRequest(limit_price=round(bid_price * 0.99, 2))
        stop_loss_request = StopLossRequest(stop_price=round(bid_price * 1.01, 2))
    bracket_order_data = MarketOrderRequest(
        symbol=symbol,
        qty=1,
        side=side,
        time_in_force=TimeInForce.GTC,
        take_profit=take_profit_request,
        stop_loss=stop_loss_request
    )

    bracket_order = trading_client.submit_order(order_data=bracket_order_data)
    print("Created a bracket order" + str(bracket_order.client_order_id))
    return bracket_order


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

