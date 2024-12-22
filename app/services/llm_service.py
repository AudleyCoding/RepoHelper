import requests
from typing import Dict
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

LANGUAGE_PROMPTS = {
    'en': 'Analyze this repository and provide a detailed summary in English.',
    'es': 'Analiza este repositorio y proporciona un resumen detallado en español.',
    'fr': 'Analysez ce dépôt et fournissez un résumé détaillé en français.',
    'de': 'Analysieren Sie dieses Repository und erstellen Sie eine detaillierte Zusammenfassung auf Deutsch.',
    'zh': '请用中文分析这个代码仓库并提供详细总结。',
}

class LLMService:
    def __init__(self, api_url: str):
        self.api_url = api_url
        self.headers = {
            'Content-Type': 'application/json'
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def analyze_repo(self, repo_data: Dict, language: str = 'en') -> str:
        """
        Analyze repository data using the local LLM.
        
        Args:
            repo_data: Dictionary containing repository information
            language: Target language for the analysis
        
        Returns:
            str: Generated analysis
        """
        # Get the language-specific prompt
        base_prompt = LANGUAGE_PROMPTS.get(language, LANGUAGE_PROMPTS['en'])
        
        prompt = f"""{base_prompt}

Repository Information:
- Name: {repo_data.get('name')}
- Description: {repo_data.get('description')}
- Primary Language: {repo_data.get('language')}
- Languages Used: {', '.join(repo_data.get('languages', []))}

README Content:
{repo_data.get('readme', 'No README available')}

File Structure:
{repo_data.get('file_structure', 'No file structure available')}

Please provide:
1. A clear description of the repository's purpose and main functionality
2. Key features and capabilities
3. Important dependencies and technical requirements
4. Main workflows or usage patterns
5. Notable code organization and architecture decisions

Format the response in Markdown."""

        try:
            logger.info(f"Sending analysis request to LLM API in {language}")
            response = requests.post(
                f"{self.api_url}/v1/chat/completions",
                headers=self.headers,
                json={
                    "model": "llama2",
                    "messages": [
                        {"role": "system", "content": f"You are a helpful assistant that analyzes GitHub repositories. Respond in {language}."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1000
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
            
        except requests.exceptions.RequestException as e:
            logger.error(f"LLM API error: {str(e)}")
            if hasattr(e, 'response'):
                logger.error(f"Response status: {e.response.status_code} - {e.response.text}")
            raise
