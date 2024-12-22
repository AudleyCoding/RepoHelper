# GitHub Repository Analyzer

A lightweight web application that analyzes GitHub repositories using the GitHub API and a local LLM for intelligent analysis.

## Features

- Fetch and analyze GitHub repository metadata
- Extract key information from README files and source code
- Generate comprehensive analysis using a local LLM
- Support for multiple languages
- Export analysis in Markdown or PDF format
- Modern, responsive web interface

## Prerequisites

- Python 3.8+
- Local LLM server running on http://0.0.0.0:4000 (LiteLLM with llama2 model)
- GitHub Personal Access Token (for API access)

## Setup

1. Clone the repository:
```bash
git clone [repository-url]
cd RepoHelper
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory:
```bash
GITHUB_TOKEN=your_github_personal_access_token
SECRET_KEY=your_secret_key_here
```

5. Run the application:
```bash
python run.py
```

The application will be available at `http://localhost:5000`.

## Usage

1. Enter a GitHub repository URL in the input field
2. Select the desired language for the analysis
3. Click "Analyze Repository"
4. View the analysis results and repository information
5. Export the analysis in Markdown or PDF format

## Architecture

The application follows a modular architecture:

- `app/`: Main application package
  - `services/`: Core services for GitHub API and LLM integration
  - `templates/`: HTML templates
  - `static/`: CSS and JavaScript files
  - `routes.py`: API endpoints and route handlers
  - `config.py`: Application configuration

## Error Handling

The application includes comprehensive error handling for:
- Invalid GitHub URLs
- API rate limiting
- Missing repository data
- LLM service failures
- Export failures

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License
