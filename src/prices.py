from datetime import date

import yfinance as yf


class Prices:
    """Retrieve historical prices and compute relevant metrics."""

    def __init__(self, initial_tickers, date_start):
        self.tickers = initial_tickers
        self.date_range = (date_start, date.today().strftime("%Y-%m-%d"))
        self.prices_raw = self.get_historical_prices(initial_tickers)
        self.prices_normalized = self.prices_raw / self.prices_raw.iloc[0]
        self.percentage_changes = (
            self.prices_normalized / (self.prices_normalized.shift(1) + 1e-7) - 1
        ).fillna(0)
        self.rolling_changes = self.percentage_changes.rolling(window=251, min_periods=1).sum()

    def get_historical_prices(self, tickers):
        df = (
            yf.download(
                tickers,
                interval="1d",
                start=self.date_range[0],
                end=self.date_range[1],
                auto_adjust=False,
                progress=False,
            )
            .Close.bfill()
            .ffill()
        )
        return df
