import os
import json
import streamlit as st
import networkx as nx
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage

# --- Set API Key ---
load_dotenv()

# --- Cache the graph to prevent reloading on every chat message ---
@st.cache_resource
def load_graph():
    with open("graph.json") as f:
        graph_data = json.load(f)
    
    G = nx.DiGraph()
    for node_id, node in graph_data["nodes"].items():
        G.add_node(node_id, type=node["type"], **node.get("properties", {}))
    for edge in graph_data["edges"]:
        G.add_edge(edge["source"], edge["target"], type=edge["type"], **edge.get("properties", {}))
    return G

G = load_graph()

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
    
    context_parts = []
    for node_id, data, _ in scored_nodes[:top_k]:
        context_parts.append(f"[{data.get('type', 'Entity')}] {node_id}")
        for _, target, edata in G.out_edges(node_id, data=True):
            context_parts.append(f"  -> {edata.get('type', 'related_to')} -> [{G.nodes[target].get('type', '')}] {target}")
        for source, _, edata in G.in_edges(node_id, data=True):
            context_parts.append(f"  <- {edata.get('type', 'related_to')} <- [{G.nodes[source].get('type', '')}] {source}")
            
    return "\n".join(context_parts) if context_parts else "No relevant graph context found."

# --- Initialize Chain ---
llm = ChatGroq(model_name="llama-3.1-8b-instant", temperature=0)

prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an expert career guidance counselor for Indian students.
    
You have a knowledge graph showing entities and their relationships based on the student's query:
{graph_context}

Use this graph context to give accurate, structured answers. 
Provide straight-forward, concise answers (use bullet points where possible).
Greet the user and remember their name if they provide it in previous messages."""),
    ("placeholder", "{chat_history}"),
    ("human", "{question}"),
])

chain = prompt | llm

# --- Build the Streamlit UI ---
st.set_page_config(page_title="Career Counselor", page_icon="🎓")
st.title("🎓 Career Guidance Counselor")
st.caption("Powered by GraphRAG & Llama-3.1")

# Initialize chat memory in Streamlit session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display past chat messages
for msg in st.session_state.messages:
    role = "user" if isinstance(msg, HumanMessage) else "assistant"
    with st.chat_message(role):
        st.markdown(msg.content)

# Accept user input at the bottom of the screen
if prompt_text := st.chat_input("E.g., What should I choose after 10th?"):
    # Display user's new message
    with st.chat_message("user"):
        st.markdown(prompt_text)
        
    # Get contextual graph data based on query
    graph_context = retrieve_context(prompt_text)
    
    # Generate and display AI response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = chain.invoke({
                "graph_context": graph_context,
                "chat_history": st.session_state.messages,
                "question": prompt_text,
            })
            st.markdown(response.content)
            
    # Save interaction to memory
    st.session_state.messages.extend([
        HumanMessage(content=prompt_text),
        AIMessage(content=response.content)
    ])
