from dash import Dash, Input, Output, State, ctx, dcc, html

from src.prices import Prices
from src.style_elements import (
    plot_prices,
    setup_interval_buttons,
    setup_ticker_selection,
)
from src.utils import adjust_date_range, date_to_idx_range, get_date_range


class NormalizedAssetPricesApp:

    def __init__(
        self,
        initial_tickers=["QQQ", "SPY", "VTI", "VT"],
        date_start="2000-01-01",
        initial_interval_days=365,
    ):
        self.setup_env(initial_tickers, date_start, initial_interval_days)
        self.interval_buttons_html, self.interval_buttons_ids, self.interval_offsets = (
            setup_interval_buttons()
        )
        self.ticker_selection = setup_ticker_selection(initial_tickers)
        self.setup_app()

    def setup_env(self, initial_tickers, date_start, initial_interval_days):
        self.prices = Prices(initial_tickers, date_start)
        self.timestamps = self.prices.date_range
        self.idx_range = date_to_idx_range(
            self.timestamps,
            adjust_date_range(self.timestamps, initial_interval_days),
        )
        self.fig = plot_prices(
            self.timestamps,
            self.prices.prices_normalized,
            self.prices.rolling_changes,
            self.idx_range,
        )

    def update_figure(self, tickers, date_range=[None, None]):
        tickers_updated, range_updated = False, False

        if set(tickers) != self.prices.tickers:
            self.prices.update_tickers(tickers)
            tickers_updated = True
            print(f"tickers update: {', '.join(tickers) if tickers else 'None'}")

        idx_range = date_to_idx_range(self.timestamps, date_range)
        if idx_range != self.idx_range:
            self.idx_range = idx_range
            range_updated = True
            print(f"interval update: {date_range=}")

        if tickers_updated or range_updated:
            self.fig = plot_prices(
                self.timestamps,
                self.prices.prices_normalized,
                self.prices.rolling_changes,
                idx_range,
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
            relayout_data, tickers, n10y, n5y, n3y, n2y, n1y, n6m, n1m, current_figure
        ):
            date_range = get_date_range(current_figure["layout"])
            triggered_id = ctx.triggered_id
            if triggered_id in self.interval_buttons_ids:
                date_range = adjust_date_range(
                    self.timestamps, self.interval_offsets[triggered_id], date_range
                )
            fig = self.update_figure(tickers, date_range)
            return fig

    def run(self, **kwargs):
        self.app.run_server(**kwargs)


def create_app():
    dash_app = NormalizedAssetPricesApp()
    server = dash_app.app.server
    return dash_app, server
