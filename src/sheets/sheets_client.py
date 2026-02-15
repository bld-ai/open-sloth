"""
Generic Google Sheets client with dynamic sheet access.
"""

import re
from typing import List, Dict, Optional
import gspread
from google.oauth2.service_account import Credentials
from loguru import logger

from src.config.settings import settings
from src.utils.errors import sheets_retry, SheetsConnectionError


class SheetsClient:
    """Generic client for Google Sheets with dynamic sheet access."""

    def __init__(self):
        self.service_account_email = None
        self.spreadsheet = None
        self.client = self._auth()

    def _auth(self) -> gspread.Client:
        """Authenticate with Google Sheets."""
        try:
            creds = Credentials.from_service_account_file(
                settings.google_credentials_file,
                scopes=[
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive",
                ],
            )
            self.service_account_email = creds.service_account_email
            return gspread.authorize(creds)
        except Exception as e:
            raise SheetsConnectionError(f"Auth failed: {e}")

    def _extract_sheet_id(self, url_or_id: str) -> str:
        """Extract sheet ID from URL or return as-is if already an ID."""

        match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url_or_id)
        if match:
            return match.group(1)
        return url_or_id

    def _connect(self, sheet_id: Optional[str] = None):
        """Connect to a spreadsheet."""
        if sheet_id:
            target_id = self._extract_sheet_id(sheet_id)
            self.spreadsheet = self.client.open_by_key(target_id)
            logger.info(f"Connected to: {self.spreadsheet.title}")
        elif settings.google_sheet_id:
            self.spreadsheet = self.client.open_by_key(settings.google_sheet_id)
            logger.info(f"Connected to default: {self.spreadsheet.title}")
        elif not self.spreadsheet:
            raise SheetsConnectionError("No sheet specified and no default configured")

    def _get_sheet(self, name: Optional[str] = None):
        """Get worksheet by name or first sheet."""
        if not self.spreadsheet:
            self._connect()
        if name:
            return self.spreadsheet.worksheet(name)
        return self.spreadsheet.get_worksheet(0)

    @sheets_retry
    def list_all_accessible_sheets(self) -> List[Dict]:
        """List all spreadsheets shared with the service account (requires Drive API)."""
        try:
            all_sheets = self.client.openall()
            return [
                {"id": sheet.id, "title": sheet.title, "url": sheet.url}
                for sheet in all_sheets
            ]
        except Exception as e:
            logger.warning(f"Cannot list sheets (Drive API may not be enabled): {e}")
            return [
                {
                    "error": "Enable Google Drive API to list all sheets, or share a sheet URL directly"
                }
            ]

    @sheets_retry
    def open_sheet(self, url_or_id: str) -> Dict:
        """Open a spreadsheet by URL or ID."""
        sheet_id = self._extract_sheet_id(url_or_id)
        try:
            self._connect(sheet_id)
            return {
                "id": self.spreadsheet.id,
                "title": self.spreadsheet.title,
                "url": self.spreadsheet.url,
                "worksheets": [ws.title for ws in self.spreadsheet.worksheets()],
                "service_account": self.service_account_email,
            }
        except gspread.exceptions.SpreadsheetNotFound:
            return {
                "error": f"Sheet not found. Share it with: {self.service_account_email}"
            }
        except gspread.exceptions.APIError as e:
            if "403" in str(e):
                return {
                    "error": f"No access. Share the sheet with: {self.service_account_email}"
                }
            raise

    def get_active_sheet_info(self) -> Optional[Dict]:
        """Get info about currently active spreadsheet."""
        if not self.spreadsheet:
            return None
        return {
            "id": self.spreadsheet.id,
            "title": self.spreadsheet.title,
            "url": self.spreadsheet.url,
            "worksheets": [ws.title for ws in self.spreadsheet.worksheets()],
        }

    def get_sheet_structure(self) -> Optional[Dict]:
        """Get lightweight structure: tab names and headers only (1 API call per tab)."""
        if not self.spreadsheet:
            try:
                self._connect()
            except Exception:
                return None
        if not self.spreadsheet:
            return None

        structure = {
            "title": self.spreadsheet.title,
            "tabs": {}
        }
        for ws in self.spreadsheet.worksheets():
            try:
                headers = ws.row_values(1)
                if not headers:
                    continue
                structure["tabs"][ws.title] = {
                    "headers": headers,
                    "row_count": ws.row_count - 1,
                }
            except Exception as e:
                logger.debug(f"Could not read headers for tab '{ws.title}': {e}")
                continue
        return structure

    @sheets_retry
    def list_sheets(self) -> List[Dict]:
        """List all worksheets in the active spreadsheet."""
        if not self.spreadsheet:
            self._connect()
        return [
            {"name": ws.title, "rows": ws.row_count}
            for ws in self.spreadsheet.worksheets()
        ]

    @sheets_retry
    def read_sheet(self, sheet_name: Optional[str] = None) -> Dict:
        """Read all rows from a worksheet, including headers."""
        ws = self._get_sheet(sheet_name)
        headers = ws.row_values(1)
        records = ws.get_all_records()
        return {"headers": headers, "rows": records}

    @sheets_retry
    def add_row(self, data: Dict[str, str], sheet_name: Optional[str] = None):
        """Add a row to a worksheet. Maps data keys to sheet headers case-insensitively."""
        ws = self._get_sheet(sheet_name)
        headers = ws.row_values(1)
        logger.debug(f"Sheet headers: {headers}")
        logger.debug(f"Data to add: {data}")

        data_lower = {k.lower().strip(): v for k, v in data.items()}
        row = [data_lower.get(h.lower().strip(), "") for h in headers]

        if not any(row):
            logger.warning(
                f"Could not map data to headers. Headers: {headers}, Data keys: {list(data.keys())}"
            )
            return {"error": f"Could not map data. Sheet headers are: {headers}"}

        ws.append_row(row)
        logger.info(f"Added row to {sheet_name or 'default'}: {row}")
        return {"success": True, "row_added": row, "headers": headers}

    @sheets_retry
    def update_cell(
        self, row: int, column: str, value: str, sheet_name: Optional[str] = None
    ):
        """Update a cell. Column matching is case-insensitive."""
        ws = self._get_sheet(sheet_name)
        headers = ws.row_values(1)
        headers_lower = [h.lower().strip() for h in headers]
        col_lower = column.lower().strip()
        if col_lower not in headers_lower:
            raise ValueError(f"Column '{column}' not found. Available: {headers}")
        col_idx = headers_lower.index(col_lower) + 1
        ws.update_cell(row + 1, col_idx, value)
        logger.info(f"Updated [{row}, {headers[col_idx - 1]}] = {value}")

    @sheets_retry
    def delete_row(self, row: int, sheet_name: Optional[str] = None):
        """Delete a row."""
        ws = self._get_sheet(sheet_name)
        ws.delete_rows(row + 1)
        logger.info(f"Deleted row {row}")

    @sheets_retry
    def search(self, query: str) -> List[Dict]:
        """Search across all worksheets in active spreadsheet."""
        if not self.spreadsheet:
            self._connect()
        results = []
        q = query.lower()
        for ws in self.spreadsheet.worksheets():
            try:
                for idx, row in enumerate(ws.get_all_records(), 1):
                    if any(q in str(v).lower() for v in row.values()):
                        results.append({"sheet": ws.title, "row": idx, "data": row})
            except Exception as e:
                logger.debug(f"Skipping worksheet '{ws.title}' during search: {e}")
                continue
        return results

    def health_check(self) -> bool:
        """Check connection using Sheets API only (no Drive API needed)."""
        try:

            if settings.google_sheet_id:
                self._connect()
                return True

            return self.service_account_email is not None
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


sheets_client = SheetsClient()
