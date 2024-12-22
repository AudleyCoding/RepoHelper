from flask import Blueprint, jsonify, request, render_template, current_app, send_file
from .services.github_service import GitHubService
from .services.llm_service import LLMService
import logging
from markdown2 import markdown
import json
import traceback
import re
from requests.exceptions import RequestException
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
import tempfile
from pathlib import Path
import os
import io
import urllib.parse

# Register Chinese font
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))

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
    'zh': '代码仓库分析'
}

def get_safe_filename(language, format_type):
    """Get a safe filename for the given language."""
    base_name = FILE_NAMES[language]
    filename = f"{base_name}.{format_type}"
    
    # URL encode the filename for safety while preserving Chinese characters
    if language == 'zh':
        filename = urllib.parse.quote(filename)
    
    return filename

def process_markdown_text(text, style):
    """Process markdown text to handle bold, italic, and code formatting"""
    # Handle bold text
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    # Handle italic text
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    # Handle inline code
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    return text

def is_header_underline(line):
    """Check if a line is a markdown header underline (=== or ---)"""
    return bool(re.match(r'^[=\-]+$', line.strip()))

def process_list_item(line):
    """Process a list item to determine its level and clean the text"""
    original_line = line
    line = line.rstrip()
    indent = len(line) - len(line.lstrip())
    level = indent // 2
    
    # Clean up the text
    text = line.lstrip()
    
    # Determine the bullet type
    bullet = '•'
    if text.startswith('+ '):
        bullet = '+'
        text = text[2:]
    elif text.startswith('- '):
        text = text[2:]
    elif text.startswith('* '):
        text = text[2:]
    else:
        for i in range(1, 10):
            if text.startswith(f'{i}. '):
                text = text[len(f'{i}. '):]
                break
    
    return level, bullet, text.strip()

