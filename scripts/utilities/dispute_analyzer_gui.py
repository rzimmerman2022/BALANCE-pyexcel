#!/usr/bin/env python3
"""
BALANCE Dispute & Refund Analyzer - Modern GUI Version (rebuild)

Clean, working CustomTkinter GUI restoring all features.
"""
from __future__ import annotations

import contextlib
import logging
from datetime import datetime, timedelta
from pathlib import Path

import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk
import pandas as pd

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

COLORS = {
    "primary": "#1e88e5",
    "secondary": "#00acc1",
    "success": "#43a047",
    "warning": "#fb8c00",
    "danger": "#e53935",
    "info": "#5e35b1",
    "dark": "#1a1a2e",
    "card": "#16213e",
    "text": "#ffffff",
    "text_secondary": "#b0b0b0",
}


class DisputeAnalyzerGUI(ctk.CTk):
    def __init__(self) -> None:
    # Initialize the main window and layout.
    # Sets up styling, loads data, and builds the sidebar/main content.
        super().__init__()
        self.title("BALANCE - Dispute & Refund Analyzer v2.0")
        self.geometry("1400x900")
        self.minsize(1100, 700)

        # center window
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        with contextlib.suppress(Exception):
            self.iconbitmap(default="icon.ico")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.df: pd.DataFrame | None = None
        self.load_data()

        self.main_container = ctk.CTkFrame(self, corner_radius=0)
        self.main_container.grid(row=0, column=0, sticky="nsew")
        self.main_container.grid_columnconfigure(1, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        self.create_sidebar()
        self.create_main_content()
        self.show_dashboard()

    def load_data(self) -> None:
        """Load the latest cleaned transactions dataset from output/.

        Looks for Parquet first then CSV, coerces date dtype, ensures
        required columns exist, and derives amount_abs for convenience.
        """
        out = Path("output")
        pq = sorted(out.glob("*.parquet"), key=lambda p: p.stat().st_mtime)
        csv = sorted(out.glob("*.csv"), key=lambda p: p.stat().st_mtime)
        try:
            if pq:
                self.df = pd.read_parquet(pq[-1])
            elif csv:
                # best-effort date parsing
                self.df = pd.read_csv(csv[-1])
                if "date" in self.df.columns:
                    self.df["date"] = pd.to_datetime(self.df["date"], errors="coerce")
            else:
                messagebox.showerror("Error", "No cleaned data found in 'output/'. Run the pipeline first.")
                self.destroy()
                return

            required = {"date", "amount", "merchant_standardized", "description", "potential_refund"}
            missing = [c for c in required if c not in self.df.columns]
            if missing:
                messagebox.showerror("Schema Error", f"Missing required columns: {', '.join(missing)}")
                self.destroy()
                return

            if not pd.api.types.is_datetime64_any_dtype(self.df["date"]):
                self.df["date"] = pd.to_datetime(self.df["date"], errors="coerce")

            if "amount_abs" not in self.df.columns:
                self.df["amount_abs"] = self.df["amount"].abs()

            self.df["potential_refund"] = self.df["potential_refund"].fillna(False).astype(bool)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data: {e}")
            self.destroy()

    def create_sidebar(self) -> None:
        side = ctk.CTkFrame(self.main_container, width=240, corner_radius=0)
        side.grid(row=0, column=0, sticky="nsew")
        side.grid_rowconfigure(8, weight=1)

        ctk.CTkLabel(side, text="🏦 BALANCE", font=ctk.CTkFont(size=28, weight="bold")).grid(
            row=0, column=0, padx=16, pady=(16, 6), sticky="w"
        )
        ctk.CTkLabel(side, text="Dispute & Refund Analyzer", text_color=COLORS["text_secondary"]).grid(
            row=1, column=0, padx=16, pady=(0, 16), sticky="w"
        )

        self.nav_buttons: list[ctk.CTkButton] = []
        items = [
            ("📊 Dashboard", self.show_dashboard),
            ("🔍 Find Refunds", self.show_refund_search),
            ("👥 Duplicate Charges", self.show_duplicate_finder),
            ("✅ Check Refund Status", self.show_refund_checker),
            ("📈 Dispute Analysis", self.show_dispute_analysis),
            ("🔎 Advanced Search", self.show_advanced_search),
            ("💾 Export Data", self.show_export),
        ]
        for i, (label, cmd) in enumerate(items, start=2):
            b = ctk.CTkButton(side, text=label, command=cmd, anchor="w", fg_color="transparent")
            b.grid(row=i, column=0, padx=12, pady=4, sticky="ew")
            self.nav_buttons.append(b)

        if self.df is not None:
            ctk.CTkLabel(
                side,
                text=(
                    f"📁 {len(self.df):,} transactions\n"
                    f"📅 {self.df['date'].min():%b %d, %Y} → {self.df['date'].max():%b %d, %Y}"
                ),
                text_color=COLORS["text_secondary"],
                justify="left",
            ).grid(row=len(items) + 2, column=0, padx=12, pady=18, sticky="ew")

    def create_main_content(self) -> None:
        self.content_frame = ctk.CTkFrame(self.main_container, corner_radius=12, fg_color=COLORS["dark"])  # type: ignore[arg-type]
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 16), pady=16)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(1, weight=1)

    def clear_content(self) -> None:
        for w in self.content_frame.winfo_children():
            w.destroy()

    def show_dashboard(self) -> None:
        self.clear_content()
        ctk.CTkLabel(self.content_frame, text="Dashboard Overview", font=ctk.CTkFont(size=26, weight="bold")).grid(
            row=0, column=0, padx=20, pady=(18, 6), sticky="w"
        )

        total_disputes = int(self.df["potential_refund"].sum())
        dispute_amount = float(self.df[self.df["potential_refund"]]["amount"].sum())
        recent_disputes = int(
            self.df[(self.df["potential_refund"]) & (self.df["date"] >= datetime.now() - timedelta(days=30))].shape[0]
        )
        total_refunds = int(self.df[self.df["amount"] > 0].shape[0])

        metrics = [
            ("🔴 Total Disputes", f"{total_disputes:,}"),
            ("💰 Dispute Amount", f"${abs(dispute_amount):,.0f}"),
            ("📅 Recent (30d)", f"{recent_disputes:,}"),
            ("✅ Total Refunds", f"{total_refunds:,}"),
        ]

        row = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        row.grid(row=1, column=0, padx=20, pady=6, sticky="ew")
        row.grid_columnconfigure((0, 1, 2, 3), weight=1)

        for i, (label, val) in enumerate(metrics):
            card = ctk.CTkFrame(row, corner_radius=10, fg_color=COLORS["card"])  # type: ignore[arg-type]
            card.grid(row=0, column=i, padx=6, pady=6, sticky="ew")
            ctk.CTkLabel(card, text=label, text_color=COLORS["text_secondary"]).grid(
                row=0, column=0, padx=12, pady=(10, 0), sticky="w"
            )
            ctk.CTkLabel(card, text=val, font=ctk.CTkFont(size=20, weight="bold")).grid(
                row=1, column=0, padx=12, pady=(0, 10), sticky="w"
            )

        wrap = ctk.CTkFrame(self.content_frame, corner_radius=10, fg_color=COLORS["card"])  # type: ignore[arg-type]
        wrap.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.content_frame.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(wrap, text="⚠️ Recent Potential Disputes", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, padx=14, pady=(14, 6), sticky="w"
        )
        self.create_data_table(wrap, self.df[self.df["potential_refund"]].tail(20))
        total = int(self.df["potential_refund"].sum())
        shown = min(20, total)
        ctk.CTkLabel(
            wrap,
            text=f"Showing {shown} of {total} total disputes",
            text_color=COLORS["text_secondary"],
        ).grid(row=2, column=0, padx=14, pady=(0, 10), sticky="w")

    def create_data_table(self, parent, data: pd.DataFrame) -> None:
        """Render a ttk Treeview with alternating rows and sortable headers."""
        tree_frame = ttk.Frame(parent)
        tree_frame.grid(row=1, column=0, padx=14, pady=(0, 10), sticky="nsew")
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background=COLORS["dark"],
            foreground=COLORS["text"],
            fieldbackground=COLORS["dark"],
            borderwidth=0,
            rowheight=26,
        )
        style.configure(
            "Treeview.Heading",
            background=COLORS["card"],
            foreground=COLORS["text"],
            borderwidth=0,
            relief="flat",
        )
        style.map(
            "Treeview",
            background=[("selected", COLORS["primary"])],
            foreground=[("selected", COLORS["text"])],
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

        cfg = {
            "Date": {"width": 110, "anchor": "center"},
            "Merchant": {"width": 220, "anchor": "w"},
            "Amount": {"width": 110, "anchor": "e"},
            "Status": {"width": 120, "anchor": "center"},
            "Description": {"width": 400, "anchor": "w"},
        }
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=cfg[c]["width"], anchor=cfg[c]["anchor"])

        sort_state = dict.fromkeys(cols, False)

        def sort_by(col: str) -> None:
            reverse = not sort_state[col]
            sort_state[col] = reverse
            try:
                if col == "Date":
                    sorted_df = data.sort_values("date", ascending=not reverse)
                elif col == "Amount":
                    sorted_df = data.sort_values("amount", ascending=not reverse)
                elif col == "Merchant":
                    sorted_df = data.sort_values("merchant_standardized", ascending=not reverse)
                else:
                    sorted_df = data
                tree.delete(*tree.get_children())
                for i, row in sorted_df.reset_index(drop=True).iterrows():
                    status = (
                        "⚠️ Dispute"
                        if row["potential_refund"]
                        else ("✅ Refund" if row["amount"] > 0 else "📝 Charge")
                    )
                    values = [
                        row["date"].strftime("%m/%d/%Y") if pd.notna(row["date"]) else "",
                        str(row["merchant_standardized"])[:30],
                        f"${abs(row['amount']):,.2f}",
                        status,
                        str(row["description"])[:60] if pd.notna(row["description"]) else "",
                    ]
                    tag = "evenrow" if i % 2 == 0 else "oddrow"
                    tree.insert("", "end", values=values, tags=(tag,))
            except Exception as exc:
                logging.debug("Sort failed: %s", exc)

        for c in cols:
            tree.heading(c, command=(lambda cc=c: sort_by(cc)))

        for i, row in data.reset_index(drop=True).iterrows():
            status = (
                "⚠️ Dispute" if row["potential_refund"] else ("✅ Refund" if row["amount"] > 0 else "📝 Charge")
            )
            values = [
                row["date"].strftime("%m/%d/%Y") if pd.notna(row["date"]) else "",
                str(row["merchant_standardized"])[:30],
                f"${abs(row['amount']):,.2f}",
                status,
                str(row["description"])[:60] if pd.notna(row["description"]) else "",
            ]
            tag = "evenrow" if i % 2 == 0 else "oddrow"
            tree.insert("", "end", values=values, tags=(tag,))

        tree.tag_configure("evenrow", background=COLORS["dark"])
        tree.tag_configure("oddrow", background=COLORS["card"])
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

    def show_refund_search(self) -> None:
        self.clear_content()
        ctk.CTkLabel(self.content_frame, text="🔍 Find Refunds by Merchant", font=ctk.CTkFont(size=24, weight="bold")).grid(
            row=0, column=0, padx=20, pady=(18, 6), sticky="w"
        )
        form = ctk.CTkFrame(self.content_frame, corner_radius=10, fg_color=COLORS["card"])  # type: ignore[arg-type]
        form.grid(row=1, column=0, padx=20, pady=6, sticky="ew")

        ctk.CTkLabel(form, text="Merchant:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.merchant_entry = ctk.CTkEntry(form, placeholder_text="e.g., Amazon", width=260)
        self.merchant_entry.grid(row=0, column=1, padx=6, pady=10)

        ctk.CTkLabel(form, text="Days back:").grid(row=0, column=2, padx=10, pady=10, sticky="w")
        self.days_var = tk.StringVar(value="90")
        ctk.CTkEntry(form, textvariable=self.days_var, width=90).grid(row=0, column=3, padx=6, pady=10)

        ctk.CTkButton(form, text="Search", command=self.search_refunds, width=120).grid(
            row=0, column=4, padx=10, pady=10
        )

        self.results_frame = ctk.CTkFrame(self.content_frame)
        self.results_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.content_frame.grid_rowconfigure(2, weight=1)

    def search_refunds(self) -> None:
        merchant = self.merchant_entry.get().strip()
        if not merchant:
            messagebox.showwarning("Input Error", "Please enter a merchant name")
            return
        try:
            days = int(self.days_var.get()) if str(self.days_var.get()).isdigit() else 90
        except Exception:
            days = 90

        for w in self.results_frame.winfo_children():
            w.destroy()

        pat = merchant
        m = self.df["merchant_standardized"].str.contains(pat, case=False, na=False)
        refund_mask = self.df["potential_refund"]
        date_mask = self.df["date"] >= (datetime.now() - timedelta(days=days))
        res = self.df[m & (refund_mask | (self.df["amount"] > 0)) & date_mask]

        if len(res) > 0:
            ctk.CTkLabel(
                self.results_frame,
                text=f"Found {len(res)} potential refunds/credits for '{merchant}'",
                font=ctk.CTkFont(size=16, weight="bold"),
            ).grid(row=0, column=0, padx=14, pady=(14, 6), sticky="w")
            total_credits = res[res["amount"] > 0]["amount"].sum()
            ctk.CTkLabel(
                self.results_frame,
                text=f"Total credits: ${total_credits:,.2f}",
                text_color="#28a745",
            ).grid(row=1, column=0, padx=14, sticky="w")
            tbl = ctk.CTkFrame(self.results_frame)
            tbl.grid(row=2, column=0, padx=14, pady=8, sticky="nsew")
            self.results_frame.grid_rowconfigure(2, weight=1)
            self.results_frame.grid_columnconfigure(0, weight=1)
            self.create_data_table(tbl, res)
        else:
            ctk.CTkLabel(
                self.results_frame,
                text=f"No refunds found for '{merchant}' in the last {days} days",
                text_color=("gray60", "gray40"),
            ).grid(row=0, column=0, padx=14, pady=14, sticky="w")

    def show_duplicate_finder(self) -> None:
        self.clear_content()
        ctk.CTkLabel(self.content_frame, text="👥 Find Duplicate Charges", font=ctk.CTkFont(size=24, weight="bold")).grid(
            row=0, column=0, padx=20, pady=(18, 6), sticky="w"
        )
        form = ctk.CTkFrame(self.content_frame, corner_radius=10, fg_color=COLORS["card"])  # type: ignore[arg-type]
        form.grid(row=1, column=0, padx=20, pady=6, sticky="ew")

        ctk.CTkLabel(form, text="Check within (days):").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.dup_days_var = tk.StringVar(value="3")
        ctk.CTkEntry(form, textvariable=self.dup_days_var, width=90).grid(row=0, column=1, padx=6, pady=10)
        ctk.CTkButton(form, text="Find Duplicates", command=self.find_duplicates).grid(row=0, column=2, padx=10, pady=10)

        self.dup_results_frame = ctk.CTkFrame(self.content_frame)
        self.dup_results_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.content_frame.grid_rowconfigure(2, weight=1)

    def find_duplicates(self) -> None:
        """Detect likely duplicate charges by merchant and absolute amount.

        Pairs charges within a user-defined day window and presents a concise card list.
        """
        try:
            days_window = int(self.dup_days_var.get())
        except Exception:
            days_window = 3

        for w in self.dup_results_frame.winfo_children():
            w.destroy()

        dups: list[dict] = []
        charges = self.df[self.df["amount"] < 0]
        for (merchant, _amount_abs), grp in charges.groupby(["merchant_standardized", "amount_abs"]):
            if len(grp) > 1:
                g = grp.sort_values("date")
                for i in range(len(g) - 1):
                    delta = (g.iloc[i + 1]["date"] - g.iloc[i]["date"]).days
                    if delta <= days_window:
                        dups.append(
                            {
                                "date1": g.iloc[i]["date"],
                                "date2": g.iloc[i + 1]["date"],
                                "merchant": merchant,
                                "amount": -float(g.iloc[i]["amount_abs"]),
                                "days_apart": delta,
                                "description1": g.iloc[i]["description"],
                                "description2": g.iloc[i + 1]["description"],
                            }
                        )

        if dups:
            ctk.CTkLabel(
                self.dup_results_frame,
                text=f"⚠️ Found {len(dups)} potential duplicate charges",
                text_color=COLORS["warning"],
                font=ctk.CTkFont(size=16, weight="bold"),
            ).grid(row=0, column=0, padx=14, pady=(14, 6), sticky="w")
            scroll = ctk.CTkScrollableFrame(self.dup_results_frame)
            scroll.grid(row=1, column=0, padx=14, pady=8, sticky="nsew")
            self.dup_results_frame.grid_rowconfigure(1, weight=1)
            for i, dup in enumerate(dups[:20]):
                card = ctk.CTkFrame(scroll, corner_radius=10, fg_color=COLORS["card"])  # type: ignore[arg-type]
                card.grid(row=i, column=0, padx=8, pady=6, sticky="ew")
                ctk.CTkLabel(
                    card,
                    text=f"{dup['merchant']} - ${dup['amount']:,.2f}",
                    font=ctk.CTkFont(size=14, weight="bold"),
                ).grid(row=0, column=0, padx=12, pady=(10, 2), sticky="w")
                ctk.CTkLabel(
                    card,
                    text=f"📅 {dup['date1']:%Y-%m-%d} and {dup['date2']:%Y-%m-%d} ({dup['days_apart']} days apart)",
                    text_color=COLORS["text_secondary"],
                ).grid(row=1, column=0, padx=12, pady=(0, 10), sticky="w")
        else:
            ctk.CTkLabel(
                self.dup_results_frame,
                text=f"✅ No suspicious duplicate charges found within {days_window} days",
                text_color="#28a745",
            ).grid(row=0, column=0, padx=14, pady=14, sticky="w")

    def show_refund_checker(self) -> None:
        self.clear_content()
        ctk.CTkLabel(self.content_frame, text="Check Refund Status", font=ctk.CTkFont(size=24, weight="bold")).grid(
            row=0, column=0, padx=20, pady=(18, 6), sticky="w"
        )
        form = ctk.CTkFrame(self.content_frame, corner_radius=10, fg_color=COLORS["card"])  # type: ignore[arg-type]
        form.grid(row=1, column=0, padx=20, pady=6, sticky="ew")

        self.check_merchant = ctk.CTkEntry(form, placeholder_text="Merchant", width=220)
        self.check_merchant.grid(row=0, column=0, padx=8, pady=8)
        self.check_amount = ctk.CTkEntry(form, placeholder_text="Charge Amount", width=140)
        self.check_amount.grid(row=0, column=1, padx=8, pady=8)
        self.check_date = ctk.CTkEntry(form, placeholder_text="YYYY-MM-DD", width=160)
        self.check_date.grid(row=0, column=2, padx=8, pady=8)
        ctk.CTkButton(form, text="✅ Check", command=self.check_refund_status, width=140).grid(
            row=0, column=3, padx=8, pady=8
        )

        self.check_results_frame = ctk.CTkFrame(self.content_frame)
        self.check_results_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.content_frame.grid_rowconfigure(2, weight=1)

    def check_refund_status(self) -> None:
        merchant = self.check_merchant.get().strip()
        amount_str = self.check_amount.get().strip()
        date_str = self.check_date.get().strip()
        if not (merchant and amount_str and date_str):
            messagebox.showwarning("Input Error", "Please fill all fields")
            return
        try:
            amount = float(amount_str)
            charge_date = pd.to_datetime(date_str)
        except Exception:
            messagebox.showerror("Input Error", "Invalid amount or date format")
            return

        for w in self.check_results_frame.winfo_children():
            w.destroy()

        start, end = charge_date, charge_date + timedelta(days=60)
        m = self.df["merchant_standardized"].str.contains(merchant, case=False, na=False)
        date_mask = (self.df["date"] >= start) & (self.df["date"] <= end)
        amount_mask = (self.df["amount"].abs() - abs(amount)).abs() < 0.01
        refund_mask = self.df["amount"] > 0
        hits = self.df[m & date_mask & amount_mask & refund_mask]

        box = ctk.CTkFrame(self.check_results_frame, corner_radius=10, fg_color=COLORS["card"])  # type: ignore[arg-type]
        box.grid(row=0, column=0, padx=12, pady=12, sticky="ew")
        ctk.CTkLabel(
            box,
            text=f"Original Charge: {merchant} - ${amount:.2f} on {date_str}",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, padx=10, pady=(10, 4), sticky="w")

        if len(hits) > 0:
            ctk.CTkLabel(
                box,
                text="✅ REFUND FOUND",
                text_color="#28a745",
                font=ctk.CTkFont(size=18, weight="bold"),
            ).grid(row=1, column=0, padx=10, pady=4, sticky="w")
            for _, r in hits.iterrows():
                ctk.CTkLabel(box, text=f"📅 {r['date']:%Y-%m-%d} - ${r['amount']:,.2f}").grid(
                    row=2, column=0, padx=22, pady=4, sticky="w"
                )
        else:
            ctk.CTkLabel(
                box,
                text="❌ NO REFUND FOUND",
                text_color="#dc3545",
                font=ctk.CTkFont(size=18, weight="bold"),
            ).grid(row=1, column=0, padx=10, pady=4, sticky="w")
            ctk.CTkLabel(
                box,
                text="No matching refund found within 60 days of the charge",
                text_color=COLORS["text_secondary"],
            ).grid(row=2, column=0, padx=10, pady=(0, 10), sticky="w")

    def show_dispute_analysis(self) -> None:
        self.clear_content()
        ctk.CTkLabel(self.content_frame, text="Comprehensive Dispute Analysis", font=ctk.CTkFont(size=24, weight="bold")).grid(
            row=0, column=0, padx=20, pady=(18, 6), sticky="w"
        )

        total = int(self.df["potential_refund"].sum())
        disputes = self.df[self.df["potential_refund"]]
        if total == 0:
            ctk.CTkLabel(
                self.content_frame,
                text="No disputes found in the dataset",
                text_color=COLORS["text_secondary"],
            ).grid(row=1, column=0, padx=20, pady=10, sticky="w")
            return

        cards = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        cards.grid(row=1, column=0, padx=20, pady=6, sticky="ew")
        cards.grid_columnconfigure((0, 1, 2), weight=1)

        total_amount = float(disputes["amount"].sum())
        date_range = f"{disputes['date'].min():%b %Y} - {disputes['date'].max():%b %Y}"
        for i, (label, val) in enumerate(
            [("Total Disputes", f"{total:,}"), ("Total Amount", f"${abs(total_amount):,.0f}"), ("Date Range", date_range)]
        ):
            card = ctk.CTkFrame(cards, corner_radius=10, fg_color=COLORS["card"])  # type: ignore[arg-type]
            card.grid(row=0, column=i, padx=6, pady=6, sticky="ew")
            ctk.CTkLabel(card, text=label, text_color=COLORS["text_secondary"]).grid(
                row=0, column=0, padx=12, pady=(10, 0), sticky="w"
            )
            ctk.CTkLabel(card, text=val, font=ctk.CTkFont(size=20, weight="bold")).grid(
                row=1, column=0, padx=12, pady=(0, 10), sticky="w"
            )

        box = ctk.CTkFrame(self.content_frame, corner_radius=10, fg_color=COLORS["card"])  # type: ignore[arg-type]
        box.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.content_frame.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(box, text="Top Merchants with Disputes", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, padx=14, pady=(14, 6), sticky="w"
        )
        grp = disputes.groupby("merchant_standardized").agg({"amount": ["count", "sum"]}).round(2)
        grp.columns = ["Count", "Total Amount"]
        grp = grp.sort_values("Count", ascending=False).head(10)

        scroll = ctk.CTkScrollableFrame(box)
        scroll.grid(row=1, column=0, padx=14, pady=(0, 14), sticky="nsew")
        for i, (merchant, row) in enumerate(grp.iterrows()):
            card = ctk.CTkFrame(scroll, corner_radius=10, fg_color=COLORS["card"])  # type: ignore[arg-type]
            card.grid(row=i, column=0, padx=8, pady=6, sticky="ew")
            ctk.CTkLabel(card, text=str(merchant)[:40], font=ctk.CTkFont(size=14, weight="bold")).grid(
                row=0, column=0, padx=12, pady=(10, 2), sticky="w"
            )
            ctk.CTkLabel(
                card,
                text=f"Disputes: {int(row['Count'])} | Amount: ${abs(row['Total Amount']):,.2f}",
                text_color=COLORS["text_secondary"],
            ).grid(row=1, column=0, padx=12, pady=(0, 10), sticky="w")

    def show_advanced_search(self) -> None:
        self.clear_content()
        ctk.CTkLabel(self.content_frame, text="🔎 Advanced Search", font=ctk.CTkFont(size=24, weight="bold")).grid(
            row=0, column=0, padx=20, pady=(18, 6), sticky="w"
        )
        form = ctk.CTkFrame(self.content_frame, corner_radius=10, fg_color=COLORS["card"])  # type: ignore[arg-type]
        form.grid(row=1, column=0, padx=20, pady=6, sticky="ew")

        self.start_date = ctk.CTkEntry(form, placeholder_text="Start (YYYY-MM-DD)", width=150)
        self.start_date.grid(row=0, column=0, padx=8, pady=8)
        self.end_date = ctk.CTkEntry(form, placeholder_text="End (YYYY-MM-DD)", width=150)
        self.end_date.grid(row=0, column=1, padx=8, pady=8)
        self.min_amount = ctk.CTkEntry(form, placeholder_text="Min amount", width=140)
        self.min_amount.grid(row=0, column=2, padx=8, pady=8)
        self.max_amount = ctk.CTkEntry(form, placeholder_text="Max amount", width=140)
        self.max_amount.grid(row=0, column=3, padx=8, pady=8)
        self.adv_merchant = ctk.CTkEntry(form, placeholder_text="Merchant contains", width=220)
        self.adv_merchant.grid(row=0, column=4, padx=8, pady=8)
        self.only_disputes = ctk.CTkCheckBox(form, text="Only potential disputes")
        self.only_disputes.grid(row=0, column=5, padx=8, pady=8)
        ctk.CTkButton(form, text="Search", command=self.perform_advanced_search).grid(row=0, column=6, padx=8, pady=8)

        self.adv_results_frame = ctk.CTkFrame(self.content_frame)
        self.adv_results_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.content_frame.grid_rowconfigure(2, weight=1)

    def perform_advanced_search(self) -> None:
        df = self.df.copy()
        if self.start_date.get().strip():
            with contextlib.suppress(Exception):
                df = df[df["date"] >= pd.to_datetime(self.start_date.get().strip())]
        if self.end_date.get().strip():
            with contextlib.suppress(Exception):
                df = df[df["date"] <= pd.to_datetime(self.end_date.get().strip())]
        if self.min_amount.get().strip():
            with contextlib.suppress(Exception):
                df = df[df["amount_abs"] >= float(self.min_amount.get().strip())]
        if self.max_amount.get().strip():
            with contextlib.suppress(Exception):
                df = df[df["amount_abs"] <= float(self.max_amount.get().strip())]
        if self.adv_merchant.get().strip():
            pat = self.adv_merchant.get().strip()
            df = df[df["merchant_standardized"].str.contains(pat, case=False, na=False)]
        if self.only_disputes.get():
            df = df[df["potential_refund"]]

        for w in self.adv_results_frame.winfo_children():
            w.destroy()

        if len(df) > 0:
            ctk.CTkLabel(
                self.adv_results_frame,
                text=f"Found {len(df)} matching transactions",
                font=ctk.CTkFont(size=16, weight="bold"),
            ).grid(row=0, column=0, padx=14, pady=(14, 6), sticky="w")
            table = ctk.CTkFrame(self.adv_results_frame)
            table.grid(row=1, column=0, padx=14, pady=8, sticky="nsew")
            self.adv_results_frame.grid_rowconfigure(1, weight=1)
            self.create_data_table(table, df.head(100))
        else:
            ctk.CTkLabel(
                self.adv_results_frame,
                text="No transactions match your search criteria",
                text_color=("gray60", "gray40"),
            ).grid(row=0, column=0, padx=14, pady=14, sticky="w")

    def show_export(self) -> None:
        self.clear_content()
        ctk.CTkLabel(self.content_frame, text="Export Data", font=ctk.CTkFont(size=24, weight="bold")).grid(
            row=0, column=0, padx=20, pady=(18, 6), sticky="w"
        )
        box = ctk.CTkFrame(self.content_frame, corner_radius=10, fg_color=COLORS["card"])  # type: ignore[arg-type]
        box.grid(row=1, column=0, padx=20, pady=8, sticky="ew")

        opts = [
            ("📊 All Transactions", lambda: self.export_results(self.df, "all_transactions")),
            ("🔴 All Disputes", lambda: self.export_results(self.df[self.df["potential_refund"]], "all_disputes")),
            (
                "📅 Last 30 Days",
                lambda: self.export_results(
                    self.df[self.df["date"] >= datetime.now() - timedelta(days=30)],
                    "last_30_days",
                ),
            ),
            ("✅ All Refunds (Credits)", lambda: self.export_results(self.df[self.df["amount"] > 0], "all_refunds")),
        ]
        for i, (label, cmd) in enumerate(opts):
            ctk.CTkButton(box, text=label, command=cmd, anchor="w").grid(row=i // 2, column=i % 2, padx=10, pady=8)

    def export_results(self, data: pd.DataFrame, prefix: str = "export") -> None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = Path("output") / f"{prefix}_{ts}.xlsx"
        try:
            data.to_excel(path, index=False)
            messagebox.showinfo("Export Successful", f"Exported {len(data)} records to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export: {e}")


def main() -> None:
    app = DisputeAnalyzerGUI()
    app.mainloop()


if __name__ == "__main__":
    main()