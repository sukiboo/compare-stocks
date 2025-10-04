import itertools
from datetime import datetime

import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html

from src.utils import get_available_tickers, normalize_prices


def setup_ticker_selection(initial_tickers):
    available_tickers = get_available_tickers()
    ticker_selection = dcc.Dropdown(
        id="ticker-selection",
        options=[{"label": ticker, "value": ticker.upper()} for ticker in available_tickers],
        value=initial_tickers,
        multi=True,
        placeholder="Select tickers...",
    )
    return ticker_selection


def setup_interval_buttons():
    button_style = {
        "padding": "10px 20px",
        "borderRadius": "10px",
        "cursor": "pointer",
        "fontFamily": "'Courier New', Courier, monospace",
        "fontWeight": "bold",
        "textAlign": "center",
    }
    interval_buttons_html = html.Div(
        [
            html.Button("ytd", id="btn-ytd", n_clicks=0, style=button_style),
            html.Button("1mo", id="btn-1mo", n_clicks=0, style=button_style),
            html.Button("6mo", id="btn-6mo", n_clicks=0, style=button_style),
            html.Button("1y", id="btn-1y", n_clicks=0, style=button_style),
            html.Button("2y", id="btn-2y", n_clicks=0, style=button_style),
            html.Button("3y", id="btn-3y", n_clicks=0, style=button_style),
            html.Button("5y", id="btn-5y", n_clicks=0, style=button_style),
            html.Button("10y", id="btn-10y", n_clicks=0, style=button_style),
        ],
        style={"marginTop": "5px", "gap": "5px", "display": "flex", "flexWrap": "wrap"},
    )
    interval_buttons_ids = [
        "btn-ytd",
        "btn-1mo",
        "btn-6mo",
        "btn-1y",
        "btn-2y",
        "btn-3y",
        "btn-5y",
        "btn-10y",
    ]
    interval_offsets = {
        "btn-ytd": max(1, (datetime.now() - datetime(datetime.now().year, 1, 1)).days),
        "btn-1mo": 30,
        "btn-6mo": 182,
        "btn-1y": 365,
        "btn-2y": 2 * 365,
        "btn-3y": 3 * 365,
        "btn-5y": 5 * 365,
        "btn-10y": 10 * 365,
    }
    return interval_buttons_html, interval_buttons_ids, interval_offsets


def plot_prices(timestamps, prices, rolling_changes, idx_range):
    idx0, idx1 = idx_range
    date_range = [timestamps[idx0], timestamps[idx1]]
    prices_normalized = normalize_prices(prices, date_range)

    fig = go.Figure()

    # rangeslider plot
    colors = itertools.cycle(px.colors.qualitative.Set2)
    for asset in prices.columns:
        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=rolling_changes[asset],
                line=dict(color=next(colors)),
                xaxis="x1",
                yaxis="y1",
                showlegend=False,
            )
        )

    # main plot
    colors = itertools.cycle(px.colors.qualitative.Set2)
    for asset in prices_normalized.columns:
        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=100 * prices_normalized[asset],
                line=dict(width=3, color=next(colors)),
                name=asset,
                xaxis="x2",
                yaxis="y2",
            )
        )

    # dummy traces to show ticks on the right
    for _ in prices_normalized.columns:
        fig.add_trace(
            go.Scatter(
                x=[],
                y=[],
                xaxis="x2",
                yaxis="y3",
                showlegend=False,
            )
        )

    # configure axes
    xaxis1_dict = dict(rangeslider=dict(visible=True, thickness=0.1), tickangle=-30, nticks=20)
    xaxis2_dict = dict(matches="x1", showticklabels=False)
    xaxis1_dict["range"] = date_range
    xaxis2_dict["range"] = date_range
    yaxis1_dict = dict(showticklabels=False)
    yaxis2_dict = dict(
        autorange=True,
        title="relative price change",
        nticks=12,
        tickformat=".0f",
        ticksuffix="%",
        ticks="outside",
    )
    yaxis3_dict = dict(
        matches="y2",
        overlaying="y2",
        side="right",
        nticks=12,
        tickformat=".0f",
        ticksuffix="%",
        ticks="outside",
    )

    fig.update_layout(
        xaxis1=xaxis1_dict,
        yaxis1=yaxis1_dict,
        xaxis2=xaxis2_dict,
        yaxis2=yaxis2_dict,
        yaxis3=yaxis3_dict,
        uirevision="constant",  # prevent resets from the xrange compression
        font=dict(family="Courier New, Monospace", size=14, weight="bold"),
        legend=dict(
            title=dict(text="assets: "),
            orientation="h",
            x=0.0,
            y=1.0,
            xanchor="left",
            yanchor="bottom",
        ),
        margin=dict(t=50, b=50),
        template="plotly",
        height=600,
    )

    return fig
