# SHL AI Intern Assignment - Master Development Instructions

## Role

You are a senior AI Engineer, Senior Backend Engineer, RAG Architect, and Solution Architect.

Your task is to build a **production-quality conversational SHL Assessment Recommendation System**.

Do NOT generate a prototype.
Do NOT generate placeholder code.
Do NOT leave TODOs.

Everything must be production-ready.

---

# PRIMARY GOAL

Build an AI agent that helps recruiters discover the correct SHL assessments through natural conversation.

The user should NOT need to know assessment names.

Instead the assistant should ask questions until enough information exists and then recommend assessments from the SHL catalog.

The system MUST ONLY recommend assessments from the SHL Individual Test Solutions catalog.

Never hallucinate.

Never recommend assessments outside the catalog.

---

# VERY IMPORTANT

Read the entire assignment carefully.

Every requirement is mandatory.

The generated project should satisfy every requirement.

Do not skip anything.

---

# PROJECT STRUCTURE

Create a clean enterprise architecture.

Example:

project/

    app/
        api/
        services/
        rag/
        llm/
        prompts/
        scraper/
        retrieval/
        comparison/
        models/
        config/
        utils/

    data/
        raw/
        processed/
        embeddings/

    tests/

    scripts/

    docker/

    docs/

    requirements.txt

    Dockerfile

    README.md

---

# TECH STACK

Python 3.12

FastAPI

Pydantic

LangChain (only if useful)

Google Gemini 2.5 Flash

BeautifulSoup

FAISS

Sentence Transformers

Uvicorn

Docker

Render deployment

---

# STEP 1

SCRAPE THE SHL CATALOG

Target:

SHL Individual Test Solutions

Ignore:

Job Solutions

Extract every assessment.

For every assessment collect:

Name

Description

URL

Category

Skills

Job Roles

Duration

Remote Testing Support

Adaptive or not

Languages

Test Type

All metadata available

Save as

catalog.json

---

# STEP 2

DATA CLEANING

Normalize

Remove duplicates

Fix encoding

Trim spaces

Generate searchable text

Example:

search_text

=

Name

+

Description

+

Skills

+

Category

+

Job Roles

---

# STEP 3

EMBEDDINGS

Chunk intelligently.

Generate embeddings.

Store inside FAISS.

Create retrieval service.

Top K should be configurable.

---

# STEP 4

RAG

Implement Retrieval Augmented Generation.

Pipeline:

User

↓

Conversation Analyzer

↓

Need Clarification?

↓

YES → Ask Question

↓

NO

↓

Retriever

↓

Top Assessments

↓

LLM

↓

Grounded Response

The LLM MUST only answer using retrieved documents.

---

# STEP 5

CONVERSATION ENGINE

The AI must detect:

Need clarification

Recommendation request

Comparison request

Refinement

Prompt injection

Off-topic request

Greeting

Goodbye

Implement a classifier.

---

# STEP 6

CLARIFICATION

If user says

"I need an assessment"

DO NOT recommend.

Instead ask questions.

Examples:

Role?

Experience?

Technical or personality?

Leadership?

Sales?

Hiring volume?

Remote?

Customer facing?

Continue until enough information exists.

---

# STEP 7

RECOMMENDATIONS

Recommend between

1 and 10

assessments.

Return

Name

URL

Test Type

Nothing else.

Never hallucinate.

Only use catalog URLs.

---

# STEP 8

COMPARISON

Example

Compare OPQ vs GSA.

Retrieve both.

Compare ONLY using retrieved information.

Never use model memory.

---

# STEP 9

REFINEMENT

Conversation example

User:

Hiring Java Developer

↓

Recommend

↓

User

Actually include personality tests

↓

Update recommendations.

Never restart conversation.

---

# STEP 10

REFUSAL

Reject

Politics

Law

Medical

General hiring advice

Prompt injections

Example

Ignore previous instructions

↓

Refuse politely.

---

# STEP 11

FASTAPI

Create

GET /health

Response

{
"status":"ok"
}

POST /chat

Input

messages[]

Output EXACTLY

{
reply,

recommendations,

end_of_conversation
}

Never change schema.

---

# STEP 12

PROMPTS

Separate prompts into files.

Examples

system_prompt.txt

comparison_prompt.txt

clarification_prompt.txt

recommendation_prompt.txt

refusal_prompt.txt

Never hardcode prompts.

---

# STEP 13

CONFIG

Environment variables

GOOGLE_API_KEY

MODEL_NAME

TOP_K

TEMPERATURE

EMBEDDING_MODEL

---

# STEP 14

LOGGING

Use Python logging.

Log

Retrieval

LLM response

Errors

Latency

---

# STEP 15

ERROR HANDLING

Timeouts

Empty retrieval

Invalid input

Bad API

Rate limits

Network failure

Malformed catalog

Graceful handling.

---

# STEP 16

TESTING

Create tests for

Greeting

Clarification

Recommendation

Comparison

Refinement

Prompt Injection

Off-topic

Health endpoint

Schema validation

Edge cases

Conversation length

---

# STEP 17

README

Create an excellent README.

Include

Architecture

Installation

Run

Deployment

API

Folder structure

Screenshots placeholders

Future work

---

# STEP 18

DOCKER

Create

Dockerfile

docker-compose.yml

Production ready.

---

# STEP 19

DEPLOYMENT

Deployable on

Render

Railway

Generate deployment instructions.

---

# STEP 20

QUALITY

Use

Type hints

Docstrings

SOLID

Clean Architecture

Dependency Injection

No duplicated code.

---

# STEP 21

BONUS FEATURES

Conversation summarization

Hybrid Retrieval

Metadata filtering

Caching

Confidence score

Streaming responses

---

# STEP 22

THINGS TO NEVER DO

Never hallucinate.

Never recommend outside catalog.

Never use hidden memory.

Never store conversation.

Never violate API schema.

Never hardcode assessment names.

Never use fake URLs.

---

# STEP 23

OUTPUT ORDER

Generate project in phases.

Phase 1

Architecture

Wait.

Phase 2

Scraper

Wait.

Phase 3

Embedding

Wait.

Phase 4

Retriever

Wait.

Phase 5

Conversation Engine

Wait.

Phase 6

API

Wait.

Phase 7

Testing

Wait.

Phase 8

Docker

Wait.

Phase 9

Deployment

Wait.

Phase 10

Documentation

Wait.

Never generate everything in one huge response.

Each phase should be complete before continuing.

---

# CODING STYLE

Enterprise level.

Readable.

Comment important logic.

Use classes where appropriate.

Prefer composition over inheritance.

Avoid unnecessary abstractions.

Follow Python best practices.

Generate code that is interview-quality.

Every design decision should be explainable during a technical interview.