from __future__ import annotations

from tkinter import ttk
from typing import Any

import customtkinter as ctk
import pandas as pd
from balance_pipeline.gui.theme import Theme


class DataTable(ctk.CTkFrame):  # type: ignore[misc]
    """A reusable data table widget using ttk.Treeview."""

    def __init__(self, master: Any, dataframe: pd.DataFrame, **kwargs: Any) -> None:
        super().__init__(master, **kwargs)
        self.dataframe = dataframe

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._create_table()

    def _create_table(self) -> None:
        """Renders the ttk Treeview with alternating rows and sortable headers."""
        tree_frame = ttk.Frame(self)
        tree_frame.grid(row=0, column=0, sticky="nsew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background=Theme.dark,
            foreground=Theme.text,
            fieldbackground=Theme.dark,
            borderwidth=0,
            rowheight=26,
        )
        style.configure(
            "Treeview.Heading",
            background=Theme.card,
            foreground=Theme.text,
            borderwidth=0,
            relief="flat",
            font=Theme.font_bold,
        )
        style.map(
            "Treeview",
            background=[("selected", Theme.primary)],
            foreground=[("selected", Theme.text)],
        )

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")

        cols = ["Date", "Merchant", "Amount", "Status", "Description"]
        tree = ttk.Treeview(
            tree_frame,
            columns=cols,
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            height=12,
            selectmode="browse",
        )
        vsb.config(command=tree.yview)
        hsb.config(command=tree.xview)

        col_configs: dict[str, dict[str, Any]] = {
            "Date": {"width": 110, "anchor": "center"},
            "Merchant": {"width": 220, "anchor": "w"},
            "Amount": {"width": 110, "anchor": "e"},
            "Status": {"width": 120, "anchor": "center"},
            "Description": {"width": 400, "anchor": "w"},
        }
        for c in cols:
            tree.heading(c, text=c)
            anchor_val = col_configs[c].get("anchor", "w")
            tree.column(
                c,
                width=col_configs[c].get("width", 100),
                anchor=anchor_val,
            )

        # Data insertion
        for i, (_, row) in enumerate(self.dataframe.reset_index(drop=True).iterrows()):
            status = (
                "⚠️ Dispute"
                if row.get("potential_refund")
                else ("✅ Refund" if row.get("amount", 0) > 0 else "📝 Charge")
            )
            # Ensure values are of a consistent type before formatting
            date_val = row.get("date")
            date_str = date_val.strftime("%m/%d/%Y") if pd.notna(date_val) else ""
            merchant_str = str(row.get("merchant_standardized", ""))[:30]
            amount_val = row.get("amount", 0.0)
            amount_str = f"${abs(amount_val):,.2f}"
            desc_str = str(row.get("description", ""))[:60]

            values = [date_str, merchant_str, amount_str, status, desc_str]
            tag = "evenrow" if i % 2 == 0 else "oddrow"
            tree.insert("", "end", values=values, tags=(tag,))

        tree.tag_configure("evenrow", background=Theme.dark)
        tree.tag_configure("oddrow", background=Theme.card)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
