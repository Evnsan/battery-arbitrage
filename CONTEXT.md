# Battery Arbitrage: Domain Context

## Overview

Battery arbitrage consists of buying electricity when prices are low, storing the energy, and selling it when prices are higher. When multiple electricity markets are available, a battery can allocate its charging and discharging capacity across them to maximize its trading profit.

This model represents a battery participating in one or more wholesale electricity markets. It assumes the battery is a price taker, meaning its decisions do not affect market prices.

The model is intentionally simplified and does not represent all the constraints and costs of real-world electricity trading.

## Electricity markets

Each market has its own electricity prices and trading intervals. Prices are expressed in pounds per megawatt-hour (£/MWh).

Markets may use different interval durations. In the example dataset:

- **Market 1:** half-hourly prices, with a duration of 0.5 hours per interval.
- **Market 2:** hourly prices, with a duration of 1 hour per interval.

A market commitment specifies the power allocated to charging or discharging for the entire interval. The committed power remains constant throughout that interval.

The energy traded during an interval is the committed power multiplied by the interval duration. The corresponding cash flow is the energy traded multiplied by the market price.

For example, discharging at 5 MW for half an hour at £50/MWh generates £125 in revenue:

$$
5\,\text{MW} \times 0.5\,\text{h} \times 50\,\frac{£}{\text{MWh}} = £125
$$

Charging at the same power and price incurs a cost of £125.

## Battery model and assumptions

The battery has a limited charging rate, discharging rate, and energy storage capacity. Its stored energy changes as it charges and discharges.

The model uses the following simplified battery configuration:

| Parameter                 | Value | Unit |
| ------------------------- | ----: | ---- |
| Maximum charging power    |     5 | MW   |
| Maximum discharging power |     5 | MW   |
| Energy storage capacity   |    10 | MWh  |
| Initial stored energy     |     2 | MWh  |

The following assumptions apply:

- Charging and discharging are mutually exclusive at each physical timestep, across all markets.
- The battery's aggregate charging or discharging power cannot exceed its corresponding power limit.
- Stored energy cannot fall below zero or exceed the battery's capacity.
- The battery cannot discharge energy it does not have or charge beyond its available storage capacity.
- Charging and discharging are modeled with no energy losses.
- All prices over the modeled period are known in advance (perfect foresight). All markets are optimized jointly, as if they cleared at the same time.
- The final stored energy may be any physically feasible level. It does not need to equal the initial stored energy.
- Electricity purchases and sales are the only costs and revenues included. Battery degradation, transaction fees, and other operating costs are excluded.

The battery can allocate its available power across markets, provided that the combined commitments respect the battery's physical constraints. The same energy cannot be sold twice.

## Physical timeline and market commitments

Battery operation is represented on a common physical timeline whose timestep is the greatest common divisor of the market intervals. In the example dataset, the 30-minute and 1-hour intervals give a half-hourly physical timeline.

A commitment in a market must remain valid for that market's entire interval. Consequently, an hourly Market 2 commitment applies consistently to both half-hour timesteps within that hour.

The battery's shared power and energy constraints apply throughout the physical timeline. Although a market commitment may span multiple physical timesteps, its financial contribution must be counted only once for its full market interval.

### Alignment of market data

The prices of a market are a step function: a price applies from its timestamp (the **start** of the interval) until the next timestamp. When the physical timestep is shorter than a market's interval, the price is repeated on every timestep the interval covers, so the price is constant within each market interval.

Alignment works as follows:

- Each market's interval is **inferred** as the median difference between its consecutive timestamps. Every difference must be within the timestamp tolerance (default 1000 ms) of that median.
- Timestamps are snapped to a grid anchored at the earliest timestamp across all markets. A timestamp that deviates from the grid by more than the tolerance is rejected.
- The timeline contains only the period covered by **every** market, starting and ending on a boundary shared by all markets and containing whole intervals only. Data outside this period is discarded without a warning, so the modeled period can be shorter than the data. If no such period exists, an error is raised.
- A requested period (`--start-time`, `--end-time`) is applied after alignment as the half-open window `[start, end)`. Each bound must coincide with an interval boundary of every market, and bounds outside the coverage are clipped.

## Trading objective

The objective is to maximize total trading profit over the modeled period.

Trading profit is the sum of electricity sales revenue minus electricity purchase costs across both markets. Each transaction's cash flow is calculated using its committed power, market price, and interval duration.

