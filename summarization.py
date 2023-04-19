from call_graph_generator import get_call_graph_from_repo
from node import Flavor
import openai
import pickle
import tqdm
import os
import git
import shutil

openai_key = "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"
openai.api_key = openai_key

def run_chatgpt_prompt(code, subcalls):
    prompt = "Subcall defintions: \n"
    for subcall, val in subcalls.items():
        if val is not None:
            prompt += subcall.name + " " + val + "\n"
    prompt += "Method Code: \n"
    prompt += code + "\n"
    prompt += "Generate a summary that is no more than 5 sentances for the method"
    if len(subcalls.items()) > 0:
        prompt += " based on the subcall definitions provided above"
    prompt += "."
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
                {"role": "system", "content": "You are a code summarization assistant."},
                {"role": "user", "content": prompt}
            ]
    )    

    return completion['choices'][0]['message']['content']



def run_summary(graph, node, chain=[]):
    for subcall in graph.nodes[node]["subcalls"]:
        if subcall.flavor == Flavor.METHOD:
            if graph.nodes[subcall]["summary"] is None and subcall.name != node.name and subcall not in chain:
                print("SC: ", type(subcall))
                run_summary(graph, subcall, [node] + chain)
    subcalls = {}
    for subsubcall in graph.nodes[node]["subcalls"]:
        if subsubcall.flavor == Flavor.METHOD:
            subcalls[subsubcall] = graph.nodes[subsubcall]["summary"]
    
    code = "".join(open(graph.nodes[node]["file"]).readlines()[node.ast_node.lineno - 1:node.ast_node.end_lineno+1])
    graph.nodes[node]["summary"] = run_chatgpt_prompt(code, subcalls)
    
def constrcut_replace_maps(nodes):
    replace_map = {}
    for node in nodes:
        if node.flavor == Flavor.METHOD:
            file = nodes[node]["file"]
            if file not in replace_map:
                replace_map[file] = []
            replace_map[file].append((node.ast_node.lineno, node.ast_node.end_lineno, nodes[node]["summary"]))
    return replace_map

def generate_replace_file(file, replace_map):
    data = open(file).readlines()
    final_data = "".join(data.copy())
    for each in replace_map:
        start = each[0]
        end = each[1]
        summary = each[2]
        method_header = data[start - 1]
        repl = method_header + " " + summary
        final_data = final_data.replace("".join(data[start - 1 : end]), repl)
    return final_data

def get_docfile(prompt):
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
                {"role": "system", "content": "You are a code summarization assistant."},
                {"role": "user", "content": f'{prompt}\n Generate a well-structured and comprehensive documentation in .md format for the following Python file, including code snippets and example usages when necessary. Choose which sections to add or hide based on the relevance of the content: '}
            ]
    )    

    return completion['choices'][0]['message']['content']

def summarize_repo(repo_dir, load_from_file=True):
    autodocs_dir = os.path.join(repo_dir, "autodocs")
    if load_from_file:
        with open('my_dict.pickle', 'rb') as f:
            graph = pickle.load(f)
            cm = constrcut_replace_maps(graph)
            
            for file in cm:
                repl_data = generate_replace_file(file, cm[file])
                if not os.path.exists(autodocs_dir):
                    os.makedirs(autodocs_dir)
                try:
                    file_name = os.path.basename(file).replace(".py", ".md")
                    root = os.path.join(repo_dir, 'autodocs')
                    path = os.path.join(root, file_name)
                    docs = get_docfile(repl_data)
                    print(f"outputting to: {path}")
                    with open(path, "w") as f:
                        f.write(docs)
                except:
                    print(f'Failed for {file}')

        return graph
    
    graph, file_map = get_call_graph_from_repo(repo_dir)

    for node in tqdm.tqdm(graph.nodes.keys()):
        if node.flavor == Flavor.METHOD:
            run_summary(graph, node)

    with open('my_dict.pickle', 'wb') as f:
        pickle.dump(graph.nodes, f)
    return graph

def generate_docs():
    summarize_repo(".")

def clone_repo(repo_url, local_dir):
    if not os.path.exists(local_dir):
        os.makedirs(local_dir)
    try:
        git.Repo.clone_from(repo_url, local_dir)
    except Exception as e:
        print(f"Error while cloning the repository: {e}")

def push_to_repo(repo_dir, branch, commit_message, pat, repo_url):
    try:
        repo = git.Repo(repo_dir)
        try:
            repo.git.checkout(branch)
        except git.exc.GitCommandError:
            repo.git.checkout('-b', branch)
        repo.git.add(A=True)
        repo.git.commit('-m', commit_message)
        repo.git.push("--force", f"https://{pat}@{repo_url[8:]}")
    except Exception as e:
        print(f"Error while pushing to the repository: {e}")

def generate_documentation(local_dir):
    # Generate documentation
    graph = summarize_repo(local_dir, load_from_file=True)
    print("AutoDocs Generated")
    return graph

def push_documentation_to_github(pat, repo_url, local_dir, branch="autodocs"):
    # Push the generated documentation to the repository
    commit_message = "AutoDocs"
    push_to_repo(local_dir, branch, commit_message, pat, repo_url)
    print("AutoDocs Pushed to GitHub")

def generate_docs_for_github_repo(pat, repo_url, username, branch="autodocs"):
    local_dir = os.path.join(username, "cloned_repo")
    
    # Clone the repository
    clone_repo(repo_url, local_dir)

    # Generate documentation
    graph = generate_documentation(local_dir)

    # Push the generated documentation to the repository
    push_documentation_to_github(pat, repo_url, local_dir, branch)

    # Clean up the local repository directory
    #shutil.rmtree(local_dir)

#github_token = "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"
#generate_docs_for_github_repo(github_token, "https://github.com/jborg2/code_summary_microservice")