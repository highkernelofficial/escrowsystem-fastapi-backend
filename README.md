# FRESCROW — FastAPI AI & Algorand Smart Contract Engine ⚡🤖

[![Python 3.13+](https://img.shields.io/badge/Python-3.13%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Algorand](https://img.shields.io/badge/Algorand-PyTeal_%26_SDK-000000?style=for-the-badge&logo=algorand&logoColor=white)](https://www.algorand.com/)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-3_Flash-4285F4?style=for-the-badge&logo=googlegemini&logoColor=white)](https://ai.google.dev/)
[![LangChain](https://img.shields.io/badge/LangChain-LangGraph_%26_MCP-121212?style=for-the-badge&logo=chainlink&logoColor=white)](https://www.langchain.com/)
[![uv](https://img.shields.io/badge/managed_by-uv-DE5D43?style=for-the-badge&logo=python&logoColor=white)](https://github.com/astral-sh/uv)

The **FRESCROW FastAPI Backend** is the high-performance AI and Blockchain microservice powering the **FRESCROW Milestone Escrow Platform**. Built with FastAPI, PyTeal, Algorand SDK, Google Gemini 3 Flash, and LangChain MCP (Model Context Protocol) integration, it is responsible for:

1. **PyTeal Smart Contract Compilation & Transaction Management**: Dynamically compiling stateful PyTeal smart contracts and building unsigned Algorand transaction bytes for deployment, funding, and milestone release.
2. **AI Milestone Generation**: Automatically analyzing project title, description, tech stack, and budget to generate structured milestone breakdowns (3-5 milestones totaling 100% budget).
3. **AI Deliverable Evaluation (MCP Agent)**: Interacting with GitHub repositories via Model Context Protocol (MCP) and LLM reasoning to evaluate code deliverables, verify framework usage, assign quality scores (0-100), and auto-recommend approval or feedback.

---

## 🏛️ System Architecture

```
                                +---------------------------+
                                |  Spring Boot Main Backend |
                                +-------------+-------------+
                                              |
                         HTTP REST Requests   |
                                              v
+-----------------------------------------------------------------------------------+
|                            FastAPI Microservice Engine                            |
|                                                                                   |
|  +--------------------------------+         +----------------------------------+  |
|  |     AI Engine (LangChain)      |         |   Blockchain Engine (Algorand)   |  |
|  |                                |         |                                  |  |
|  | - Google Gemini 3 Flash        |         | - PyTeal Smart Contract Compiler |  |
|  | - Milestone Auto-Breakdown     |         | - Contract Deployment Txn Builder|  |
|  | - MCP GitHub Repo Evaluator    |         | - Escrow Funding Group Builder   |  |
|  | - Structured JSON Parsers      |         | - Single-call Release Txn Builder|  |
|  +---------------+----------------+         +----------------+-----------------+  |
+------------------|-------------------------------------------|--------------------+
                   |                                           |
                   v                                           v
         +-------------------+                       +-------------------+
         | GitHub MCP Server |                       | Algorand Testnet  |
         +-------------------+                       +-------------------+
```

---

## 📦 Key Capabilities

### 1. 📜 Smart Contract Engine (PyTeal & Algorand)
- **Dynamic PyTeal Approval Program**: Compiles an Algorand stateful application supporting four key operations:
  - `on_create`: Initializes global storage with `creator` address.
  - `fund`: Registers milestone details (`milestone_id -> amount`) and updates state to `SUBMITTED` (`status = 2`).
  - `approve`: Updates milestone state to `APPROVED` (`status = 3`).
  - `approve_and_release`: Single atomic call that verifies `status == 2`, sets `status = 3`, and triggers an **Inner Payment Transaction** transferring microAlgos directly to the freelancer's wallet.
- **Fee Pooling**: Inner payment fees are covered by the transaction caller (`fee=0` on inner txn), ensuring seamless execution.
- **Transaction Grouping**: Constructs msgpack-encoded transaction bytes returned to the client/frontend for Pera Wallet signing.

### 2. 🤖 AI Agent Engine (LangChain & Gemini 3 Flash)
- **Milestone Decomposition**: Accepts project specifications and returns a normalized JSON array of milestones ensuring 100% total allocation.
- **GitHub Code Review via MCP**: Leverages Model Context Protocol (`MultiServerMCPClient`) with GitHub API integration to inspect submitted code repositories, examine `README.md`, verify tech stack implementation, and determine whether the submission meets project acceptance criteria.

---

## 🛠️ Project Structure

```
escrowsystem-fastapi-backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── api_router.py       # Main API Router aggregator
│   │       ├── ai.py               # AI Milestone & Evaluation Endpoints
│   │       └── blockchain.py       # Algorand Txn & Contract Endpoints
│   ├── contracts/
│   ├── compile_contract.py # PyTeal compilation script
│   │   └── escrow_contract.py  # PyTeal approval & clear state programs
│   ├── schemas/
│   │   ├── ai_schema.py        # Pydantic schemas for AI requests/responses
│   │   └── blockchain_schema.py# Pydantic schemas for Blockchain requests/responses
│   └── services/
│       ├── ai_service.py       # Gemini + LangChain + MCP execution logic
│       └── blockchain_service.py# Algorand SDK transaction builders & indexer queries
├── main.py                         # FastAPI App initialization & CORS config
├── pyproject.toml                  # Python dependencies managed via uv
├── uv.lock                         # Lockfile for deterministic builds
└── README.md
```

---

## 🚀 API Endpoint Reference

### 🤖 AI Endpoints (`/api/v1/ai`)

#### 1. Generate Milestones
- **POST** `/api/v1/ai/generate-milestones`
- **Request Body**:
  ```json
  {
    "title": "Decentralized Escrow DApp",
    "description": "Build an escrow platform on Algorand",
    "tech_stack": "Next.js, Python, PyTeal, Java",
    "expected_outcome": "Working escrow dApp with wallet integration",
    "total_budget": 500.0
  }
  ```
- **Response**:
  ```json
  {
    "milestones": [
      {
        "title": "Smart Contract Architecture",
        "description": "Develop and test PyTeal escrow contract",
        "percentage": 30,
        "amount": 150.0
      },
      {
        "title": "Frontend Integration",
        "description": "Pera Wallet integration & UI components",
        "percentage": 50,
        "amount": 250.0
      },
      {
        "title": "Testing & Deployment",
        "description": "Testnet validation and mainnet readiness",
        "percentage": 20,
        "amount": 100.0
      }
    ]
  }
  ```

#### 2. Evaluate Deliverable Submission
- **POST** `/api/v1/ai/evaluate`
- **Request Body**:
  ```json
  {
    "milestone_id": "M1",
    "submission": "https://github.com/user/escrow-frontend"
  }
  ```
- **Response**:
  ```json
  {
    "score": 92,
    "approved": true,
    "feedback": "Repository contains complete Next.js setup with active Pera Wallet connection and smart contract call utilities."
  }
  ```

---

### ⛓️ Blockchain Endpoints (`/api/v1/blockchain`)

#### 1. Build Contract Deployment Transaction
- **POST** `/api/v1/blockchain/deploy-contract`
- **Request Body**:
  ```json
  {
    "sender": "ALGORAND_WALLET_ADDRESS_HERE"
  }
  ```
- **Response**:
  ```json
  {
    "txn": "<base64_msgpack_encoded_transaction>"
  }
  ```

#### 2. Resolve App ID from Transaction Hash
- **POST** `/api/v1/blockchain/get-app-id`
- **Request Body**:
  ```json
  {
    "txn_id": "TRANSACTION_HASH_STRING"
  }
  ```
- **Response**:
  ```json
  {
    "app_id": 732910482
  }
  ```

#### 3. Build Project Funding Transaction Group
- **POST** `/api/v1/blockchain/fund-project`
- **Request Body**:
  ```json
  {
    "sender": "CLIENT_ALGORAND_ADDRESS",
    "app_id": 732910482,
    "total_amount": 500.0,
    "milestones": [
      { "milestone_id": "m_1", "amount": 150.0 },
      { "milestone_id": "m_2", "amount": 250.0 },
      { "milestone_id": "m_3", "amount": 100.0 }
    ]
  }
  ```
- **Response**:
  ```json
  {
    "txns": [
      "<base64_encoded_payment_txn>",
      "<base64_encoded_app_call_m1>",
      "<base64_encoded_app_call_m2>",
      "<base64_encoded_app_call_m3>"
    ]
  }
  ```

#### 4. Build Milestone Release Transaction
- **POST** `/api/v1/blockchain/release-milestone`
- **Request Body**:
  ```json
  {
    "sender": "CLIENT_ALGORAND_ADDRESS",
    "app_id": 732910482,
    "milestone_id": "m_1",
    "freelancer_address": "FREELANCER_ALGORAND_ADDRESS"
  }
  ```
- **Response**:
  ```json
  {
    "txn": "<base64_encoded_approve_and_release_app_call>"
  }
  ```

---

## 💻 Prerequisites & Setup

### Prerequisites
- **Python**: `>= 3.13`
- **uv**: Fast Python package installer and resolver (`pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **Algorand Testnet Access**: Algonode API endpoint (default: `https://testnet-api.algonode.cloud`)

### Environment Configuration (`.env`)
Create a `.env` file in the root directory of this backend:

```env
# Google Gemini API Key for AI Milestone Generation & Evaluation
GOOGLE_API_KEY=your_google_gemini_api_key_here

# GitHub Personal Access Token for MCP GitHub Tool Execution
GITHUB_PAT=your_github_personal_access_token_here
```

---

## 🏃 Local Execution Guide

### Using `uv` (Recommended)

1. **Install Dependencies**:
   ```bash
   uv sync
   ```

2. **Run the Development Server**:
   ```bash
   uv run main.py
   ```
   Or via `uvicorn`:
   ```bash
   uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. **Verify Health & Documentation**:
   - Health Check: `http://localhost:8000/health`
   - Interactive OpenAPI Docs: `http://localhost:8000/docs`
   - Redoc API Specs: `http://localhost:8000/redoc`

---

## 🐳 Deployment Guide (Render / Cloud Platforms)

- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port 8000`
- **Python Version**: `3.13`
- Ensure `GOOGLE_API_KEY` and `GITHUB_PAT` environment variables are populated in your deployment dashboard.
