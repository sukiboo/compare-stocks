import os

from src.dash_app import create_app
from src.prices import get_historical_prices

if __name__ == "__main__":
    tickers = ["AAPL", "MSFT", "GOOGL"]
    df = get_historical_prices(tickers)

    dash_app, server = create_app(df)
    dash_app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
