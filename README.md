# ⚖️ Legal AI Swarm OS (Unified Pipeline)

## Mission Statement
Law firms and Pro Se litigants frequently download massive batches of disorganized public records, discovery files, and court dockets. These files arrive with cryptic UUID filenames and fragmented metadata, making chronological case review impossible. 

The **Legal AI Swarm OS** is a hybrid multi-threaded application built for macOS Apple Silicon. It acts as an automated digital data engineer. It deploys a swarm of simultaneous bots to ingest chaotic document dumps, execute OCR, extract chronological metadata via cloud LLMs, and then perform offline semantic routing and cryptographic deduplication to build pristine, air-gapped Retrieval-Augmented Generation (RAG) databases.

---

## 🚀 Core Pipeline Capabilities

The Swarm OS features a unified CustomTkinter GUI that routes operations through 4 distinct phases:

### Phase 1: AI OCR & Chronological Renaming (Cloud API)
* **Dual-Engine Extraction:** Utilizes the `google-genai` SDK (`gemini-2.5-flash`) to perform two tasks simultaneously:
  1. **Chronological Metadata:** Extracts Execution Dates and Document Types to rename files to a strict `YYYY-MM-DD_Document_Type.ext` format.
  2. **Full-Document OCR:** Extracts 100% of the raw text and generates a sibling `.txt` file for lightweight vectorization.
* **Format Agnostic:** Natively intercepts proprietary formats (Apple `.HEIC` photos, multi-page `.TIFFs`) and silently converts them to PDFs in the background for flawless AI ingestion.
* **Strict Cloud Hygiene:** Enforces a `client.files.delete()` command the millisecond data is extracted, ensuring confidential legal documents are wiped from Google's servers instantly.

### Phase 2A: RAG Context Classifier (Cloud API)
* **Semantic Routing:** Rather than relying on simple keywords, this phase reads the lightweight `.txt` files and asks Gemini to intelligently classify the document's context (e.g., `Medical`, `Legal_Pleadings`, `Corporate`, `Financial`).
* **Cost Efficiency:** By only sending the first 10,000 characters of the extracted `.txt` file instead of re-uploading massive PDFs, this phase categorizes thousands of documents for fractions of a cent. It moves both the `.txt` and the sibling media file into specific Knowledge Base subfolders.

### Phase 2B: Offline Medical Sieve (100% Local)
* **Fast Keyword Sieve:** An entirely offline process that scans the `.txt` files for specific family names, conditions (e.g., "synovial cyst"), and medical terminology. 
* **Privacy First:** Instantly segregates highly sensitive medical records into a quarantined folder without ever connecting to the internet.

### Phase 3: Cryptographic Deduplication (100% Local)
* **SHA-256 Hashing:** Uses local mathematical algorithms to read the exact binary fingerprint of every file in the directory. 
* **RAG Hygiene:** If it finds an exact byte-for-byte duplicate (even if the filenames are completely different), it quarantines the duplicate media file *and* its sibling `.txt` file into a `Duplicates_Bin` to prevent poisoning the downstream RAG vector database. 

---

## ⚙️ Technical Architecture & Features

* **Multi-Threaded Swarm:** Utilizes Python's `concurrent.futures.ThreadPoolExecutor` strictly capped at 8 concurrent bots to maximize processing speed while respecting Google API rate limits.
* **Thread-Safe Locks:** Implements `threading.Lock()` to prevent file-move collisions and CSV write-crashes when multiple bots access the same directories simultaneously.
* **Ghost Correction Regex:** A built-in sanitization engine that strips conversational AI filler (e.g., *"Here is the extracted text:"*) and stray markdown formatting from the OCR output.
* **Immutable Ledgering:** Every action (renames, categorizations, and deduplications) is permanently logged to local CSV files (`document_catalog_gemini.csv` and `duplicate_log.csv`) for forensic auditing.

## 🛠 Usage
1. Ensure your Google API Key is pasted into the GUI (it will securely save to `~/.legal_sorter_api_key.txt`).
2. Select your Master Source folder.
3. Select your Target folder (or select the same folder for in-place deduplication/routing).
4. Select the desired Pipeline Phase and click **Run Swarm Engine**.