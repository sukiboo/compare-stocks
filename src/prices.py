import yfinance as yf


def get_historical_prices(tickers):
    df = (
        yf.download(
            tickers,
            interval="1d",
            period="max",
            progress=False,
        )
        .Close.bfill()
        .ffill()
    )
    return df
