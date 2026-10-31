# Agent Guidelines

## General Principles

- Keep the implementation simple and avoid unnecessary abstractions.
- Prefer readable, maintainable code over clever solutions.
- Follow the domain assumptions documented in `CONTEXT.md`.
- Do not introduce requirements or assumptions that are not documented or agreed upon.

## Architecture

Keep responsibilities separate while avoiding unnecessary layers.

- **Parsing:** Read input files and extract market data. Must not depend on optimization logic.
- **Validation:** Check input data for structural and data-quality issues and infer market intervals. Must not depend on optimization logic.
- **Time alignment:** Align market data with different interval durations on a common physical timeline. Must not depend on optimization logic.
- **Period selection:** Restrict an aligned timeline to a requested time window on shared market boundaries. Must not depend on optimization logic.
- **Optimization:** Model the battery's decisions and constraints, and calculate the optimal dispatch.
- **Reporting:** Present optimization results as report rows. Must not depend on Pyomo or other solver-specific details.
- **CSV export:** Write reports to files. Must not depend on Pyomo or other solver-specific details.
- **Pipeline and CLI:** `pipeline.py` runs the stages in order and `cli.py` exposes them on the command line. These are the only modules that may depend on several stages.

Keep dependencies flowing between these responsibilities through explicit interfaces. Parsing, validation, time alignment, period selection, reporting, and export should remain independent of the optimizer's internal implementation.

## Interfaces

Shared data structures are defined in `src/battery_arbitrage/domain.py` as frozen dataclasses and type aliases. Stages communicate through these types and do not depend on each other's internals.

Discuss and agree on an approach before changing module APIs or shared data structures.

## Quality checks

Before submitting changes, run the checks that CI runs: `ruff check .`, `mypy src` and `python -m pytest`. Keep docstrings and the documentation (`README.md`, `CONTEXT.md`) in line with the behavior of the code.

## Scope

- Avoid overengineering and unnecessary dependencies.
- Do not add features beyond the project's agreed scope without discussion.
- Keep the project easy to understand, run, and review.
