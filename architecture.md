# Ask DIYA - Application Architecture & Workflow

This document outlines the complete architecture, technical stack, and data flow of the "Ask DIYA" Career Guidance Chatbot.

## 1. System Overview

The application is a highly scalable, web-based Career Guidance LLM Chatbot. It leverages a **Graph-based Retrieval-Augmented Generation (GraphRAG)** approach to provide accurate, structured career advice. 

In order to handle concurrent users efficiently and minimize LLM API costs, the system utilizes asynchronous processing, an exact-match caching layer, and an efficient in-memory conversation state.

---

## 2. Tech Stack

* **Frontend:** HTML5, Vanilla JavaScript, Tailwind CSS (via CDN).
* **Backend Framework:** FastAPI (Python), Uvicorn.
* **AI & Orchestration:** LangChain (`langchain_core`, `langchain_groq`).
* **LLM Provider:** Groq (Model: `llama-3.1-8b-instant`).
* **Graph Knowledge Base:** NetworkX handling a predefined graph (`graph.json`).
* **Caching:** LangChain `SQLiteCache` (`.langchain_cache.db`).

---

## 3. Core Components

### A. The Frontend (`index.html`)
The frontend is a lightweight, single-page application (SPA).
* **UI/UX:** Built with Tailwind CSS for a modern, responsive design.
* **State Management:** Fully stateless on the client-side. The DOM updates dynamically when the user sends a message or when a response is received from the backend.
* **Session Control:** Triggers a `/clear` API call when the page is refreshed or the "New Session" button is clicked, ensuring privacy and clean conversation states.

### B. The API Layer (`api.py`)
Built with **FastAPI**, this layer bridges the web interface and the underlying AI logic.
* **`GET /`**: Serves the `index.html` static file directly to the client.
* **`POST /chat`**: Accepts a JSON payload containing the user's message, passes it to the AI logic asynchronously, and returns the generated text.
* **`POST /clear`**: Wipes the active session's conversation history from the server memory.
* **Auto-Launch:** Automatically opens the default web browser upon server initialization securely utilizing a background thread.

### C. The AI & Graph Engine (`app.py`)
This is the core engine containing the GraphRAG implementation and LLM prompt chaining.
* **Graph Initialization:** Loads `graph.json` into a `NetworkX.DiGraph`. 
* **Context Retrieval (`retrieve_context`):** Parses user queries, matches them against nodes/entities in the graph, and extracts a "subgraph" (matching nodes and their immediate edges). This ensures the LLM's answers are heavily grounded in structured, predefined relationships (e.g., Course A -> Leads To -> Career B).
* **Conversation Memory (`chat_memory`):** A volatile global list storing the current session's `HumanMessage` and `AIMessage` objects to provide the LLM with conversational context (allowing follow-up questions).
* **LangChain Pipeline:** 
  `Prompt (System + History + User context) -> Groq LLM -> Output`.

---

## 4. Execution Workflow (Step-by-Step)

1. **App Startup:** 
   User runs `python api.py`. FastAPI mounts the routes, initializes the NetworkX graph in memory, connects to the SQLite Cache database, and opens the `index.html` page in the browser.
2. **Session Initialization:**
   As the DOM loads, the frontend calls `POST /clear` to ensure the backend memory list is empty. A default welcome message is rendered on the UI.
3. **User Query:**
   The user types a question (e.g., *"What is Graphic Design?"*) and clicks Send. The UI instantly paints the user's chat bubble and triggers a `POST` request to `/chat`.
4. **Graph Retrieval (RAG):**
   The backend's `acareer_chatbot` function intercepts the query. It searches the NetworkX graph for overlapping keywords, extracting surrounding contextual edges (related degrees, exams, career mappings) into a formatted text string.
5. **Caching Layer:**
   LangChain intercepts the request before hitting the Groq API. It checks `.langchain_cache.db`:
   * *Cache Hit:* If the exact prompt was asked before, it returns the generated answer immediately (saving time and 100% of the API cost).
   * *Cache Miss:* It proceeds to step 6.
6. **LLM Generation:**
   The Context, the Conversation History, and the System Prompt are compiled and passed asynchronously to the Groq API (`chain.ainvoke`). 
7. **Response & Memory Storage:**
   The LLM's response is appended alongside the user's query into the `chat_memory` array for future context.
8. **UI Delivery:**
   The API returns the LLM string to the frontend, which parses basic markdown and renders the Counselor's chat bubble on the screen.