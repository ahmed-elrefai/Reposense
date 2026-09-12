from models import GitHubResponse
def build_summary(github_response:GitHubResponse): 
    print()
    print("=====================")
    context = github_response.context_pack
    files = []
    summary = f"repository name:\t {github_response.repo_name} \n\n"
    files.extend(context.md_files)
    files.extend(context.entry_files)
    files.extend(context.manifest)
    files.extend(context.project_tree)
    
    summary += "\n".join(files)
    return summary
    
def build_report_prompt(github_response: GitHubResponse) -> str:
    repo_name = github_response.repo_name
    evidence = build_summary(github_response)  # your truncated, labeled pack

    return f"""You are Repo Sense. Produce a single-shot structured report about a public GitHub repository.

Return ONLY valid JSON. No markdown. No prose outside JSON. No code fences.

Exact schema (all keys required):
{{
  "status": "ok" | "low_confidence" | "refuse",
  "repo": {{
    "owner": "string",
    "name": "string",
    "url": "string"
  }},
  "goal": "string",
  "inputs": ["string"],
  "outputs": ["string"],
  "how_it_works": "string",
  "stack": ["string"],
  "confidence": 0.0,
  "gaps": ["string"],
  "sources": ["string"]
}}

Rules:
1. Use ONLY the evidence below. Do not invent files, APIs, or behavior that are not supported by the evidence.
2. If evidence is missing, empty, or too thin to support a useful report:
   - set "status" to "refuse" or "low_confidence"
   - lower "confidence"
   - explain missing pieces in "gaps"
3. "sources" must list only paths that actually appear in the evidence.
4. Prefer precise, short statements over long essays.
5. "confidence" is a float from 0.0 to 1.0.
6. Parse owner/name from repo identifier when possible. If URL is unknown, leave "url" as empty string.

Repository identifier:
{repo_name}

Evidence pack:
{evidence}
"""

