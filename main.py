from tracemalloc import start
from dotenv import load_dotenv
from typing import Annotated
from langgraph import graph
from langgraph.graph import StateGraph, END, START
from langgraph.graph import message
from langgraph.graph.message import add_messages
from langchain.chat_models import init_chat_model
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
import json
from web_operations import (
    serp_search,
    reddit_search_api,
    retrieve_reddit_posts as fetch_reddit_posts,
)
from prompts import (
    get_google_analysis_messages,
    get_bing_analysis_messages,
    get_reddit_url_analysis_messages,
    get_reddit_analysis_messages,
    get_synthesis_messages,
)

load_dotenv()

llm=init_chat_model('groq:llama-3.1-8b-instant')

dataset_id="gd_lvz8ah06191smkebj4"


def _compact_search_payload(payload, max_organic: int = 3, max_chars: int = 4000) -> str:
    """Reduce prompt size before sending to the LLM (helps avoid rate limits)."""
    if payload is None:
        return ""

    if isinstance(payload, str):
        text = payload
    elif isinstance(payload, dict):
        payload_copy = dict(payload)
        # Keep only top-N organic results to reduce prompt tokens.
        organic = payload_copy.get("organic")
        if isinstance(organic, list):
            payload_copy["organic"] = organic[:max_organic]
        text = json.dumps(payload_copy, ensure_ascii=False)
    else:
        # Fallback: stringify unknown types.
        text = json.dumps(payload, ensure_ascii=False, default=str)

    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...[truncated]"


def _force_concise_response(messages: list[dict], max_words: int = 120) -> list[dict]:
    """Instruct the model to return a short answer to reduce completion tokens."""
    if messages and messages[0].get("role") == "system":
        messages = list(messages)
        messages[0] = dict(messages[0])
        messages[0]["content"] = (
            messages[0]["content"]
            + f"\n\nIMPORTANT: Keep your response under {max_words} words."
        )
    return messages

class State(TypedDict):
    messages:Annotated[list, add_messages]
    user_question:str | None
    google_results:str | None
    bing_results:str | None
    reddit_results:str | None
    selected_reddit_urls:list[str] | None
    reddit_post_data:list | None
    google_analysis:str | None
    bing_analysis:str | None
    reddit_analysis:str | None
    final_answer:str | None

class RedditURLAnalysis(BaseModel):
    selected_urls: list[str] = Field(description="List of Reddit URLs that are most relevant to the user's question")

def google_search(state: State):
    user_question=state.get("user_question","")
    print(f"Searching google for : {user_question}")
    google_results=serp_search(user_question,  engine="Google")
    print(google_results)
    return {"google_results":google_results}

def bing_search(state: State):
    user_question=state.get("user_question","")
    print(f"Searching bing for : {user_question}")
    bing_results=serp_search(user_question, engine="Bing")
    print(bing_results)
    return {"bing_results":bing_results}

def reddit_search(state: State):
    user_question=state.get("user_question","")
    print(f"Searching reddit for : {user_question}")
    reddit_results=reddit_search_api(user_question)
    print(reddit_results)
    return {"reddit_results":reddit_results}

def analyse_reddit_posts(state: State):
    user_question=state.get("user_question","")
    reddit_results=state.get("reddit_results","")

    if not reddit_results:
        return {"selected_reddit_urls":[]}
    structured_llm = llm.with_structured_output(RedditURLAnalysis)
    messages = get_reddit_url_analysis_messages(user_question, reddit_results)
    
    try:
        analysis = structured_llm.invoke(messages)
        selected_urls = analysis.selected_urls

        print("\nSelected Reddit URLs:")
        for i, url in enumerate(selected_urls,1):
            print(f"    {i}.{url}")
    except Exception as e:
        print(e)
        selected_urls = []

    return {"selected_reddit_urls":selected_urls}

def analyse_google_results(state: State):
    print("Analyzing google search results")

    user_question=state.get("user_question", "")
    google_results=_compact_search_payload(state.get("google_results", ""))

    messages=_force_concise_response(
        get_google_analysis_messages(user_question, google_results), max_words=120
    )

    reply = llm.invoke(messages)

    return {"google_analysis": reply.content}

def analyse_bing_results(state: State):
    print("Analyzing bing search results")

    user_question=state.get("user_question", "")
    bing_results=_compact_search_payload(state.get("bing_results", ""))

    messages=_force_concise_response(
        get_bing_analysis_messages(user_question, bing_results), max_words=120
    )

    reply = llm.invoke(messages)

    return {"bing_analysis": reply.content}

