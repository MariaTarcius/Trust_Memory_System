# 🧠 Trust-Aware Memory Intelligence System

## 📌 Overview

The Trust-Aware Memory Intelligence System (TAMIS) is a multi-agent AI framework designed to manage evolving information streams and maintain a trustworthy memory over time.

Unlike traditional chatbots or Retrieval-Augmented Generation (RAG) systems that focus primarily on answering questions, TAMIS focuses on **memory evolution**. The system continuously analyzes incoming information and decides:

- What to remember
- What to update
- What to reject
- What to merge
- What to downgrade
- What to forget

Every memory entry maintains:

- Confidence Score
- Timestamp
- Source Information
- Current Status
- Provenance History
- Change Log

The primary objective is to answer:

> **"Why do I believe this fact right now, and how has that belief changed over time?"**

---

# 🎯 Problem Statement

Modern AI systems can generate responses and retrieve information, but they often struggle with maintaining a reliable memory that evolves over time.

Real-world information is:

- Noisy
- Contradictory
- Incomplete
- Continuously changing

Traditional systems frequently overwrite information without preserving reasoning, provenance, or historical context.

This project addresses the challenge of building a memory intelligence system that continuously evaluates incoming claims and updates its beliefs in a transparent and explainable manner.

---

# 🏗️ System Architecture

```text
                         Incoming Claim
                                │
                                ▼
 ┌──────────────────────────────────────────────────┐
 │             Claim Extraction Agent               │
 └──────────────────────┬───────────────────────────┘
                        ▼
 ┌──────────────────────────────────────────────────┐
 │               Verification Agent                 │
 └──────────────────────┬───────────────────────────┘
                        ▼
 ┌──────────────────────────────────────────────────┐
 │               Embedding Service                  │
 └──────────────────────┬───────────────────────────┘
                        ▼
 ┌──────────────────────────────────────────────────┐
 │              ChromaDB Vector Store               │
 └──────────────────────┬───────────────────────────┘
                        ▼
 ┌──────────────────────────────────────────────────┐
 │             Contradiction Agent                  │
 └──────────────────────┬───────────────────────────┘
                        ▼
 ┌──────────────────────────────────────────────────┐
 │               Memory Curator Agent               │
 └──────────────────────┬───────────────────────────┘
                        ▼
           ┌────────────────────────────┐
           │      JSON Memory Store     │
           └────────────┬───────────────┘
                        ▼
           ┌────────────────────────────┐
           │         Change Log         │
           └────────────┬───────────────┘
                        ▼
           ┌────────────────────────────┐
           │      Explainability        │
           └────────────────────────────┘
```

---

# 📂 Project Structure

```text
trust_memory_system/

├── app.py
│
├── data/
│   └── claims_stream.json
│
├── database/
│   ├── sqlite.db
│   └── init_db.py
│
├── agents/
│   ├── extraction_agent.py
│   ├── verification_agent.py
│   ├── contradiction_agent.py
│   └── curator_agent.py
│
├── embeddings/
│   └── embedding_service.py
│
├── vectorstore/
│   └── chroma_store.py
│
├── graph/
│   └── workflow.py
│
├── memory/
│   ├── memory_store.py
│   └── change_log.py
│
├── utils/
│   └── confidence.py
│
└── requirements.txt
```

---

# 🛠️ Technology Stack

## 🐍 Python

### Purpose

Python serves as the primary programming language for the system.

### Responsibilities

- Agent implementation
- Workflow orchestration
- Memory management
- Data processing
- Backend development

### Why Python?

- Extensive AI ecosystem
- Rich library support
- Easy integration with LLM frameworks

---

## 🔄 LangGraph

### Purpose

LangGraph orchestrates the multi-agent workflow.

### Responsibilities

Manages execution flow between:

```text
Claim Extraction
      ↓
Verification
      ↓
Contradiction Detection
      ↓
Memory Curation
```

### Why LangGraph?

- Stateful execution
- Agent coordination
- Workflow control
- Memory-aware pipelines

---

## 🔗 LangChain

### Purpose

Provides tools for interacting with Large Language Models.

### Responsibilities

- Prompt management
- Structured outputs
- LLM integration
- Embedding pipelines

### Why LangChain?

- Simplifies LLM development
- Supports multiple model providers
- Integrates easily with vector databases

---

## 🤖 Large Language Model (LLM)

### Recommended Models

- :contentReference[oaicite:0]{index=0}
- :contentReference[oaicite:1]{index=1}
- :contentReference[oaicite:2]{index=2}

### Purpose

Acts as the reasoning engine of the system.

### Used In

#### Claim Extraction Agent

Extracts structured claims from natural language.

#### Verification Agent

Evaluates claim validity.

#### Contradiction Agent

Analyzes conflicting information.

#### Memory Curator Agent

Determines memory actions:

- Accept
- Update
- Merge
- Reject
- Forget

---

## 🔍 Embedding Model

### Recommended Model

:contentReference[oaicite:3]{index=3}

### Purpose

Converts claims into vector representations.

### Example

Claim A:

```text
Startup A secured $5M funding
```

Claim B:

```text
Startup A raised five million dollars
```

Both claims have similar semantic meaning despite different wording.

### Benefits

- Semantic similarity detection
- Duplicate detection
- Related claim retrieval

---

## 📦 ChromaDB

### Purpose

Stores and retrieves embeddings.

### Responsibilities

- Semantic search
- Similarity retrieval
- Duplicate detection
- Contradiction support

### Why ChromaDB?

- Lightweight
- Fast retrieval
- Open-source
- Easy integration

