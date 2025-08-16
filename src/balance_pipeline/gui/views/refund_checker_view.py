from __future__ import annotations

from tkinter import messagebox
from typing import Any

import customtkinter as ctk
import pandas as pd
from balance_pipeline.gui.analysis import AnalysisController
from balance_pipeline.gui.theme import Theme


class RefundCheckerView(ctk.CTkFrame):  # type: ignore[misc]
    """A view for checking if a specific charge was refunded."""

    def __init__(self, master: Any, controller: AnalysisController) -> None:
        super().__init__(master, fg_color="transparent")
        self.controller = controller
        self._build_view()

    def _build_view(self) -> None:
        ctk.CTkLabel(self, text="✅ Check Refund Status", font=Theme.font_h1).grid(
            row=0, column=0, padx=20, pady=(18, 6), sticky="w"
        )

        form = ctk.CTkFrame(self, corner_radius=10, fg_color=Theme.card)
        form.grid(row=1, column=0, padx=20, pady=6, sticky="ew")

        self.merchant_entry = ctk.CTkEntry(form, placeholder_text="Merchant", width=220)
        self.merchant_entry.grid(row=0, column=0, padx=8, pady=8)
        self.amount_entry = ctk.CTkEntry(
            form, placeholder_text="Charge Amount", width=140
        )
        self.amount_entry.grid(row=0, column=1, padx=8, pady=8)
        self.date_entry = ctk.CTkEntry(form, placeholder_text="YYYY-MM-DD", width=160)
        self.date_entry.grid(row=0, column=2, padx=8, pady=8)
        ctk.CTkButton(
            form, text="Check", command=self._check_refund_status, width=140
        ).grid(row=0, column=3, padx=8, pady=8)

        self.results_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.results_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")

    def _check_refund_status(self) -> None:
        merchant = self.merchant_entry.get().strip()
        amount_str = self.amount_entry.get().strip()
        date_str = self.date_entry.get().strip()

        if not (merchant and amount_str and date_str):
            messagebox.showwarning("Input Error", "Please fill all fields.")
            return
        try:
            amount = float(amount_str)
            charge_date = pd.to_datetime(date_str)
        except ValueError:
            messagebox.showerror("Input Error", "Invalid amount or date format.")
            return

        for widget in self.results_frame.winfo_children():
            widget.destroy()

        hits = self.controller.check_refund_status(merchant, amount, charge_date)

        box = ctk.CTkFrame(self.results_frame, corner_radius=10, fg_color=Theme.card)
        box.pack(fill="x", padx=12, pady=12)

        ctk.CTkLabel(
            box,
            text=f"Original Charge: {merchant} - ${amount:,.2f} on {date_str}",
            font=Theme.font_bold,
        ).grid(row=0, column=0, padx=10, pady=(10, 4), sticky="w")

        if not hits.empty:
            ctk.CTkLabel(
                box,
                text="✅ REFUND FOUND",
                text_color=Theme.success,
                font=Theme.font_h2,
            ).grid(row=1, column=0, padx=10, pady=4, sticky="w")
            for _, row in hits.iterrows():
                ctk.CTkLabel(
                    box, text=f"  - 📅 {row['date']:%Y-%m-%d} - ${row['amount']:,.2f}"
                ).grid(row=box.grid_size()[0], column=0, padx=22, pady=2, sticky="w")
        else:
            ctk.CTkLabel(
                box,
                text="❌ NO REFUND FOUND",
                text_color=Theme.danger,
                font=Theme.font_h2,
            ).grid(row=1, column=0, padx=10, pady=4, sticky="w")
            ctk.CTkLabel(
                box,
                text="No matching refund found within 60 days of the charge.",
                text_color=Theme.text_secondary,
            ).grid(row=2, column=0, padx=10, pady=(0, 10), sticky="w")
