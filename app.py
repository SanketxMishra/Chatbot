import os
import json
import networkx as nx
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.globals import set_llm_cache
from langchain_community.cache import SQLiteCache
import asyncio

load_dotenv()

# Set up Exact-Match Caching in SQLite
set_llm_cache(SQLiteCache(database_path=".langchain_cache.db"))

# Load the graph into NetworkX
with open("graph.json") as f:
    graph_data = json.load(f)

G = nx.DiGraph()
for node_id, node in graph_data["nodes"].items():
    G.add_node(node_id, type=node["type"], **node.get("properties", {}))
for edge in graph_data["edges"]:
    G.add_edge(edge["source"], edge["target"], type=edge["type"], **edge.get("properties", {}))

print(f"Loaded graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges\n")


def retrieve_context(query: str, top_k: int = 30) -> str:
    """Find relevant nodes/edges by keyword matching on the graph."""
    query_terms = set(query.lower().split())
    scored_nodes = []

    for node_id, data in G.nodes(data=True):
        node_text = f"{node_id} {data.get('type', '')}".lower()
        score = sum(1 for term in query_terms if term in node_text)
        if score > 0:
            scored_nodes.append((node_id, data, score))

    scored_nodes.sort(key=lambda x: x[2], reverse=True)
    relevant_ids = {n[0] for n in scored_nodes[:top_k]}

    # Gather subgraph context: relevant nodes + their neighbors + connecting edges
    context_parts = []
    for node_id, data, _ in scored_nodes[:top_k]:
        context_parts.append(f"[{data.get('type', 'Entity')}] {node_id}")
        # Add edges from/to this node
        for _, target, edata in G.out_edges(node_id, data=True):
            context_parts.append(f"  -> {edata.get('type', 'related_to')} -> [{G.nodes[target].get('type', '')}] {target}")
        for source, _, edata in G.in_edges(node_id, data=True):
            context_parts.append(f"  <- {edata.get('type', 'related_to')} <- [{G.nodes[source].get('type', '')}] {source}")

    return "\n".join(context_parts) if context_parts else "No relevant graph context found."


# Load raw KB as fallback context
with open("india_career_guidance_kb.md", encoding="utf-8") as f:
    knowledge_base = f.read()

# For Groq free tier, full KB is too large (~10k tokens). Only relying on graph context.
llm = ChatGroq(model_name="llama-3.1-8b-instant", temperature=0)

prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an expert career guidance counselor for Indian students.

You have a knowledge graph showing entities and their relationships based on the student's query:
{graph_context}

IMPORTANT INSTRUCTIONS:
1. Provide straight-forward, concise answers (use bullets).
2. ONLY answer questions related to career guidance, education, exams, and streams.
3. Be very warm and encouraging.
"""),
    ("placeholder", "{chat_history}"),
    ("human", "{question}"),
])

chain = prompt | llm

# Global dictionary to hold conversational context in-memory per session
chat_memory = {}

def clear_memory(session_id="default"):
    """Wipes the current conversation from memory for a session."""
    global chat_memory
    if session_id in chat_memory:
        chat_memory[session_id] = []

async def acareer_chatbot(question: str, session_id: str = "default") -> str:
    """Asynchronous handling of the chatbot query to prevent server stalling."""
    global chat_memory
    if session_id not in chat_memory:
        chat_memory[session_id] = []

    graph_context = retrieve_context(question)
    
    # ainvoke will let the web server handle thousands of concurrent requests
    response = await chain.ainvoke({
        "graph_context": graph_context,
        "chat_history": chat_memory[session_id],
        "question": question,
    })
    
    # Store the back-and-forth into the runtime memory list
    chat_memory[session_id].extend([
        HumanMessage(content=question),
        AIMessage(content=response.content)
    ])
    
    return response.content

# Updated terminal handling for async execution
if __name__ == "__main__":
    print("Career Guidance Chatbot (GraphRAG) - Async & Cached")
    print("Type 'quit' to exit.\n")
    session_id = "terminal_session"
    while True:
        question = input("You: ").strip()
        if question.lower() in ("quit", "exit", "q"):
            break
        if not question:
            continue
        print(f"\nCounselor: {asyncio.run(acareer_chatbot(question, session_id))}\n")
