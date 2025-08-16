from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from tkinter import messagebox
from typing import Any

import customtkinter as ctk
import pandas as pd
from balance_pipeline.gui.analysis import AnalysisController
from balance_pipeline.gui.theme import Theme


class ExportView(ctk.CTkFrame):  # type: ignore[misc]
    """A view for exporting data to files."""

    def __init__(self, master: Any, controller: AnalysisController) -> None:
        super().__init__(master, fg_color="transparent")
        self.controller = controller
        self._build_view()

    def _build_view(self) -> None:
        ctk.CTkLabel(self, text="💾 Export Data", font=Theme.font_h1).grid(
            row=0, column=0, padx=20, pady=(18, 6), sticky="w"
        )

        box = ctk.CTkFrame(self, corner_radius=10, fg_color=Theme.card)
        box.grid(row=1, column=0, padx=20, pady=8, sticky="ew")

        df = self.controller.get_dataframe()

        export_options: list[tuple[str, Callable[[], pd.DataFrame]]] = [
            ("📊 All Transactions", lambda: df),
            ("🔴 All Disputes", lambda: df[df["potential_refund"]]),
            (
                "📅 Last 30 Days",
                lambda: df[df["date"] >= datetime.now() - pd.Timedelta(days=30)],
            ),
            ("✅ All Refunds (Credits)", lambda: df[df["amount"] > 0]),
        ]

        for i, (label, data_func) in enumerate(export_options):
            button = ctk.CTkButton(
                box,
                text=label,
                anchor="w",
                command=lambda df_func=data_func, p=label.split(" ")[1].lower(): self._export_data(
                    df_func(), p
                ),
            )
            button.grid(
                row=i // 2, column=i % 2, padx=10, pady=8, sticky="ew"
            )

    def _export_data(self, data: pd.DataFrame, prefix: str) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = Path("output") / f"{prefix}_{timestamp}.xlsx"
        try:
            data.to_excel(filename, index=False, engine="openpyxl")
            messagebox.showinfo(
                "Export Successful", f"Exported {len(data)} records to:\n{filename}"
            )
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export data: {e}")
