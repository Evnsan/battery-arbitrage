# Battery Arbitrage

A Python project for modeling battery dispatch and optimizing electricity trading profit across multiple wholesale markets with different trading intervals.

The model treats the battery as a price taker and uses historical market prices to determine when to charge and discharge while respecting its physical constraints.

## Features

- Load market prices from an Excel workbook, with one worksheet per market.
- Support markets with different trading interval durations (the interval of each market is inferred from its timestamps).
- Optimize battery charging and discharging decisions across markets with a mixed-integer linear program (Pyomo + HiGHS).
- Enforce battery power limits, storage capacity, and charge/discharge exclusivity.
- Optionally restrict the optimization to a time window.
- Generate CSV reports of battery operation, market dispatch, and cumulative trading cash flow.

## How it works

The model uses market prices to determine how the battery should allocate its charging and discharging capacity over the selected period.

The battery can purchase electricity when prices are low and sell it when prices are higher. Its decisions must respect its available stored energy, storage capacity, and power limits. When participating in multiple markets, the model must also account for their different trading intervals and avoid selling the same energy twice.

The optimization objective is to maximize trading profit, calculated as electricity sales revenue minus electricity purchase costs.

The pipeline runs these stages in order:

1. **Parse** the workbook into one price series per market.
2. **Validate** the series and infer each market's interval.
3. **Align** the markets on a common physical timeline whose timestep is the greatest common divisor of the market intervals. Prices of longer intervals are repeated on every timestep they cover.
4. **Select the period** (only if `--start-time` or `--end-time` is given).
5. **Optimize** with HiGHS. Market commitments are constant over each market interval; the battery's energy and power constraints apply at every physical timestep.
6. **Report** dispatch and operation rows and export them to CSV.

See [CONTEXT.md](CONTEXT.md) for the domain assumptions, battery parameters, and input data format.

## Requirements

