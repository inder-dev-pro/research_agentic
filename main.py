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
from IPython.display import display, Image
from web_operations import serp_search

load_dotenv()

llm=init_chat_model('groq:llama-3.1-8b-instant')

class State(TypedDict):
    messages:Annotated[list, add_messages]
    user_question:str | None
    google_results:str | None
    bing_results:str | None
    reddit_results:str | None
    selected_reddit_urls:list[str] | None
    reddit_post_data:str | None
    google_analysis:str | None
    bing_analysis:str | None
    reddit_analysis:str | None
    final_answer:str | None


def google_search(state: State):
    user_question=state.get("user_question")
    print(f"Searching google for : {user_question}")
    google_results=serp_search(user_question,  engine="Google")
    print(google_results)
    return {"google_results":google_results}

def bing_search(state: State):
    user_question=state.get("user_question")
    print(f"Searching bing for : {user_question}")
    bing_results=serp_search(user_question, engine="Bing")
    print(bing_results)
    return {"bing_results":bing_results}

def reddit_search(state: State):
    user_question=state.get("user_question")
    print(f"Searching reddit for : {user_question}")
    reddit_results=[]
    return {"reddit_results":reddit_results}

def analyse_reddit_posts(state: State):
    return

def analyse_google_results(state: State):
    return

def analyse_bing_results(state: State):
    return

def retrieve_reddit_posts(state: State):
    return

def analyse_reddit_results(state: State):
    return

def synthesize_analyses(state: State):
    return

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
            print(f"\nFinal Answer:\n{final_state.get("final_answer")}\n")

        print("-"*80)

if __name__=="__main__":
    run_chatbot()