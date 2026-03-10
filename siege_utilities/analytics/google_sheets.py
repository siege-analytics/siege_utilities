"""
Google Sheets write service.

Provides functions for creating spreadsheets, writing data, managing
tabs (sheets), and performing batch updates via the Sheets API v4.

All functions accept a ``GoogleWorkspaceClient`` for authentication.

Usage:
    from siege_utilities.analytics.google_workspace import GoogleWorkspaceClient
    from siege_utilities.analytics.google_sheets import (
        create_spreadsheet, write_dataframe, append_rows,
    )

    client = GoogleWorkspaceClient.from_service_account()
    spreadsheet_id = create_spreadsheet(client, "Q1 Report")
    write_dataframe(client, spreadsheet_id, df)
"""

import logging
from typing import Any, Dict, List, Optional, Union

log = logging.getLogger(__name__)

try:
    import pandas as pd
    _PANDAS_AVAILABLE = True
except ImportError:
    pd = None
    _PANDAS_AVAILABLE = False


def create_spreadsheet(
    client,
    title: str,
    sheet_names: Optional[List[str]] = None,
) -> str:
    """Create a new Google Spreadsheet and return its ID.

    Args:
        client: Authenticated GoogleWorkspaceClient.
        title: Title for the new spreadsheet.
        sheet_names: Optional list of sheet/tab names to create.
            If omitted, a single default "Sheet1" is created.

    Returns:
        The spreadsheet ID string.
    """
    body: Dict[str, Any] = {"properties": {"title": title}}
    if sheet_names:
        body["sheets"] = [
            {"properties": {"title": name}} for name in sheet_names
        ]

    result = client.sheets_service().spreadsheets().create(body=body).execute()
    spreadsheet_id = result["spreadsheetId"]
    log.info("Created spreadsheet %r (%s)", title, spreadsheet_id)
    return spreadsheet_id


def write_values(
    client,
    spreadsheet_id: str,
    range_: str,
    values: List[List[Any]],
    value_input_option: str = "USER_ENTERED",
) -> Dict[str, Any]:
    """Write a 2-D list of values to a range.

    Args:
        client: Authenticated GoogleWorkspaceClient.
        spreadsheet_id: Target spreadsheet ID.
        range_: A1 notation range (e.g. ``"Sheet1!A1:D10"``).
        values: Row-major list of lists.
        value_input_option: ``"RAW"`` or ``"USER_ENTERED"`` (default).

    Returns:
        The API response dict.
    """
    body = {"values": values}
    result = (
        client.sheets_service()
        .spreadsheets()
        .values()
        .update(
            spreadsheetId=spreadsheet_id,
            range=range_,
            valueInputOption=value_input_option,
            body=body,
        )
        .execute()
    )
    log.info(
        "Wrote %d cells to %s range %s",
        result.get("updatedCells", 0),
        spreadsheet_id,
        range_,
    )
    return result


def append_rows(
    client,
    spreadsheet_id: str,
    range_: str,
    values: List[List[Any]],
    value_input_option: str = "USER_ENTERED",
) -> Dict[str, Any]:
    """Append rows after existing data in a range.

    Args:
        client: Authenticated GoogleWorkspaceClient.
        spreadsheet_id: Target spreadsheet ID.
        range_: A1 notation range to search for a table (e.g. ``"Sheet1"``).
        values: Row-major list of lists to append.
        value_input_option: ``"RAW"`` or ``"USER_ENTERED"`` (default).

    Returns:
        The API response dict.
    """
    body = {"values": values}
    result = (
        client.sheets_service()
        .spreadsheets()
        .values()
        .append(
            spreadsheetId=spreadsheet_id,
            range=range_,
            valueInputOption=value_input_option,
            insertDataOption="INSERT_ROWS",
            body=body,
        )
        .execute()
    )
    log.info("Appended %d rows to %s", len(values), spreadsheet_id)
    return result


def read_values(
    client,
    spreadsheet_id: str,
    range_: str,
) -> List[List[Any]]:
    """Read values from a range.

    Returns:
        Row-major list of lists (may be ragged).
    """
    result = (
        client.sheets_service()
        .spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=range_)
        .execute()
    )
    return result.get("values", [])


