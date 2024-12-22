from app.services.github_service import GitHubService
from dotenv import load_dotenv
import os
import logging

logging.basicConfig(level=logging.INFO)

def test_github_api():
    load_dotenv()
    token = os.getenv('GITHUB_TOKEN', '').strip().strip('"')
    print(f"Token (first 10 chars): {token[:10]}...")
    
    service = GitHubService(token)
    
    # Test repository access
    owner = "mkl13031"
    repo = "591RentNotify"
    
    try:
        print("\nTesting repository metadata:")
        metadata = service.get_repo_metadata(owner, repo)
        print(f"Repository name: {metadata.get('name')}")
        print(f"Description: {metadata.get('description')}")
        
        print("\nTesting repository languages:")
        languages = service.get_languages(owner, repo)
        print(f"Languages: {languages}")
        
        print("\nTesting repository contents:")
        contents = service.get_repo_contents(owner, repo)
        print("Files:")
        for content in contents:
            print(f"- {content.path}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_github_api()
