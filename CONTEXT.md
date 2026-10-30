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
- The final stored energy may be any physically feasible level. It does not need to equal the initial stored energy.
- Electricity purchases and sales are the only costs and revenues included. Battery degradation, transaction fees, and other operating costs are excluded.

The battery can allocate its available power across markets, provided that the combined commitments respect the battery's physical constraints. The same energy cannot be sold twice.

## Physical timeline and market commitments

Battery operation is represented on a half-hourly physical timeline, corresponding to the shortest interval in the example markets.

A commitment in a market must remain valid for that market's entire interval. Consequently, an hourly Market 2 commitment applies consistently to both half-hour timesteps within that hour.

The battery's shared power and energy constraints apply throughout the physical timeline. Although a market commitment may span multiple physical timesteps, its financial contribution must be counted only once for its full market interval.

## Trading objective

The objective is to maximize total trading profit over the modeled period.

Trading profit is the sum of electricity sales revenue minus electricity purchase costs across both markets. Each transaction's cash flow is calculated using its committed power, market price, and interval duration.

Because the final stored energy is unconstrained beyond physical feasibility, the model may use energy already stored at the beginning of the modeled period to generate revenue. The resulting profit therefore does not necessarily represent a complete cycle in which the battery returns to its initial energy level.

## Input data format

Input data is supplied as an Excel workbook (`.xlsx`) containing one worksheet per market.

Each market worksheet contains timestamps in its first column and prices in a column whose header ends with `Price [£/MWh]`. The first column does not need a header. Timestamps may be stored as Excel datetimes, ISO-formatted strings, or month-first strings in `MM/DD/YY HH:MM` format. Timestamps identify market intervals, and prices are expressed in £/MWh.

The supported example workbook is `data/cleaned_market_data.xlsx`. The repository also includes `data/market_data.xlsx`, which is the raw source data and is not a supported input. The example workbook contains:

| Worksheet          | Timestamp interval | Price column             |
| ------------------ | ------------------ | ------------------------ |
| `Half-hourly data` | 30 minutes         | `Market 1 Price [£/MWh]` |
| `Hourly data`      | 1 hour             | `Market 2 Price [£/MWh]` |

Other workbooks can be used as long as they follow the same general structure: market data is organized by worksheet, with timestamps and corresponding prices. The number of markets and their interval durations may vary.

Timestamps must identify the intended market intervals consistently. Differences in timestamp precision, missing observations, duplicate timestamps, and invalid prices can affect alignment and interpretation of the data.

Each market must have a consistent interval duration throughout the
modeled period. Timestamps should identify consecutive market intervals
at that frequency, without unexpected gaps or overlaps. Different markets
may use different interval durations.
