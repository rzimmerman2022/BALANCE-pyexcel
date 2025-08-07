from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Assuming config.py is accessible
from .config import AnalysisConfig

logger = logging.getLogger(__name__)

def _generate_dashboard_html(
    visualizations: dict[str, str], 
    alt_texts: dict[str, str],
    output_dir: Path,
    logger_instance: logging.Logger = logger
) -> Path:
    """Generate HTML dashboard."""
    logger_instance.info(f"Generating HTML dashboard in {output_dir}...")
    html_content = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Shared Expense Analysis Dashboard v2.3</title>
<style>body{font-family:'Inter',Arial,sans-serif;margin:20px;background-color:#f5f5f5;}
.container{max-width:1400px;margin:0 auto;background-color:white;padding:30px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1);}
h1{font-family:'Montserrat',sans-serif;text-align:center;margin-bottom:30px;}
.nav{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:20px;padding-bottom:15px;border-bottom:1px solid #eee;}
.nav-item{padding:8px 15px;background-color:#007ACC;color:white;text-decoration:none;border-radius:5px;font-size:14px;}
.section{margin-bottom:30px;padding-top:20px;} .section h2{margin-bottom:15px;border-bottom:1px solid #ddd;padding-bottom:8px;}
.visual-container{border:1px solid #ddd;padding:10px;background:#fafafa;min-height:400px;display:flex;align-items:center;justify-content:center;overflow:auto;}
iframe,img{max-width:100%;height:auto;border:none;border-radius:5px;}
.timestamp{text-align:center;color:#666;font-size:12px;margin-top:30px;}</style></head><body><div class="container"><h1>Expense Dashboard v2.3</h1><div class="nav">
"""
    for viz_name in sorted(visualizations.keys()):
        display_name = viz_name.replace("-", " ").title()
        html_content += f'<a href="#{viz_name}" class="nav-item">{display_name}</a>'
    
    html_content += '</div><div class="sections">'
    for viz_name, viz_path_str in sorted(visualizations.items()):
        viz_file_path = Path(viz_path_str) # Use the full path for checking suffix, but relative for src
        viz_relative_path = viz_file_path.name # Use only filename for src attribute
        display_name = viz_name.replace("-", " ").title()
        alt = alt_texts.get(viz_name, "Visualization")
        html_content += f'<div class="section" id="{viz_name}"><h2>{display_name}</h2><div class="visual-container">'
        if viz_file_path.suffix == ".html":
            html_content += f'<iframe src="{viz_relative_path}" title="{alt}" style="width:100%;height:600px;"></iframe>'
        elif viz_file_path.suffix == ".png":
            html_content += f'<img src="{viz_relative_path}" alt="{alt}">'
        else:
            html_content += f"<p>Cannot display {viz_relative_path}</p>"
        html_content += "</div></div>"
    
    html_content += f'</div><div class="timestamp">Generated: {datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S %Z")}</div></div></body></html>'

    dashboard_path = output_dir / "dashboard_v2.3.html"
    try:
        with open(dashboard_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger_instance.info(f"Successfully generated HTML dashboard: {dashboard_path}")
    except PermissionError as e:
        logger_instance.error(f"Permission denied writing HTML dashboard {dashboard_path}: {e}")
        raise
    except OSError as e:
        logger_instance.error(f"OS error writing HTML dashboard {dashboard_path}: {e}")
        raise
    except UnicodeEncodeError as e:
        logger_instance.error(f"Encoding error writing HTML dashboard {dashboard_path}: {e}")
        raise
    return dashboard_path


def _generate_executive_summary_pdf(
    summary_data: dict[str, Any], # Allow Any for values
    visualizations: dict[str, str],
    alt_texts: dict[str, str],
    recommendations: list[str],
    output_dir: Path,
    logger_instance: logging.Logger = logger
) -> Path:
    logger_instance.info(f"Generating Executive Summary PDF in {output_dir}...")
    pdf_path = output_dir / "executive_report_v2.3.pdf"
    doc = SimpleDocTemplate(
        str(pdf_path), pagesize=landscape(A4),
        topMargin=0.5*inch, bottomMargin=0.5*inch,
        leftMargin=0.5*inch, rightMargin=0.5*inch
    )
    story: list[Any] = [] # Story can contain various ReportLab flowables
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Justify", alignment=TA_LEFT))
    styles.add(ParagraphStyle(name="H1Custom", fontSize=20, leading=22, alignment=TA_CENTER, spaceAfter=20, textColor=colors.HexColor("#007ACC")))
    styles.add(ParagraphStyle(name="H2Custom", fontSize=16, leading=18, alignment=TA_LEFT, spaceAfter=10, spaceBefore=10, textColor=colors.HexColor("#005A99")))
    styles.add(ParagraphStyle(name="ItalicCustom", fontName="Helvetica-Oblique", fontSize=9, leading=11))


    story.append(Paragraph("Shared Expense Analysis - Executive Summary v2.3", styles["H1Custom"]))
    story.append(Paragraph(f"Report Date: {datetime.now(UTC).strftime('%B %d, %Y %Z')}", styles["Normal"]))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Key Metrics", styles["H2Custom"]))
    metrics_table_data = [["Metric", "Value"]] + [[k, str(v)] for k, v in summary_data.items()]
    table_width = A4[1] - 1*inch # landscape A4 width minus margins
    col_widths = [table_width * 0.4, table_width * 0.6]
    metrics_table = Table(metrics_table_data, colWidths=col_widths)
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#007ACC")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(metrics_table)
    story.append(PageBreak())

    story.append(Paragraph("Key Recommendations", styles["H2Custom"]))
    for i, rec in enumerate(recommendations, 1):
        story.append(Paragraph(f"{i}. {rec}", styles["Normal"]))
        story.append(Spacer(1, 0.1 * inch))
    story.append(PageBreak())

    story.append(Paragraph("Visualizations Overview", styles["H2Custom"]))
    for viz_name, viz_path_str in sorted(visualizations.items()):
        viz_file_path = Path(viz_path_str)
        if viz_file_path.suffix == ".png":
            story.append(Paragraph(viz_name.replace("-", " ").title(), styles["Heading3"]))
            try:
                # Ensure the image path is correct relative to where the PDF is being generated
                # If viz_path_str is already an absolute path or relative to CWD, it should work.
                # If it's relative to output_dir, ensure it's correctly formed.
                img = Image(str(viz_file_path.resolve())) # Use resolved absolute path
                
                img_width_pts, img_height_pts = img.imageWidth, img.imageHeight
                target_frame_width = A4[1] - 1*inch # landscape A4 width - margins
                target_frame_height = A4[0] - 1*inch - 1*inch # landscape A4 height - margins - space for title/alt
                
                scale_w = target_frame_width / img_width_pts if img_width_pts > target_frame_width else 1.0
                scale_h = target_frame_height / img_height_pts if img_height_pts > target_frame_height else 1.0
                final_scale_factor = min(scale_w, scale_h, 1.0) # Don't scale up

                img.drawWidth = img_width_pts * final_scale_factor
                img.drawHeight = img_height_pts * final_scale_factor
                story.append(img)
            except Exception as img_err:
                logger_instance.warning(f"Placeholder image missing; skipping image block: {viz_file_path.name} - {img_err}")
                story.append(Paragraph(f"[Image not available: {viz_file_path.name}]", styles["ItalicCustom"]))
            
            alt = alt_texts.get(viz_name, "")
            if alt: story.append(Paragraph(f"{alt}", styles["ItalicCustom"]))
            story.append(Spacer(1, 0.2 * inch))
    
    try:
        doc.build(story)
        logger_instance.info(f"Successfully generated PDF report: {pdf_path}")
    except Exception as pdf_build_err:
        logger_instance.error(f"Error building PDF {pdf_path}: {pdf_build_err}", exc_info=True)
        fallback_path = output_dir / "executive_report_fallback.txt"
        try:
            with open(fallback_path, "w", encoding="utf-8") as f:
                f.write("PDF Generation Failed. Summary Data:\n")
                for k, v_val in summary_data.items(): f.write(f"{k}: {v_val}\n")
                f.write("\nRecommendations:\n")
                for rec in recommendations: f.write(f"- {rec}\n")
            logger_instance.info(f"Wrote fallback text report to {fallback_path}")
            return fallback_path
        except Exception as fallback_err:
            logger_instance.error(f"Failed to write fallback text report: {fallback_err}")
            # Potentially re-raise or handle as critical error
    return pdf_path


def generate_all_outputs(
    master_ledger: pd.DataFrame,
    reconciliation_results: dict[str, Any],
    analytics_results: dict[str, Any],
    risk_assessment: dict[str, Any],
    recommendations: list[str],
    visualizations: dict[str, str], # Paths to already generated viz files
    alt_texts: dict[str, str],
    data_quality_issues: list[dict[str, Any]], # Direct list of DQ issues
    config: AnalysisConfig, # Pass full config
    output_dir_path_str: str = "analysis_output", # Allow overriding output dir
    logger_instance: logging.Logger = logger
) -> dict[str, str]:
    logger_instance.info(f"Generating all output files in '{output_dir_path_str}'...")
    output_dir = Path(output_dir_path_str)
    output_dir.mkdir(exist_ok=True)
    output_paths: dict[str, str] = {}

    master_ledger_export = master_ledger.copy()
    if "Date" in master_ledger_export.columns:
        master_ledger_export["Date"] = pd.to_datetime(master_ledger_export["Date"]).dt.strftime("%Y-%m-%d")

    # Aliases for user-friendly CSV/Excel
    master_ledger_export["Category_Display"] = master_ledger_export.get("TransactionType", pd.NA)
    master_ledger_export["Amount_Charged_Display"] = master_ledger_export.get("ActualAmount", pd.NA)
    master_ledger_export["Shared_Amount_Display"] = master_ledger_export.get("AllowedAmount", pd.NA)
    master_ledger_export["Cumulative_Balance_Display"] = master_ledger_export.get("RunningBalance", pd.NA)

    # 1. Master Ledger CSV
    if not master_ledger_export.empty:
        ledger_path = output_dir / "master_ledger_v2.3.csv"
        try:
            master_ledger_export.to_csv(ledger_path, index=False)
            output_paths["master_ledger_csv"] = str(ledger_path)
            logger_instance.info(f"Saved: {ledger_path}")
        except Exception as e:
            logger_instance.error(f"Failed to save master_ledger_v2.3.csv: {e}")

        # 2. Line-by-line reconciliation CSV
        recon_csv_path = output_dir / "line_by_line_reconciliation_v2.3.csv"
        recon_cols = [
            "Date", "Category_Display", "Payer", "Description", "Amount_Charged_Display",
            "Shared_Amount_Display", "RyanOwes", "JordynOwes", "BalanceImpact",
            "Cumulative_Balance_Display", "Who_Paid_Text", "Share_Type", 
            "Shared_Reason", "DataQuality_Audit", "DataQualityFlag", "TransactionID"
        ]
        final_recon_cols = [col for col in recon_cols if col in master_ledger_export.columns]
        try:
            master_ledger_export[final_recon_cols].to_csv(recon_csv_path, index=False)
            output_paths["reconciliation_detail_csv"] = str(recon_csv_path)
            logger_instance.info(f"Saved: {recon_csv_path}")
        except Exception as e:
            logger_instance.error(f"Failed to save line_by_line_reconciliation_v2.3.csv: {e}")

    # 3. Executive Summary CSV
    # Calculate data quality score here if not passed in analytics_results
    # For now, assuming it's part of analytics_results or calculated separately by orchestrator
    dq_score = analytics_results.get("data_quality_score", 0.0) # Get it from analytics if available

    summary_data = {
        "Overall Balance": f"${reconciliation_results.get('amount_owed', 0):,.2f} ({reconciliation_results.get('who_owes_whom', 'N/A')})",
        "Total Shared Processed": f"${reconciliation_results.get('total_shared_amount', 0):,.2f}",
        "Data Quality Score": f"{dq_score:.1f}%",
        "Overall Risk Level": risk_assessment.get("overall_risk_level", "N/A"),
        "Triple Reconciliation Matched": "YES" if reconciliation_results.get("reconciled", False) else "NO",
        "Ledger Balance Matched": str(analytics_results.get("validation_summary",{}).get("ledger_balance_match", "N/A")), # Assuming validation summary is in analytics
        "Processing Time (s)": f"{analytics_results.get('performance_metrics',{}).get('processing_time_seconds',0):.1f}",
        "Total Transactions Analyzed": len(master_ledger) if not master_ledger.empty else 0,
    }
    # Add source data summary if available in analytics_results
    src_summary = analytics_results.get("data_sources_summary", {})
    for src_name, details in src_summary.items():
        summary_data[f"Source - {src_name} rows"] = details.get("rows",0)
        
    summary_df = pd.DataFrame(list(summary_data.items()), columns=["Metric", "Value"])
    exec_path = output_dir / "executive_summary_v2.3.csv"
    try:
        summary_df.to_csv(exec_path, index=False)
        output_paths["executive_summary_csv"] = str(exec_path)
        logger_instance.info(f"Saved: {exec_path}")
    except Exception as e:
        logger_instance.error(f"Failed to save executive_summary_v2.3.csv: {e}")


    # 4. Alt-texts JSON
    alt_text_path = output_dir / "alt_texts_v2.3.json"
    try:
        with open(alt_text_path, "w", encoding="utf-8") as f:
            json.dump(alt_texts, f, indent=2)
        output_paths["alt_texts_json"] = str(alt_text_path)
        logger_instance.info(f"Saved: {alt_text_path} with {len(alt_texts)} entries")
    except Exception as e:
        logger_instance.error(f"Failed to save alt_texts_v2.3.json: {e}")

    # 5. Data Quality Issues Log CSV
    if data_quality_issues:
        error_df = pd.DataFrame(data_quality_issues)
        if "row_data_sample" in error_df.columns:
            error_df["row_data_sample"] = error_df["row_data_sample"].astype(str)
        error_path = output_dir / "data_quality_issues_log_v2.3.csv"
        try:
            error_df.to_csv(error_path, index=False)
            output_paths["data_quality_log_csv"] = str(error_path)
            logger_instance.info(f"Saved: {error_path}")
        except Exception as e:
            logger_instance.error(f"Failed to save data_quality_issues_log_v2.3.csv: {e}")
    else:
        logger_instance.info("No data quality issues to log to CSV.")


    # 6. Excel Report
    excel_path = output_dir / "financial_analysis_report_v2.3.xlsx"
    try:
        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            summary_df.to_excel(writer, sheet_name="Executive Summary", index=False)
            if not master_ledger_export.empty:
                excel_ledger_cols = [col for col in final_recon_cols if col in master_ledger_export.columns]
                master_ledger_export[excel_ledger_cols].to_excel(writer, sheet_name="Ledger Highlights", index=False)
            
            pd.DataFrame(list(reconciliation_results.items()), columns=["Metric", "Value"]).to_excel(writer, sheet_name="Reconciliation Details", index=False)
            if "category_details" in reconciliation_results and reconciliation_results["category_details"]:
                pd.DataFrame(reconciliation_results["category_details"]).to_excel(writer, sheet_name="Recon Category Breakdown", index=False)
            
            if "expense_category_analysis" in analytics_results and isinstance(analytics_results["expense_category_analysis"].get("summary_table"), list):
                pd.DataFrame(analytics_results["expense_category_analysis"]["summary_table"]).to_excel(writer, sheet_name="Expense Category Stats", index=False)
            
            if "details" in risk_assessment and risk_assessment["details"]:
                pd.DataFrame(risk_assessment["details"]).to_excel(writer, sheet_name="Risk Assessment Details", index=False)
            
            pd.DataFrame(recommendations, columns=["Recommendations"]).to_excel(writer, sheet_name="Recommendations", index=False)

            visual_index_data = [{"Visualization": k, "Filename": Path(v).name, "Alt Text": alt_texts.get(k, "N/A")} for k,v in visualizations.items()]
            pd.DataFrame(visual_index_data).to_excel(writer, sheet_name="Visual Index", index=False)
        
        output_paths["excel_report"] = str(excel_path)
        logger_instance.info(f"Saved: {excel_path}")
    except Exception as e_excel:
        logger_instance.error(f"Failed to generate Excel report {excel_path}: {e_excel}", exc_info=True)

    # 7. Dashboard HTML
    try:
        dashboard_path = _generate_dashboard_html(visualizations, alt_texts, output_dir, logger_instance)
        output_paths["dashboard_html"] = str(dashboard_path)
        # logger_instance.info(f"Saved: {dashboard_path}") # Already logged in helper
    except Exception as e_dash:
        logger_instance.error(f"Failed to generate dashboard HTML: {e_dash}", exc_info=True)

    # 8. Executive PDF
    try:
        pdf_path = _generate_executive_summary_pdf(summary_data, visualizations, alt_texts, recommendations, output_dir, logger_instance)
        output_paths["executive_pdf"] = str(pdf_path)
        # logger_instance.info(f"Saved: {pdf_path}") # Already logged in helper
    except Exception as e_pdf:
        logger_instance.error(f"Failed to generate executive PDF: {e_pdf}", exc_info=True)

    logger_instance.info(f"Generated {len(output_paths)} output files in {output_dir.resolve()}")
    return output_paths
