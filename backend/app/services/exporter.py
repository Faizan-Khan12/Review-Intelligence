"""
Export service for generating CSV and PDF reports.
"""

import os
import pandas as pd
from typing import Dict, Any
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from app.core.config import settings
from app.utils.helpers import format_timestamp


class Exporter:
    """Export analysis results to various formats."""
    
    def __init__(self):
        self.export_folder = settings.EXPORT_FOLDER
        os.makedirs(self.export_folder, exist_ok=True)
    
    def export_to_csv(
        self,
        analysis_data: Dict[str, Any],
        reviews: list = None
    ) -> Dict[str, Any]:
        """
        Export analysis results to comprehensive CSV/Excel with multiple sheets.

        Args:
            analysis_data: Analysis results
            reviews: Optional raw reviews data

        Returns:
            Export result with file path
        """
        try:
            asin = analysis_data.get('asin', 'unknown')
            timestamp = format_timestamp()
            filename = f"analysis_{asin}_{timestamp}.xlsx"  # Changed to xlsx for multi-sheet
            filepath = os.path.join(self.export_folder, filename)

            # Sheet 1: Executive Summary
            summary_rows = []
            product_info = analysis_data.get('product_info', {})

            summary_rows.append(['ASIN', asin])
            summary_rows.append(['Product Title', product_info.get('title', 'N/A')])
            summary_rows.append(['Brand', product_info.get('brand', 'N/A')])
            summary_rows.append(['Total Reviews', analysis_data.get('total_reviews', 0)])
            summary_rows.append(['Average Rating', analysis_data.get('average_rating', 0)])
            summary_rows.append(['Country', analysis_data.get('country', 'US')])
            summary_rows.append(['Data Source', analysis_data.get('data_source', 'unknown')])
            summary_rows.append(['AI Provider', analysis_data.get('ai_provider', 'N/A')])
            summary_rows.append(['', ''])  # Blank row

            # Sentiment distribution
            sentiment = analysis_data.get('sentiment_distribution', {})
            if sentiment:
                summary_rows.append(['Sentiment Analysis', ''])
                summary_rows.append(['Positive Reviews', sentiment.get('positive', 0)])
                summary_rows.append(['Neutral Reviews', sentiment.get('neutral', 0)])
                summary_rows.append(['Negative Reviews', sentiment.get('negative', 0)])
                total = sentiment.get('positive', 0) + sentiment.get('neutral', 0) + sentiment.get('negative', 0)
                if total > 0:
                    summary_rows.append(['Positive %', f"{sentiment.get('positive', 0) / total * 100:.1f}%"])
                summary_rows.append(['', ''])

            # Bot detection stats
            bot_detection = analysis_data.get('bot_detection', {})
            if bot_detection:
                summary_rows.append(['Bot Detection', ''])
                summary_rows.append(['Total Reviews Analyzed', bot_detection.get('total_reviews', 0)])
                summary_rows.append(['Genuine Reviews', bot_detection.get('genuine_count', 0)])
                summary_rows.append(['Bot Reviews Filtered', bot_detection.get('bot_count', 0)])
                summary_rows.append(['Bot Percentage', f"{bot_detection.get('bot_percentage', 0)}%"])

            df_summary = pd.DataFrame(summary_rows, columns=['Metric', 'Value'])

            # Sheet 2: Keywords
            keywords = analysis_data.get('top_keywords', [])
            df_keywords = pd.DataFrame(keywords) if keywords else pd.DataFrame()

            # Sheet 3: Themes
            themes = analysis_data.get('themes', [])
            df_themes = pd.DataFrame(themes) if themes else pd.DataFrame()

            # Sheet 4: Insights
            insights = analysis_data.get('insights', [])
            df_insights = pd.DataFrame({'Insight': insights}) if insights else pd.DataFrame()

            # Sheet 5: Rating Distribution
            rating_dist = analysis_data.get('rating_distribution', {})
            if rating_dist:
                rating_rows = []
                for star in ['5', '4', '3', '2', '1']:
                    count = rating_dist.get(f'{star}_star', rating_dist.get(star, 0))
                    rating_rows.append({'Rating': f'{star} Star', 'Count': count})
                df_ratings = pd.DataFrame(rating_rows)
            else:
                df_ratings = pd.DataFrame()

            # Sheet 6: All Reviews (if provided)
            reviews_list = reviews or analysis_data.get('reviews', [])
            if reviews_list:
                df_reviews = pd.DataFrame(reviews_list)
            else:
                df_reviews = pd.DataFrame()

            # Write to Excel with multiple sheets
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df_summary.to_excel(writer, sheet_name='Summary', index=False)

                if not df_keywords.empty:
                    df_keywords.to_excel(writer, sheet_name='Keywords', index=False)

                if not df_themes.empty:
                    df_themes.to_excel(writer, sheet_name='Themes', index=False)

                if not df_insights.empty:
                    df_insights.to_excel(writer, sheet_name='Insights', index=False)

                if not df_ratings.empty:
                    df_ratings.to_excel(writer, sheet_name='Rating Distribution', index=False)

                if not df_reviews.empty:
                    # Select key columns for reviews
                    review_cols = ['title', 'text', 'rating', 'author', 'date', 'sentiment', 'verified', 'bot_score']
                    available_cols = [col for col in review_cols if col in df_reviews.columns]
                    df_reviews[available_cols].to_excel(writer, sheet_name='All Reviews', index=False)

            file_size = os.path.getsize(filepath)

            return {
                "success": True,
                "file_path": filepath,
                "file_size": file_size,
                "format": "xlsx",
                "download_url": f"/exports/{filename}"
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"CSV export failed: {str(e)}"
            }
    
    def export_to_pdf(
        self,
        analysis_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Export analysis results to comprehensive PDF report.

        Args:
            analysis_data: Analysis results

        Returns:
            Export result with file path
        """
        try:
            asin = analysis_data.get('asin', 'unknown')
            timestamp = format_timestamp()
            filename = f"report_{asin}_{timestamp}.pdf"
            filepath = os.path.join(self.export_folder, filename)

            # Create PDF
            doc = SimpleDocTemplate(filepath, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()

            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1f2937'),
                spaceAfter=30,
            )

            # Title
            title = Paragraph("Amazon Review Intelligence Report", title_style)
            story.append(title)
            story.append(Spacer(1, 0.2*inch))

            # Product Info
            product_info = analysis_data.get('product_info', {})
            product_title = product_info.get('title', 'N/A')
            brand = product_info.get('brand', 'N/A')

            info_text = Paragraph(
                f"<b>Product:</b> {product_title}<br/>"
                f"<b>Brand:</b> {brand}<br/>"
                f"<b>ASIN:</b> {asin}<br/>"
                f"<b>Country:</b> {analysis_data.get('country', 'N/A')}<br/>"
                f"<b>Analyzed:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}<br/>"
                f"<b>Total Reviews:</b> {analysis_data.get('total_reviews', 0)}<br/>"
                f"<b>Average Rating:</b> {analysis_data.get('average_rating', 0):.2f} ⭐<br/>"
                f"<b>Data Source:</b> {analysis_data.get('data_source', 'N/A')}",
                styles['Normal']
            )
            story.append(info_text)
            story.append(Spacer(1, 0.3*inch))

            # Executive Summary
            summary_title = Paragraph("<b>Executive Summary</b>", styles['Heading2'])
            story.append(summary_title)
            summary = analysis_data.get('summary', 'No summary available')
            summary_text = Paragraph(summary, styles['Normal'])
            story.append(summary_text)
            story.append(Spacer(1, 0.3*inch))

            # Sentiment Distribution
            sentiment_title = Paragraph("<b>Sentiment Distribution</b>", styles['Heading2'])
            story.append(sentiment_title)

            sentiment = analysis_data.get('sentiment_distribution') or {}
            total_reviews = max(analysis_data.get('total_reviews', 0), 1)
            sentiment_data = [
                ['Sentiment', 'Count', 'Percentage'],
                ['Positive', str(sentiment.get('positive', 0)), f"{sentiment.get('positive', 0) / total_reviews * 100:.1f}%"],
                ['Neutral', str(sentiment.get('neutral', 0)), f"{sentiment.get('neutral', 0) / total_reviews * 100:.1f}%"],
                ['Negative', str(sentiment.get('negative', 0)), f"{sentiment.get('negative', 0) / total_reviews * 100:.1f}%"],
            ]

            sentiment_table = Table(sentiment_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
            sentiment_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f3f4f6')),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))

            story.append(sentiment_table)
            story.append(Spacer(1, 0.3*inch))

            # Bot Detection Results (if available)
            bot_detection = analysis_data.get('bot_detection', {})
            if bot_detection and bot_detection.get('bot_count', 0) > 0:
                bot_title = Paragraph("<b>Bot Detection Results</b>", styles['Heading2'])
                story.append(bot_title)

                bot_data = [
                    ['Metric', 'Value'],
                    ['Total Reviews Analyzed', str(bot_detection.get('total_reviews', 0))],
                    ['Genuine Reviews', str(bot_detection.get('genuine_count', 0))],
                    ['Bot Reviews Filtered', str(bot_detection.get('bot_count', 0))],
                    ['Bot Percentage', f"{bot_detection.get('bot_percentage', 0)}%"],
                ]

                bot_table = Table(bot_data, colWidths=[3*inch, 2*inch])
                bot_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ef4444')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fee2e2')),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))

                story.append(bot_table)
                story.append(Spacer(1, 0.3*inch))

            # Top Keywords
            keywords_title = Paragraph("<b>Top Keywords</b>", styles['Heading2'])
            story.append(keywords_title)

            keywords = analysis_data.get('top_keywords', [])[:15]
            if keywords:
                keyword_data = [['Rank', 'Keyword', 'Frequency']]
                for idx, kw in enumerate(keywords, 1):
                    keyword_data.append([
                        str(idx),
                        kw.get('word', ''),
                        str(kw.get('frequency', 0))
                    ])

                keyword_table = Table(keyword_data, colWidths=[0.7*inch, 3*inch, 1.3*inch])
                keyword_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))

                story.append(keyword_table)

            story.append(Spacer(1, 0.3*inch))

            # Themes
            themes = analysis_data.get('themes', [])
            if themes:
                themes_title = Paragraph("<b>Common Themes</b>", styles['Heading2'])
                story.append(themes_title)

                theme_data = [['Theme', 'Mentions', 'Sentiment']]
                for theme in themes[:10]:
                    theme_data.append([
                        theme.get('theme', ''),
                        str(theme.get('mentions', 0)),
                        theme.get('sentiment', 'neutral').capitalize()
                    ])

                theme_table = Table(theme_data, colWidths=[2.5*inch, 1.2*inch, 1.3*inch])
                theme_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8b5cf6')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))

                story.append(theme_table)
                story.append(Spacer(1, 0.3*inch))

            # Key Insights
            insights_title = Paragraph("<b>Key Insights & Recommendations</b>", styles['Heading2'])
            story.append(insights_title)

            insights = analysis_data.get('insights', [])
            if insights:
                for insight in insights:
                    bullet = Paragraph(f"• {insight}", styles['Normal'])
                    story.append(bullet)
                    story.append(Spacer(1, 0.1*inch))
            else:
                no_insights = Paragraph("No insights available", styles['Normal'])
                story.append(no_insights)

            story.append(Spacer(1, 0.3*inch))

            # Rating Distribution
            rating_dist = analysis_data.get('rating_distribution', {})
            if rating_dist:
                rating_title = Paragraph("<b>Rating Distribution</b>", styles['Heading2'])
                story.append(rating_title)

                rating_data = [['Rating', 'Count']]
                for star in ['5', '4', '3', '2', '1']:
                    count = rating_dist.get(f'{star}_star', rating_dist.get(star, 0))
                    rating_data.append([f"{star} Star", str(count)])

                rating_table = Table(rating_data, colWidths=[2*inch, 2*inch])
                rating_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f59e0b')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))

                story.append(rating_table)

            # Footer
            story.append(Spacer(1, 0.5*inch))
            footer = Paragraph(
                f"<i>Report generated by Technolity Amazon Review Intelligence<br/>"
                f"© 2025 Technolity. All rights reserved.</i>",
                styles['Normal']
            )
            story.append(footer)

            # Build PDF
            doc.build(story)

            file_size = os.path.getsize(filepath)

            return {
                "success": True,
                "file_path": filepath,
                "file_size": file_size,
                "format": "pdf",
                "download_url": f"/exports/{filename}"
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"PDF export failed: {str(e)}"
            }


# Singleton instance
exporter = Exporter()
