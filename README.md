# Law Firm AI Data Pipeline: From Chaos to Air-Gapped RAG

## ⚖️ Mission Statement & Use Case
Law firms frequently download massive batches of disorganized public records, discovery files, and deeds from county portals (e.g., Miami-Dade, Broward). These files arrive with cryptic UUID filenames and fragmented metadata, making chronological case review and batch-printing a time-consuming manual task. 

This pipeline acts as an automated digital paralegal and data engineer. It is a hybrid architecture that uses a custom-built, multi-threaded macOS desktop app to triage and chronologically sort chaotic document dumps, and then utilizes local, air-gapped Large Language Models (LLMs) on Apple Silicon to perform deep Retrieval-Augmented Generation (RAG) for secure legal reasoning and drafting.

---

## 🚀 Phase 1: The AI Sorter Engine (Triage & Extraction)
Before local AI can query documents, the raw desktop dumps must pass through a strict, automated triage system to ensure chronological formatting, data hygiene, and text extraction. This is handled by a standalone, multi-threaded macOS application built with CustomTkinter.

* **Swarm Processing (Multithreading):** Utilizes `concurrent.futures` to deploy a pool of simultaneous AI worker bots. This deep-crawls nested directories and processes multiple files in parallel, drastically cutting ingestion time.
* **Dual-Engine Extraction:** Utilizes the `google-genai` SDK (`gemini-2.5-flash`) to perform two tasks in a single breath:
  1. **Metadata:** Distinguishes between execution dates and misleading stamps to generate chronological names (`YYYY-MM-DD_Document_Type.ext`).
  2. **Full-Document OCR:** Extracts 100% of the raw text to generate lightweight, unabridged sibling `.txt` files for vectorization.
* **Universal Format Support (Ghost Conversion):** Natively intercepts legacy/proprietary formats like multi-page TIFFs and Apple `.HEIC` photos, silently converting them to temporary PDFs in the background for flawless AI ingestion.
* **Bulletproof ASCII Protection:** Bypasses network crashes caused by special characters (em-dashes, smart quotes) by creating sanitized, strictly ASCII-named "Ghost Copies" for the upload phase.
* **Immutable Ledgering:** Every successful rename, classification, and original file path is logged to a thread-safe `document_catalog_gemini.csv` for a permanent forensic audit trail.
* **Strict Cloud Hygiene:** The app enforces a `client.files.delete()` command the millisecond the data is extracted, ensuring legal documents are wiped from Google's servers immediately. API keys are securely stored in a hidden local Mac profile (`~/.legal_sorter_api_key.txt`), never in the codebase.

## 🔒 Phase 2: The Air-Gapped RAG Architecture
Once files are perfectly named and extracted into `.txt` format, the system shifts to absolute client privilege. Factual knowledge is strictly separated from behavioral training, processing all reasoning entirely offline.

* **Local Engine:** Utilizes Ollama to interface directly with the M3 MacBook Air's Metal GPU and 24GB of unified memory.
* **Reasoning Model:** Runs Google's Gemma 3 (12B parameter) model, which features a massive 128K context window for heavy document synthesis.
* **The Vector Database:** Open WebUI (`localhost:8080`) hosts the vector database, converting the extracted `.txt` files into searchable mathematical vectors using local embedding models (e.g., `nomic-embed-text`).
* **Model Knowledge (The "What"):** Confidential case facts and timelines are never used to train the model's permanent weights. They are injected temporarily into the model's short-term memory via the local RAG Knowledge Bases.

## 🤖 Phase 3: Virtual Agents & Sandboxing
To prevent the AI from cross-contaminating the facts of different matters, the system utilizes custom "Workspace Models" within Open WebUI.

* **The Base Engine:** All agents run off the same core 12B Gemma 3 model to optimize disk space on the external SSD.
* **The Ironclad System Prompt:** Each agent is locked into its sandbox via a strict system prompt isolating it to a specific litigation matter.
* **Fact Injection:** The specific RAG folder (Knowledge Base) containing only the documents for that specific case is attached directly to the agent.

## 🔄 Development Philosophy: Cloud Prototyping to Edge Deployment
To accelerate development, new drafting workflows and complex system prompts are first tested using a hybrid approach.

* **Phase 1 (Cloud):** Use Google AI Studio's massive infrastructure to prove the concept works and refine the extraction prompts. 
* **Phase 2 (Edge):** Once the prototype is flawless, the pipeline is ported down to the local, air-gapped system (VS Code + GitHub Copilot) for final execution on highly confidential matters.