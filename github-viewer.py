#!/usr/bin/env python
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests",
# ]
# ///
import os
import json
from wsgiref import headers
import time
from typing import Dict, Any

import requests
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser

# Cache settings
CACHE_DURATION = 900  # 15 minutes in seconds
REVIEW_CACHE_FILE = 'review_cache.json'
PR_CACHE_FILE = 'pr_cache.json'
pr_cache: Dict[str, Any] = {}
review_cache: Dict[str, Any] = {}


def load_review_cache():
    global review_cache
    try:
        if os.path.exists(REVIEW_CACHE_FILE):
            with open(REVIEW_CACHE_FILE, 'r') as f:
                review_cache = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        print(f"Error loading review cache: {e}")

def load_pr_cache():
    global pr_cache
    try:
        if os.path.exists(PR_CACHE_FILE):
            with open(PR_CACHE_FILE, 'r') as f:
                pr_cache = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        print(f"Error loading PR cache: {e}")


# Configuration file path
CONFIG_FILE = 'config.json'



# Global variables for GitHub credentials
g_github_username = ''  # Default username
g_github_token = ''
g_show_others_only = False  # Filter state for mine/others PRs


def load_config():
    global g_github_username, g_github_token, g_show_others_only
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                g_github_username = config.get('username', g_github_username)
                g_github_token = config.get('token', '')
                g_show_others_only = config.get('show_others_only', False)
        else:
            # If no config file, try loading token from environment as a fallback
            g_github_token = os.getenv('GITHUB_TOKEN', '')
    except (IOError, json.JSONDecodeError) as e:
        print(f"Error loading config file: {e}. Using defaults.")
        g_github_token = os.getenv('GITHUB_TOKEN', '') # Fallback on error

def save_config():
    config = {
        'username': g_github_username,
        'token': g_github_token,
        'show_others_only': g_show_others_only
    }
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
    except IOError as e:
        messagebox.showerror("Error Saving Config", f"Could not save settings: {e}")

def save_settings(username_entry, token_entry, settings_window):
    global g_github_username, g_github_token
    new_username = username_entry.get()
    new_token = token_entry.get()

    if not new_username:
        messagebox.showwarning("Input Error", "GitHub Username cannot be empty.")
        return

    # No validation for token being empty, as user might want to clear it to use public API only (though current setup requires token)

    g_github_username = new_username
    g_github_token = new_token

    save_config() # Save to file
    settings_window.destroy()
    load_prs() # Refresh PRs after saving settings