Because the final stored energy is unconstrained beyond physical feasibility, the model may use energy already stored at the beginning of the modeled period to generate revenue. The resulting profit therefore does not necessarily represent a complete cycle in which the battery returns to its initial energy level.

### Optimization model

The problem is a mixed-integer linear program built with Pyomo and solved with HiGHS:

- Charging and discharging power are decision variables per **market interval**, so a commitment is one variable shared by all the physical timesteps it covers.
- The stored energy at each timestep follows from the aggregate charging and discharging power of all markets.
- A binary operating-mode variable per physical timestep makes charging and discharging mutually exclusive across all markets. Without it, the battery could buy in one market and sell in another during the same timestep for a positive cash flow and no net energy change.
- Solver settings: time limit of 300 seconds and relative MIP gap of 2%. The reported solution can therefore be up to about 2% below the true optimum, and a run that does not finish within the time limit fails instead of returning the best solution found.
- The reported total profit is recomputed from the extracted schedule as the sum of `(discharge - charge) × price × timestep` over all markets and timesteps.

## Input data format

Input data is supplied as an Excel workbook (`.xlsx`) containing one worksheet per market.

Every worksheet is treated as a market, named after the worksheet, so the workbook should not contain other sheets. Each market worksheet contains timestamps in its first column and prices in a column whose header ends with `Price [£/MWh]`. The header is the first non-blank row, exactly one column may match, and the first column does not need a header. Fully blank rows are ignored. Timestamps may be stored as Excel datetimes, ISO-formatted strings, or month-first strings in `MM/DD/YY HH:MM` format; strings that are not valid ISO are always read as month-first (`03/04/25 12:00` is 4 March). Timestamps identify the **start** of market intervals, and prices are expressed in £/MWh.

The supported example workbook is `data/cleaned_market_data.xlsx`. The repository also includes `data/market_data.xlsx`, which is the raw source data and is not a supported input. The example workbook covers 1 January 2018 to 31 December 2020 (52,608 half-hourly prices and 26,304 hourly prices; the hourly timestamps carry a small sub-second jitter that the alignment tolerance absorbs) and contains:

| Worksheet          | Timestamp interval | Price column             |
| ------------------ | ------------------ | ------------------------ |
| `Half-hourly data` | 30 minutes         | `Market 1 Price [£/MWh]` |
| `Hourly data`      | 1 hour             | `Market 2 Price [£/MWh]` |

Other workbooks can be used as long as they follow the same general structure: market data is organized by worksheet, with timestamps and corresponding prices. The number of markets and their interval durations may vary.

Timestamps must identify the intended market intervals consistently. Data labelled by interval end would be shifted by one interval, and the model cannot detect this.

Each market must have a consistent interval duration throughout the
modeled period. Timestamps should identify consecutive market intervals
at that frequency, without gaps or overlaps. Different markets
may use different interval durations.

The following problems are rejected with an error that names the worksheet or market: a missing, unparseable or duplicate timestamp; a missing, unparseable, boolean or non-finite price; a worksheet without data or without exactly one price column; fewer than two observations; non-uniform intervals (including any gap); timestamps that are not aligned to the common grid; and markets with no common coverage. Prices are not checked for plausibility, so negative or extreme prices are accepted.

Timestamps should form a continuous time axis. Local times spanning a daylight-saving change are rejected (the repeated hour creates duplicate timestamps, and the skipped hour creates a gap), so such data should be supplied in UTC. Naive and timezone-aware timestamps should not be mixed; time bounds given on the command line must have the same timezone awareness as the data.

## Reports

The optimization result is converted into two reports at the resolution of the physical timeline:

- **Market dispatch:** one row per timestamp and market with the price, the charging and discharging power, and the cash flow `(discharge - charge) × price × timestep` of that row. A commitment in a market whose interval spans several timesteps appears on several rows with the same power, each carrying its share of the cash flow.
- **Battery operation:** one row per timestamp with the charging and discharging power and cash flow summed across markets, the stored energy at the **start** of the timestep, and the cumulative cash flow.

Both reports are exported to CSV with ISO 8601 timestamps and unrounded values. The CSV files do not contain the total profit, the modeled period or the battery parameters; the total profit is printed by the command-line interface.

## Battery configuration

The default battery configuration of the table above is used by the command-line interface, which has no options to change it. A different `BatteryConfig` can be passed when calling `battery_arbitrage.pipeline.run_optimization` from Python. Power and capacity must not be negative, and the initial energy must be between zero and the storage capacity.
