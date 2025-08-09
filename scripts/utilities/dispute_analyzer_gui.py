#!/usr/bin/env python3
"""
BALANCE Dispute & Refund Analyzer - Modern GUI Version

Professional graphical interface for comprehensive dispute analysis and refund verification.
Features modern dark theme, interactive data visualization, and advanced search capabilities.

Usage:
    python scripts/utilities/dispute_analyzer_gui.py

Features:
    - Modern dark theme with professional UI/UX design
    - Interactive dashboard with real-time metrics
    - Advanced search and filtering capabilities
    - Duplicate charge detection algorithm
    - Refund status verification system
    - One-click Excel export functionality
    - Comprehensive dispute analysis reports

Requirements:
    - customtkinter (auto-installed on first run)
    - pandas, numpy (from main project requirements)
    - tkinter (included with Python)

Author: BALANCE Pipeline Team
Version: 1.0.0
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import re
from threading import Thread
import customtkinter as ctk

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")  # Modes: "System", "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue", "green", "dark-blue"

class DisputeAnalyzerGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("BALANCE - Dispute & Refund Analyzer")
        self.geometry("1400x800")
        
        # Configure grid weight
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Load data
        self.df = None
        self.filtered_df = None
        self.load_data()
        
        # Create main container
        self.main_container = ctk.CTkFrame(self, corner_radius=0)
        self.main_container.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.main_container.grid_columnconfigure(1, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)
        
        # Create sidebar
        self.create_sidebar()
        
        # Create main content area
        self.create_main_content()
        
        # Load initial view
        self.show_dashboard()
    
    def load_data(self):
        """Load the most recent cleaned transaction file"""
        output_dir = Path("output")
        
        # Find latest cleaned file
        parquet_files = list(output_dir.glob("transactions_cleaned_*.parquet"))
        csv_files = list(output_dir.glob("transactions_cleaned_*.csv"))
        
        try:
            if parquet_files:
                latest_file = max(parquet_files, key=lambda x: x.stat().st_mtime)
                self.df = pd.read_parquet(latest_file)
            elif csv_files:
                latest_file = max(csv_files, key=lambda x: x.stat().st_mtime)
                self.df = pd.read_csv(latest_file, parse_dates=['date'])
            else:
                messagebox.showerror("Error", "No cleaned data files found. Run quick_powerbi_prep.py first.")
                self.destroy()
                return
            
            self.filtered_df = self.df.copy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data: {str(e)}")
            self.destroy()
    
    def create_sidebar(self):
        """Create the sidebar with navigation buttons"""
        sidebar = ctk.CTkFrame(self.main_container, width=250, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_rowconfigure(8, weight=1)
        
        # Logo/Title
        logo_label = ctk.CTkLabel(
            sidebar, 
            text="🏦 BALANCE", 
            font=ctk.CTkFont(size=28, weight="bold")
        )
        logo_label.grid(row=0, column=0, padx=20, pady=(20, 5))
        
        subtitle = ctk.CTkLabel(
            sidebar, 
            text="Dispute & Refund Analyzer", 
            font=ctk.CTkFont(size=14),
            text_color=("gray60", "gray40")
        )
        subtitle.grid(row=1, column=0, padx=20, pady=(0, 30))
        
        # Navigation buttons
        self.nav_buttons = []
        
        buttons_config = [
            ("📊 Dashboard", self.show_dashboard),
            ("🔍 Find Refunds", self.show_refund_search),
            ("👥 Duplicate Charges", self.show_duplicate_finder),
            ("✅ Check Refund Status", self.show_refund_checker),
            ("📈 Dispute Analysis", self.show_dispute_analysis),
            ("🔎 Advanced Search", self.show_advanced_search),
            ("💾 Export Data", self.show_export)
        ]
        
        for i, (text, command) in enumerate(buttons_config):
            btn = ctk.CTkButton(
                sidebar,
                text=text,
                command=command,
                height=40,
                font=ctk.CTkFont(size=14),
                anchor="w"
            )
            btn.grid(row=i+2, column=0, padx=20, pady=5, sticky="ew")
            self.nav_buttons.append(btn)
        
        # Data info at bottom
        if self.df is not None:
            info_frame = ctk.CTkFrame(sidebar, corner_radius=10)
            info_frame.grid(row=10, column=0, padx=20, pady=20, sticky="ew")
            
            info_text = f"📁 {len(self.df):,} transactions\n"
            info_text += f"📅 {self.df['date'].min().strftime('%b %Y')} - {self.df['date'].max().strftime('%b %Y')}"
            
            info_label = ctk.CTkLabel(
                info_frame,
                text=info_text,
                font=ctk.CTkFont(size=12),
                justify="left"
            )
            info_label.grid(row=0, column=0, padx=15, pady=15)
    
    def create_main_content(self):
        """Create the main content area"""
        self.content_frame = ctk.CTkFrame(self.main_container, corner_radius=10)
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=20)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(1, weight=1)
    
    def clear_content(self):
        """Clear the content frame"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def show_dashboard(self):
        """Show the main dashboard"""
        self.clear_content()
        
        # Title
        title = ctk.CTkLabel(
            self.content_frame,
            text="Dashboard Overview",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        title.grid(row=0, column=0, columnspan=3, padx=30, pady=(30, 20), sticky="w")
        
        # Create metrics cards
        metrics_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        metrics_frame.grid(row=1, column=0, padx=30, pady=10, sticky="ew")
        metrics_frame.grid_columnconfigure((0,1,2,3), weight=1)
        
        # Calculate metrics
        total_disputes = self.df['potential_refund'].sum()
        dispute_amount = self.df[self.df['potential_refund'] == True]['amount'].sum()
        recent_disputes = self.df[
            (self.df['potential_refund'] == True) & 
            (self.df['date'] >= datetime.now() - timedelta(days=30))
        ].shape[0]
        total_refunds = self.df[self.df['amount'] > 0].shape[0]
        
        metrics = [
            ("🔴 Total Disputes", f"{total_disputes:,}", "error"),
            ("💰 Dispute Amount", f"${abs(dispute_amount):,.0f}", "warning"),
            ("📅 Recent (30d)", f"{recent_disputes:,}", "info"),
            ("✅ Total Refunds", f"{total_refunds:,}", "success")
        ]
        
        for i, (label, value, color_type) in enumerate(metrics):
            self.create_metric_card(metrics_frame, label, value, i, color_type)
        
        # Recent disputes table
        table_frame = ctk.CTkFrame(self.content_frame)
        table_frame.grid(row=2, column=0, padx=30, pady=20, sticky="nsew")
        self.content_frame.grid_rowconfigure(2, weight=1)
        
        table_title = ctk.CTkLabel(
            table_frame,
            text="Recent Potential Disputes",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        table_title.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Create treeview for table
        tree_frame = ctk.CTkFrame(table_frame)
        tree_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        table_frame.grid_rowconfigure(1, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        self.create_data_table(
            tree_frame,
            self.df[self.df['potential_refund'] == True].tail(20)
        )
    
    def create_metric_card(self, parent, label, value, column, color_type="info"):
        """Create a metric card"""
        colors = {
            "error": "#dc3545",
            "warning": "#ffc107",
            "info": "#17a2b8",
            "success": "#28a745"
        }
        
        card = ctk.CTkFrame(parent, corner_radius=10)
        card.grid(row=0, column=column, padx=10, pady=10, sticky="ew")
        
        label_widget = ctk.CTkLabel(
            card,
            text=label,
            font=ctk.CTkFont(size=14),
            text_color=("gray60", "gray40")
        )
        label_widget.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")
        
        value_widget = ctk.CTkLabel(
            card,
            text=value,
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=colors.get(color_type, "#17a2b8")
        )
        value_widget.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="w")
    
    def create_data_table(self, parent, data):
        """Create a data table with treeview"""
        # Create frame for treeview and scrollbars
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill="both", expand=True)
        
        # Configure style
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", 
                       background="#2b2b2b",
                       foreground="white",
                       fieldbackground="#2b2b2b",
                       borderwidth=0)
        style.configure("Treeview.Heading",
                       background="#1f1f1f",
                       foreground="white",
                       borderwidth=0)
        style.map("Treeview", background=[("selected", "#144870")])
        
        # Create scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        
        # Create treeview
        columns = ['Date', 'Merchant', 'Amount', 'Description']
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings',
                          yscrollcommand=vsb.set, xscrollcommand=hsb.set,
                          height=15)
        
        vsb.config(command=tree.yview)
        hsb.config(command=tree.xview)
        
        # Configure columns
        for col in columns:
            tree.heading(col, text=col)
            if col == 'Description':
                tree.column(col, width=400)
            elif col == 'Amount':
                tree.column(col, width=100, anchor='e')
            else:
                tree.column(col, width=150)
        
        # Add data
        for _, row in data.iterrows():
            values = [
                row['date'].strftime('%Y-%m-%d'),
                row['merchant_standardized'][:30],
                f"${row['amount']:,.2f}",
                str(row['description'])[:60]
            ]
            tree.insert('', 'end', values=values)
        
        # Pack everything
        tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
    
    def show_refund_search(self):
        """Show refund search interface"""
        self.clear_content()
        
        title = ctk.CTkLabel(
            self.content_frame,
            text="Find Refunds by Merchant",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        title.grid(row=0, column=0, padx=30, pady=(30, 20), sticky="w")
        
        # Search frame
        search_frame = ctk.CTkFrame(self.content_frame)
        search_frame.grid(row=1, column=0, padx=30, pady=10, sticky="ew")
        
        # Merchant input
        merchant_label = ctk.CTkLabel(
            search_frame,
            text="Merchant Name:",
            font=ctk.CTkFont(size=14)
        )
        merchant_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        self.merchant_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Enter merchant name (e.g., Amazon)",
            width=300,
            font=ctk.CTkFont(size=14)
        )
        self.merchant_entry.grid(row=0, column=1, padx=10, pady=20)
        
        # Days back
        days_label = ctk.CTkLabel(
            search_frame,
            text="Days to look back:",
            font=ctk.CTkFont(size=14)
        )
        days_label.grid(row=0, column=2, padx=20, pady=20, sticky="w")
        
        self.days_var = tk.StringVar(value="90")
        days_entry = ctk.CTkEntry(
            search_frame,
            textvariable=self.days_var,
            width=100,
            font=ctk.CTkFont(size=14)
        )
        days_entry.grid(row=0, column=3, padx=10, pady=20)
        
        # Search button
        search_btn = ctk.CTkButton(
            search_frame,
            text="🔍 Search",
            command=self.search_refunds,
            width=150,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        search_btn.grid(row=0, column=4, padx=20, pady=20)
        
        # Results frame
        self.results_frame = ctk.CTkFrame(self.content_frame)
        self.results_frame.grid(row=2, column=0, padx=30, pady=20, sticky="nsew")
        self.content_frame.grid_rowconfigure(2, weight=1)
    
    def search_refunds(self):
        """Search for refunds"""
        merchant = self.merchant_entry.get()
        if not merchant:
            messagebox.showwarning("Input Error", "Please enter a merchant name")
            return
        
        try:
            days = int(self.days_var.get())
        except:
            days = 90
        
        # Clear previous results
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        
        # Search for refunds
        merchant_pattern = merchant.upper()
        merchant_mask = self.df['merchant_standardized'].str.contains(
            merchant_pattern, case=False, na=False
        )
        refund_mask = self.df['potential_refund'] == True
        date_mask = self.df['date'] >= (datetime.now() - timedelta(days=days))
        
        results = self.df[merchant_mask & (refund_mask | (self.df['amount'] > 0)) & date_mask]
        
        # Display results
        if len(results) > 0:
            # Summary
            summary = ctk.CTkLabel(
                self.results_frame,
                text=f"Found {len(results)} potential refunds/credits for '{merchant}'",
                font=ctk.CTkFont(size=16, weight="bold")
            )
            summary.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
            
            total_credits = results[results['amount'] > 0]['amount'].sum()
            total_label = ctk.CTkLabel(
                self.results_frame,
                text=f"Total credits: ${total_credits:,.2f}",
                font=ctk.CTkFont(size=14),
                text_color="#28a745"
            )
            total_label.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")
            
            # Table
            table_frame = ctk.CTkFrame(self.results_frame)
            table_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
            self.results_frame.grid_rowconfigure(2, weight=1)
            self.results_frame.grid_columnconfigure(0, weight=1)
            
            self.create_data_table(table_frame, results)
        else:
            no_results = ctk.CTkLabel(
                self.results_frame,
                text=f"No refunds found for '{merchant}' in the last {days} days",
                font=ctk.CTkFont(size=16),
                text_color=("gray60", "gray40")
            )
            no_results.grid(row=0, column=0, padx=20, pady=20)
    
    def show_duplicate_finder(self):
        """Show duplicate charge finder"""
        self.clear_content()
        
        title = ctk.CTkLabel(
            self.content_frame,
            text="Find Duplicate Charges",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        title.grid(row=0, column=0, padx=30, pady=(30, 20), sticky="w")
        
        # Settings frame
        settings_frame = ctk.CTkFrame(self.content_frame)
        settings_frame.grid(row=1, column=0, padx=30, pady=10, sticky="ew")
        
        # Days window
        days_label = ctk.CTkLabel(
            settings_frame,
            text="Check for duplicates within:",
            font=ctk.CTkFont(size=14)
        )
        days_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        self.dup_days_var = tk.StringVar(value="3")
        days_entry = ctk.CTkEntry(
            settings_frame,
            textvariable=self.dup_days_var,
            width=80,
            font=ctk.CTkFont(size=14)
        )
        days_entry.grid(row=0, column=1, padx=10, pady=20)
        
        days_text = ctk.CTkLabel(
            settings_frame,
            text="days",
            font=ctk.CTkFont(size=14)
        )
        days_text.grid(row=0, column=2, padx=(0, 20), pady=20, sticky="w")
        
        # Search button
        search_btn = ctk.CTkButton(
            settings_frame,
            text="🔍 Find Duplicates",
            command=self.find_duplicates,
            width=200,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        search_btn.grid(row=0, column=3, padx=20, pady=20)
        
        # Results frame
        self.dup_results_frame = ctk.CTkFrame(self.content_frame)
        self.dup_results_frame.grid(row=2, column=0, padx=30, pady=20, sticky="nsew")
        self.content_frame.grid_rowconfigure(2, weight=1)
    
    def find_duplicates(self):
        """Find duplicate charges"""
        try:
            days_window = int(self.dup_days_var.get())
        except:
            days_window = 3
        
        # Clear previous results
        for widget in self.dup_results_frame.winfo_children():
            widget.destroy()
        
        # Find duplicates
        duplicates = []
        
        for (merchant, amount), group in self.df[self.df['amount'] < 0].groupby(['merchant_standardized', 'amount_abs']):
            if len(group) > 1:
                group_sorted = group.sort_values('date')
                for i in range(len(group_sorted) - 1):
                    date_diff = (group_sorted.iloc[i+1]['date'] - group_sorted.iloc[i]['date']).days
                    if date_diff <= days_window:
                        duplicates.append({
                            'date1': group_sorted.iloc[i]['date'],
                            'date2': group_sorted.iloc[i+1]['date'],
                            'merchant': merchant,
                            'amount': amount,
                            'days_apart': date_diff,
                            'description1': group_sorted.iloc[i]['description'],
                            'description2': group_sorted.iloc[i+1]['description']
                        })
        
        # Display results
        if duplicates:
            # Summary
            summary = ctk.CTkLabel(
                self.dup_results_frame,
                text=f"⚠️ Found {len(duplicates)} potential duplicate charges",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color="#ffc107"
            )
            summary.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
            
            # Create scrollable frame for duplicate cards
            scroll_frame = ctk.CTkScrollableFrame(self.dup_results_frame)
            scroll_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
            self.dup_results_frame.grid_rowconfigure(1, weight=1)
            self.dup_results_frame.grid_columnconfigure(0, weight=1)
            
            # Display each duplicate as a card
            for i, dup in enumerate(duplicates[:20]):  # Limit to 20 for performance
                card = ctk.CTkFrame(scroll_frame, corner_radius=10)
                card.grid(row=i, column=0, padx=10, pady=5, sticky="ew")
                scroll_frame.grid_columnconfigure(0, weight=1)
                
                # Merchant and amount
                header = ctk.CTkLabel(
                    card,
                    text=f"{dup['merchant']} - ${dup['amount']:,.2f}",
                    font=ctk.CTkFont(size=14, weight="bold")
                )
                header.grid(row=0, column=0, padx=15, pady=(10, 5), sticky="w")
                
                # Dates
                dates_text = f"📅 {dup['date1'].strftime('%Y-%m-%d')} and {dup['date2'].strftime('%Y-%m-%d')} ({dup['days_apart']} days apart)"
                dates_label = ctk.CTkLabel(
                    card,
                    text=dates_text,
                    font=ctk.CTkFont(size=12),
                    text_color=("gray60", "gray40")
                )
                dates_label.grid(row=1, column=0, padx=15, pady=(0, 10), sticky="w")
        else:
            no_results = ctk.CTkLabel(
                self.dup_results_frame,
                text=f"✅ No suspicious duplicate charges found within {days_window} days",
                font=ctk.CTkFont(size=16),
                text_color="#28a745"
            )
            no_results.grid(row=0, column=0, padx=20, pady=20)
    
    def show_refund_checker(self):
        """Show refund status checker"""
        self.clear_content()
        
        title = ctk.CTkLabel(
            self.content_frame,
            text="Check Refund Status",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        title.grid(row=0, column=0, padx=30, pady=(30, 20), sticky="w")
        
        # Input frame
        input_frame = ctk.CTkFrame(self.content_frame)
        input_frame.grid(row=1, column=0, padx=30, pady=10, sticky="ew")
        
        # Merchant
        merchant_label = ctk.CTkLabel(
            input_frame,
            text="Merchant:",
            font=ctk.CTkFont(size=14)
        )
        merchant_label.grid(row=0, column=0, padx=20, pady=15, sticky="w")
        
        self.check_merchant = ctk.CTkEntry(
            input_frame,
            placeholder_text="e.g., Amazon",
            width=200,
            font=ctk.CTkFont(size=14)
        )
        self.check_merchant.grid(row=0, column=1, padx=10, pady=15)
        
        # Amount
        amount_label = ctk.CTkLabel(
            input_frame,
            text="Charge Amount:",
            font=ctk.CTkFont(size=14)
        )
        amount_label.grid(row=0, column=2, padx=20, pady=15, sticky="w")
        
        self.check_amount = ctk.CTkEntry(
            input_frame,
            placeholder_text="e.g., 99.99",
            width=150,
            font=ctk.CTkFont(size=14)
        )
        self.check_amount.grid(row=0, column=3, padx=10, pady=15)
        
        # Date
        date_label = ctk.CTkLabel(
            input_frame,
            text="Charge Date:",
            font=ctk.CTkFont(size=14)
        )
        date_label.grid(row=1, column=0, padx=20, pady=15, sticky="w")
        
        self.check_date = ctk.CTkEntry(
            input_frame,
            placeholder_text="YYYY-MM-DD",
            width=200,
            font=ctk.CTkFont(size=14)
        )
        self.check_date.grid(row=1, column=1, padx=10, pady=15)
        
        # Check button
        check_btn = ctk.CTkButton(
            input_frame,
            text="✅ Check Status",
            command=self.check_refund_status,
            width=200,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        check_btn.grid(row=1, column=2, columnspan=2, padx=20, pady=15)
        
        # Results frame
        self.check_results_frame = ctk.CTkFrame(self.content_frame)
        self.check_results_frame.grid(row=2, column=0, padx=30, pady=20, sticky="nsew")
        self.content_frame.grid_rowconfigure(2, weight=1)
    
    def check_refund_status(self):
        """Check if a charge was refunded"""
        merchant = self.check_merchant.get()
        amount_str = self.check_amount.get()
        date_str = self.check_date.get()
        
        if not all([merchant, amount_str, date_str]):
            messagebox.showwarning("Input Error", "Please fill all fields")
            return
        
        try:
            amount = float(amount_str)
            charge_date = pd.to_datetime(date_str)
        except:
            messagebox.showerror("Input Error", "Invalid amount or date format")
            return
        
        # Clear previous results
        for widget in self.check_results_frame.winfo_children():
            widget.destroy()
        
        # Search for refund
        search_start = charge_date
        search_end = charge_date + timedelta(days=60)
        
        merchant_mask = self.df['merchant_standardized'].str.contains(
            merchant.upper(), case=False, na=False
        )
        date_mask = (self.df['date'] >= search_start) & (self.df['date'] <= search_end)
        amount_mask = abs(self.df['amount'] - abs(amount)) < 0.01
        refund_mask = self.df['amount'] > 0
        
        potential_refunds = self.df[merchant_mask & date_mask & amount_mask & refund_mask]
        
        # Display results
        result_frame = ctk.CTkFrame(self.check_results_frame, corner_radius=10)
        result_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        
        # Original charge info
        charge_info = ctk.CTkLabel(
            result_frame,
            text=f"Original Charge: {merchant} - ${amount:.2f} on {date_str}",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        charge_info.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        if len(potential_refunds) > 0:
            # Refund found
            status = ctk.CTkLabel(
                result_frame,
                text="✅ REFUND FOUND",
                font=ctk.CTkFont(size=18, weight="bold"),
                text_color="#28a745"
            )
            status.grid(row=1, column=0, padx=20, pady=10, sticky="w")
            
            for _, refund in potential_refunds.iterrows():
                refund_text = f"📅 {refund['date'].strftime('%Y-%m-%d')} - ${refund['amount']:,.2f}"
                refund_label = ctk.CTkLabel(
                    result_frame,
                    text=refund_text,
                    font=ctk.CTkFont(size=12)
                )
                refund_label.grid(row=2, column=0, padx=40, pady=5, sticky="w")
        else:
            # No refund found
            status = ctk.CTkLabel(
                result_frame,
                text="❌ NO REFUND FOUND",
                font=ctk.CTkFont(size=18, weight="bold"),
                text_color="#dc3545"
            )
            status.grid(row=1, column=0, padx=20, pady=10, sticky="w")
            
            info = ctk.CTkLabel(
                result_frame,
                text="No matching refund found within 60 days of the charge",
                font=ctk.CTkFont(size=12),
                text_color=("gray60", "gray40")
            )
            info.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="w")
    
    def show_dispute_analysis(self):
        """Show comprehensive dispute analysis"""
        self.clear_content()
        
        title = ctk.CTkLabel(
            self.content_frame,
            text="Comprehensive Dispute Analysis",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        title.grid(row=0, column=0, padx=30, pady=(30, 20), sticky="w")
        
        # Calculate statistics
        total_disputes = self.df['potential_refund'].sum()
        dispute_df = self.df[self.df['potential_refund'] == True]
        
        if total_disputes > 0:
            # Stats cards
            stats_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
            stats_frame.grid(row=1, column=0, padx=30, pady=10, sticky="ew")
            stats_frame.grid_columnconfigure((0,1,2), weight=1)
            
            total_amount = dispute_df['amount'].sum()
            date_range = f"{dispute_df['date'].min().strftime('%b %Y')} - {dispute_df['date'].max().strftime('%b %Y')}"
            
            stats = [
                ("Total Disputes", f"{total_disputes:,}", "error"),
                ("Total Amount", f"${abs(total_amount):,.0f}", "warning"),
                ("Date Range", date_range, "info")
            ]
            
            for i, (label, value, color) in enumerate(stats):
                self.create_metric_card(stats_frame, label, value, i, color)
            
            # Top merchants with disputes
            merchants_frame = ctk.CTkFrame(self.content_frame)
            merchants_frame.grid(row=2, column=0, padx=30, pady=20, sticky="nsew")
            self.content_frame.grid_rowconfigure(2, weight=1)
            
            merchants_title = ctk.CTkLabel(
                merchants_frame,
                text="Top Merchants with Disputes",
                font=ctk.CTkFont(size=18, weight="bold")
            )
            merchants_title.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
            
            # Create merchant analysis
            merchant_disputes = dispute_df.groupby('merchant_standardized').agg({
                'amount': ['count', 'sum']
            }).round(2)
            merchant_disputes.columns = ['Count', 'Total Amount']
            merchant_disputes = merchant_disputes.sort_values('Count', ascending=False).head(10)
            
            # Display as cards
            scroll_frame = ctk.CTkScrollableFrame(merchants_frame)
            scroll_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
            merchants_frame.grid_rowconfigure(1, weight=1)
            merchants_frame.grid_columnconfigure(0, weight=1)
            
            for i, (merchant, row) in enumerate(merchant_disputes.iterrows()):
                card = ctk.CTkFrame(scroll_frame, corner_radius=10)
                card.grid(row=i, column=0, padx=10, pady=5, sticky="ew")
                scroll_frame.grid_columnconfigure(0, weight=1)
                
                merchant_name = ctk.CTkLabel(
                    card,
                    text=merchant[:40],
                    font=ctk.CTkFont(size=14, weight="bold")
                )
                merchant_name.grid(row=0, column=0, padx=15, pady=(10, 5), sticky="w")
                
                stats_text = f"Disputes: {int(row['Count'])} | Amount: ${abs(row['Total Amount']):,.2f}"
                stats_label = ctk.CTkLabel(
                    card,
                    text=stats_text,
                    font=ctk.CTkFont(size=12),
                    text_color=("gray60", "gray40")
                )
                stats_label.grid(row=1, column=0, padx=15, pady=(0, 10), sticky="w")
        else:
            no_disputes = ctk.CTkLabel(
                self.content_frame,
                text="No disputes found in the dataset",
                font=ctk.CTkFont(size=16),
                text_color=("gray60", "gray40")
            )
            no_disputes.grid(row=1, column=0, padx=30, pady=20)
    
    def show_advanced_search(self):
        """Show advanced search interface"""
        self.clear_content()
        
        title = ctk.CTkLabel(
            self.content_frame,
            text="Advanced Search",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        title.grid(row=0, column=0, padx=30, pady=(30, 20), sticky="w")
        
        # Search options frame
        search_frame = ctk.CTkFrame(self.content_frame)
        search_frame.grid(row=1, column=0, padx=30, pady=10, sticky="ew")
        
        # Date range
        date_label = ctk.CTkLabel(
            search_frame,
            text="Date Range:",
            font=ctk.CTkFont(size=14)
        )
        date_label.grid(row=0, column=0, padx=20, pady=15, sticky="w")
        
        self.start_date = ctk.CTkEntry(
            search_frame,
            placeholder_text="Start (YYYY-MM-DD)",
            width=150,
            font=ctk.CTkFont(size=14)
        )
        self.start_date.grid(row=0, column=1, padx=10, pady=15)
        
        to_label = ctk.CTkLabel(
            search_frame,
            text="to",
            font=ctk.CTkFont(size=14)
        )
        to_label.grid(row=0, column=2, padx=10, pady=15)
        
        self.end_date = ctk.CTkEntry(
            search_frame,
            placeholder_text="End (YYYY-MM-DD)",
            width=150,
            font=ctk.CTkFont(size=14)
        )
        self.end_date.grid(row=0, column=3, padx=10, pady=15)
        
        # Amount range
        amount_label = ctk.CTkLabel(
            search_frame,
            text="Amount Range:",
            font=ctk.CTkFont(size=14)
        )
        amount_label.grid(row=1, column=0, padx=20, pady=15, sticky="w")
        
        self.min_amount = ctk.CTkEntry(
            search_frame,
            placeholder_text="Min amount",
            width=150,
            font=ctk.CTkFont(size=14)
        )
        self.min_amount.grid(row=1, column=1, padx=10, pady=15)
        
        to_label2 = ctk.CTkLabel(
            search_frame,
            text="to",
            font=ctk.CTkFont(size=14)
        )
        to_label2.grid(row=1, column=2, padx=10, pady=15)
        
        self.max_amount = ctk.CTkEntry(
            search_frame,
            placeholder_text="Max amount",
            width=150,
            font=ctk.CTkFont(size=14)
        )
        self.max_amount.grid(row=1, column=3, padx=10, pady=15)
        
        # Merchant filter
        merchant_label = ctk.CTkLabel(
            search_frame,
            text="Merchant Contains:",
            font=ctk.CTkFont(size=14)
        )
        merchant_label.grid(row=2, column=0, padx=20, pady=15, sticky="w")
        
        self.adv_merchant = ctk.CTkEntry(
            search_frame,
            placeholder_text="Enter merchant name",
            width=330,
            font=ctk.CTkFont(size=14)
        )
        self.adv_merchant.grid(row=2, column=1, columnspan=3, padx=10, pady=15, sticky="w")
        
        # Options
        self.only_disputes = ctk.CTkCheckBox(
            search_frame,
            text="Only show potential disputes",
            font=ctk.CTkFont(size=14)
        )
        self.only_disputes.grid(row=3, column=0, columnspan=2, padx=20, pady=15, sticky="w")
        
        # Search button
        search_btn = ctk.CTkButton(
            search_frame,
            text="🔍 Search",
            command=self.perform_advanced_search,
            width=150,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        search_btn.grid(row=3, column=3, padx=20, pady=15)
        
        # Results frame
        self.adv_results_frame = ctk.CTkFrame(self.content_frame)
        self.adv_results_frame.grid(row=2, column=0, padx=30, pady=20, sticky="nsew")
        self.content_frame.grid_rowconfigure(2, weight=1)
    
    def perform_advanced_search(self):
        """Perform advanced search"""
        # Build query
        filtered = self.df.copy()
        
        # Date filter
        if self.start_date.get():
            try:
                start = pd.to_datetime(self.start_date.get())
                filtered = filtered[filtered['date'] >= start]
            except:
                pass
        
        if self.end_date.get():
            try:
                end = pd.to_datetime(self.end_date.get())
                filtered = filtered[filtered['date'] <= end]
            except:
                pass
        
        # Amount filter
        if self.min_amount.get():
            try:
                min_amt = float(self.min_amount.get())
                filtered = filtered[filtered['amount_abs'] >= min_amt]
            except:
                pass
        
        if self.max_amount.get():
            try:
                max_amt = float(self.max_amount.get())
                filtered = filtered[filtered['amount_abs'] <= max_amt]
            except:
                pass
        
        # Merchant filter
        if self.adv_merchant.get():
            filtered = filtered[
                filtered['merchant_standardized'].str.contains(
                    self.adv_merchant.get().upper(), case=False, na=False
                )
            ]
        
        # Dispute filter
        if self.only_disputes.get():
            filtered = filtered[filtered['potential_refund'] == True]
        
        # Clear previous results
        for widget in self.adv_results_frame.winfo_children():
            widget.destroy()
        
        # Display results
        if len(filtered) > 0:
            summary = ctk.CTkLabel(
                self.adv_results_frame,
                text=f"Found {len(filtered)} matching transactions",
                font=ctk.CTkFont(size=16, weight="bold")
            )
            summary.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
            
            # Export button
            export_btn = ctk.CTkButton(
                self.adv_results_frame,
                text="💾 Export Results",
                command=lambda: self.export_results(filtered),
                width=150,
                height=35,
                font=ctk.CTkFont(size=12)
            )
            export_btn.grid(row=0, column=1, padx=20, pady=(20, 10), sticky="e")
            self.adv_results_frame.grid_columnconfigure(1, weight=1)
            
            # Table
            table_frame = ctk.CTkFrame(self.adv_results_frame)
            table_frame.grid(row=1, column=0, columnspan=2, padx=20, pady=10, sticky="nsew")
            self.adv_results_frame.grid_rowconfigure(1, weight=1)
            
            self.create_data_table(table_frame, filtered.head(100))
        else:
            no_results = ctk.CTkLabel(
                self.adv_results_frame,
                text="No transactions match your search criteria",
                font=ctk.CTkFont(size=16),
                text_color=("gray60", "gray40")
            )
            no_results.grid(row=0, column=0, padx=20, pady=20)
    
    def show_export(self):
        """Show export options"""
        self.clear_content()
        
        title = ctk.CTkLabel(
            self.content_frame,
            text="Export Data",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        title.grid(row=0, column=0, padx=30, pady=(30, 20), sticky="w")
        
        # Export options
        options_frame = ctk.CTkFrame(self.content_frame)
        options_frame.grid(row=1, column=0, padx=30, pady=20, sticky="ew")
        
        export_options = [
            ("📊 All Transactions", lambda: self.export_results(self.df, "all_transactions")),
            ("🔴 All Disputes", lambda: self.export_results(
                self.df[self.df['potential_refund'] == True], "all_disputes"
            )),
            ("📅 Last 30 Days", lambda: self.export_results(
                self.df[self.df['date'] >= datetime.now() - timedelta(days=30)], "last_30_days"
            )),
            ("✅ All Refunds (Credits)", lambda: self.export_results(
                self.df[self.df['amount'] > 0], "all_refunds"
            ))
        ]
        
        for i, (label, command) in enumerate(export_options):
            btn = ctk.CTkButton(
                options_frame,
                text=label,
                command=command,
                width=250,
                height=50,
                font=ctk.CTkFont(size=14),
                anchor="w"
            )
            btn.grid(row=i//2, column=i%2, padx=20, pady=10)
    
    def export_results(self, data, prefix="export"):
        """Export results to Excel"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.xlsx"
        filepath = Path("output") / filename
        
        try:
            data.to_excel(filepath, index=False)
            messagebox.showinfo("Export Successful", 
                              f"Exported {len(data)} records to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export: {str(e)}")

def main():
    # Check if customtkinter is installed
    try:
        import customtkinter
    except ImportError:
        print("Installing required package: customtkinter...")
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "customtkinter"])
        print("Package installed. Please restart the script.")
        return
    
    app = DisputeAnalyzerGUI()
    app.mainloop()

if __name__ == "__main__":
    main()