def open_settings_window():
    settings_window = tk.Toplevel(root)
    settings_window.title("Settings")
    settings_window.geometry("450x180") # Adjusted size slightly

    settings_window.columnconfigure(1, weight=1)

    ttk.Label(settings_window, text="GitHub Username:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
    username_var = tk.StringVar(value=g_github_username)
    username_entry = ttk.Entry(settings_window, textvariable=username_var, width=40)
    username_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

    ttk.Label(settings_window, text="GitHub Token:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
    token_var = tk.StringVar(value=g_github_token)
    token_entry = ttk.Entry(settings_window, textvariable=token_var, width=40, show="*")
    token_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

    info_label = ttk.Label(settings_window, text="Token requires 'repo' scope for private PRs.", foreground="grey")
    info_label.grid(row=2, column=0, columnspan=2, padx=10, pady=(0,10), sticky="w")

    save_button = ttk.Button(settings_window, text="Save",
                             command=lambda: save_settings(username_entry, token_entry, settings_window))
    save_button.grid(row=3, column=0, columnspan=2, pady=10)

    settings_window.transient(root)
    settings_window.grab_set()
    root.wait_window(settings_window)


def get_pr_review_state(pull_request_url, headers):
    try:
        # Check cache first
        current_time = time.time()
        if pull_request_url in review_cache:
            cached_data = review_cache[pull_request_url]
            if current_time - cached_data['timestamp'] < CACHE_DURATION:
                return cached_data['state']

        # Convert API URL to the correct format and extract components
        api_parts = pull_request_url.replace('https://api.github.com/repos/', '').split('/')
        owner = api_parts[0]
        repo = api_parts[1]
        number = api_parts[3]  # PR number is after 'pulls'
        review_url = f'https://api.github.com/repos/{owner}/{repo}/pulls/{number}/reviews'
        headers = {
            'Authorization': f'token {g_github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        print(f"Calling GitHub API for reviews: {review_url}")
        response = requests.get(review_url, headers=headers)
        response.raise_for_status()
        reviews = response.json()

        # Get the latest review state for each reviewer
        latest_reviews = {}
        for review in reviews:
            reviewer = review['user']['login']
            state = review['state']
            latest_reviews[reviewer] = state

        # Determine overall review state
        if not latest_reviews:
            state = "REVIEW_REQUIRED"
        elif any(state == "CHANGES_REQUESTED" for state in latest_reviews.values()):
            state = "CHANGES_REQUESTED"
        elif all(state == "APPROVED" for state in latest_reviews.values()):
            state = "ALL_APPROVED"
        elif any(state == "APPROVED" for state in latest_reviews.values()):
            state = "APPROVED"
        else:
            state = "REVIEW_IN_PROGRESS"

        # Update cache with longer duration
        review_cache[pull_request_url] = {
            'state': state,
            'timestamp': time.time()
        }
        with open(REVIEW_CACHE_FILE, 'w') as f:
            json.dump(review_cache, f)
        return state
    except Exception as e:
        print(f"Error getting review state: {e}")
        return "UNKNOWN"


def get_pull_requests():
    current_time = time.time()
    if not g_github_token:
        messagebox.showwarning(
            "Authentication Required",
            "GitHub Token is missing. Please set it in Settings to view private PRs."
        )
        return []

    if not g_github_username:
        messagebox.showwarning(
            "Configuration Required",
            "GitHub Username is missing. Please set it in Settings."
        )
        return []

    headers = {
        'Authorization': f'token {g_github_token}',
        'Accept': 'application/vnd.github.v3+json, application/vnd.github.shadow-cat-preview+json'
    }

    pull_requests = []
    page = 1
    # Added state:open to the query
    if g_show_others_only:
        base_query = f'is:pr+state:open+author:{g_github_username}+-user:{g_github_username}+archived:false'  # Show only others repos
    else:
        base_query = f'is:pr+state:open+author:{g_github_username}+user:{g_github_username}+archived:false'  # Show only mine repos
    print(f"Fetching PRs with query: {base_query}")  # Debugging print for query

    while True:
        url = f'https://api.github.com/search/issues?q={base_query}&page={page}&per_page=100'
        # Use url with filters as cache key
        if url in pr_cache:
            cached_data = pr_cache[url]
            if current_time - cached_data['timestamp'] < CACHE_DURATION:
                pull_requests.extend(cached_data['data']['items'])
                if not cached_data.get('has_next'):
                    break
                page += 1
                continue

        # Use base query for API call
        url = f'https://api.github.com/search/issues?q={base_query}&page={page}&per_page=100'
        print(f"Calling GitHub API: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=10) # Added timeout
            response.raise_for_status() # Raises HTTPError for bad responses (4XX or 5XX)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                messagebox.showerror("Authentication Failed", "Invalid GitHub Token or insufficient permissions. Please check your token in Settings (ensure 'repo' scope).")
            else:
                messagebox.showerror("API Error", f"Error fetching pull requests: {e.response.status_code} - {e.response.reason}")
            return [] # Return empty list on critical API errors
        except requests.exceptions.RequestException as e: # Catch other network errors
            messagebox.showerror("Network Error", f"Could not connect to GitHub: {e}")
            return []


        data = response.json()
        if not data['items']:
            break

        # Update cache with unfiltered results
        pr_cache[url] = {
            'data': data,
            'timestamp': time.time(),
            'has_next': 'next' in response.links
        }

        # Filter results in memory
        if g_show_others_only:
            pull_requests.extend([pr for pr in data['items'] if pr['repository_url'].split('/')[-2] != g_github_username])
        else:
            pull_requests.extend(data['items'])
        if 'next' not in response.links: # Check if there's a next page
            break
        page += 1


    return pull_requests

def open_pr(url):
    webbrowser.open(url)

def treeview_sort_column(tv, col, reverse):
    l = [(tv.set(k, col), k) for k in tv.get_children('')]
    try:
        l.sort(key=lambda x: (float(x[0]) if x[0].replace('.', '', 1).isdigit() else x[0].lower()), reverse=reverse)
    except ValueError:
        l.sort(key=lambda x: x[0].lower(), reverse=reverse)

    for index, (val, k) in enumerate(l):
        tv.move(k, '', index)
    tv.heading(col, command=lambda: treeview_sort_column(tv, col, not reverse))


def toggle_filter():
    global g_show_others_only
    g_show_others_only = not g_show_others_only
    filter_button.configure(text="Show Mine PRs" if g_show_others_only else "Show Others PRs")
    save_config()
    load_prs()


# Global variable for auto-refresh
auto_refresh_job = None


def schedule_next_refresh():
    global auto_refresh_job
    if auto_refresh_job is not None:
        root.after_cancel(auto_refresh_job)
    auto_refresh_job = root.after(30000, load_prs)  # 30 seconds (not busting the cache)


def clear_caches():
    global pr_cache, review_cache
    pr_cache = {}
    review_cache = {}


def refresh_prs():
    clear_caches()
    load_prs()


def load_prs():
    for row in tree.get_children():
        tree.delete(row)

    pull_requests = get_pull_requests()
    print(f"Loaded {len(pull_requests)} open pull requests for user {g_github_username}.")
    headers = {
        'Authorization': f'token {g_github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    # Batch process review states
    review_states = {}
    for pr in pull_requests:
        review_states[pr['url']] = get_pr_review_state(pr['url'], headers)

    for pr in pull_requests:
        repo_name = pr['repository_url'].split('/')[-1]
        review_state = review_states.get(pr['url'], 'UNKNOWN')
        tree.insert("", "end", values=(pr['title'], review_state, repo_name, pr['html_url']))

    # Schedule next refresh
    schedule_next_refresh()


# --- Main Application Setup ---
root = tk.Tk()
root.title("GitHub Open Pull Requests Viewer") # Updated title
root.geometry("850x600")

# Load configuration at startup
load_config()

root.columnconfigure(0, weight=1)
root.rowconfigure(1, weight=1)

button_frame = ttk.Frame(root)
button_frame.grid(row=0, column=0, sticky='ew', padx=10, pady=(10,0))

refresh_button = ttk.Button(button_frame, text="Refresh PRs", command=refresh_prs)
refresh_button.pack(side='left', padx=(0,5))

filter_button = ttk.Button(button_frame, text="Show Mine PRs" if g_show_others_only else "Show Others PRs",
                           command=lambda: toggle_filter())
filter_button.pack(side='left')

settings_button = ttk.Button(button_frame, text="Settings", command=open_settings_window)
settings_button.pack(side='right', padx=(0, 5))

tree_frame = ttk.Frame(root)
tree_frame.grid(row=1, column=0, sticky='nsew', padx=10, pady=10)
tree_frame.columnconfigure(0, weight=1)
tree_frame.rowconfigure(0, weight=1)

tree = ttk.Treeview(tree_frame, columns=("Title", "State", "Repo", "URL"), show='headings')
headings = {"Title": "Title", "State": "State", "Repo": "Repo", "URL": "URL"}
for col, text in headings.items():
    tree.heading(col, text=text, command=lambda c=col: treeview_sort_column(tree, c, False))

col_widths = {"Title": 350, "State": 80, "Repo": 150, "URL": 250}
for col, width in col_widths.items():
    tree.column(col, anchor="w", width=width, stretch=tk.YES)
tree.column("State", anchor="center")

scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
tree.configure(yscroll=scrollbar.set)
tree.grid(row=0, column=0, sticky='nsew')
scrollbar.grid(row=0, column=1, sticky='ns')

def on_double_click(event):
    item = tree.selection()
    if item:
        item = item[0]
        url = tree.item(item, "values")[3]
        open_pr(url)
tree.bind("<Double-1>", on_double_click)

# Load caches
load_review_cache()
load_pr_cache()

# Initial load
load_prs()

print("Starting the Tkinter event loop...")


def on_closing():
    global auto_refresh_job
    if auto_refresh_job is not None:
        root.after_cancel(auto_refresh_job)
    root.destroy()


root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()

# Save cache on exit
with open(REVIEW_CACHE_FILE, 'w') as f:
    json.dump(review_cache, f)

# Save PR cache on exit
with open(PR_CACHE_FILE, 'w') as f:
    json.dump(pr_cache, f)