def create_pdf_style(language):
    """Create PDF styles with appropriate font for the language"""
    styles = getSampleStyleSheet()
    
    # Use Chinese font for Chinese language
    if language == 'zh':
        font_name = 'STSong-Light'
    else:
        font_name = 'Helvetica'
    
    # Create custom styles with the appropriate font
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=20,
        alignment=1,  # Center alignment
        fontName=font_name,
        leading=32,  # Add more space between lines
        textColor=colors.HexColor('#2C3E50'),  # Dark blue-grey color
        bold=True
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        fontName=font_name,
        leading=16,  # Increase line spacing
        spaceBefore=6,
        spaceAfter=6,
        allowWidows=0,
        allowOrphans=0
    )
    
    heading_styles = {}
    base_sizes = {1: 18, 2: 16, 3: 14}  # Adjusted heading sizes
    
    for i in range(1, 4):
        heading_styles[i] = ParagraphStyle(
            f'CustomHeading{i}',
            parent=styles[f'Heading{i}'],
            fontSize=base_sizes[i],
            spaceBefore=16 if i == 1 else 12,
            spaceAfter=8,
            fontName=font_name,
            leading=base_sizes[i] + 8,  # Dynamic leading based on font size
            textColor=colors.HexColor('#2C3E50'),  # Dark blue-grey color
            bold=True,
            allowWidows=0,
            allowOrphans=0
        )
    
    bullet_style = ParagraphStyle(
        'Bullet',
        parent=normal_style,
        fontSize=11,
        fontName=font_name,
        leading=16,
        leftIndent=20,
        firstLineIndent=0,
        spaceBefore=3,
        spaceAfter=3,
        bulletIndent=10,
        allowWidows=0,
        allowOrphans=0
    )
    
    code_style = ParagraphStyle(
        'Code',
        parent=normal_style,
        fontName='Courier',
        fontSize=9,
        leftIndent=36,
        rightIndent=36,
        textColor=colors.HexColor('#2F3129'),  # Dark grey for better readability
        backColor=colors.HexColor('#F8F8F8'),  # Light grey background
        spaceBefore=12,
        spaceAfter=12,
        leading=14,  # Tighter line spacing for code
        face='monospace',
        allowWidows=0,
        allowOrphans=0
    )
    
    return title_style, normal_style, heading_styles, bullet_style, code_style

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
                'filename': f"{FILE_NAMES[language]}.md"
            })
        elif format_type == 'pdf':
            # Create a PDF in memory
            pdf_buffer = io.BytesIO()
            
            # Create the PDF document with A4 size and margins
            doc = SimpleDocTemplate(
                pdf_buffer,
                pagesize=letter,
                rightMargin=54,  # Adjusted margins
                leftMargin=54,
                topMargin=54,
                bottomMargin=54,
                title=TITLES.get(language, TITLES['en'])  # Add PDF title metadata
            )
            
            # Get styles with appropriate font
            title_style, normal_style, heading_styles, bullet_style, code_style = create_pdf_style(language)
            
            # Convert markdown to a format ReportLab can handle
            story = []
            
            # Add title in the correct language
            title_text = process_markdown_text(TITLES.get(language, TITLES['en']), title_style)
            story.append(Paragraph(title_text, title_style))
            story.append(Spacer(1, 24))  # More space after title
            
            # Process the content line by line
            lines = analysis.split('\n')
            in_code_block = False
            code_content = []
            current_paragraph = []
            
            i = 0
            while i < len(lines):
                line = lines[i].rstrip()
                
                # Skip empty lines but add paragraph if we have content
                if not line:
                    if current_paragraph:
                        text = ' '.join(current_paragraph)
                        text = process_markdown_text(text, normal_style)
                        story.append(Paragraph(text, normal_style))
                        story.append(Spacer(1, 4))
                        current_paragraph = []
                    i += 1
                    continue
                
                # Handle code blocks
                if line.startswith('```') or line.endswith('```'):
                    if line.startswith('```'):
                        in_code_block = True
                        code_content = []
                    else:
                        in_code_block = False
                        if code_content:
                            story.append(Paragraph('\n'.join(code_content), code_style))
                        code_content = []
                    i += 1
                    continue
                
                if in_code_block:
                    code_content.append(line)
                    i += 1
                    continue
                
                # Handle headers
                if line.startswith('#'):
                    # Add any pending paragraph
                    if current_paragraph:
                        text = ' '.join(current_paragraph)
                        text = process_markdown_text(text, normal_style)
                        story.append(Paragraph(text, normal_style))
                        current_paragraph = []
                    
                    level = len(line.split()[0])  # Count the number of #
                    text = line.lstrip('#').strip()
                    text = process_markdown_text(text, heading_styles[min(level, 3)])
                    style = heading_styles.get(min(level, 3))
                    story.append(Spacer(1, 8))
                    story.append(Paragraph(text, style))
                    story.append(Spacer(1, 4))
                    i += 1
                # Handle alternate header style (=== or ---)
                elif i + 1 < len(lines) and is_header_underline(lines[i + 1]):
                    # Add any pending paragraph
                    if current_paragraph:
                        text = ' '.join(current_paragraph)
                        text = process_markdown_text(text, normal_style)
                        story.append(Paragraph(text, normal_style))
                        current_paragraph = []
                    
                    # Determine header level (=== is h1, --- is h2)
                    level = 1 if lines[i + 1].strip()[0] == '=' else 2
                    text = line.strip()
                    text = process_markdown_text(text, heading_styles[level])
                    style = heading_styles.get(level)
                    story.append(Spacer(1, 8))
                    story.append(Paragraph(text, style))
                    story.append(Spacer(1, 4))
                    i += 2  # Skip both the header text and the underline
                    continue
                
                # Handle list items
                elif line.lstrip().startswith(('+ ', '- ', '* ', '1. ', '2. ', '3. ', '4. ', '5. ')):
                    # Add any pending paragraph
                    if current_paragraph:
                        text = ' '.join(current_paragraph)
                        text = process_markdown_text(text, normal_style)
                        story.append(Paragraph(text, normal_style))
                        current_paragraph = []
                    
                    level, bullet, text = process_list_item(line)
                    
                    # Create bullet style with proper indentation
                    current_bullet_style = ParagraphStyle(
                        f'Bullet{level}',
                        parent=bullet_style,
                        leftIndent=20 + (20 * level),
                        bulletIndent=10 + (20 * level)
                    )
                    
                    text = process_markdown_text(text, current_bullet_style)
                    story.append(Paragraph(f'{bullet} {text}', current_bullet_style))
                    i += 1
                
                # Handle normal paragraphs
                else:
                    current_paragraph.append(line)
                    i += 1
            
            # Add any remaining paragraph
            if current_paragraph:
                text = ' '.join(current_paragraph)
                text = process_markdown_text(text, normal_style)
                story.append(Paragraph(text, normal_style))
            
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
