from battery_arbitrage.domain import MarketData

def parse_market_data(file_path: str) -> MarketData:
    """
    Parse market price data from an Excel workbook (.xlsx).

    The workbook contains one worksheet per market. The worksheet name is used
    as the market name. In each worksheet, the first column holds the
    timestamps that identify the market intervals, and the price column is the
    one whose header ends with "Price [£/MWh]". Fully blank rows are ignored.

    This function only converts the file into MarketData.

    Args:
        file_path (str): Path to the Excel workbook.

    Returns:
        MarketData: A dictionary mapping each market name (worksheet name) to a
            dictionary of interval timestamps and prices in £/MWh.

    Raises:
        FileNotFoundError: If file_path does not exist.
        ValueError: If the file cannot be read as an Excel workbook, or if a
            worksheet has no data rows, lacks a timestamp or price column,
            has more than one price column, contains a missing or unparseable
            timestamp or price, or contains duplicate timestamps. The message
            names the offending worksheet.
    """
    raise NotImplementedError("parse_market_data is not implemented yet")
    return {}
