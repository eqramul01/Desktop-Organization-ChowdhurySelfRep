# Law Firm AI Data Pipeline: From Chaos to RAG

## ⚖️ Mission Statement & Use Case
Law firms frequently download massive batches of disorganized public records, discovery files, and deeds from county portals (e.g., Miami-Dade, Broward). These files arrive with cryptic UUID filenames and fragmented metadata, making chronological case review and batch-printing a time-consuming manual task. 

This pipeline acts as an automated digital paralegal and data engineer. It is a hybrid architecture that uses Google's flagship multimodal APIs to chronologically sort and rename chaotic PDF dumps, and then utilizes local, air-gapped Large Language Models (LLMs) on Apple Silicon to perform deep Retrieval-Augmented Generation (RAG) for secure legal reasoning and drafting.

---

## Phase 1: The Cloud Sorting Engine (Triage & Rename)
Before local AI can query documents, the raw desktop dumps must pass through a strict, automated Python triage system to ensure chronological formatting and data hygiene.

* **Native macOS GUI:** The `gemini_master_gui.py` script uses `osascript` via Python's `subprocess` to summon native Finder popups for dynamic source and target folder selection.
* **Bleeding-Edge Vision Parsing:** Utilizes the `google-genai` Python SDK to upload multi-page PDFs directly into Gemini's context window. The model distinguishes between actual execution dates and misleading "Notary Commission Expiration" stamps to generate chronological names (`YYYY-MM-DD_Document_Type.pdf`).
* **Immutable Ledgering:** Every successful rename and classification is silently logged to a `document_catalog_gemini.csv` file for a permanent audit trail.
* **Strict Cloud Hygiene:** The script enforces a `client.files.delete()` command the millisecond the JSON is extracted, ensuring legal PDFs are wiped from Google's servers immediately.

## Phase 2: The Extraction Engine (`squeegee.py`)
Once the files are perfectly named and staged in the `Cleaned_Records` folder, the text must be liberated from the PDFs for vectorization.
* **Full-Document OCR:** The `squeegee.py` script pulls 100% of the raw text from every single page, generating lightweight, unabridged sibling `.txt` files directly alongside the original PDFs.
* **Format Normalization:** Proprietary formats or unreadable images are intercepted and converted to standard formats to ensure compatibility with Python libraries. 

## Phase 3: The Air-Gapped RAG Architecture
To maintain absolute client privilege, the system strictly separates factual knowledge from behavioral training, processing all reasoning entirely offline.
* **Local Engine:** Utilizes Ollama to interface directly with the M3 MacBook Air's Metal GPU and 24GB of unified memory.
* **Reasoning Model:** Runs Google's Gemma 3 (12B parameter) model, which features a massive 128K context window for heavy document synthesis.
* **The Vector Database:** Open WebUI (`localhost:8080`) hosts the vector database, converting the extracted `.txt` files into searchable mathematical vectors using local embedding models (e.g., `nomic-embed-text`).
* **Model Knowledge (The "What"):** Confidential case facts and timelines are never used to train the model's permanent weights. They are injected temporarily into the model's short-term memory via the local RAG Knowledge Bases.

## Phase 4: Virtual Agents & Sandboxing
To prevent the AI from cross-contaminating the facts of different matters, the system utilizes custom "Workspace Models" within Open WebUI.
* **The Base Engine:** All agents run off the same core 12B Gemma 3 model to optimize disk space on the external SSD.
* **The Ironclad System Prompt:** Each agent is locked into its sandbox via a strict system prompt isolating it to a specific litigation matter.
* **Fact Injection:** The specific RAG folder (Knowledge Base) containing only the documents for that specific case is attached directly to the agent.

## 🚀 Development Philosophy: Cloud Prototyping to Edge Deployment
To accelerate development, new drafting workflows and complex system prompts are first tested using a hybrid approach.
* **Phase 1 (Cloud):** Use Google AI Studio's massive infrastructure to prove the concept works and refine the extraction prompts. 
* **Phase 2 (Edge):** Once the prototype is flawless, the pipeline is ported down to the local, air-gapped system (VS Code + GitHub Copilot) for final execution on highly confidential matters.