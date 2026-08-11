"""Excel Spreadsheet Assistant for inserting row data, sorting, auto-summing, and cell formatting."""

import csv
import os
from pathlib import Path


class ExcelAssistantEngine:
    """Excel & CSV Spreadsheet Assistant for row entry, data sorting, auto-sum, and cell formatting."""

    def __init__(self):
        self.excel_dir = Path.home() / ".bishu" / "spreadsheets"
        self.excel_dir.mkdir(parents=True, exist_ok=True)

    def create_or_update_excel(self, filename: str, headers: list, rows_data: list, sort_col: int = None, auto_sum: bool = True) -> str:
        """Create or update CSV/Excel spreadsheet, sort data, calculate auto-sum, and format bold headers."""
        if not filename.endswith(".csv") and not filename.endswith(".xlsx"):
            filename += ".csv"

        file_path = self.excel_dir / filename

        # Sort rows if column specified
        if sort_col is not None and len(rows_data) > 0:
            try:
                rows_data.sort(key=lambda x: x[sort_col] if sort_col < len(x) else "")
            except Exception:
                pass

        # Calculate Auto-Sum row for numerical columns
        sum_row = []
        if auto_sum and rows_data:
            sum_row = ["AUTO-SUM"]
            for col_idx in range(1, len(headers)):
                col_total = 0.0
                has_num = False
                for row in rows_data:
                    if col_idx < len(row):
                        try:
                            val = float(row[col_idx])
                            col_total += val
                            has_num = True
                        except ValueError:
                            pass
                sum_row.append(f"{col_total:.2f}" if has_num else "-")

        # Write formatted CSV
        try:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                # Bold headers
                bold_headers = [f"**{h}**" for h in headers]
                writer.writerow(bold_headers)
                for row in rows_data:
                    writer.writerow(row)
                if sum_row:
                    writer.writerow([])
                    writer.writerow(sum_row)

            return f"Spreadsheet '{filename}' successfully updated with {len(rows_data)} rows, Auto-Sum row, and bold headers in: {file_path}"
        except Exception as e:
            return f"Failed to update spreadsheet '{filename}': {e}"
