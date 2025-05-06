# GitHub Pull Request Viewer

A desktop application built with Python and Tkinter that helps you manage and monitor your GitHub Pull Requests efficiently.

## Features

- 👀 View all your open Pull Requests in one place
- 🔄 Real-time review status tracking
- 🔍 Filter between your PRs and PRs in other repositories
- 🔄 Cache system for improved performance
- 🎯 Double-click to open PRs in your default browser
- ⚡ Sort PRs by title, state, or repository
- ⚙️ Configurable settings with GUI interface

## Requirements

- Python 3.10 or higher
- Required Python packages:
  - pyperclip
  - requests

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
```
2. Install the required dependencies:
```bash
pip install pyperclip requests
```
## Configuration

1. Launch the application
2. Click on the "Settings" button
3. Enter your:
   - GitHub username
   - GitHub personal access token (requires 'repo' scope for private repositories)

The configuration will be automatically saved for future sessions.

## Usage

1. Start the application:
```bash
python github-viewer.py
```
2. Use the interface to:
   - View your open Pull Requests
   - Click "Refresh PRs" to update the list
   - Toggle between viewing your PRs or PRs in other repositories
   - Double-click any PR to open it in your browser
   - Sort PRs by clicking on column headers

## Features in Detail

### Pull Request Information
- Title of the PR
- Current review state
- Repository name
- Direct link to PR

### Review States
- APPROVED
- CHANGES_REQUESTED
- REVIEW_REQUIRED
- REVIEW_IN_PROGRESS
- UNKNOWN (in case of API errors)

### Caching
- PR data is cached for 30 minutes
- Review states are cached separately
- Cache is automatically saved on exit and loaded on startup

## Environment Variables

You can optionally set your GitHub token as an environment variable:
```bash
export GITHUB_TOKEN=your_token_here
```


## Notes

- The application requires a GitHub token with 'repo' scope for accessing private repositories
- Cache files (`review_cache.json` and `pr_cache.json`) are created in the application directory
- Configuration is stored in `config.json`

