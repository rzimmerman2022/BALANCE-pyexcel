from __future__ import annotations

from typing import Any

import customtkinter as ctk
from balance_pipeline.gui.analysis import AnalysisController
from balance_pipeline.gui.theme import Theme
from balance_pipeline.gui.widgets.data_table import DataTable


class DashboardView(ctk.CTkFrame):  # type: ignore[misc]
    """Dashboard view showing key metrics and recent disputes."""

    def __init__(self, master: Any, controller: AnalysisController) -> None:
        super().__init__(master, fg_color="transparent")
        self.controller = controller
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.build_view()

    def build_view(self) -> None:
        ctk.CTkLabel(self, text="Dashboard Overview", font=Theme.font_h1).grid(
            row=0, column=0, padx=20, pady=(18, 6), sticky="w"
        )

        metrics = self.controller.get_dashboard_metrics()

        metric_display_data = [
            ("🔴 Total Disputes", f"{metrics.get('total_disputes', 0):,}"),
            ("💰 Dispute Amount", f"${abs(metrics.get('dispute_amount', 0)):,.0f}"),
            ("📅 Recent (30d)", f"{metrics.get('recent_disputes', 0):,}"),
            ("✅ Total Refunds", f"{metrics.get('total_refunds', 0):,}"),
        ]

        metrics_row = ctk.CTkFrame(self, fg_color="transparent")
        metrics_row.grid(row=1, column=0, padx=20, pady=6, sticky="ew")
        metrics_row.grid_columnconfigure(
            list(range(len(metric_display_data))), weight=1
        )

        for i, (label, value) in enumerate(metric_display_data):
            card = ctk.CTkFrame(metrics_row, corner_radius=10, fg_color=Theme.card)
            card.grid(row=0, column=i, padx=6, pady=6, sticky="ew")
            ctk.CTkLabel(card, text=label, text_color=Theme.text_secondary).grid(
                row=0, column=0, padx=12, pady=(10, 0), sticky="w"
            )
            ctk.CTkLabel(card, text=value, font=Theme.font_metric).grid(
                row=1, column=0, padx=12, pady=(0, 10), sticky="w"
            )

        disputes_frame = ctk.CTkFrame(self, corner_radius=10, fg_color=Theme.card)
        disputes_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        disputes_frame.grid_columnconfigure(0, weight=1)
        disputes_frame.grid_rowconfigure(1, weight=1)


        ctk.CTkLabel(
            disputes_frame, text="⚠️ Recent Potential Disputes", font=Theme.font_h2
        ).grid(row=0, column=0, padx=14, pady=(14, 6), sticky="w")

        recent_disputes_df = self.controller.get_recent_disputes()

        table = DataTable(disputes_frame, recent_disputes_df)
        table.grid(row=1, column=0, padx=14, pady=(0, 10), sticky="nsew")

        total = metrics.get("total_disputes", 0)
        shown = min(len(recent_disputes_df), total)
        ctk.CTkLabel(
            disputes_frame,
            text=f"Showing {shown} of {total} total disputes",
            text_color=Theme.text_secondary,
        ).grid(row=2, column=0, padx=14, pady=(0, 10), sticky="w")
