# Agent Guidelines

## General Principles

- Keep the implementation simple and avoid unnecessary abstractions.
- Prefer readable, maintainable code over clever solutions.
- Follow the domain assumptions documented in `CONTEXT.md`.
- Do not introduce requirements or assumptions that are not documented or agreed upon.

## Architecture

Keep responsibilities separate while avoiding unnecessary layers.

- **Parsing:** Read input files and extract market data. Must not depend on optimization logic.
- **Validation:** Check input data for structural and data-quality issues. Must not depend on optimization logic.
- **Time alignment:** Align market data with different interval durations on a common physical timeline. Must not depend on optimization logic.
- **Optimization:** Model the battery's decisions and constraints, and calculate the optimal dispatch.
- **Output and reporting:** Present optimization results and generate reports. Must not depend on Pyomo or other solver-specific details.

Keep dependencies flowing between these responsibilities through explicit interfaces. Parsing, validation, time alignment, and reporting should remain independent of the optimizer's internal implementation.

## Interfaces

Module APIs and shared data structures have not yet been finalized.

Before defining interfaces or introducing shared data structures, discuss the options and agree on an approach. Dataclasses may be appropriate, but do not introduce them prematurely.

## Scope

- Avoid overengineering and unnecessary dependencies.
- Do not add features beyond the project's agreed scope without discussion.
- Keep the project easy to understand, run, and review.
