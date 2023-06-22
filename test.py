import httpx
import os
import dotenv

dotenv.load_dotenv()

base_url = "http://127.0.0.1:8000"

def test_analyse_repo(github_token, openai_token, username, repo_name):
    data = {
        "access_token": github_token,
        "openai_token": openai_token,
        "username": username,
        "repo_name": repo_name,
        "local_dir": "."
    }
    response = httpx.post(f"{base_url}/analyse_repo", json=data)
    print("Analyse Repo Response:")
    print(response.json())
    return response.json().get("taskID")


if __name__ == "__main__":
    #load token from .env file
    github_token = os.getenv("GITHUB_TOKEN")
    openai_token = os.getenv("OPENAI_TOKEN")

    username = os.getenv("GITHUB_USERNAME")
    local_dir = "."
    repo_name="test_repo"

    # Test analyse_repo endpoint
    task_id = test_analyse_repo(github_token, openai_token, username, repo_name)
    print(f"Task ID: {task_id}")
    # Continuously check the task status using the task_id

    # Test push_to_github endpoint
    #test_push_to_github(pat, repo_url, local_dir, username)