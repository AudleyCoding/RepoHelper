import requests
from typing import Dict, List, Optional
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import logging
import base64

logger = logging.getLogger(__name__)

class RepoContent(BaseModel):
    name: str
    path: str
    type: str
    content: Optional[str] = None
    size: int

class GitHubService:
    def __init__(self, token: Optional[str] = None):
        self.token = token.strip().strip('"') if token else None  # Remove quotes and whitespace
        if not self.token:
            logger.warning("No GitHub token provided. API rate limits will be restricted.")
        
        self.headers = {
            'Accept': 'application/vnd.github.v3+json',
            'Authorization': f'token {self.token}' if self.token else ''  # Changed back to 'token' prefix
        }
        logger.info(f"Initializing GitHub service with token: {'Present' if self.token else 'Not present'}")
        self.base_url = 'https://api.github.com'

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def get_repo_metadata(self, owner: str, repo: str) -> Dict:
        """Fetch repository metadata."""
        url = f'{self.base_url}/repos/{owner}/{repo}'
        logger.info(f"Fetching repo metadata from: {url}")
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"GitHub API error: {e.response.status_code} - {e.response.text}")
            logger.error(f"Headers used: {self.headers}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def get_repo_contents(self, owner: str, repo: str, path: str = '') -> List[RepoContent]:
        """Fetch repository contents."""
        url = f'{self.base_url}/repos/{owner}/{repo}/contents/{path}'
        logger.info(f"Fetching repo contents from: {url}")
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            contents = response.json()
            if not isinstance(contents, list):
                contents = [contents]
            return [RepoContent(**item) for item in contents]
        except requests.exceptions.HTTPError as e:
            logger.error(f"GitHub API error: {e.response.status_code} - {e.response.text}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def get_languages(self, owner: str, repo: str) -> Dict:
        """Fetch repository languages."""
        url = f'{self.base_url}/repos/{owner}/{repo}/languages'
        logger.info(f"Fetching repo languages from: {url}")
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"GitHub API error: {e.response.status_code} - {e.response.text}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def get_readme(self, owner: str, repo: str) -> Optional[str]:
        """Fetch repository README content."""
        url = f'{self.base_url}/repos/{owner}/{repo}/readme'
        logger.info(f"Fetching repo README from: {url}")
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            content = response.json().get('content', '')
            if content:
                return base64.b64decode(content).decode('utf-8')
            return None
        except requests.exceptions.RequestException as e:
            if getattr(e.response, 'status_code', 0) == 404:
                logger.warning(f"No README found for {owner}/{repo}")
                return None
            logger.error(f"Failed to fetch README: {str(e)}")
            if hasattr(e, 'response'):
                logger.error(f"Response status: {e.response.status_code} - {e.response.text}")
            raise

    def parse_github_url(self, url: str) -> tuple[str, str]:
        """Parse GitHub URL into owner and repo."""
        parts = url.rstrip('/').split('/')
        if 'github.com' not in url:
            raise ValueError("Not a valid GitHub URL")
        return parts[-2], parts[-1]
