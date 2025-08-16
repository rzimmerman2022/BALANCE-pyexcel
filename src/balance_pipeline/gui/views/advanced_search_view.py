from __future__ import annotations

from typing import Any

import customtkinter as ctk
from balance_pipeline.gui.analysis import AnalysisController
from balance_pipeline.gui.theme import Theme
from balance_pipeline.gui.widgets.data_table import DataTable


class AdvancedSearchView(ctk.CTkFrame):  # type: ignore[misc]
    """A view for performing advanced searches on the transaction data."""

    def __init__(self, master: Any, controller: AnalysisController) -> None:
        super().__init__(master, fg_color="transparent")
        self.controller = controller

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_view()

    def _build_view(self) -> None:
        ctk.CTkLabel(self, text="🔎 Advanced Search", font=Theme.font_h1).grid(
            row=0, column=0, padx=20, pady=(18, 6), sticky="w"
        )

        form = ctk.CTkFrame(self, corner_radius=10, fg_color=Theme.card)
        form.grid(row=1, column=0, padx=20, pady=6, sticky="ew")

        self.start_date_entry = ctk.CTkEntry(
            form, placeholder_text="Start (YYYY-MM-DD)"
        )
        self.start_date_entry.grid(row=0, column=0, padx=8, pady=8)
        self.end_date_entry = ctk.CTkEntry(form, placeholder_text="End (YYYY-MM-DD)")
        self.end_date_entry.grid(row=0, column=1, padx=8, pady=8)
        self.min_amount_entry = ctk.CTkEntry(form, placeholder_text="Min amount")
        self.min_amount_entry.grid(row=0, column=2, padx=8, pady=8)
        self.max_amount_entry = ctk.CTkEntry(form, placeholder_text="Max amount")
        self.max_amount_entry.grid(row=0, column=3, padx=8, pady=8)
        self.merchant_entry = ctk.CTkEntry(form, placeholder_text="Merchant contains")
        self.merchant_entry.grid(row=0, column=4, padx=8, pady=8)
        self.disputes_only_check = ctk.CTkCheckBox(
            form, text="Only potential disputes"
        )
        self.disputes_only_check.grid(row=0, column=5, padx=8, pady=8)
        ctk.CTkButton(form, text="Search", command=self._perform_search).grid(
            row=0, column=6, padx=8, pady=8
        )

        self.results_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.results_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.results_frame.grid_columnconfigure(0, weight=1)
        self.results_frame.grid_rowconfigure(1, weight=1)

    def _perform_search(self) -> None:
        params = {
            "start_date": self.start_date_entry.get().strip(),
            "end_date": self.end_date_entry.get().strip(),
            "min_amount": self.min_amount_entry.get().strip(),
            "max_amount": self.max_amount_entry.get().strip(),
            "merchant": self.merchant_entry.get().strip(),
            "only_disputes": self.disputes_only_check.get(),
        }

        for widget in self.results_frame.winfo_children():
            widget.destroy()

        results_df = self.controller.perform_advanced_search(params)

        if not results_df.empty:
            ctk.CTkLabel(
                self.results_frame,
                text=f"Found {len(results_df)} matching transactions",
                font=Theme.font_h2,
            ).grid(row=0, column=0, padx=14, pady=(14, 6), sticky="w")

            table = DataTable(self.results_frame, results_df)
            table.grid(row=1, column=0, sticky="nsew")

        else:
            ctk.CTkLabel(
                self.results_frame,
                text="No transactions match your search criteria.",
                text_color=Theme.text_secondary,
            ).grid(row=0, column=0, padx=14, pady=14, sticky="w")
