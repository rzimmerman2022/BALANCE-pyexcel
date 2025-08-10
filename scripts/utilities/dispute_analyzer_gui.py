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
import numpy as np
from typing import Optional, Dict, List, Tuple
import json

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")  # Modes: "System", "Dark", "Light"
ctk.set_default_color_theme("dark-blue")  # Enhanced theme for professional look

# Custom color palette for modern aesthetics
COLORS = {
    'primary': '#1e88e5',      # Bright blue
    'secondary': '#00acc1',    # Cyan
    'success': '#43a047',      # Green
    'warning': '#fb8c00',      # Orange
    'danger': '#e53935',       # Red
    'info': '#5e35b1',         # Purple
    'dark': '#1a1a2e',         # Dark background
    'card': '#16213e',         # Card background
    'text': '#ffffff',         # Primary text
    'text_secondary': '#b0b0b0', # Secondary text
    'accent': '#00d4ff',       # Accent color
    'gradient_start': '#667eea',
    'gradient_end': '#764ba2'
}

class DisputeAnalyzerGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("BALANCE - Dispute & Refund Analyzer v2.0")
        self.geometry("1600x900")
        self.minsize(1200, 700)
        
        # Center window on screen
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
        
        # Configure window icon (if available)
        try:
            self.iconbitmap(default='icon.ico')
        except:
            pass
        
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
        
        # Enhanced Logo/Title with gradient effect
        logo_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=20, pady=(20, 5))
        
        logo_label = ctk.CTkLabel(
            logo_frame, 
            text="🏦 BALANCE", 
            font=ctk.CTkFont(family="Segoe UI", size=32, weight="bold"),
            text_color=COLORS['accent']
        )
        logo_label.pack()
        
        subtitle = ctk.CTkLabel(
            sidebar, 
            text="Dispute & Refund Analyzer", 
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color=COLORS['text_secondary']
        )
        subtitle.grid(row=1, column=0, padx=20, pady=(0, 20))
        
        # Add animated separator line
        separator = ctk.CTkFrame(sidebar, height=2, fg_color=COLORS['accent'])
        separator.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))
        
        # Navigation buttons
        self.nav_buttons = []
        
        buttons_config = [
            ("📊 Dashboard", self.show_dashboard, "View key metrics and recent activity"),
            ("🔍 Find Refunds", self.show_refund_search, "Search for merchant refunds"),
            ("👥 Duplicate Charges", self.show_duplicate_finder, "Detect duplicate transactions"),
            ("✅ Check Refund Status", self.show_refund_checker, "Verify specific refunds"),
            ("📈 Dispute Analysis", self.show_dispute_analysis, "Comprehensive analysis"),
            ("🔎 Advanced Search", self.show_advanced_search, "Multi-filter search"),
            ("💾 Export Data", self.show_export, "Export to Excel")
        ]
        
        self.selected_button = None
        for i, (text, command, tooltip) in enumerate(buttons_config):
            btn = ctk.CTkButton(
                sidebar,
                text=text,
                command=lambda cmd=command, b=i: self.navigate_to(cmd, b),
                height=45,
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                fg_color="transparent",
                text_color=COLORS['text_secondary'],
                hover_color=COLORS['card'],
                anchor="w",
                corner_radius=10
            )
            btn.grid(row=i+3, column=0, padx=20, pady=3, sticky="ew")
            self.nav_buttons.append(btn)
            
            # Add tooltip on hover (store for later use)
            btn.tooltip = tooltip
        
        # Data info at bottom
        if self.df is not None:
            # Enhanced info frame with gradient border
            info_frame = ctk.CTkFrame(
                sidebar, 
                corner_radius=15,
                fg_color=COLORS['card'],
                border_width=2,
                border_color=COLORS['accent']
            )
            info_frame.grid(row=11, column=0, padx=20, pady=20, sticky="ew")
            
            # Stats with icons
            stats_text = f"📊 Statistics\n"
            stats_text += f"├─ 📁 {len(self.df):,} transactions\n"
            stats_text += f"├─ 📅 {self.df['date'].min().strftime('%b %d, %Y')}\n"
            stats_text += f"└─ 📅 {self.df['date'].max().strftime('%b %d, %Y')}"
            
            info_label = ctk.CTkLabel(
                info_frame,
                text=stats_text,
                font=ctk.CTkFont(family="Consolas", size=11),
                justify="left",
                text_color=COLORS['text_secondary']
            )
            info_label.grid(row=0, column=0, padx=15, pady=15)
    
    def navigate_to(self, command, button_index):
        """Navigate to a section with button highlighting"""
        # Reset all buttons
        for btn in self.nav_buttons:
            btn.configure(
                fg_color="transparent",
                text_color=COLORS['text_secondary']
            )
        
        # Highlight selected button
        self.nav_buttons[button_index].configure(
            fg_color=COLORS['primary'],
            text_color=COLORS['text']
        )
        self.selected_button = button_index
        
        # Execute command
        command()
    
    def create_main_content(self):
        """Create the main content area with enhanced styling"""
        self.content_frame = ctk.CTkFrame(
            self.main_container, 
            corner_radius=15,
            fg_color=COLORS['dark']
        )
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=20)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(1, weight=1)
    
    def clear_content(self):
        """Clear the content frame"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def show_dashboard(self):
        """Show the main dashboard with modern design"""
        self.clear_content()
        
        # Header with gradient background effect
        header_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(30, 20))
        header_frame.grid_columnconfigure(1, weight=1)
        
        # Title with modern typography
        title = ctk.CTkLabel(
            header_frame,
            text="Dashboard Overview",
            font=ctk.CTkFont(family="Segoe UI", size=32, weight="bold"),
            text_color=COLORS['text']
        )
        title.grid(row=0, column=0, sticky="w")
        
        # Add real-time indicator
        time_label = ctk.CTkLabel(
            header_frame,
            text=f"Last updated: {datetime.now().strftime('%I:%M %p')}",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLORS['text_secondary']
        )
        time_label.grid(row=0, column=1, sticky="e")
        
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
        
        # Enhanced table with modern styling
        table_frame = ctk.CTkFrame(
            self.content_frame,
            corner_radius=15,
            fg_color=COLORS['card']
        )
        table_frame.grid(row=2, column=0, padx=30, pady=20, sticky="nsew")
        self.content_frame.grid_rowconfigure(2, weight=1)
        
        # Table header with actions
        table_header = ctk.CTkFrame(table_frame, fg_color="transparent")
        table_header.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        table_header.grid_columnconfigure(1, weight=1)
        
        table_title = ctk.CTkLabel(
            table_header,
            text="⚠️ Recent Potential Disputes",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=COLORS['text']
        )
        table_title.grid(row=0, column=0, sticky="w")
        
        # Quick action buttons
        action_frame = ctk.CTkFrame(table_header, fg_color="transparent")
        action_frame.grid(row=0, column=1, sticky="e")
        
        export_btn = ctk.CTkButton(
            action_frame,
            text="Export",
            width=80,
            height=30,
            corner_radius=8,
            fg_color=COLORS['primary'],
            hover_color=COLORS['secondary'],
            font=ctk.CTkFont(size=12)
        )
        export_btn.pack(side="right", padx=5)
        
        # Create enhanced treeview for table
        tree_container = ctk.CTkFrame(table_frame, fg_color="transparent")
        tree_container.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        table_frame.grid_rowconfigure(1, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        self.create_data_table(
            tree_container,
            self.df[self.df['potential_refund'] == True].tail(20)
        )
        
        # Add summary stats at bottom
        stats_frame = ctk.CTkFrame(table_frame, fg_color="transparent", height=40)
        stats_frame.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="ew")
        
        disputes_shown = min(20, len(self.df[self.df['potential_refund'] == True]))
        stats_label = ctk.CTkLabel(
            stats_frame,
            text=f"Showing {disputes_shown} of {len(self.df[self.df['potential_refund'] == True])} total disputes",
            font=ctk.CTkFont(size=11),
            text_color=COLORS['text_secondary']
        )
        stats_label.pack(side="left")
    
    def create_metric_card(self, parent, label, value, column, color_type="info"):
        """Create an enhanced metric card with animations"""
        colors = {
            "error": COLORS['danger'],
            "warning": COLORS['warning'],
            "info": COLORS['info'],
            "success": COLORS['success']
        }
        
        # Enhanced card with gradient border and shadow effect
        card = ctk.CTkFrame(
            parent, 
            corner_radius=15,
            fg_color=COLORS['card'],
            border_width=2,
            border_color=colors.get(color_type, COLORS['info'])
        )
        card.grid(row=0, column=column, padx=8, pady=10, sticky="ew")
        
        # Icon background circle
        icon_frame = ctk.CTkFrame(
            card,
            width=50,
            height=50,
            corner_radius=25,
            fg_color=colors.get(color_type, COLORS['info'])
        )
        icon_frame.grid(row=0, column=0, rowspan=2, padx=20, pady=20)
        icon_frame.grid_propagate(False)
        
        # Add icon emoji
        icon_map = {
            "🔴 Total Disputes": "⚠️",
            "💰 Dispute Amount": "💸",
            "📅 Recent (30d)": "📊",
            "✅ Total Refunds": "✔️"
        }
        icon_text = icon_map.get(label, "📊")
        icon_label = ctk.CTkLabel(
            icon_frame,
            text=icon_text,
            font=ctk.CTkFont(size=24)
        )
        icon_label.place(relx=0.5, rely=0.5, anchor="center")
        
        # Metric details
        details_frame = ctk.CTkFrame(card, fg_color="transparent")
        details_frame.grid(row=0, column=1, rowspan=2, padx=(0, 20), pady=15, sticky="w")
        
        label_widget = ctk.CTkLabel(
            details_frame,
            text=label.split(' ', 1)[1] if ' ' in label else label,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=COLORS['text_secondary']
        )
        label_widget.grid(row=0, column=0, sticky="w")
        
        value_widget = ctk.CTkLabel(
            details_frame,
            text=value,
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
            text_color=COLORS['text']
        )
        value_widget.grid(row=1, column=0, sticky="w")
        
        # Add trend indicator (placeholder for future implementation)
        trend_frame = ctk.CTkFrame(card, fg_color="transparent")
        trend_frame.grid(row=0, column=2, rowspan=2, padx=(0, 20), pady=15, sticky="e")
        
        # Simulate trend
        import random
        trend = random.choice(["↑", "↓", "→"])
        trend_color = COLORS['success'] if trend == "↑" else COLORS['danger'] if trend == "↓" else COLORS['text_secondary']
        trend_label = ctk.CTkLabel(
            trend_frame,
            text=trend,
            font=ctk.CTkFont(size=20),
            text_color=trend_color
        )
        trend_label.pack()
    
    def create_data_table(self, parent, data):
        """Create a data table with treeview"""
        # Create frame for treeview and scrollbars
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill="both", expand=True)
        
        # Configure modern style
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", 
                       background=COLORS['dark'],
                       foreground=COLORS['text'],
                       fieldbackground=COLORS['dark'],
                       borderwidth=0,
                       rowheight=30)
        style.configure("Treeview.Heading",
                       background=COLORS['card'],
                       foreground=COLORS['text'],
                       borderwidth=0,
                       relief="flat")
        style.map("Treeview", 
                 background=[("selected", COLORS['primary'])],
                 foreground=[("selected", COLORS['text'])])
        
        # Create scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        
        # Create enhanced treeview with better columns
        columns = ['Date', 'Merchant', 'Amount', 'Status', 'Description']
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings',
                          yscrollcommand=vsb.set, xscrollcommand=hsb.set,
                          height=12,
                          selectmode='browse')
        
        vsb.config(command=tree.yview)
        hsb.config(command=tree.xview)
        
        # Configure columns with better widths and alignments
        column_configs = {
            'Date': {'width': 100, 'anchor': 'center'},
            'Merchant': {'width': 200, 'anchor': 'w'},
            'Amount': {'width': 100, 'anchor': 'e'},
            'Status': {'width': 100, 'anchor': 'center'},
            'Description': {'width': 400, 'anchor': 'w'}
        }
        
        for col in columns:
            config = column_configs.get(col, {'width': 150, 'anchor': 'w'})
            tree.heading(col, text=col)
            tree.column(col, width=config['width'], anchor=config['anchor'])
        
        # Add data with status indicators
        for idx, row in data.iterrows():
            # Determine status
            if row['potential_refund']:
                status = "⚠️ Dispute"
            elif row['amount'] > 0:
                status = "✅ Refund"
            else:
                status = "📝 Charge"
            
            values = [
                row['date'].strftime('%m/%d/%Y'),
                row['merchant_standardized'][:30],
                f"${abs(row['amount']):,.2f}",
                status,
                str(row['description'])[:50] if pd.notna(row['description']) else ''
            ]
            
            # Add with alternating row colors (tag-based)
            tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
            tree.insert('', 'end', values=values, tags=(tag,))
        
        # Configure tag colors for alternating rows
        tree.tag_configure('evenrow', background=COLORS['dark'])
        tree.tag_configure('oddrow', background=COLORS['card'])
        
        # Pack everything
        tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
    
    def show_refund_search(self):
        """Show enhanced refund search interface"""
        self.clear_content()
        
        # Header
        header_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(30, 20))
        
        title = ctk.CTkLabel(
            header_frame,
            text="🔍 Find Refunds by Merchant",
            font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"),
            text_color=COLORS['text']
        )
        title.pack(side="left")
        
        subtitle = ctk.CTkLabel(
            header_frame,
            text="Search for merchant refunds and credits",
            font=ctk.CTkFont(size=12),
            text_color=COLORS['text_secondary']
        )
        subtitle.pack(side="left", padx=(20, 0))
        
        # Enhanced search frame with modern design
        search_frame = ctk.CTkFrame(
            self.content_frame,
            corner_radius=15,
            fg_color=COLORS['card'],
            border_width=2,
            border_color=COLORS['primary']
        )
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
            width=350,
            height=40,
            corner_radius=10,
            border_width=2,
            border_color=COLORS['accent'],
            font=ctk.CTkFont(family="Segoe UI", size=14)
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
        
        # Enhanced search button with hover effect
        search_btn = ctk.CTkButton(
            search_frame,
            text="🔍 Search",
            command=self.search_refunds,
            width=150,
            height=40,
            corner_radius=10,
            fg_color=COLORS['primary'],
            hover_color=COLORS['secondary'],
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")
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
        """Show enhanced duplicate charge finder"""
        self.clear_content()
        
        # Header with icon and description
        header_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(30, 20))
        
        title = ctk.CTkLabel(
            header_frame,
            text="👥 Find Duplicate Charges",
            font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"),
            text_color=COLORS['text']
        )
        title.pack(anchor="w")
        
        desc = ctk.CTkLabel(
            header_frame,
            text="Detect potential duplicate transactions within a specified time window",
            font=ctk.CTkFont(size=12),
            text_color=COLORS['text_secondary']
        )
        desc.pack(anchor="w", pady=(5, 0))
        
        # Enhanced settings frame
        settings_frame = ctk.CTkFrame(
            self.content_frame,
            corner_radius=15,
            fg_color=COLORS['card']
        )
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
        
        # Enhanced search button
        search_btn = ctk.CTkButton(
            settings_frame,
            text="🔍 Find Duplicates",
            command=self.find_duplicates,
            width=200,
            height=40,
            corner_radius=10,
            fg_color=COLORS['warning'],
            hover_color=COLORS['primary'],
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")
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
            
            # Display each duplicate as an enhanced card
            for i, dup in enumerate(duplicates[:20]):  # Limit to 20 for performance
                card = ctk.CTkFrame(
                    scroll_frame, 
                    corner_radius=12,
                    fg_color=COLORS['card'],
                    border_width=2,
                    border_color=COLORS['warning']
                )
                card.grid(row=i, column=0, padx=10, pady=8, sticky="ew")
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
        """Show enhanced advanced search interface"""
        self.clear_content()
        
        # Header
        header_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(30, 20))
        
        title = ctk.CTkLabel(
            header_frame,
            text="🔎 Advanced Search",
            font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"),
            text_color=COLORS['text']
        )
        title.pack(anchor="w")
        
        desc = ctk.CTkLabel(
            header_frame,
            text="Apply multiple filters to find specific transactions",
            font=ctk.CTkFont(size=12),
            text_color=COLORS['text_secondary']
        )
        desc.pack(anchor="w", pady=(5, 0))
        
        # Enhanced search options frame
        search_frame = ctk.CTkFrame(
            self.content_frame,
            corner_radius=15,
            fg_color=COLORS['card']
        )
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
        
        # Enhanced search button
        search_btn = ctk.CTkButton(
            search_frame,
            text="🔍 Search",
            command=self.perform_advanced_search,
            width=150,
            height=40,
            corner_radius=10,
            fg_color=COLORS['info'],
            hover_color=COLORS['primary'],
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")
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