---

## 📄 JSON Memory Store

### Purpose

Stores the current belief state.

### Example

```json
{
  "entity": "Startup A",
  "belief": "$8M",
  "confidence": 0.89,
  "status": "accepted"
}
```

### Stores

- Current belief
- Confidence score
- Timestamp
- Status
- Provenance

### Why JSON?

- Human-readable
- Easy debugging
- Lightweight persistence

---

## 📝 Change Log

### Purpose

Maintains the history of memory evolution.

### Example

```json
{
  "old_value": "$5M",
  "new_value": "$8M",
  "action": "UPDATE",
  "reason": "Conflict Resolution"
}
```

### Benefits

- Explainability
- Provenance tracking
- Auditing

---

## 🗄️ SQLite

### Purpose

Stores structured metadata.

### Stores

- Agent outputs
- Evaluation metrics
- System statistics
- Application logs

### Why SQLite?

- Lightweight
- No external server required
- Easy deployment

---

## 🎨 Streamlit

### Purpose

Provides the user interface.

### Features

- Submit claims
- View memory
- Explain beliefs
- Inspect history
- Monitor confidence scores

### Why Streamlit?

- Fast UI development
- Interactive dashboards
- Python-native

---

# 🤖 Multi-Agent Architecture

---

## 1️⃣ Claim Extraction Agent

### Purpose

Converts raw text into structured claims.

### Input

```text
Startup A raised $5M in 2021
```

### Output

```json
{
  "entity": "Startup A",
  "event": "funding",
  "amount": "5M",
  "year": "2021"
}
```

### Responsibilities

- Entity extraction
- Event extraction
- Value extraction
- Timestamp extraction

---

## 2️⃣ Verification Agent

### Purpose

Validates claim quality and reliability.

### Responsibilities

- Schema validation
- Plausibility checks
- Confidence assignment
- Reliability assessment

### Example Output

```json
{
  "valid": true,
  "confidence": 0.85
}
```

---

## 3️⃣ Contradiction Agent

### Purpose

Detects conflicts between incoming claims and stored memory.

### Example

Existing Memory:

```text
Startup A raised $5M in 2021
```

Incoming Claim:

```text
Startup A raised $8M in 2021
```

Output:

```json
{
  "conflict": true,
  "type": "value_conflict"
}
```

---

## 4️⃣ Memory Curator Agent

### Purpose

Maintains and evolves memory.

### Possible Actions

- ACCEPT
- UPDATE
- MERGE
- REJECT
- DOWNGRADE
- FORGET

### Responsibilities

- Update memory
- Adjust confidence
- Record history
- Maintain provenance

---

# 🔄 Complete Workflow

```text
Incoming Claim
      │
      ▼
Claim Extraction Agent
      │
      ▼
Verification Agent
      │
      ▼
Embedding Generation
      │
      ▼
ChromaDB Retrieval
      │
      ▼
Contradiction Agent
      │
      ▼
Memory Curator Agent
      │
      ▼
JSON Memory Update
      │
      ▼
Change Log Update
      │
      ▼
Explainability Output
```

---

# 🧠 Memory Evolution Example

### T1

```text
Startup A raised $5M in 2021
```

Memory:

```json
{
  "belief": "$5M",
  "confidence": 0.70
}
```

---

### T2

```text
Startup A raised $8M in 2021
```

Contradiction detected.

Memory updated:

```json
{
  "belief": "$8M",
  "confidence": 0.87,
  "status": "updated"
}
```

Change logged:

```json
{
  "old": "$5M",
  "new": "$8M",
  "reason": "conflict resolution"
}
```

---

# ⚠️ Edge Cases Handled

## Duplicate Claims

Prevents confidence inflation from repeated information.

---

## Missing Timestamps

Uses confidence-based reasoning when timestamps are unavailable.

---

## Contradictory Information

Triggers contradiction detection and belief revision.

---

## Equal Confidence Conflicts

Uses provenance and evidence strength for resolution.

---

## Memory Overflow

Supports memory pruning and compression strategies.

---

# 📊 Evaluation Metrics

The system evaluates memory quality using:

### Belief Accuracy

Measures correctness of final stored beliefs.

### Contradiction Detection Rate

Measures conflict identification performance.

### Confidence Calibration

Measures alignment between confidence and correctness.

### Memory Stability

Measures consistency of beliefs over time.

### Explainability Quality

Measures reasoning quality and transparency.

---

# 🚀 Installation

## Clone Repository

```bash
git clone <repository-url>
cd trust_memory_system
```

## Create Virtual Environment

```bash
python -m venv .venv
```

## Activate Environment

### Windows

```bash
.venv\Scripts\activate
```

### Linux / Mac

```bash
source .venv/bin/activate
```

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

# ▶️ Run Application

```bash
streamlit run app.py
```

---

# 🌟 Key Features

- Multi-Agent Architecture
- Trust-Aware Memory Management
- Semantic Retrieval using Embeddings
- ChromaDB Vector Search
- Memory Evolution Tracking
- Confidence Scoring
- Provenance Management
- Contradiction Detection
- Explainable AI
- Change Log Tracking

---

# 🔮 Future Improvements

- Knowledge Graph Integration
- Neo4j Support
- Memory Compression Algorithms
- Real-Time Streaming Claims
- Advanced Provenance Visualization
- Automated Evaluation Dashboard

---

# 👥 Team

Trust-Aware Memory Intelligence System

Built for the GenAI Hackathon.

---

## 📜 License

This project is intended for research, educational purposes, and hackathon participation.
