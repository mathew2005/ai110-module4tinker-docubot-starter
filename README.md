# DocuBot

DocuBot is a small command-line tool that answers developer questions by searching through local documentation files. The project is designed around three modes so you can directly compare how retrieval and generation each affect answer quality.

---

## How it works

**Mode 1 — Naive LLM**  
Sends just your question to Gemini. No docs are actually passed — the model answers from its training data. Useful as a baseline to see how much the model "knows" without any grounding.

**Mode 2 — Retrieval only**  
Searches the docs folder using a word-count scoring system and returns the most relevant paragraph chunks. No LLM involved at all.

**Mode 3 — RAG (Retrieval Augmented Generation)**  
Retrieves the top matching chunks first, then passes only those to Gemini. The model is instructed to answer using only what was retrieved.

The `docs/` folder contains realistic-looking developer documentation (API reference, auth guide, database guide, setup guide). These are plain text files — no backend, no server, nothing to set up.

---

## Setup

### 1. Install dependencies

```
pip install -r requirements.txt
```

### 2. Set up your environment variables

Create a `.env` file in the project root:

```
cp .env.example .env
```

Then open `.env` and add your Gemini API key:

```
GEMINI_API_KEY=your_api_key_here
```

If you skip this, modes 1 and 3 won't work, but mode 2 (retrieval only) runs fine without it.

---

## Running DocuBot

```
python main.py
```

Pick a mode when prompted:

- `1` — Naive LLM (Gemini, no retrieval)
- `2` — Retrieval only (no LLM)
- `3` — RAG (retrieval + Gemini)

Then either press Enter to run the built-in sample queries or type your own question.

---

## Evaluating retrieval (optional)

```
python evaluation.py
```

Runs the sample queries through retrieval and prints hit rate stats. Useful for checking whether your indexing and scoring changes actually improved things.

---

## Files you'll work in

| File | What it does |
|---|---|
| `docubot.py` | Core retrieval logic — chunking, indexing, scoring, snippet selection |
| `llm_client.py` | Gemini prompts — controls how grounded or open-ended the answers are |
| `dataset.py` | Sample queries used for testing and evaluation |

---

## Requirements

- Python 3.9 or later
- A Gemini API key (only needed for modes 1 and 3)
- No database, no server, no external services beyond the LLM API calls

---

## Reflection

The two things a student most needs to take away from this project are a real understanding of what a RAG system is and a clear sense of how the three modes actually differ from each other — not just in theory but in output.

Answer quality depends on what evidence reaches the model and what guardrails decide when to refuse. Retrieval errors and generation errors can both produce a bad answer, but they need different fixes. The most useful debugging habit is tracing one query all the way through — index → score → retrieved chunks → final answer — before touching any code.

AI was genuinely helpful for understanding the problem space and comparing behavior across modes quickly. But when it came to designing how the system should work, it had to be a collaboration. The AI needed direction; it couldn't make the right calls without being guided toward them. That distinction matters: AI as a thinking partner is useful, AI as a replacement for thinking is not.

That's also the biggest risk with this assignment. It's easy for a student to hand the whole thing to AI and get something that runs without understanding why. During breakouts, the most effective check isn't asking "did you use AI" but asking them to walk through what they actually understand — and then breaking down the confusing parts through follow-up questions rather than just re-explaining it. If they can't trace a query through the system in their own words, they haven't gotten what the assignment is trying to teach.
