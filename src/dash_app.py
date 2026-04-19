import json
from collections.abc import Sequence
from typing import Any

from dash import Dash, Input, Output, State, ctx, dcc, html
from dateutil import parser  # type: ignore
from plotly.graph_objects import Figure

from src.constants import (
    APP_DATE_START,
    APP_INITIAL_INTERVAL_DAYS,
    APP_INITIAL_TICKERS,
    APP_MAX_TICKERS,
)
from src.prices import Prices
from src.style_elements import (
    BUTTON_STYLE_ACTIVE,
    BUTTON_STYLE_INACTIVE,
    plot_prices,
    setup_interval_buttons,
    setup_ticker_selection,
)
from src.utils import (
    adjust_date_range,
    date_to_idx_range,
    get_date_range,
    normalize_ticker_symbol,
)

INTERVAL_LENGTH_TOLERANCE_DAYS = 2


class NormalizedAssetPricesApp:

    def __init__(
        self,
        initial_tickers: list[str] = APP_INITIAL_TICKERS,
        date_start: str = APP_DATE_START,
        initial_interval_days: int = APP_INITIAL_INTERVAL_DAYS,
    ) -> None:
        self.setup_env(initial_tickers, date_start, initial_interval_days)
        self.interval_buttons_html, self.interval_buttons_ids, self.interval_offsets = (
            setup_interval_buttons()
        )
        self.initial_active_btn = next(
            (
                bid
                for bid in self.interval_buttons_ids
                if bid != "btn-ytd" and self.interval_offsets[bid] == initial_interval_days
            ),
            None,
        )
        self.initial_tickers = initial_tickers
        self.ticker_selection = setup_ticker_selection(initial_tickers)
        self.setup_app()

    def setup_env(
        self, initial_tickers: list[str], date_start: str, initial_interval_days: int
    ) -> None:
        self.prices = Prices(initial_tickers, date_start)
        self.timestamps = self.prices.date_range
        self.idx_range = date_to_idx_range(
            self.timestamps,
            adjust_date_range(self.timestamps, initial_interval_days),
        )
        self.fig = plot_prices(
            self.timestamps,
            self.prices.prices_normalized,
            self.prices.prices_raw,
            self.prices.rolling_changes,
            self.idx_range,
        )

    def update_figure(
        self, tickers: list[str], date_range: Sequence[str | None] = [None, None]
    ) -> Figure:
        tickers_updated, range_updated = False, False

        if list(tickers) != self.prices.tickers:
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
                self.prices.prices_raw,
                self.prices.rolling_changes,
                idx_range,
            )

        return self.fig

    def setup_app(self) -> None:
        self.app = Dash(__name__)
        self.app.layout = html.Div(
            [
                dcc.Graph(id="plotly-normalized-asset-prices", figure=self.fig),
                dcc.Store(id="debounced-relayout", data=None),
                dcc.Store(id="active-interval-btn", data=self.initial_active_btn),
                self.interval_buttons_html,
                self.ticker_selection,
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

        button_ids_js = json.dumps(self.interval_buttons_ids)
        active_style_js = json.dumps(BUTTON_STYLE_ACTIVE)
        inactive_style_js = json.dumps(BUTTON_STYLE_INACTIVE)
        self.app.clientside_callback(
            f"""
            function (activeBtn) {{
                const ids = {button_ids_js};
                const active = {active_style_js};
                const inactive = {inactive_style_js};
                return ids.map(id => id === activeBtn ? active : inactive);
            }}
            """,
            [Output(button_id, "style") for button_id in self.interval_buttons_ids],
            Input("active-interval-btn", "data"),
        )

        @self.app.callback(
            [
                Output("ticker-selection", "options"),
                Output("ticker-selection", "value"),
                Output("ticker-input", "value"),
                Output("ticker-input", "placeholder"),
            ],
            [Input("ticker-input", "n_submit"), Input("ticker-selection", "value")],
            [State("ticker-input", "value"), State("ticker-selection", "value")],
            prevent_initial_call=True,
        )
        def update_tickers(
            n_submit: int,
            selected_tickers: list[str] | None,
            input_ticker: str,
            current_tickers: list[str] | None,
        ) -> tuple[list[dict[str, str]], list[str], str, str]:
            triggered_id = ctx.triggered_id
            tickers = current_tickers if current_tickers else []
            options = [{"label": t, "value": t} for t in tickers]

            if triggered_id == "ticker-input" and input_ticker.strip():
                ticker = normalize_ticker_symbol(input_ticker)
                if ticker in tickers:
                    return options, tickers, "", f"⚠️ `{ticker}` already added"
                elif not self.prices.is_valid_ticker(ticker):
                    return options, tickers, "", f"❌ `{ticker}` is not valid"
                elif len(tickers) >= APP_MAX_TICKERS:
                    return options, tickers, "", f"⛔ {APP_MAX_TICKERS} tickers max!"
                else:
                    tickers = tickers + [ticker]
                    options = [{"label": t, "value": t} for t in tickers]
                    return options, tickers, "", f"✅ `{ticker}` added"
            else:
                tickers = selected_tickers if selected_tickers else []
                options = [{"label": t, "value": t} for t in tickers]
                return options, tickers, input_ticker or "", "Enter ticker symbol..."

        @self.app.callback(
            [
                Output("plotly-normalized-asset-prices", "figure"),
                Output("active-interval-btn", "data"),
            ],
            [
                Input("debounced-relayout", "data"),
                Input("ticker-selection", "value"),
                *[Input(button_id, "n_clicks") for button_id in self.interval_buttons_ids],
            ],
            [
                State("plotly-normalized-asset-prices", "figure"),
                State("active-interval-btn", "data"),
            ],
            prevent_initial_call=True,
        )
        def update_figure_after_delay(
            relayout_data: Any,
            tickers: list[str] | None,
            nytd: int,
            n1mo: int,
            n6mo: int,
            n1y: int,
            n2y: int,
            n3y: int,
            n5y: int,
            n10y: int,
            current_figure: dict[str, Any],
            active_btn: str | None,
        ) -> tuple[Figure, str | None]:
            date_range = get_date_range(current_figure["layout"])
            triggered_id = ctx.triggered_id
            if triggered_id in self.interval_buttons_ids:
                offset_days = self.interval_offsets[triggered_id]
                date_range = adjust_date_range(
                    self.timestamps, offset_days, triggered_id, date_range
                )
                active_btn = triggered_id
            elif triggered_id == "debounced-relayout" and active_btn is not None:
                start, end = date_range
                if start and end:
                    length_days = (parser.parse(end) - parser.parse(start)).days
                    expected = self.interval_offsets[active_btn]
                    if abs(length_days - expected) > INTERVAL_LENGTH_TOLERANCE_DAYS:
                        active_btn = None
                else:
                    active_btn = None
            fig = self.update_figure(tickers or [], date_range)
            return fig, active_btn

    def run(self, **kwargs: Any) -> None:
        self.app.run_server(**kwargs)


def create_app() -> tuple[NormalizedAssetPricesApp, Any]:
    dash_app = NormalizedAssetPricesApp()
    server = dash_app.app.server
    return dash_app, server
