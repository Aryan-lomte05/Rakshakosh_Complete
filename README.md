# RakshaKosh

**An air-gapped document question answering system that refuses to answer when it has nothing to answer from.**

[![Python](https://img.shields.io/badge/python-FastAPI-8B7CF6?style=flat-square)](#running-it)
[![Offline](https://img.shields.io/badge/mode-air--gapped,%20local%20Ollama-4BC8C0?style=flat-square)](#air-gapped-by-design)
[![Crypto](https://img.shields.io/badge/at%20rest-AES--GCM%20·%20PBKDF2-15181D?style=flat-square)](#documents-encrypted-at-rest)
[![Grounding](https://img.shields.io/badge/abstention-enforced-ef4444?style=flat-square)](#the-two-guards)

Most retrieval augmented generation systems will answer anything. Ask about a topic absent from the corpus and
a confident, fluent, unsupported answer comes back, because nothing in the pipeline is responsible for saying
"I do not know".

RakshaKosh treats abstention as a first class behaviour, enforced by code rather than requested in a prompt,
and runs entirely offline so that confidential documents never leave the machine.

## The two guards

Two small classes carry most of the trustworthiness of the system.

**`RefusalGuard`** decides whether to answer at all, before generation:

```python
def should_refuse(self, intent, retrieved_chunks) -> bool:
    if intent == "out_of_scope":
        return True
    if not retrieved_chunks or len(retrieved_chunks) == 0:
        return True
    return False
```

No retrieved chunks means no answer. Not a hedged answer, not a general one. The user is told to upload
relevant material or ask a document grounded question.

**`CitationEnforcer`** checks the answer after generation and rejects it if it carries no citations. An answer
without a source is treated as a failure, not as output.

Together they close the two ends: the model is not invited to speak without evidence, and what it produces is
not accepted without attribution.

## The retrieval pipeline

More than a single embedding lookup:

| Stage | Module | Purpose |
|---|---|---|
| Intent classification | `ai_model/agent/intent_classifier.py` | Route the question, and detect out of scope early |
| Query decomposition | `ai_model/rag/query_decomposer.py` | Break a multi part question into retrievable sub questions |
| Retrieval | `retrieval/retrieval_pipeline.py` | Vector search over the indexed corpus (Qdrant) |
| Reranking | `ai_model/rag/llm_reranker.py` | Reorder candidates by actual relevance, not just embedding distance |
| Context assembly | `ai_model/rag/context_builder.py` | Build the prompt context under a budget |
| Semantic cache | `retrieval/semantic_cache.py` | Reuse answers for questions that mean the same thing |
| Follow up resolution | `ai_model/conversation/followup_resolver.py` | Resolve "and what about the second one?" against conversation state |

Conversation state and memory are handled separately (`conversation/conversation_state.py`,
`memory_manager.py`), so a follow up question is rewritten into a standalone query before it reaches retrieval,
which is where most conversational RAG systems quietly break.

Typed boundaries throughout: `schemas/agent_io.py` and `schemas/citation.py` define what crosses between
stages.

## Air gapped by design

`config/config.json` sets `"mode": "air-gapped-local"`, with the backend bound to `127.0.0.1`. Generation runs
through a local **Ollama** client (`ai_model/llm/ollama_client.py`). There is no hosted provider in the path,
which is the whole point: the documents this is built for are ones that cannot be sent to an API.

## Documents encrypted at rest

| Module | Purpose |
|---|---|
| `security/aes_gcm.py` | Authenticated encryption, so tampering is detected and not just decrypted into nonsense |
| `security/key_derivation.py` | PBKDF2-HMAC-SHA256 key derivation from a passphrase |
| `security/document_crypto.py` | Per document encryption and decryption |
| `security/password_vault.py` | Encrypted credential vault |
| `ingestion/secure_ingestor.py` | Ingestion path that encrypts as it indexes |

Each of these has a test in `test_scripts/` (`test_aes_gcm.py`, `test_key_derivation.py`,
`test_document_crypto.py`, `test_password_vault.py`), which is the right place to spend test effort in a system
like this.

Ingestion uses **Docling** (`ingestion/docling_processor.py`) for structured extraction from PDFs, with a
faster path in `fast_ingestion.py`.

## Repository map

| Path | Contents |
|---|---|
| `backend/ai_model/agent/` | Controller, intent classifier, refusal guard |
| `backend/ai_model/rag/` | Decomposition, reranking, context building, citation enforcement |
| `backend/ai_model/conversation/` | Conversation state, memory, follow up resolution |
| `backend/retrieval/` | Retrieval pipeline, interactive retriever, semantic cache |
| `backend/security/` | AES-GCM, key derivation, document crypto, password vault |
| `backend/ingestion/` | Docling processing, fast and secure ingestion, text extraction |
| `backend/api/` | FastAPI app, agent, ingestion and analytics endpoints |
| `test_scripts/` | Crypto and extraction tests |

## Running it

```bash
pip install -r requirements.txt
# start Ollama locally and pull the model named in the config
./run_rakshakosh.sh        # or run_rakshakosh.bat on Windows
```

Qdrant is expected locally; `debug_qdrant.py` checks the connection.

---

## Status and honest limits

- **Phase 1.** `config.json` says so. The guards, crypto and pipeline work; this is not a finished product.
- **The guards are coarse.** `CitationEnforcer` checks that citations exist and that the answer is longer than
  20 characters. It does not verify that each claim in the answer is actually supported by the cited chunk,
  which is the harder and more valuable check.
- **No retrieval quality measurement.** No recall at k, no answer faithfulness score, no abstention precision.
  For a system whose main claim is grounded refusal, measuring how often it refuses when it should and answers
  when it should is the obvious missing evidence.
- **PBKDF2 at 100,000 iterations** is below current guidance for PBKDF2-HMAC-SHA256, and the repository ships
  an example encrypted vault alongside its salt. Both are fine for a demo and both should change before real
  use: raise the iteration count substantially, or move to scrypt or Argon2id, and keep vaults out of version
  control.
- **Example documents are committed** in `backend/test_docs/` and `backend/temp_ingest/`, including an
  encrypted PDF. Test corpora belong outside the repository.

Built for the RakshaKosh project. The name means "protection treasury".
