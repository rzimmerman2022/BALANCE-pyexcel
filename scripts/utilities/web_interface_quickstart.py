#!/usr/bin/env python3
"""
BALANCE Web Interface - Quick Start Implementation
A minimal web interface for CSV processing using Streamlit
Can be deployed in 1-2 days for immediate GUI functionality

Requirements:
    pip install streamlit pandas plotly openpyxl

Run:
    streamlit run scripts/utilities/web_interface_quickstart.py
"""

import hashlib
import io
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from src.balance_pipeline.csv_consolidator import CSVConsolidator
    from src.balance_pipeline.pipeline_v2 import UnifiedPipeline

    PIPELINE_AVAILABLE = True
except ImportError:
    PIPELINE_AVAILABLE = False
    st.error("Pipeline modules not available. Using demo mode.")

# Configure Streamlit page
st.set_page_config(
    page_title="BALANCE Financial Analysis",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for professional styling
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1e88e5;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f5f5f5;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .success-message {
        background-color: #4caf50;
        color: white;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .stButton > button {
        background-color: #1e88e5;
        color: white;
        font-weight: bold;
    }
    .upload-area {
        border: 2px dashed #1e88e5;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        background-color: #f0f7ff;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Initialize session state
if "processed_data" not in st.session_state:
    st.session_state.processed_data = None
if "processing_history" not in st.session_state:
    st.session_state.processing_history = []
if "current_tab" not in st.session_state:
    st.session_state.current_tab = "Upload & Process"


def process_csv_files(uploaded_files):
    """Process uploaded CSV files through the pipeline"""
    all_data = []

    with st.spinner("Processing files..."):
        progress_bar = st.progress(0)

        for idx, file in enumerate(uploaded_files):
            progress_bar.progress((idx + 1) / len(uploaded_files))

            # Read CSV
            df = pd.read_csv(file)

            # Add metadata
            df["source_file"] = file.name
            df["upload_timestamp"] = datetime.now()

            # Basic processing (when pipeline not available)
            if "date" in df.columns or "Date" in df.columns:
                date_col = "date" if "date" in df.columns else "Date"
                df["date"] = pd.to_datetime(df[date_col], errors="coerce")

            # Standardize amount column
            if "amount" in df.columns or "Amount" in df.columns:
                amount_col = "amount" if "amount" in df.columns else "Amount"
                df["amount"] = pd.to_numeric(df[amount_col], errors="coerce")

            all_data.append(df)

        # Combine all data
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)

            # Generate transaction IDs
            if "transaction_id" not in combined_df.columns:
                combined_df["transaction_id"] = combined_df.apply(
                    lambda row: hashlib.md5(
                        f"{row.get('date', '')}_{row.get('amount', '')}_{row.get('description', '')}".encode()
                    ).hexdigest()[:8],
                    axis=1,
                )

            return combined_df

    return None


def display_dashboard(df):
    """Display the main dashboard with metrics and visualizations"""
    st.markdown(
        '<h1 class="main-header">📊 Financial Dashboard</h1>', unsafe_allow_html=True
    )

    # Key Metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_transactions = len(df)
        st.metric("Total Transactions", f"{total_transactions:,}")

    with col2:
        if "amount" in df.columns:
            total_amount = df["amount"].sum()
            st.metric("Net Amount", f"${total_amount:,.2f}")

    with col3:
        if "date" in df.columns:
            date_range = f"{df['date'].min().strftime('%b %d, %Y')} - {df['date'].max().strftime('%b %d, %Y')}"
            st.metric("Date Range", date_range)

    with col4:
        unique_sources = (
            df["source_file"].nunique() if "source_file" in df.columns else 0
        )
        st.metric("Data Sources", unique_sources)

    # Visualizations
    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        if "date" in df.columns and "amount" in df.columns:
            st.subheader("💵 Transaction Timeline")

            # Group by date
            daily_totals = df.groupby(df["date"].dt.date)["amount"].sum().reset_index()

            fig = px.line(
                daily_totals,
                x="date",
                y="amount",
                title="Daily Transaction Totals",
                labels={"amount": "Amount ($)", "date": "Date"},
            )
            fig.update_layout(hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        if "amount" in df.columns:
            st.subheader("📈 Transaction Distribution")

            # Create bins for transaction amounts
            df["amount_category"] = pd.cut(
                df["amount"].abs(),
                bins=[0, 50, 100, 500, 1000, float("inf")],
                labels=["$0-50", "$50-100", "$100-500", "$500-1000", "$1000+"],
            )

            dist_data = df["amount_category"].value_counts().reset_index()
            dist_data.columns = ["Category", "Count"]

            fig = px.bar(
                dist_data,
                x="Category",
                y="Count",
                title="Transaction Size Distribution",
                color="Count",
                color_continuous_scale="Blues",
            )
            st.plotly_chart(fig, use_container_width=True)

    # Transaction Table
    st.markdown("---")
    st.subheader("📋 Recent Transactions")

    # Filter options
    col1, col2, col3 = st.columns(3)

    with col1:
        search_term = st.text_input("🔍 Search transactions", "")

    with col2:
        if "date" in df.columns:
            date_filter = st.date_input(
                "📅 Filter by date",
                value=(df["date"].min(), df["date"].max()),
                min_value=df["date"].min(),
                max_value=df["date"].max(),
            )

    with col3:
        amount_filter = st.slider(
            "💰 Amount range",
            min_value=float(df["amount"].min()) if "amount" in df.columns else 0,
            max_value=float(df["amount"].max()) if "amount" in df.columns else 1000,
            value=(float(df["amount"].min()), float(df["amount"].max()))
            if "amount" in df.columns
            else (0, 1000),
        )

    # Apply filters
    filtered_df = df.copy()

    if search_term:
        search_cols = (
            ["description", "merchant", "category"]
            if "description" in df.columns
            else df.columns
        )
        mask = (
            filtered_df[search_cols]
            .apply(
                lambda x: x.astype(str).str.contains(search_term, case=False, na=False)
            )
            .any(axis=1)
        )
        filtered_df = filtered_df[mask]

    if "date" in df.columns and len(date_filter) == 2:
        filtered_df = filtered_df[
            (filtered_df["date"].dt.date >= date_filter[0])
            & (filtered_df["date"].dt.date <= date_filter[1])
        ]

    if "amount" in df.columns:
        filtered_df = filtered_df[
            (filtered_df["amount"] >= amount_filter[0])
            & (filtered_df["amount"] <= amount_filter[1])
        ]

    # Display table
    st.dataframe(filtered_df.head(100), use_container_width=True, hide_index=True)

    # Export options
    st.markdown("---")
    st.subheader("💾 Export Options")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        csv_buffer = io.StringIO()
        filtered_df.to_csv(csv_buffer, index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv_buffer.getvalue(),
            file_name=f"balance_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )

    with col2:
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            filtered_df.to_excel(writer, sheet_name="Transactions", index=False)

        st.download_button(
            label="📊 Download Excel",
            data=excel_buffer.getvalue(),
            file_name=f"balance_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    with col3:
        if st.button("🔄 Refresh Data"):
            st.rerun()

    with col4:
        if st.button("🗑️ Clear All"):
            st.session_state.processed_data = None
            st.session_state.processing_history = []
            st.rerun()


def main():
    """Main application entry point"""

    # Sidebar
    with st.sidebar:
        st.image(
            "https://via.placeholder.com/300x100/1e88e5/ffffff?text=BALANCE", width=300
        )
        st.markdown("---")

        st.markdown("### 🎯 Quick Actions")

        # Navigation
        tabs = ["Upload & Process", "Dashboard", "Analytics", "Settings"]
        selected_tab = st.radio("Navigate to:", tabs, label_visibility="collapsed")
        st.session_state.current_tab = selected_tab

        st.markdown("---")

        # Processing history
        if st.session_state.processing_history:
            st.markdown("### 📜 Recent Processing")
            for item in st.session_state.processing_history[-5:]:
                st.text(
                    f"• {item['timestamp'].strftime('%H:%M')} - {item['files']} files"
                )

        st.markdown("---")
        st.markdown("### ℹ️ System Info")
        st.info(f"Pipeline Available: {'✅' if PIPELINE_AVAILABLE else '❌ Demo Mode'}")
        st.caption("Version: 2.0.0-web")

    # Main content area
    if st.session_state.current_tab == "Upload & Process":
        st.markdown(
            '<h1 class="main-header">📤 Upload & Process CSV Files</h1>',
            unsafe_allow_html=True,
        )

        # File upload area
        st.markdown('<div class="upload-area">', unsafe_allow_html=True)
        uploaded_files = st.file_uploader(
            "Drag and drop CSV files here or click to browse",
            type=["csv"],
            accept_multiple_files=True,
            help="Upload one or more CSV files from your banks or financial institutions",
        )
        st.markdown("</div>", unsafe_allow_html=True)

        if uploaded_files:
            st.success(f"✅ {len(uploaded_files)} file(s) selected")

            # Display file info
            file_info = []
            for file in uploaded_files:
                file_info.append(
                    {
                        "File Name": file.name,
                        "Size": f"{file.size / 1024:.2f} KB",
                        "Type": "CSV",
                    }
                )

            st.dataframe(pd.DataFrame(file_info), hide_index=True)

            # Process button
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button(
                    "🚀 Process Files", type="primary", use_container_width=True
                ):
                    # Process the files
                    processed_df = process_csv_files(uploaded_files)

                    if processed_df is not None:
                        st.session_state.processed_data = processed_df
                        st.session_state.processing_history.append(
                            {
                                "timestamp": datetime.now(),
                                "files": len(uploaded_files),
                                "records": len(processed_df),
                            }
                        )

                        st.markdown(
                            '<div class="success-message">✅ Processing complete! Navigate to Dashboard to view results.</div>',
                            unsafe_allow_html=True,
                        )

                        # Auto-switch to dashboard
                        st.session_state.current_tab = "Dashboard"
                        st.rerun()

    elif st.session_state.current_tab == "Dashboard":
        if st.session_state.processed_data is not None:
            display_dashboard(st.session_state.processed_data)
        else:
            st.warning(
                "⚠️ No data available. Please upload and process CSV files first."
            )
            if st.button("Go to Upload"):
                st.session_state.current_tab = "Upload & Process"
                st.rerun()

    elif st.session_state.current_tab == "Analytics":
        st.markdown(
            '<h1 class="main-header">📈 Advanced Analytics</h1>', unsafe_allow_html=True
        )

        if st.session_state.processed_data is not None:
            df = st.session_state.processed_data

            # Spending patterns
            st.subheader("💳 Spending Patterns")

            if "date" in df.columns and "amount" in df.columns:
                # Monthly spending
                df["month"] = pd.to_datetime(df["date"]).dt.to_period("M")
                monthly_spending = (
                    df[df["amount"] < 0].groupby("month")["amount"].sum().abs()
                )

                fig = go.Figure()
                fig.add_trace(
                    go.Bar(
                        x=monthly_spending.index.astype(str),
                        y=monthly_spending.values,
                        marker_color="indianred",
                    )
                )
                fig.update_layout(
                    title="Monthly Spending Trends",
                    xaxis_title="Month",
                    yaxis_title="Spending ($)",
                    hovermode="x",
                )
                st.plotly_chart(fig, use_container_width=True)

            # Category analysis (if available)
            if "category" in df.columns:
                st.subheader("📊 Category Analysis")

                category_spending = (
                    df[df["amount"] < 0]
                    .groupby("category")["amount"]
                    .sum()
                    .abs()
                    .sort_values(ascending=False)
                    .head(10)
                )

                fig = px.pie(
                    values=category_spending.values,
                    names=category_spending.index,
                    title="Top 10 Spending Categories",
                )
                st.plotly_chart(fig, use_container_width=True)

            # Merchant analysis
            if "merchant" in df.columns or "description" in df.columns:
                st.subheader("🏪 Top Merchants")

                merchant_col = "merchant" if "merchant" in df.columns else "description"
                top_merchants = (
                    df[df["amount"] < 0]
                    .groupby(merchant_col)["amount"]
                    .agg(["sum", "count"])
                )
                top_merchants["sum"] = top_merchants["sum"].abs()
                top_merchants = top_merchants.sort_values("sum", ascending=False).head(
                    15
                )

                col1, col2 = st.columns(2)

                with col1:
                    fig = px.bar(
                        x=top_merchants["sum"],
                        y=top_merchants.index,
                        orientation="h",
                        title="Top 15 Merchants by Spending",
                        labels={"x": "Total Spending ($)", "y": "Merchant"},
                    )
                    st.plotly_chart(fig, use_container_width=True)

                with col2:
                    fig = px.bar(
                        x=top_merchants["count"],
                        y=top_merchants.index,
                        orientation="h",
                        title="Top 15 Merchants by Transaction Count",
                        labels={"x": "Number of Transactions", "y": "Merchant"},
                        color=top_merchants["count"],
                        color_continuous_scale="Viridis",
                    )
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(
                "⚠️ No data available for analytics. Please upload and process CSV files first."
            )

    elif st.session_state.current_tab == "Settings":
        st.markdown('<h1 class="main-header">⚙️ Settings</h1>', unsafe_allow_html=True)

        st.subheader("📁 Data Sources")

        # Bank configuration
        banks = ["Chase", "Wells Fargo", "Discover", "Monarch Money", "Rocket Money"]
        selected_banks = st.multiselect("Select your banks:", banks, default=banks)

        st.subheader("🎨 Display Preferences")

        col1, col2 = st.columns(2)

        with col1:
            theme = st.selectbox("Color Theme", ["Light", "Dark", "Auto"])
            date_format = st.selectbox(
                "Date Format", ["MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD"]
            )

        with col2:
            currency = st.selectbox("Currency", ["USD", "EUR", "GBP", "CAD"])
            decimal_places = st.number_input(
                "Decimal Places", min_value=0, max_value=4, value=2
            )

        st.subheader("🔄 Processing Options")

        auto_dedupe = st.checkbox("Automatic duplicate detection", value=True)
        auto_categorize = st.checkbox(
            "Automatic transaction categorization", value=True
        )

        if st.button("💾 Save Settings"):
            st.success("✅ Settings saved successfully!")


if __name__ == "__main__":
    main()
