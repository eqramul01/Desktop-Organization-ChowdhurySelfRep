# Public Gameplan: Local AI Legal Research Engine 

**Objective:** To build a fully offline, air-gapped Retrieval-Augmented Generation (RAG) system for legal reasoning, document synthesis, and drafting, leveraging local Large Language Models (LLMs) on an M3 MacBook Air (24GB RAM) with a 6TB external SSD. 

The latest text extraction script, named squeegee.py, processed the contents of the AI_Staging_Ground/Documents folder, which was comprised of dense .pdf and .docx legal and personal files. Crucially, the script utilizes full-document OCR (Optical Character Recognition) and deep text extraction to pull 100% of the raw text from every single page, generating lightweight, unabridged sibling .txt files directly alongside the originals. This structured output allows a local RAG system to efficiently ingest the complete text to construct a searchable vector database, enabling the LLM to output accurate legal reasoning while preserving the original PDFs for physical review and citation.

---

## 1. Current Progress: Infrastructure Setup
The foundational offline environment has been successfully deployed.
* **Local Engine:** Installed Ollama to interface with the Apple Silicon Metal GPU and utilize unified memory.
* **Reasoning Model:** Downloaded and loaded Google's Gemma 3 (12B parameter) model, which features multimodal vision capabilities and a massive 128K context window.
* **Local GUI:** Successfully bypassed a broken dependency by installing Open WebUI version `0.8.8` via the `uv` package manager. This provides a secure, private browser interface (running on `localhost:8080`) that never connects to the internet.

## 2. The Data Pipeline Strategy ("Sieve and Stage")
To prevent unformatted files from crashing the local embedding models, all raw desktop dumps must pass through a strict, automated Python triage system before the AI interacts with them.
* **Strict Whitelisting:** The script automatically filters out unsupported formats (like `.dmg` or `.app`) into a `Quarantine_Bin`, keeping only readable formats (`.pdf`, `.docx`, `.txt`, `.jpg`, etc.).
* **Format Normalization:** Proprietary Apple `.HEIC` images will be silently intercepted and converted to `.jpg` using macOS's native `sips` command to ensure compatibility with Python vision libraries.
* **Extraction:** Lightweight Python libraries will extract text from legal PDFs and Word documents, saving them as clean `.txt` files in a categorized `AI_Staging_Ground` directory.

## 3. The AI Architecture: Style vs. Facts
To maintain absolute client privilege while achieving highly personalized drafting, the system strictly separates factual knowledge from behavioral training.
* **Model Behavior (The "How"):** The model will be fine-tuned to learn specific legal writing styles, structures, and citation formatting exclusively using past, publicly filed (unredacted) briefs. 
* **Model Knowledge (The "What"):** Confidential case facts, timelines, and unfiled motions are never used to train the model's permanent weights. Instead, they are injected temporarily into the model's short-term memory via local RAG Knowledge Bases, ensuring an airtight, sandboxed perimeter. 

## 4. Execution Tooling: Control vs. Autonomy
A decision framework has been established for writing the necessary extraction scripts:
* **Google Antigravity (Agentic IDE):** Offers massive speed by deploying autonomous agents to write and execute terminal scripts in the background. 
* **VS Code + GitHub Copilot (Pair Programming):** Requires manual keystrokes to execute code, providing absolute, surgical safety when handling privileged desktop data dumps.

## 5. The RAG Engine (Knowledge Base Construction)
Once the raw data is cleaned and staged, it must be converted into a format the AI can instantly search. 
* **The Embedding Layer:** The system uses a specialized, secondary model running in Ollama (e.g., `nomic-embed-text`) to convert text documents into mathematical vectors.
* **The Vector Database:** Open WebUI's built-in vector database indexes the organized folders. 
* **Resource Management:** Indexing hundreds of gigabytes of text is resource-intensive and is scheduled to run overnight to manage the MacBook Air's passive cooling.

## 6. Virtual Agents (Model-Level Sandboxing)
To prevent the AI from cross-contaminating the facts of different cases, the system utilizes custom "Workspace Models".
* **The Base Engine:** All agents run off the same core 12B Gemma 3 model, eliminating the need to download redundant 6GB model files.
* **The Ironclad System Prompt:** Each agent is locked into its sandbox via a strict system prompt isolating it to a specific litigation matter.
* **Fact Injection:** The specific RAG folder (Knowledge Base) containing only the documents for that specific case is attached directly to the agent.

## 7. Ad-Hoc Analysis (The "Multi-File Pass")
For immediate, single-issue analysis that does not require building a permanent Knowledge Base, the system leverages Gemma 3's massive 128K context window.
* **Execution:** Multiple PDFs/Docs are dragged directly into the Open WebUI chat. The interface extracts the text and injects it directly into Gemma's short-term memory.
* **Optimal Use Case:** A handful of files (3 to 10 PDFs) is perfect for the chat box. Massive batches (50+ PDFs) require the formal Knowledge Base method.

## 8. Cloud Prototyping to Edge Deployment
To accelerate development, new drafting workflows and complex system prompts are first tested using "Cloud Prototyping before Edge Deployment".
* **Phase 1 (Cloud):** Use Google AI Studio's massive infrastructure to prove the concept works and refine datasets. 
* **Phase 2 (Edge):** Once the prototype is flawless, the pipeline is ported down to the local, air-gapped system for final execution on highly confidential matters.