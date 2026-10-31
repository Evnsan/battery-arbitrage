from collections.abc import Sequence
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from openpyxl import Workbook

from battery_arbitrage.domain import MarketData
from battery_arbitrage.parsing import parse_market_data

TIMESTAMP_HEADER = "Timestamp"
PRICE_HEADER = "Market Price [£/MWh]"
NOTES_HEADER = "Notes"
UNEXPECTED_HEADER = "Something else"

SHEET_HALF_HOURLY = "Half-hourly data"
SHEET_HOURLY = "Hourly data"
BAD_SHEET = "Bad sheet"

START_TIME = datetime(2024, 1, 1, 0, 0)
HALF_HOUR = timedelta(minutes=30)
ONE_HOUR = timedelta(hours=1)
NEXT_HOUR = START_TIME + ONE_HOUR
FOURTH_HALF_HOUR_START = START_TIME + HALF_HOUR * 3

FIRST_HALF_HOUR_PRICE = 10.0
SECOND_HALF_HOUR_PRICE = 20.0
THIRD_HALF_HOUR_PRICE = 30.0
FOURTH_HALF_HOUR_PRICE = 40.0
FIRST_HOURLY_PRICE = 15.0
SECOND_HOURLY_PRICE = 35.0

VALID_PRICE = 1.0
NEXT_VALID_PRICE = 2.0
INTEGER_PRICE_SAMPLES = [10, 20]
HEADER_LOOKUP_PRICE = 5.0
INVALID_PRICE_TEXT = "abc"
INVALID_TIMESTAMP_TEXT = "not a date"
MONTH_FIRST_TIMESTAMP_TEXT = "1/2/18 0:30"
PARSED_MONTH_FIRST_TIMESTAMP = datetime(2018, 1, 2, 0, 30)
ISO_TIMESTAMP_TEXT = "2018-01-02T00:30:00"
ISO_TIMESTAMP_SPACE_TEXT = "2018-01-02 00:30:00"
PARSED_ISO_TIMESTAMP = datetime(2018, 1, 2, 0, 30)


# --- Helpers ----------------------------------------------------------------


def write_workbook(
    path: Path, sheets: dict[str, list[list[Any]]]
) -> str:
    """
    Write worksheet rows to an .xlsx file; each worksheet starts with a header.
    """
    wb = Workbook()
    default_sheet = wb.active
    if default_sheet is not None:
        wb.remove(default_sheet)
    for name, rows in sheets.items():
        ws = wb.create_sheet(title=name)
        for row in rows:
            ws.append(row)
    wb.save(path)
    return str(path)


def market_rows(
    interval: timedelta, prices: Sequence[int | float]
) -> list[list[Any]]:
    """Build rows with a headerless timestamp column and a price header."""
    return [[None, PRICE_HEADER]] + [
        [START_TIME + interval * i, price] for i, price in enumerate(prices)
    ]


# --- Good input -> MarketData -----------------------------------------------


@pytest.fixture
def example_workbook(tmp_path: Path) -> str:
    return write_workbook(
        tmp_path / "example.xlsx",
        {
            SHEET_HALF_HOURLY: market_rows(
                HALF_HOUR,
                [
                    FIRST_HALF_HOUR_PRICE,
                    SECOND_HALF_HOUR_PRICE,
                    THIRD_HALF_HOUR_PRICE,
                    FOURTH_HALF_HOUR_PRICE,
                ],
            ),
            SHEET_HOURLY: market_rows(
                ONE_HOUR, [FIRST_HOURLY_PRICE, SECOND_HOURLY_PRICE]
            ),
        },
    )


def test_returns_one_market_per_worksheet_with_its_own_timestamps(
    example_workbook: str,
) -> None:
    expected: MarketData = {
        SHEET_HALF_HOURLY: {
            START_TIME: FIRST_HALF_HOUR_PRICE,
            START_TIME + HALF_HOUR: SECOND_HALF_HOUR_PRICE,
            START_TIME + ONE_HOUR: THIRD_HALF_HOUR_PRICE,
            FOURTH_HALF_HOUR_START: FOURTH_HALF_HOUR_PRICE,
        },
        SHEET_HOURLY: {
            START_TIME: FIRST_HOURLY_PRICE,
            NEXT_HOUR: SECOND_HOURLY_PRICE,
        },
    }

    data = parse_market_data(example_workbook)

    assert data == expected


def test_prices_are_floats_and_timestamps_are_datetimes(tmp_path: Path) -> None:
    path = write_workbook(
        tmp_path / "m.xlsx",
        {SHEET_HOURLY: market_rows(ONE_HOUR, INTEGER_PRICE_SAMPLES)},
    )

    market_data = parse_market_data(path)
    market_prices = market_data[SHEET_HOURLY]

    assert all(isinstance(ts, datetime) for ts in market_prices)
    assert all(isinstance(p, float) for p in market_prices.values())


