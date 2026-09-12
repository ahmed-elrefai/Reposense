import os
import requests
from dotenv import load_dotenv
import urllib
import json
from models import ContextPack, GitHubResponse, StdRequest
load_dotenv("./secrets/.env")
IGNORE_DIRS = {
    ".git", ".svn", ".hg",
    "node_modules", "bower_components",
    "venv", ".venv", "env", ".env",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "dist", "build", "out", ".next", ".nuxt", ".turbo",
    "target", "vendor", "coverage", ".coverage",
    ".idea", ".vscode", ".DS_Store",
}

IGNORE_FILE_SUFFIXES = {
    ".pyc", ".pyo", ".so", ".dll", ".exe",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg",
    ".mp4", ".mov", ".zip", ".tar", ".gz", ".pdf",
    ".lock",  # optional: keep package-lock if you want deps signal
}

PRIORITY_FILES = [
    "README.md", "readme.md",
    "package.json", "pyproject.toml", "requirements.txt",
    "Cargo.toml", "go.mod",
    "main.py", "app.py", "src/index.ts", "src/main.ts",
    "backend/app.py", "src/App.tsx",
]

class CustomGithubClient:
    def __init__(self):
        GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
        self.headers = {}
        if GITHUB_TOKEN:
            self.headers["Authorization"] = f'Bearer {GITHUB_TOKEN}'

    def is_ignored(self, path: str) -> bool:
        parts = path.replace("\\", "/").split("/")
        if any(p in IGNORE_DIRS for p in parts):
            return True
        name = parts[-1].lower()
        return any(name.endswith(suf) for suf in IGNORE_FILE_SUFFIXES)

    def get_file(self,owner:str, repo:str, file_path:str, max_chars:int=4000):
        if not file_path:
            raise ValueError("cannot fetch nothing..")
        
        self.headers["Accept"] = "application/vnd.github.raw"  # this gets files as text.
        file_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"

        file_response = requests.get(file_url, headers=self.headers)
        if file_response.status_code == 200:
            file_text = file_response.text
            if len(file_text) > max_chars:
                file_text = file_text[:max_chars] + "\n..[truncated]" 
            return f"file: {repo}/{file_path}\n" + file_text
        else:
            return f"file: {repo}/{file_path}\n (empty / not found)"

    def get_files(self, owner:str, repo:str, file_paths:list[str], max_chars=4000) -> list[str]:
        """retrives a list of files / file paths as a list of text content"""
        files = []
        for file_path in file_paths:
            files.append(self.get_file(owner,repo, file_path, max_chars))

        return files
    
    def parse_github_url(self, url: str) -> tuple[str, str] | None:
        if not url or not isinstance(url, str):
            return None

        url = url.strip().rstrip("/")

        # short form: owner/repo
        if "://" not in url and url.count("/") == 1:
            owner, repo = url.split("/", 1)
            repo = repo.removesuffix(".git")
            return (owner, repo) if owner and repo else None

        parsed = urllib.parse.urlparse(url)
        if parsed.netloc not in {"github.com", "www.github.com"}:
            return None

        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) < 2:
            return None

        owner, repo = parts[0], parts[1].removesuffix(".git")
        return (owner, repo) if owner and repo else None

    def select_paths_to_fetch(self, filtered_paths: list[str], limit: int = 10) -> list[str]:
        priority_names = {f.split("/")[-1] for f in PRIORITY_FILES}
        prioritized = [
            p for p in filtered_paths
            if p in PRIORITY_FILES or p.split("/")[-1] in priority_names
        ]
        rest = [p for p in filtered_paths if p not in prioritized]
        return (prioritized + rest)[:limit]

    def filter_tree(self, tree_items: list[dict], max_files: int = 80) -> list[str]:
        """Return prioritized, de-noised file paths (strings)."""
        blobs = []
        for item in tree_items:
            path = item.get("path") or ""
            if item.get("type") != "blob":
                continue
            if not path or self.is_ignored(path):
                continue
            blobs.append(path)

        priority_names = {f.split("/")[-1] for f in PRIORITY_FILES}
        prioritized = [
            p for p in blobs
            if p in PRIORITY_FILES or p.split("/")[-1] in priority_names
        ]
        rest = sorted(
            [p for p in blobs if p not in prioritized],
            key=lambda p: (p.count("/"), len(p)),  # closer to root first
        )
        return (prioritized + rest)[:max_files]
    
    def fetch_tree(self, owner, repo, recursive=1, max_files=80) -> list[dict]:
        """fetches the main branch recursively by default"""

        # gets the default branch for the repo
        url = f"https://api.github.com/repos/{owner}/{repo}"
        self.headers["Accept"] = "application/vnd.github+json"
        response = requests.get(url, headers=self.headers)
        default_branch = response.json()
        if default_branch:
            default_branch = default_branch["default_branch"]
        else:
            return []
        
        # fetches the tree of the default branch 
        tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive={recursive}"
        self.headers["Accept"] = "application/vnd.github+json"
        response = requests.get(tree_url, headers=self.headers)
        if response.status_code == 200:
            tree = json.loads(response.text).get("tree", [])
            treecontent = []
            if tree != []:
                treecontent = self.filter_tree(tree, max_files)
        else:
            raise ValueError("error code: ", response.status_code)
        return treecontent

    def fetch_repo(self, request: StdRequest) -> GitHubResponse:
        parsed = self.parse_github_url(request.repo_url)
        if not parsed:
            raise ValueError("invalid GitHub URL")
        owner, repo = parsed

        project_tree = self.fetch_tree(owner, repo, max_files=80)
        to_fetch = self.select_paths_to_fetch(project_tree, limit=10)
        fetched = self.get_files(owner, repo, to_fetch, max_chars=3000)

        md_files = [f for f in fetched if ".md" in f.split("\n", 1)[0].lower()]
        manifest = [f for f in fetched if any(m in f.split("\n", 1)[0] for m in
                    ("package.json", "pyproject.toml", "requirements.txt", "Cargo.toml", "go.mod"))]
        entry_files = [f for f in fetched if f not in md_files and f not in manifest]

        return GitHubResponse(
            repo_name=f"{owner}/{repo}",
            context_pack=ContextPack(
                md_files=md_files,
                manifest=manifest,
                entry_files=entry_files,
                project_tree=project_tree,  # paths only; NLPOps should cap how many go into prompt
            ),
        )
    
    def extract_file_paths(self,tree:list[dict], file_extension:str=".py") -> list:
        """extracts files paths ending in a specific file extension"""
        file_paths = []
        for file_path in tree:
            if file_path.endswith(file_extension):
                file_paths.append(file_path)

        return file_paths
        

# def show_result(github_response:GitHubResponse):
#     print("repository name:\t", github_response.repo_name)
#     print("=====================")
#     context = github_response.context_pack
#     files = []
#     files.extend(context.md_files)
#     files.extend(context.entry_files)
#     files.extend(context.manifest)
#     files.extend([context.project_tree])
#     for file in files:
#         if file != "":
#             print(file)
#             print("\n******************\n")

# client = CustomGithubClient()
# request = StdRequest(repo_url="https://github.com/ahmed-elrefai/codevault")
# github_response:GitHubResponse = client.fetch_repo(request)
# show_result(github_response)
