from __future__ import annotations

from tkinter import messagebox
from typing import Any

import customtkinter as ctk
from balance_pipeline.gui.analysis import AnalysisController
from balance_pipeline.gui.theme import Theme
from balance_pipeline.gui.widgets.data_table import DataTable


class RefundSearchView(ctk.CTkFrame):  # type: ignore[misc]
    """A view for finding refunds by merchant."""

    def __init__(self, master: Any, controller: AnalysisController) -> None:
        super().__init__(master, fg_color="transparent")
        self.controller = controller

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_view()

    def _build_view(self) -> None:
        ctk.CTkLabel(
            self, text="🔍 Find Refunds by Merchant", font=Theme.font_h1
        ).grid(row=0, column=0, padx=20, pady=(18, 6), sticky="w")

        form = ctk.CTkFrame(self, corner_radius=10, fg_color=Theme.card)
        form.grid(row=1, column=0, padx=20, pady=6, sticky="ew")

        ctk.CTkLabel(form, text="Merchant:").grid(
            row=0, column=0, padx=10, pady=10, sticky="w"
        )
        self.merchant_entry = ctk.CTkEntry(
            form, placeholder_text="e.g., Amazon", width=260
        )
        self.merchant_entry.grid(row=0, column=1, padx=6, pady=10)

        ctk.CTkLabel(form, text="Days back:").grid(
            row=0, column=2, padx=10, pady=10, sticky="w"
        )
        self.days_entry = ctk.CTkEntry(form, width=90)
        self.days_entry.insert(0, "90")
        self.days_entry.grid(row=0, column=3, padx=6, pady=10)

        ctk.CTkButton(
            form, text="Search", command=self._search_refunds, width=120
        ).grid(row=0, column=4, padx=10, pady=10)

        self.results_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.results_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.results_frame.grid_columnconfigure(0, weight=1)
        self.results_frame.grid_rowconfigure(1, weight=1)

    def _search_refunds(self) -> None:
        merchant = self.merchant_entry.get().strip()
        if not merchant:
            messagebox.showwarning("Input Error", "Please enter a merchant name.")
            return

        days_str = self.days_entry.get().strip()
        try:
            days = int(days_str) if days_str else 90
        except ValueError:
            messagebox.showwarning("Input Error", "Days back must be a number.")
            return

        for widget in self.results_frame.winfo_children():
            widget.destroy()

        results_df = self.controller.find_refunds_by_merchant(merchant, days)

        if not results_df.empty:
            total_credits = results_df[results_df["amount"] > 0]["amount"].sum()

            ctk.CTkLabel(
                self.results_frame,
                text=f"Found {len(results_df)} potential refunds/credits for '{merchant}'",
                font=Theme.font_h2,
            ).grid(row=0, column=0, padx=14, pady=(14, 6), sticky="w")

            ctk.CTkLabel(
                self.results_frame,
                text=f"Total credits: ${total_credits:,.2f}",
                text_color=Theme.success,
                font=Theme.font_bold,
            ).grid(row=1, column=0, padx=14, sticky="w")

            table_container = ctk.CTkFrame(self.results_frame, fg_color="transparent")
            table_container.grid(row=2, column=0, padx=0, pady=8, sticky="nsew")
            self.results_frame.grid_rowconfigure(2, weight=1)

            table = DataTable(table_container, results_df)
            table.pack(expand=True, fill="both")

        else:
            ctk.CTkLabel(
                self.results_frame,
                text=f"No refunds found for '{merchant}' in the last {days} days.",
                text_color=Theme.text_secondary,
            ).grid(row=0, column=0, padx=14, pady=14, sticky="w")