- Python 3.10 or later (the pinned dependencies and CI use Python 3.13)
- [HiGHS](https://highs.dev/), installed automatically through the `highspy` package and used via Pyomo

## Installation

Clone the repository and install the project dependencies:

```bash
git clone <repository-url>
cd battery-arbitrage

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install the package and its pinned dependencies
pip install -e .

# Or, to also install the development tools (pytest, ruff, mypy)
pip install -e ".[dev]"
```

Runtime dependencies are pinned in `requirements.txt` (compiled from `requirements.in`); development tools are in `requirements-dev.txt`.

## Input data

The model accepts an Excel workbook (`.xlsx`) containing market data organized by worksheet. **Every worksheet is treated as a market** (named after the worksheet), so the workbook must not contain other sheets. Each worksheet must contain timestamps in the first column and the corresponding market prices in £/MWh in a column whose header ends with `Price [£/MWh]`.

The supported example input is `data/cleaned_market_data.xlsx`. The repository also includes `data/market_data.xlsx`, which is the raw source data and is not a supported input.

The example dataset contains half-hourly and hourly prices from 1 January 2018 to 31 December 2020:

| Worksheet          | Market interval |
| ------------------ | --------------- |
| `Half-hourly data` | 30 minutes      |
| `Hourly data`      | 1 hour          |

Each market must have a consistent interval duration, with timestamps identifying consecutive intervals throughout the modeled period. Gaps, duplicate timestamps, missing or non-finite prices, and series with fewer than two observations are rejected with an error that names the worksheet. Timestamps are interpreted as the **start** of each interval.

See [CONTEXT.md](CONTEXT.md) for further details.

## Usage

Run the optimization and write both CSV reports with:

```bash
# Run the optimization using the example dataset
battery-arbitrage --input data/cleaned_market_data.xlsx

# Choose custom paths for the CSV reports and optimize January 2018 only
battery-arbitrage \
  --input data/cleaned_market_data.xlsx \
  --dispatch-csv results/market-dispatch.csv \
  --operation-csv results/battery-operation.csv \
  --start-time 2018-01-01T00:00:00 \
  --end-time 2018-02-01T00:00:00
```

By default, the command writes `results/dispatch.csv` and
`results/operation.csv`. Use `--tolerance-millis` to change the timestamp
alignment tolerance; its default is 1000 milliseconds. Use `--verbosity` with
`DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL` to set log verbosity; the
default is `INFO`. The options also have short forms: `-i`, `-d`, `-o`, `-t`,
`-v`, `-s`, and `-e`, respectively.

Time bounds use an inclusive start and exclusive end in ISO format
(`[start, end)`). Each bound must align to a boundary shared by all markets
(for the example data, a whole hour), bounds outside the data coverage are
clipped to the available timeline, and a window with no overlap is an error.
The bounds must use the same timezone awareness as the data (the example
workbook is timezone-naive). The battery starts the selected period at its
configured initial energy.

The command prints the output paths and total profit after the reports are
written. Expected errors (invalid data, solver failure, file problems) are
printed as `Error: ...` and the command exits with status 1.

The battery parameters cannot be changed from the command line. Library users
can pass a `BatteryConfig` to `battery_arbitrage.pipeline.run_optimization`.

## Results

Two CSV files are written, both at the resolution of the physical timeline (for the example data, 30 minutes). All values are unrounded.

- **Market dispatch report** (`dispatch.csv`): one row per timestamp and market with columns `timestamp`, `market_name`, `price_gbp_per_mwh`, `charge_mw`, `discharge_mw` and `cash_flow_gbp`. A commitment in an hourly market appears on two consecutive rows with the same power; each row carries the cash flow of one half hour, so the two rows together equal the commitment's cash flow over the full hour.
- **Battery operation report** (`operation.csv`): one row per timestamp with columns `timestamp`, `charge_mw`, `discharge_mw`, `energy_mwh`, `cash_flow_gbp` and `cumulative_cash_flow_gbp`, summed across markets. `energy_mwh` is the stored energy at the **start** of the timestep. The stored energy after the last timestep is not reported.

The total profit is printed to the console and is not stored in the CSV files. The solver status is written to the log, and the HiGHS solver log is always printed, regardless of `--verbosity`.

Results represent the modeled trading profit under the project's assumptions, not a forecast or guarantee of real-world returns.

## Solver behavior

The model is solved with HiGHS using a time limit of 300 seconds and a relative MIP gap of 2%. The solver settings are constants in `optimization.py` and cannot be changed from the command line. Consequently:

- The reported solution may be up to about 2% below the true optimum.
- If the time limit is reached, or the solver terminates with anything other than *optimal*, the run fails with an error and no CSV files are written, even if a feasible solution was found.
- The model has one binary variable per physical timestep, so solve time grows with the length of the selected period. For example, the full example dataset has 52,608 half-hour timesteps.

## Limitations

This is a simplified battery arbitrage model. It assumes:

- The battery does not influence market prices.
- All prices over the selected period are known in advance (perfect foresight), and the markets are optimized jointly as if they cleared at the same time.
- Charging and discharging have 100% efficiency.
- Charging and discharging cannot occur simultaneously.
- Electricity purchases and sales are the only costs and revenues.
- The final stored energy can be any physically feasible level. The initial energy can be sold, and the model assigns no value to energy left in the battery at the end of the period.

The model does not account for battery degradation, transaction fees, or other real-world operating costs.

Data handling limitations:

- Only the period covered by every market, starting and ending on a boundary shared by all markets, is optimized. Data outside it is discarded without a warning, so the profit refers to that period only.
- Market intervals are inferred from the median timestamp difference, not declared. Timestamps within the tolerance of the grid are snapped to it.
- Timestamps must form a continuous time axis. Local times spanning a daylight-saving change are rejected; use UTC or another continuous axis.
- Timestamp strings that are not ISO formatted are read as month-first (`MM/DD/YY HH:MM`), so `03/04/25 12:00` is 4 March.
- Prices are not checked for plausibility; negative or extreme prices are accepted.

## Development

CI (CircleCI) runs the following checks, which can also be run locally after `pip install -e ".[dev]"`:

```bash
ruff check .
mypy src
python -m pytest
```

## License

See [LICENSE](LICENSE) for licensing information.