def test_price_column_is_found_by_header_not_by_position(
    tmp_path: Path,
) -> None:
    rows: list[list[Any]] = [
        [None, NOTES_HEADER, PRICE_HEADER],
        [START_TIME, "ignore me", HEADER_LOOKUP_PRICE],
    ]
    path = write_workbook(tmp_path / "m.xlsx", {SHEET_HOURLY: rows})

    assert parse_market_data(path)[SHEET_HOURLY] == {
        START_TIME: HEADER_LOOKUP_PRICE
    }


def test_month_first_timestamp_strings_are_parsed(tmp_path: Path) -> None:
    rows: list[list[Any]] = [
        [None, PRICE_HEADER],
        [MONTH_FIRST_TIMESTAMP_TEXT, HEADER_LOOKUP_PRICE],
    ]
    path = write_workbook(tmp_path / "m.xlsx", {SHEET_HOURLY: rows})

    assert parse_market_data(path)[SHEET_HOURLY] == {
        PARSED_MONTH_FIRST_TIMESTAMP: HEADER_LOOKUP_PRICE
    }


@pytest.mark.parametrize(
    "timestamp_text", [ISO_TIMESTAMP_TEXT, ISO_TIMESTAMP_SPACE_TEXT]
)
def test_iso_timestamp_strings_are_parsed(
    tmp_path: Path, timestamp_text: str
) -> None:
    rows: list[list[Any]] = [
        [None, PRICE_HEADER],
        [timestamp_text, HEADER_LOOKUP_PRICE],
    ]
    path = write_workbook(tmp_path / "m.xlsx", {SHEET_HOURLY: rows})

    assert parse_market_data(path)[SHEET_HOURLY] == {
        PARSED_ISO_TIMESTAMP: HEADER_LOOKUP_PRICE
    }


def test_blank_rows_are_ignored(tmp_path: Path) -> None:
    rows: list[list[Any]] = [
        [None, PRICE_HEADER],
        [START_TIME, VALID_PRICE],
        [None, None],
        [NEXT_HOUR, NEXT_VALID_PRICE],
    ]
    path = write_workbook(tmp_path / "m.xlsx", {SHEET_HOURLY: rows})

    assert parse_market_data(path)[SHEET_HOURLY] == {
        START_TIME: VALID_PRICE,
        NEXT_HOUR: NEXT_VALID_PRICE,
    }


# --- Bad input -> ValueError naming the sheet -------------------------------


VALID_HEADER = [TIMESTAMP_HEADER, PRICE_HEADER]
VALID_ROW = [START_TIME, VALID_PRICE]
INVALID_SHEET_CASES = [
    pytest.param([], id="empty-sheet"),
    pytest.param([VALID_HEADER], id="header-only"),
    pytest.param(
        [[TIMESTAMP_HEADER, UNEXPECTED_HEADER], VALID_ROW], id="no-price-column"
    ),
    pytest.param(
        [
            [None, "Market 1 Price [£/MWh]", "Market 2 Price [£/MWh]"],
            [START_TIME, VALID_PRICE, NEXT_VALID_PRICE],
        ],
        id="multiple-price-columns",
    ),
    pytest.param(
        [VALID_HEADER, VALID_ROW, [NEXT_HOUR, INVALID_PRICE_TEXT]],
        id="text-price",
    ),
    pytest.param([VALID_HEADER, VALID_ROW, [NEXT_HOUR, "NaN"]], id="nan-price"),
    pytest.param(
        [VALID_HEADER, VALID_ROW, [NEXT_HOUR, "Infinity"]],
        id="infinite-price",
    ),
    pytest.param(
        [VALID_HEADER, VALID_ROW, [NEXT_HOUR, None]], id="blank-price"
    ),
    pytest.param(
        [VALID_HEADER, VALID_ROW, [INVALID_TIMESTAMP_TEXT, NEXT_VALID_PRICE]],
        id="text-timestamp",
    ),
    pytest.param(
        [VALID_HEADER, VALID_ROW, [None, NEXT_VALID_PRICE]],
        id="blank-timestamp",
    ),
    pytest.param(
        [VALID_HEADER, VALID_ROW, [START_TIME, NEXT_VALID_PRICE]],
        id="duplicate-timestamp",
    ),
]


@pytest.mark.parametrize("rows", INVALID_SHEET_CASES)
def test_invalid_sheet_data_raises_value_error_with_sheet_name(
    tmp_path: Path, rows: Any
) -> None:
    path = write_workbook(
        tmp_path / "m.xlsx",
        {
            SHEET_HOURLY: market_rows(ONE_HOUR, [VALID_PRICE]),
            BAD_SHEET: rows,
        },
    )

    with pytest.raises(ValueError, match=BAD_SHEET):
        parse_market_data(path)


# --- Smoke test against the supported example workbook ----------------------

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
EXAMPLE_WORKBOOK = DATA_DIR / "cleaned_market_data.xlsx"


def test_parses_the_example_workbook() -> None:
    data = parse_market_data(EXAMPLE_WORKBOOK)

    assert {SHEET_HALF_HOURLY, SHEET_HOURLY} <= set(data)
    assert all(prices for prices in data.values())
