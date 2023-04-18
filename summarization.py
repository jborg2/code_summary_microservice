from call_graph_generator import get_call_graph_from_repo
from node import Flavor
import openai
import pickle
import tqdm

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
    #completion = openai.ChatCompletion.create(
    #    model="gpt-3.5-turbo",
    #    messages=[
    #            {"role": "system", "content": "You are a code summarization assistant."},
    #            {"role": "user", "content": prompt}
    #        ]
    #)    

    return "" #completion['choices'][0]['message']['content']



def run_summary(graph, node, chain=[]):
    print(chain)
    for subcall in graph.nodes[node]["subcalls"]:
        if subcall.flavor == Flavor.METHOD:
            if graph.nodes[subcall]["summary"] is None and subcall.name != node.name and subcall not in chain:
                print("SC", subcall)
                run_summary(graph, subcall, [node] + chain)

            subcalls = {}
            for subsubcall in graph.nodes[subcall]["subcalls"]:
                if subsubcall.flavor == Flavor.METHOD:
                    subcalls[subsubcall] = graph.nodes[subsubcall]["summary"]
            node = graph.nodes[subcall]
            code = "".join(open(node["file"]).readlines()[subcall.ast_node.lineno - 1:subcall.ast_node.end_lineno+1])
            print("summarizing: " + subcall.name)
            graph.nodes[subcall]["summary"] = run_chatgpt_prompt(code, subcalls)
    

def summarize_repo(repo_dir):
    graph, file_map = get_call_graph_from_repo(repo_dir)
    for node in tqdm.tqdm(graph.nodes.keys()):
        if node.flavor == Flavor.METHOD:
            run_summary(graph, node)

    with open('my_dict.pickle', 'wb') as f:
        # pickle the dictionary to the file
        pickle.dump(graph.nodes, f)


summarize_repo("../pyan")