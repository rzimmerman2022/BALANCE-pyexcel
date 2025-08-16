#!/usr/bin/env python3
"""
BALANCE Dispute & Refund Analyzer - Modern GUI Version (rebuild)

Main application entry point for the GUI.
"""

from __future__ import annotations

import contextlib
import logging
from tkinter import messagebox

import customtkinter as ctk
from balance_pipeline.gui.analysis import AnalysisController
from balance_pipeline.gui.theme import Theme
from balance_pipeline.gui.views.advanced_search_view import AdvancedSearchView
from balance_pipeline.gui.views.dashboard_view import DashboardView
from balance_pipeline.gui.views.dispute_analysis_view import DisputeAnalysisView
from balance_pipeline.gui.views.duplicate_view import DuplicateView
from balance_pipeline.gui.views.export_view import ExportView
from balance_pipeline.gui.views.refund_checker_view import RefundCheckerView
from balance_pipeline.gui.views.refund_search_view import RefundSearchView

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class App(ctk.CTk):  # type: ignore[misc]
    """The main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.title("BALANCE - Dispute & Refund Analyzer v2.1")
        self.geometry("1400x900")
        self.minsize(1100, 700)

        self._center_window()
        with contextlib.suppress(Exception):
            self.iconbitmap(default="icon.ico")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        try:
            self.controller = AnalysisController()
            self.controller.load_data()
        except (FileNotFoundError, ValueError) as e:
            messagebox.showerror("Initialization Error", str(e))
            self.after(
                100, self.destroy
            )  # Schedule destruction after mainloop starts
            return

        self.main_container = ctk.CTkFrame(self, corner_radius=0)
        self.main_container.grid(row=0, column=0, sticky="nsew")
        self.main_container.grid_columnconfigure(1, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        self.create_sidebar()
        self.create_main_content()
        self.show_dashboard()

    def _center_window(self) -> None:
        """Centers the window on the screen."""
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def create_sidebar(self) -> None:
        side = ctk.CTkFrame(self.main_container, width=240, corner_radius=0)
        side.grid(row=0, column=0, sticky="nsew")
        side.grid_rowconfigure(8, weight=1)

        ctk.CTkLabel(side, text="🏦 BALANCE", font=Theme.font_large_bold).grid(
            row=0, column=0, padx=16, pady=(16, 6), sticky="w"
        )
        ctk.CTkLabel(
            side, text="Dispute & Refund Analyzer", text_color=Theme.text_secondary
        ).grid(row=1, column=0, padx=16, pady=(0, 16), sticky="w")

        self.nav_buttons: list[ctk.CTkButton] = []
        items = [
            ("📊 Dashboard", self.show_dashboard),
            ("🔍 Find Refunds", self.show_refund_search),
            ("👥 Duplicate Charges", self.show_duplicate_charges),
            ("✅ Check Refund Status", self.show_refund_checker),
            ("📈 Dispute Analysis", self.show_dispute_analysis),
            ("🔎 Advanced Search", self.show_advanced_search),
            ("💾 Export Data", self.show_export_data),
        ]
        for i, (label, cmd) in enumerate(items, start=2):
            b = ctk.CTkButton(
                side, text=label, command=cmd, anchor="w", fg_color="transparent"
            )
            b.grid(row=i, column=0, padx=12, pady=4, sticky="ew")
            self.nav_buttons.append(b)

        df = self.controller.get_dataframe()
        ctk.CTkLabel(
            side,
            text=(
                f"📁 {len(df):,} transactions\n"
                f"📅 {df['date'].min():%b %d, %Y} → {df['date'].max():%b %d, %Y}"
            ),
            text_color=Theme.text_secondary,
            justify="left",
        ).grid(row=len(items) + 2, column=0, padx=12, pady=18, sticky="ew")

    def create_main_content(self) -> None:
        self.content_frame = ctk.CTkFrame(
            self.main_container, corner_radius=12, fg_color=Theme.dark
        )
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 16), pady=16)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(1, weight=1)

    def show_view(self, view_class: type[ctk.CTkFrame] | None) -> None:
        """Clears the content frame and displays the requested view."""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        if view_class:
            view = view_class(self.content_frame, controller=self.controller)
            view.grid(row=0, column=0, sticky="nsew")

    def show_dashboard(self) -> None:
        self.show_view(DashboardView)

    def show_refund_search(self) -> None:
        self.show_view(RefundSearchView)

    def show_duplicate_charges(self) -> None:
        self.show_view(DuplicateView)

    def show_refund_checker(self) -> None:
        self.show_view(RefundCheckerView)

    def show_dispute_analysis(self) -> None:
        self.show_view(DisputeAnalysisView)

    def show_advanced_search(self) -> None:
        self.show_view(AdvancedSearchView)

    def show_export_data(self) -> None:
        self.show_view(ExportView)


def main() -> None:
    """Main function to run the application."""
    app = App()
    app.mainloop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