def read_dataframe(
    client,
    spreadsheet_id: str,
    range_: str = "Sheet1",
    has_header: bool = True,
):
    """Read a range from a spreadsheet into a pandas DataFrame.

    Args:
        client: Authenticated GoogleWorkspaceClient.
        spreadsheet_id: Source spreadsheet ID.
        range_: A1 notation range (e.g. ``"Sheet1"`` or ``"Sheet1!A1:D100"``).
        has_header: If True, first row is used as column names.

    Returns:
        pandas DataFrame.
    """
    if not _PANDAS_AVAILABLE:
        raise ImportError("pandas is required. Install with: pip install siege-utilities[data]")

    values = read_values(client, spreadsheet_id, range_)
    if not values:
        return pd.DataFrame()

    if has_header and len(values) > 1:
        return pd.DataFrame(values[1:], columns=values[0])
    elif has_header:
        return pd.DataFrame(columns=values[0])
    else:
        return pd.DataFrame(values)


def get_spreadsheet_metadata(
    client,
    spreadsheet_id: str,
) -> Dict[str, Any]:
    """Fetch spreadsheet metadata (title, sheets, locale, etc.).

    Returns:
        The spreadsheet resource dict.
    """
    return (
        client.sheets_service()
        .spreadsheets()
        .get(spreadsheetId=spreadsheet_id)
        .execute()
    )


def copy_spreadsheet(
    client,
    spreadsheet_id: str,
    title: Optional[str] = None,
) -> str:
    """Copy an entire spreadsheet via the Drive API.

    Args:
        client: Authenticated GoogleWorkspaceClient.
        spreadsheet_id: Source spreadsheet ID.
        title: Title for the copy (default: "Copy of ...").

    Returns:
        The new spreadsheet ID.
    """
    return client.copy_file(spreadsheet_id, title)


def write_dataframe(
    client,
    spreadsheet_id: str,
    df,
    sheet_name: str = "Sheet1",
    include_header: bool = True,
    start_cell: str = "A1",
) -> Dict[str, Any]:
    """Write a pandas DataFrame to a sheet.

    Args:
        client: Authenticated GoogleWorkspaceClient.
        spreadsheet_id: Target spreadsheet ID.
        df: pandas DataFrame to write.
        sheet_name: Tab name (default ``"Sheet1"``).
        include_header: Whether to include column names as first row.
        start_cell: Top-left cell (default ``"A1"``).

    Returns:
        The API response dict.
    """
    if not _PANDAS_AVAILABLE:
        raise ImportError("pandas is required. Install with: pip install siege-utilities[data]")

    values = []
    if include_header:
        values.append([str(c) for c in df.columns.tolist()])

    for _, row in df.iterrows():
        values.append([
            v if not _PANDAS_AVAILABLE or not pd.isna(v) else ""
            for v in row.tolist()
        ])

    range_ = f"{sheet_name}!{start_cell}"
    return write_values(client, spreadsheet_id, range_, values)


def add_sheet(
    client,
    spreadsheet_id: str,
    title: str,
) -> int:
    """Add a new tab/sheet to an existing spreadsheet.

    Returns:
        The new sheet ID (integer).
    """
    body = {
        "requests": [
            {"addSheet": {"properties": {"title": title}}}
        ]
    }
    result = (
        client.sheets_service()
        .spreadsheets()
        .batchUpdate(spreadsheetId=spreadsheet_id, body=body)
        .execute()
    )
    sheet_id = result["replies"][0]["addSheet"]["properties"]["sheetId"]
    log.info("Added sheet %r (id=%d) to %s", title, sheet_id, spreadsheet_id)
    return sheet_id


def batch_update(
    client,
    spreadsheet_id: str,
    requests: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Execute a batch of Sheets API requests.

    Delegates to :py:meth:`GoogleWorkspaceClient.batch_update_spreadsheet`.

    Args:
        client: Authenticated GoogleWorkspaceClient.
        spreadsheet_id: Target spreadsheet ID.
        requests: List of request dicts per the Sheets API batchUpdate spec.

    Returns:
        The API response dict.
    """
    return client.batch_update_spreadsheet(spreadsheet_id, requests)
