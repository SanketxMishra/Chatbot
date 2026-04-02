# Career Guidance Chatbot — GraphRAG (In-Memory)

An AI-powered career counseling chatbot for Indian students, built using **GraphRAG** (Graph-based Retrieval-Augmented Generation) with an in-memory graph powered by NetworkX and Google Gemini.

## Architecture

The project has two phases: **graph construction** (offline, run once) and **query answering** (online, interactive).

```
┌─────────────────────┐        ┌──────────────┐        ┌────────────┐
│ india_career_        │        │              │        │            │
│ guidance_kb.md       │──────▶ │ build_graph  │──────▶ │ graph.json │
│ (knowledge base)     │        │ .py          │        │ (1362 nodes│
└─────────────────────┘        └──────────────┘        │  1410 edges)│
                                                        └─────┬──────┘
                                                              │
                                                              ▼
                                ┌──────────────┐        ┌────────────┐
                                │   User asks  │──────▶ │  app.py    │
                                │   a question │        │ (chatbot)  │
                                └──────────────┘        └────────────┘
```

## Files

| File | Purpose | When to run |
|------|---------|-------------|
| `india_career_guidance_kb.md` | Structured knowledge base covering Indian education, careers, exams, scholarships, etc. | Reference only |
| `build_graph.py` | Extracts entities and relationships from the KB using Gemini, saves to `graph.json` | Once (or when KB changes) |
| `graph.json` | The extracted knowledge graph in JSON format | Auto-generated |
| `app.py` | Interactive chatbot that uses GraphRAG to answer questions | Every time you want to chat |

## How It Works — Detailed Logic

### Phase 1: Graph Construction (`build_graph.py`)

This runs once and performs three steps:

#### Step 1 — Chunking the Knowledge Base

The markdown file is split into overlapping chunks of ~1000 characters each using `RecursiveCharacterTextSplitter`. Overlap of 100 characters ensures that entities mentioned at chunk boundaries aren't lost.

For example, a section about "NEET exam requirements" might become one chunk, while "MBBS college admissions" becomes another.

#### Step 2 — Entity & Relationship Extraction (LLMGraphTransformer)

Each chunk is sent to Gemini with a prompt that asks: *"What entities (people, exams, careers, institutions, streams) exist in this text, and how are they related?"*

From a chunk like:
> "Students who pass NEET-UG can pursue MBBS, BDS, or BAMS at medical colleges across India."

The LLM extracts:
- **Nodes:** `NEET-UG` (Exam), `MBBS` (Course), `BDS` (Course), `BAMS` (Course)
- **Edges:** `NEET-UG → leads_to → MBBS`, `NEET-UG → leads_to → BDS`, `NEET-UG → leads_to → BAMS`

This is done for all 47 chunks, producing 1362 nodes and 1410 relationships.

#### Step 3 — Serialization

All nodes and edges are saved to `graph.json` so the chatbot can load them instantly without re-running extraction.

### Phase 2: Query Answering (`app.py`)

When you ask a question, three things happen:

#### Step 1 — Graph Loading

On startup, `graph.json` is loaded into a NetworkX directed graph (DiGraph) in memory. This is instant (~milliseconds).

#### Step 2 — Graph Retrieval

Your question is tokenized into keywords. Each graph node is scored by how many query keywords appear in its ID or type label. The top 30 matching nodes are selected, along with all their incoming and outgoing edges.

For example, asking *"What exams do I need for engineering?"* would match nodes like `JEE Main`, `JEE Advanced`, `Engineering`, `B.Tech`, and pull their relationships:
```
[Exam] JEE Main
  -> leads_to -> [Course] B.Tech
  -> conducted_by -> [Organization] NTA
[Exam] JEE Advanced
  -> leads_to -> [Institution] IIT
  <- requires <- [Stream] PCM
```

This subgraph becomes the **graph context**.

#### Step 3 — LLM Generation

Both the graph context and the full knowledge base are sent to Gemini along with your question. The graph context helps the LLM understand structured relationships (what leads to what, what requires what), while the full KB provides detailed descriptions and nuance.

The LLM synthesizes both into a natural language answer.

### Why GraphRAG Instead of Just Passing the Document?

| Approach | Strengths | Weaknesses |
|----------|-----------|------------|
| **Plain RAG** (pass full doc) | Simple, works well for small KBs | No understanding of relationships between entities |
| **GraphRAG** (this project) | Captures connections (exam → course → career), enables relationship-based queries | More complex setup, requires graph extraction step |

GraphRAG shines for questions like:
- *"What's the path from Class 12 PCB to becoming a doctor?"* — follows a chain of relationships
- *"Which exams are common between engineering and architecture?"* — finds shared connections in the graph
- *"Compare government vs private career paths after B.Tech"* — traverses multiple relationship branches

## Setup & Usage

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install langchain-google-genai langchain-experimental langchain-community langchain-text-splitters networkx

# 3. Build the graph (one-time, takes a few minutes)
python build_graph.py

# 4. Run the chatbot
python app.py
```

## ELI5 (Explain Like I'm 5)

Imagine you have a big book about careers in India. You want to build a robot that answers students' questions about it.

**The simple way:** Give the robot the whole book every time someone asks a question. The robot reads the whole thing and answers. This works, but the robot doesn't really *understand* how things connect — it just searches for words.

**The GraphRAG way (what we do):**

1. **First, we make a map.** We read the book once and draw a giant connect-the-dots picture:
   - "NEET exam" connects to "MBBS degree"
   - "MBBS degree" connects to "Doctor career"
   - "PCB stream" connects to "NEET exam"

   This map is our **knowledge graph**. We save it so we never have to make it again.

2. **When someone asks a question**, say *"How do I become a doctor?"*, we:
   - Look at our map and find "Doctor" and everything connected to it
   - Pull out that little piece of the map: Doctor ← MBBS ← NEET ← PCB stream
   - Give the robot both the map piece AND the book
   - The robot now knows the exact *path* and can explain it step by step

It's like the difference between giving someone a textbook vs. giving them a textbook AND a flowchart. The flowchart makes it way easier to trace connections.

**In short:**
- `build_graph.py` = reading the book and drawing the map (slow, do once)
- `app.py` = using the map + book to answer questions (fast, do every time)
