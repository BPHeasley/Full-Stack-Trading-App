import sqlite3
import config

from alpaca.trading import TradingClient, GetAssetsRequest, Asset, AssetClass


def add_to_db(asset: Asset):
    print("Adding {} to db".format(asset.symbol))
    try:
        cursor.execute("INSERT INTO stock (symbol, company) VALUES (?, ?)", (asset.symbol, asset.name))
    except Exception as e:
        print(asset.symbol)
        print(e)

trading_client = TradingClient(config.API_KEY, config.SECRET_KEY, paper=True)

connection = sqlite3.connect(config.DATABASE)

cursor = connection.cursor()

cursor.execute("""select symbol, company from stock""")
rows = cursor.fetchall()
symbols = [row[0] for row in rows]

# Get US Equities assets
search_params = GetAssetsRequest(asset_class=AssetClass.US_EQUITY)
assets = trading_client.get_all_assets(search_params)

for asset in assets:
    if asset.tradable and asset.status == 'active' and asset.symbol not in symbols:
        add_to_db(asset)

connection.commit()