def retrieve_reddit_posts(state: State):
    print("Getting reddit posts comments")

    selected_urls=state.get("selected_reddit_urls", [])

    if not selected_urls:
        return {"reddit_post_data":[]}

    print(f"Processing {len(selected_urls)} Reddit URLs")

    reddit_comments_bundle = fetch_reddit_posts(selected_urls)
    reddit_post_data: list = []
    if isinstance(reddit_comments_bundle, dict):
        # `web_operations.retrieve_reddit_posts` returns {"comments": [...], "total_count": ...}
        reddit_post_data = reddit_comments_bundle.get("comments", []) or []
    elif isinstance(reddit_comments_bundle, list):
        reddit_post_data = reddit_comments_bundle
    else:
        reddit_post_data = []

    if reddit_post_data:
        print(f"Successfully got {len(reddit_post_data)} posts")
    else:
        print("Failed to get post data")
        reddit_post_data=[]
    
    print(reddit_post_data)

    return {"reddit_post_data":reddit_post_data}
    

def analyse_reddit_results(state: State):
    print("Analyzing reddit search results")

    user_question=state.get("user_question", "")
    reddit_results=state.get("reddit_results", "")
    reddit_post_data=state.get("reddit_post_data", []) or []
    
    messages=get_reddit_analysis_messages(user_question, reddit_results, reddit_post_data)

    reply = llm.invoke(messages)

    return {"reddit_analysis": reply.content}

def synthesize_analyses(state: State):
    print("Combine all results together")

    user_question= state.get("user_question", "")
    google_analysis=state.get("google_analysis", "")
    bing_analysis=state.get("bing_analysis", "")
    reddit_analysis=state.get("reddit_analysis", "")

    messages=get_synthesis_messages(
        user_question, google_analysis, bing_analysis, reddit_analysis
    )

    reply=llm.invoke(messages)
    final_answer=reply.content

    return {"final_answer":final_answer, "messages":[{"role":"assistant", "content":final_answer}]}

graph_builder=StateGraph(State)

graph_builder.add_node("google_search", google_search)
graph_builder.add_node("bing_search", bing_search)
graph_builder.add_node("reddit_search", reddit_search)
graph_builder.add_node("analyse_reddit_posts", analyse_reddit_posts)
graph_builder.add_node("analyse_google_results", analyse_google_results)
graph_builder.add_node("analyse_bing_results", analyse_bing_results)
graph_builder.add_node("retrieve_reddit_posts", retrieve_reddit_posts)
graph_builder.add_node("analyse_reddit_results", analyse_reddit_results)
graph_builder.add_node("synthesize_analyses", synthesize_analyses)

graph_builder.add_edge(start_key=START, end_key="google_search")
graph_builder.add_edge(start_key=START, end_key="bing_search")
graph_builder.add_edge(start_key=START, end_key="reddit_search")

graph_builder.add_edge(start_key="google_search", end_key="analyse_reddit_posts")
graph_builder.add_edge(start_key="bing_search", end_key="analyse_reddit_posts")
graph_builder.add_edge(start_key="reddit_search", end_key="analyse_reddit_posts")

graph_builder.add_edge(start_key="analyse_reddit_posts", end_key="retrieve_reddit_posts")

graph_builder.add_edge(start_key="retrieve_reddit_posts", end_key="analyse_google_results")
graph_builder.add_edge(start_key="retrieve_reddit_posts", end_key="analyse_bing_results")
graph_builder.add_edge(start_key="retrieve_reddit_posts", end_key="analyse_reddit_results")

graph_builder.add_edge(start_key="analyse_google_results", end_key="synthesize_analyses")
graph_builder.add_edge(start_key="analyse_bing_results", end_key="synthesize_analyses")
graph_builder.add_edge(start_key="analyse_reddit_results", end_key="synthesize_analyses")

graph_builder.add_edge(start_key="synthesize_analyses", end_key=END)

app=graph_builder.compile()

def run_chatbot():
    print("Starting the Multi Resource Agent from Google, Bing, Reddit")
    print("Type exit to quit!")

    while True:
        user_input=input("Enter your message:")
        if (user_input.lower()=="exit"):
            print("Bye!")
            break
        state ={
            "messages":[{"role":"user", "content":user_input}],
            "user_question":user_input,
            "google_results":None,
            "bing_results":None,
            "reddit_results":None,
            "selected_reddit_urls":None,
            "reddit_post_data":None,
            "google_analysis":None,
            "bing_analysis":None,
            "reddit_analysis":None,
            "final_answer":None
        }
        print("\nStarting parallel research process")
        print("\nLaunching Google Bing Reddit Searcher")

        final_state=app.invoke(state)

        if (final_state.get("final_answer")):
            print(f'\nFinal Answer:\n{final_state.get("final_answer")}\n')

        print("-"*80)

if __name__=="__main__":
    run_chatbot()