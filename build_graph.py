"""Run once to build the knowledge graph and save it locally."""
import os
import json
import sys
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_experimental.graph_transformers import LLMGraphTransformer

load_dotenv()

# Load and chunk the knowledge base
loader = TextLoader("india_career_guidance_kb.md", encoding="utf-8")
documents = loader.load()
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
chunks = text_splitter.split_documents(documents)

total = len(chunks)
print(f"Split into {total} chunks. Extracting graph with Gemini...\n")

# Extract graph using LLM — process one chunk at a time with progress
llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", temperature=0)
transformer = LLMGraphTransformer(llm=llm)

graph_documents = []
for i, chunk in enumerate(chunks, 1):
    sys.stdout.write(f"\rProcessing chunk {i}/{total} [{('=' * int(30 * i / total)):<30}] {100 * i // total}%")
    sys.stdout.flush()
    result = transformer.convert_to_graph_documents([chunk])
    graph_documents.extend(result)

print("\n")

# Convert to a serializable format
nodes = {}
edges = []

for doc in graph_documents:
    for node in doc.nodes:
        nodes[node.id] = {"id": node.id, "type": node.type, "properties": node.properties}
    for rel in doc.relationships:
        edges.append({
            "source": rel.source.id,
            "source_type": rel.source.type,
            "target": rel.target.id,
            "target_type": rel.target.type,
            "type": rel.type,
            "properties": rel.properties,
        })

graph_data = {"nodes": nodes, "edges": edges}

with open("graph.json", "w") as f:
    json.dump(graph_data, f, indent=2, default=str)

print(f"Done! Saved {len(nodes)} nodes and {len(edges)} edges to graph.json")
