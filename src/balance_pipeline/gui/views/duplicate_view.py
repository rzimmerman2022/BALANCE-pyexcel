from __future__ import annotations

from tkinter import messagebox
from typing import Any

import customtkinter as ctk
from balance_pipeline.gui.analysis import AnalysisController
from balance_pipeline.gui.theme import Theme


class DuplicateView(ctk.CTkFrame):  # type: ignore[misc]
    """A view for finding duplicate charges."""

    def __init__(self, master: Any, controller: AnalysisController) -> None:
        super().__init__(master, fg_color="transparent")
        self.controller = controller

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_view()

    def _build_view(self) -> None:
        ctk.CTkLabel(
            self, text="👥 Find Duplicate Charges", font=Theme.font_h1
        ).grid(row=0, column=0, padx=20, pady=(18, 6), sticky="w")

        form = ctk.CTkFrame(self, corner_radius=10, fg_color=Theme.card)
        form.grid(row=1, column=0, padx=20, pady=6, sticky="ew")

        ctk.CTkLabel(form, text="Check within (days):").grid(
            row=0, column=0, padx=10, pady=10, sticky="w"
        )
        self.days_entry = ctk.CTkEntry(form, width=90)
        self.days_entry.insert(0, "3")
        self.days_entry.grid(row=0, column=1, padx=6, pady=10)

        ctk.CTkButton(
            form, text="Find Duplicates", command=self._find_duplicates
        ).grid(row=0, column=2, padx=10, pady=10)

        self.results_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.results_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")

    def _find_duplicates(self) -> None:
        days_str = self.days_entry.get().strip()
        try:
            days_window = int(days_str) if days_str else 3
        except ValueError:
            messagebox.showwarning("Input Error", "Days back must be a number.")
            return

        for widget in self.results_frame.winfo_children():
            widget.destroy()

        duplicates = self.controller.find_duplicate_charges(days_window)

        if duplicates:
            ctk.CTkLabel(
                self.results_frame,
                text=f"⚠️ Found {len(duplicates)} potential duplicate charges",
                text_color=Theme.warning,
                font=Theme.font_h2,
            ).pack(anchor="w", padx=14, pady=(14, 6))

            for dup in duplicates:
                card = ctk.CTkFrame(self.results_frame, corner_radius=10, fg_color=Theme.card)
                card.pack(fill="x", padx=8, pady=6)
                ctk.CTkLabel(
                    card,
                    text=f"{dup['merchant']} - ${dup['amount']:,.2f}",
                    font=Theme.font_bold,
                ).grid(row=0, column=0, padx=12, pady=(10, 2), sticky="w")
                ctk.CTkLabel(
                    card,
                    text=f"📅 {dup['date1']:%Y-%m-%d} and {dup['date2']:%Y-%m-%d} ({dup['days_apart']} days apart)",
                    text_color=Theme.text_secondary,
                ).grid(row=1, column=0, padx=12, pady=(0, 10), sticky="w")
        else:
            ctk.CTkLabel(
                self.results_frame,
                text=f"✅ No suspicious duplicate charges found within {days_window} days",
                text_color=Theme.success,
            ).pack(anchor="w", padx=14, pady=14)
