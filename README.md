# Battery Arbitrage

A Python project for modeling battery dispatch and optimizing electricity trading profit across multiple wholesale markets with different trading intervals.

The model treats the battery as a price taker and uses historical market prices to determine when to charge and discharge while respecting its physical constraints.

## Features

- Load market prices from an Excel workbook, with one worksheet per market.
- Support markets with different trading interval durations.
- Optimize battery charging and discharging decisions across markets.
- Enforce battery power limits, storage capacity, and charge/discharge exclusivity.
- Generate reports of battery operation, market dispatch, and cumulative trading cash flow.

## How it works

The model uses market prices to determine how the battery should allocate its charging and discharging capacity over the selected period.

The battery can purchase electricity when prices are low and sell it when prices are higher. Its decisions must respect its available stored energy, storage capacity, and power limits. When participating in multiple markets, the model must also account for their different trading intervals and avoid selling the same energy twice.

The optimization objective is to maximize trading profit, calculated as electricity sales revenue minus electricity purchase costs.

See [CONTEXT.md](CONTEXT.md) for the domain assumptions, battery parameters, and input data format.

## Requirements

- Python [version to be defined]
- An optimization solver supported by the project

## Installation

Clone the repository and install the project dependencies:

```bash
git clone <repository-url>
cd battery-arbitrage

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .
```

The installation instructions may change depending on the final packaging and solver configuration.

## Input data

The model accepts an Excel workbook (`.xlsx`) containing market data organized by worksheet. Each worksheet must contain timestamps and the corresponding market prices in £/MWh.

The supported example input is `data/cleaned_market_data.xlsx`. The repository also includes `data/market_data.xlsx`, which is the raw source data and is not a supported input.

The example dataset contains:

| Worksheet          | Market interval |
| ------------------ | --------------- |
| `Half-hourly data` | 30 minutes      |
| `Hourly data`      | 1 hour          |

Each market must have a consistent interval duration, with timestamps identifying consecutive intervals throughout the modeled period.

See [CONTEXT.md](CONTEXT.md) for further details.

## Usage

Run the optimization and write both CSV reports with:

```bash
# Run the optimization using the example dataset
battery-arbitrage --input data/cleaned_market_data.xlsx

# Choose custom paths for the CSV reports
battery-arbitrage \
  --input data/cleaned_market_data.xlsx \
  --dispatch-csv results/market-dispatch.csv \
  --operation-csv results/battery-operation.csv \
  --start-time 2025-01-01T00:00:00 \
  --end-time 2025-02-01T00:00:00
```

By default, the command writes `results/dispatch.csv` and
`results/operation.csv`. Use `--tolerance-millis` to change the timestamp
alignment tolerance; its default is 1000 milliseconds. Use `--verbosity` with
`DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL` to set log verbosity; the
default is `INFO`. The options also have short forms: `-i`, `-d`, `-o`, `-t`,
`-v`, `-s`, and `-e`, respectively. Time bounds use an inclusive start and
exclusive end in ISO format. Each bound must align to a boundary shared by all
markets. The battery starts the selected period at its configured initial
energy.

The command prints the output paths and total profit after the reports are
written.

## Results

The project is intended to provide:

- **Battery operation report:** charging and discharging power, stored energy, and cumulative trading cash flow over time.
- **Market dispatch report:** charging and discharging commitments allocated to each market.
- **Optimization summary:** the resulting trading profit and relevant solver status.

Results represent the modeled trading profit under the project's assumptions, not a forecast or guarantee of real-world returns.

## Limitations

This is a simplified battery arbitrage model. It assumes:

- The battery does not influence market prices.
- Charging and discharging have 100% efficiency.
- Charging and discharging cannot occur simultaneously.
- Electricity purchases and sales are the only costs and revenues.
- The final stored energy can be any physically feasible level.

The model does not account for battery degradation, transaction fees, or other real-world operating costs.

## License

See [LICENSE](LICENSE) for licensing information.
