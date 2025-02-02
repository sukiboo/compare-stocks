from datetime import timedelta

import numpy as np
from dash import Dash, Input, Output, State, ctx, dcc, html
from dateutil import parser  # type: ignore

from src.prices import get_historical_prices
from src.style_elements import (
    plot_prices,
    setup_interval_buttons,
    setup_ticker_selection,
)
from src.utils import date_to_idx_range, get_date_range


class NormalizedAssetPricesApp:

    # TODO: add initial interval
    def __init__(self, initial_tickers=["AAPL", "GOOGL", "MSFT"]):

        self.setup_env(initial_tickers)

        self.interval_buttons_html, self.interval_buttons_ids, self.interval_offsets = (
            setup_interval_buttons()
        )
        self.ticker_selection = setup_ticker_selection(initial_tickers)
        self.setup_app()

    def setup_env(self, initial_tickers):
        prices = get_historical_prices(initial_tickers)

        self.prices = prices / prices.iloc[0]
        self.percentage_changes = (self.prices / (self.prices.shift(1) + 1e-7) - 1).fillna(0)
        self.rolling_changes = self.percentage_changes.rolling(window=251, min_periods=1).sum()
        self.timestamps = self.prices.index
        self.idx_range = [0, -1]
        self.normalize_prices()
        # TODO: this is horrible, pls fix
        self.fig = plot_prices(
            self.timestamps, self.prices, self.prices_normalized, self.rolling_changes, [None, None]
        )

    def normalize_prices(self):
        idx0, idx1 = self.idx_range
        date0, date1 = self.timestamps[idx0], self.timestamps[idx1]
        price = self.prices.loc[date0]
        self.prices_normalized = np.nan * self.prices
        self.prices_normalized.loc[date0:date1] = 100 * (self.prices[date0:date1] / price - 1)

    def update_figure(self, date_range=[None, None]):
        idx_range = date_to_idx_range(self.timestamps, date_range)
        # do not update the figure if the range is unchanged
        if idx_range != self.idx_range:
            self.idx_range = idx_range
            self.normalize_prices()
            self.fig = plot_prices(
                self.timestamps,
                self.prices,
                self.prices_normalized,
                self.rolling_changes,
                date_range,
            )
        return self.fig

    def setup_app(self):
        self.app = Dash(__name__)
        self.app.layout = html.Div(
            [
                dcc.Graph(id="plotly-normalized-asset-prices", figure=self.fig),
                dcc.Store(id="debounced-relayout", data=None),
                self.ticker_selection,
                self.interval_buttons_html,
            ]
        )

        # wait 100ms between the updates, even though o1 insists that it's not a
        # "true debounce": https://chatgpt.com/share/677b0a08-712c-800c-8aa9-d4abdfa50f11
        self.app.clientside_callback(
            """
            function (relayoutData) {
                return new Promise((resolve) => {
                    setTimeout(function() {
                        resolve('Figure updated.');
                    }, 100);
                });
            }
            """,
            Output("debounced-relayout", "data"),
            Input("plotly-normalized-asset-prices", "relayoutData"),
            prevent_initial_call=True,
        )

        @self.app.callback(
            Output("plotly-normalized-asset-prices", "figure"),
            [
                Input("debounced-relayout", "data"),
                Input("ticker-selection", "value"),
                *[Input(button_id, "n_clicks") for button_id in self.interval_buttons_ids],
            ],
            State("plotly-normalized-asset-prices", "figure"),
            prevent_initial_call=True,
        )
        def update_figure_after_delay(
            relayout_data, tickers, n10y, n5y, n3y, n2y, n1y, n6m, n1m, n1w, current_figure
        ):
            print(f"Selected tickers: {', '.join(tickers) if tickers else 'None'}")
            date_range = get_date_range(current_figure["layout"])
            triggered_id = ctx.triggered_id
            if triggered_id in self.interval_buttons_ids:
                date_range = self.adjust_date_range(date_range, triggered_id)
                print(date_range)

            fig = self.update_figure(date_range)
            return fig

    # TODO: filter date_range=[None, None]
    # UPD: might have fixed it by setting the initial idx range to [0, -1]
    def adjust_date_range(self, date_range, button_id):
        start_date, end_date = date_range
        start_date = max(
            parser.parse(end_date) - timedelta(days=self.interval_offsets[button_id]),
            self.timestamps[0],
        ).strftime("%Y-%m-%d")
        return [start_date, end_date]

    def run(self, **kwargs):
        self.app.run_server(**kwargs)


def create_app():
    dash_app = NormalizedAssetPricesApp()
    server = dash_app.app.server
    return dash_app, server
