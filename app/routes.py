from flask import Blueprint, jsonify, request, render_template, current_app, send_file
from .services.github_service import GitHubService
from .services.llm_service import LLMService
import logging
from markdown2 import markdown
import json
import traceback
from requests.exceptions import RequestException
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
import tempfile
from pathlib import Path
import os
import io
import urllib.parse

main = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

TITLES = {
    'en': 'Repository Analysis',
    'es': 'Análisis del Repositorio',
    'fr': 'Analyse du Dépôt',
    'de': 'Repository-Analyse',
    'zh': '代码仓库分析'
}

FILE_NAMES = {
    'en': 'repository_analysis',
    'es': 'analisis_repositorio',
    'fr': 'analyse_depot',
    'de': 'repository_analyse',
    'zh': 'code_analysis_cn'  # Using more descriptive ASCII name for Chinese
}

def get_safe_filename(language, format_type):
    """Get a safe filename for the given language."""
    base_name = FILE_NAMES[language]
    return f"{base_name}.{format_type}"

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/api/analyze', methods=['POST'])
def analyze_repo():
    try:
        data = request.get_json()
        github_url = data.get('url')
        language = data.get('language', 'en')

        if not github_url:
            return jsonify({'error': 'GitHub URL is required'}), 400

        github_service = GitHubService(current_app.config.get('GITHUB_TOKEN'))
        llm_service = LLMService(current_app.config.get('LLM_API_URL'))

        # Parse GitHub URL
        try:
            owner, repo = github_service.parse_github_url(github_url)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

        try:
            # Fetch repository data
            repo_data = github_service.get_repo_metadata(owner, repo)
            languages = github_service.get_languages(owner, repo)
            readme_content = github_service.get_readme(owner, repo)
            
            # Get repository contents
            contents = github_service.get_repo_contents(owner, repo)
            
            # Prepare data for analysis
            analysis_data = {
                'name': repo_data['name'],
                'description': repo_data.get('description', ''),
                'language': repo_data.get('language', ''),
                'languages': list(languages.keys()),
                'readme': readme_content or 'No README available',
                'file_structure': '\n'.join([f"- {content.path}" for content in contents])
            }

            # Generate analysis
            analysis = llm_service.analyze_repo(analysis_data, language)
            
            return jsonify({
                'analysis': analysis,
                'analysis_html': markdown(analysis),
                'language': language,
                'repo_data': {
                    'name': repo_data['name'],
                    'description': repo_data.get('description', ''),
                    'languages': languages,
                    'stars': repo_data.get('stargazers_count', 0),
                    'forks': repo_data.get('forks_count', 0)
                }
            })

        except RequestException as e:
            error_msg = f"GitHub API error: {str(e)}"
            logger.error(error_msg)
            return jsonify({'error': error_msg}), 502
        except Exception as e:
            error_msg = f"Error analyzing repository: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            return jsonify({'error': error_msg}), 500

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        return jsonify({'error': error_msg}), 500

@main.route('/api/export', methods=['POST'])
def export_analysis():
    try:
        data = request.get_json()
        format_type = data.get('format', 'markdown')
        analysis = data.get('analysis')
        language = data.get('language', 'en')

        if not analysis:
            return jsonify({'error': 'Analysis content is required'}), 400

        if format_type == 'markdown':
            return jsonify({
                'content': analysis, 
                'format': 'md',
                'filename': get_safe_filename(language, 'md')
            })
        elif format_type == 'pdf':
            # Create a PDF in memory
            pdf_buffer = io.BytesIO()
            
            # Create the PDF document
            doc = SimpleDocTemplate(
                pdf_buffer,
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )
            
            # Create styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=30,
                alignment=1  # Center alignment
            )
            normal_style = styles['Normal']
            
            # Convert markdown to a format ReportLab can handle
            story = []
            
            # Add title in the correct language
            story.append(Paragraph(TITLES.get(language, TITLES['en']), title_style))
            story.append(Spacer(1, 12))
            
            # Split content into paragraphs and add them
            paragraphs = analysis.split('\n\n')
            for para in paragraphs:
                if para.strip():
                    # Handle markdown headers
                    if para.startswith('#'):
                        level = len(para.split()[0])  # Count the number of #
                        text = para.lstrip('#').strip()
                        style = ParagraphStyle(
                            f'Heading{level}',
                            parent=styles[f'Heading{min(level, 3)}'],
                            fontSize=20 - (level * 2),
                            spaceBefore=20,
                            spaceAfter=10
                        )
                    else:
                        text = para.strip()
                        style = normal_style
                        
                    # Handle markdown code blocks
                    if text.startswith('```'):
                        text = text.strip('`').strip()
                        style = ParagraphStyle(
                            'Code',
                            parent=normal_style,
                            fontName='Courier',
                            fontSize=8,
                            leftIndent=36,
                            textColor=colors.black,
                            backColor=colors.lightgrey,
                            spaceBefore=10,
                            spaceAfter=10
                        )
                    
                    # Only add non-empty paragraphs
                    if text.strip():
                        story.append(Paragraph(text, style))
                        if not isinstance(style, ParagraphStyle) or style.name != 'Code':
                            story.append(Spacer(1, 6))
            
            # Build the PDF
            doc.build(story)
            
            # Get the PDF content
            pdf_content = pdf_buffer.getvalue()
            pdf_buffer.close()
            
            # Create a new BytesIO object for sending the file
            response_buffer = io.BytesIO(pdf_content)
            response_buffer.seek(0)
            
            filename = get_safe_filename(language, 'pdf')
            
            return send_file(
                response_buffer,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=filename
            )
        else:
            return jsonify({'error': 'Unsupported format'}), 400

    except Exception as e:
        error_msg = f"Error exporting analysis: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        return jsonify({'error': error_msg}), 500
