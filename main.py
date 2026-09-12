import json
import sys

from models import StdRequest
from github_integ import CustomGithubClient
from nlpops import build_report_prompt
from llmman import generate_report


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: python -m reposense <github-url-or-owner/repo>")
        return 2

    url = argv[1].strip()
    request = StdRequest(repo_url=url)

    github = CustomGithubClient()
    github_response = github.fetch_repo(request)
    prompt = build_report_prompt(github_response)
    report = generate_report(prompt)

    print(json.dumps(report, indent=2, ensure_ascii=False))

    status = str(report.get("status", "")).lower()
    if status == "refuse":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))