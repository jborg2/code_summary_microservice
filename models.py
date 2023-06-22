from pydantic import BaseModel
from typing import Optional

class AnalyseRepoData(BaseModel):
    github_token: str
    openai_token: str
    username: str
    repo_name: str
    local_dir: str

class PushToGithubData(BaseModel):
    token: str
    local_dir: str
    branch: Optional[str] = "autodocs"
    username: str
    access_token: str

class CreateProjectData(BaseModel):
    access_token: str
    username: str
    repo_name: str