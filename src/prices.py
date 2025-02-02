import pandas as pd
import yfinance as yf


def get_available_tickers():
    nasdaq_url = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
    nyse_url = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
    nasdaq_tickers = pd.read_csv(nasdaq_url, sep="|")["Symbol"].dropna().tolist()[:-1]
    nyse_tickers = pd.read_csv(nyse_url, sep="|")["ACT Symbol"].dropna().tolist()[:-1]
    all_tickers = sorted(set(nasdaq_tickers + nyse_tickers))
    return all_tickers


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
