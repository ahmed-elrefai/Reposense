from typing import Literal
from pydantic import BaseModel

class StdRequest(BaseModel):
    repo_url:str
    mode:Literal['report'] = 'report'

class ContextPack(BaseModel):
    md_files:list
    manifest:list
    entry_files:list
    project_tree:list

class GitHubResponse(BaseModel):
    repo_name:str
    context_pack:ContextPack

    