import httpx

base_url = "http://127.0.0.1:8000"

def test_analyse_repo(pat, repo_url, username):
    data = {
        "pat": pat,
        "repo_url": repo_url,
        "username": username
    }
    response = httpx.post(f"{base_url}/analyse_repo", json=data)
    print("Analyse Repo Response:")
    print(response.json())

def test_push_to_github(pat, repo_url, local_dir, branch="autodocs"):
    data = {
        "pat": pat,
        "repo_url": repo_url,
        "local_dir": local_dir,
        "branch": branch
    }
    response = httpx.post(f"{base_url}/push_to_github", json=data)
    print("Push to GitHub Response:")
    print(response.json())

if __name__ == "__main__":
    pat = "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"
    repo_url = "https://github.com/jborg2/code_summary_microservice"
    username = "jrgood01"
    local_dir = "."

    # Test analyse_repo endpoint
    #test_analyse_repo(pat, repo_url, username)

    # Test push_to_github endpoint
    test_push_to_github(pat, repo_url, local_dir)
