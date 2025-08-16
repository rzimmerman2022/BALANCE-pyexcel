from __future__ import annotations

from typing import Any

import customtkinter as ctk
from balance_pipeline.gui.analysis import AnalysisController
from balance_pipeline.gui.theme import Theme


class DisputeAnalysisView(ctk.CTkFrame):  # type: ignore[misc]
    """A view for analyzing dispute metrics."""

    def __init__(self, master: Any, controller: AnalysisController) -> None:
        super().__init__(master, fg_color="transparent")
        self.controller = controller
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._build_view()

    def _build_view(self) -> None:
        ctk.CTkLabel(
            self, text="📈 Comprehensive Dispute Analysis", font=Theme.font_h1
        ).grid(row=0, column=0, padx=20, pady=(18, 6), sticky="w")

        analysis = self.controller.get_dispute_analysis()

        if analysis.get("total_disputes", 0) == 0:
            ctk.CTkLabel(
                self,
                text="No disputes found in the dataset.",
                text_color=Theme.text_secondary,
            ).grid(row=1, column=0, padx=20, pady=10, sticky="w")
            return

        cards = ctk.CTkFrame(self, fg_color="transparent")
        cards.grid(row=1, column=0, padx=20, pady=6, sticky="ew")
        cards.grid_columnconfigure((0, 1, 2), weight=1)

        metric_display_data = [
            ("Total Disputes", f"{analysis.get('total_disputes', 0):,}"),
            ("Total Amount", f"${abs(analysis.get('total_amount', 0)):,.0f}"),
            ("Date Range", analysis.get("date_range", "N/A")),
        ]

        for i, (label, value) in enumerate(metric_display_data):
            card = ctk.CTkFrame(cards, corner_radius=10, fg_color=Theme.card)
            card.grid(row=0, column=i, padx=6, pady=6, sticky="ew")
            ctk.CTkLabel(card, text=label, text_color=Theme.text_secondary).grid(
                row=0, column=0, padx=12, pady=(10, 0), sticky="w"
            )
            ctk.CTkLabel(card, text=value, font=Theme.font_metric).grid(
                row=1, column=0, padx=12, pady=(0, 10), sticky="w"
            )

        box = ctk.CTkFrame(self, corner_radius=10, fg_color=Theme.card)
        box.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        box.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            box, text="Top Merchants with Disputes", font=Theme.font_h2
        ).grid(row=0, column=0, padx=14, pady=(14, 6), sticky="w")

        scroll = ctk.CTkScrollableFrame(box, fg_color="transparent")
        scroll.grid(row=1, column=0, padx=6, pady=6, sticky="nsew")

        top_merchants = analysis.get("top_merchants", [])
        for i, merchant_data in enumerate(top_merchants):
            card = ctk.CTkFrame(scroll, corner_radius=10, fg_color=Theme.dark)
            card.pack(fill="x", padx=8, pady=6)
            ctk.CTkLabel(
                card,
                text=str(merchant_data.get("merchant_standardized", "Unknown"))[:40],
                font=Theme.font_bold,
            ).grid(row=0, column=0, padx=12, pady=(10, 2), sticky="w")
            ctk.CTkLabel(
                card,
                text=f"Disputes: {int(merchant_data.get('Count', 0))} | Amount: ${abs(merchant_data.get('TotalAmount', 0)):,.2f}",
                text_color=Theme.text_secondary,
            ).grid(row=1, column=0, padx=12, pady=(0, 10), sticky="w")
