# DocuBot Model Card

---

## 1. System Overview

**What is DocuBot trying to do?**

DocuBot takes local documentation files and uses them to answer developer questions. The goal is to speed up the process of looking through docs by having the system do it rather than a human reading through everything manually.

**What inputs does DocuBot take?**

Markdown files in the `docs/` folder and a plain one-sentence question from the user. In LLM modes it also needs a `GEMINI_API_KEY` environment variable.

**What outputs does DocuBot produce?**

An answer formed from information retrieved from the given documents. If no relevant information is found, it says so explicitly.

---

## 2. Retrieval Design

**How does your retrieval system work?**

- **Indexing:** Each document is split into sections using its markdown headers (`#`, `##`). Every unique word in each section gets mapped to the list of files that contain it — that's the inverted index.
- **Scoring:** For each query, the system counts how many times meaningful query words (4+ characters) appear in a section. Higher counts mean stronger relevance.
- **Selection:** The index narrows down to candidate files first, then every section from those files gets scored. Anything below the minimum score threshold gets dropped. The rest are sorted and the top results are returned.

**What tradeoffs did you make?**

Simplicity over accuracy. Using word counts and header-based chunking is fast and readable, but it has no understanding of meaning — it just matches vocabulary. That's enough for structured docs like these, but it would break down on more complex or freeform writing.

---

## 3. Use of the LLM (Gemini)

**When does DocuBot call the LLM and when does it not?**

- **Naive LLM mode:** Always calls the LLM, but without any docs — just the raw question. The model answers from its training data, not from the actual documentation.
- **Retrieval only mode:** Never calls the LLM. Returns the raw matching sections directly, labeled with their source filenames.
- **RAG mode:** Retrieves the top sections first, then sends only those to the LLM to generate a grounded natural language answer.

**What instructions do you give the LLM to keep it grounded?**

The LLM is told to answer using only the provided snippets and not to invent functions, endpoints, or config values. If the snippets don't have enough to go on, it must reply exactly: "I do not know based on the docs I have." It's also asked to mention which files it pulled from.

---

## 4. Experiments and Comparisons

Same queries run in all three modes with identical wording.

| Query | Naive LLM | Retrieval only | RAG | Notes |
|---|---|---|---|---|
| Where is the auth token generated? | **Harmful** — described generic OAuth/JWT flows, never mentioned `generate_access_token` or `auth_utils.py` | **Helpful** — returned the exact AUTH.md section naming the function and module | **Helpful** — one clean sentence with the function name and source file | RAG gives the same accuracy as retrieval but as a readable answer |
| How do I connect to the database? | **Harmful** — gave full code examples in Python, Node, Java, and MongoDB, none relevant here | **Helpful** — top result was the `DATABASE_URL` section with SQLite and PostgreSQL examples | **Helpful** — two sentences: set `DATABASE_URL`, connections handled by `db.py` | Biggest gap between naive and the other two modes |
| Which endpoint lists all users? | **Harmful** — guessed `GET /users` (wrong prefix) with made-up fields like `username` and `firstName` | **Helpful** — returned the correct `GET /api/users` section with admin-only note | **Helpful** — correct path, admin restriction, cites API_REFERENCE.md | Naive got the shape right but every specific detail was wrong |
| How does a client refresh an access token? | **Weakly helpful** — described full OAuth2 refresh token flow, more complex than this app | **Helpful** — returned the `POST /api/refresh` section with the required header format | **Helpful** — concise answer citing both AUTH.md and API_REFERENCE.md | Naive described a different auth system entirely |

**What patterns did you notice?**

Naive LLM generates fluent, confident-sounding answers but often invents plausible details that aren't in the actual docs — making it look helpful while being unreliable. Retrieval only is better when you need the exact source text, like a config value or a specific field name, without any interpretation layered on top. RAG is clearly better when the answer involves combining a few pieces of information or when the user needs a direct statement rather than a wall of raw documentation.

---

## 5. Failure Cases and Guardrails

**Failure case 1**

- Question: "What's 2 + 2?"
- What happened: The guardrail didn't trigger because the character "2" appears in the docs (in JSON examples, table values, etc.), so the system returned irrelevant sections instead of refusing.
- What should have happened: It should have recognized that no meaningful content words matched and returned "I do not know based on these docs."

**Failure case 2**

- Question: "What does the /api/projects/\<project_id\> route return?"
- What happened: The retrieval system ranked `DATABASE.md ## Query Helpers` above `API_REFERENCE.md ## Project Data Endpoints` because the word "projects" appears more in the db helpers section. The answer was technically in the second chunk, not the first.
- What should have happened: The API reference section should have ranked first since it directly answers the question about the route's response format.

**When should DocuBot say "I do not know"?**

When the query is about something not covered in the docs at all, and when the retrieved sections score below the minimum threshold — meaning the match was too weak to be useful.

**What guardrails are implemented?**

- Minimum score threshold: chunks scoring below `MIN_SCORE = 2` are dropped
- Word length filter: words under 4 characters are excluded from scoring (filters out "is", "the", "a", etc.)
- Top-k limit: at most 3 chunks returned by default
- Explicit refusal message: when `retrieve` returns empty, the answer is always "I do not know based on these docs."

---

## 6. Limitations and Future Improvements

**Current limitations**

1. No semantic understanding — "auth token" and "access token" score differently even though they mean the same thing
2. Header-based chunking is structure-dependent — docs without consistent headers would produce poor chunks
3. Fixed scoring threshold — `MIN_SCORE = 2` works for these docs but may need tuning for different corpora

**Future improvements**

1. Overlapping chunk windows — so context isn't lost at section boundaries
2. Adaptive scoring thresholds — adjust based on query length or corpus size rather than a hardcoded value
3. Semantic/embedding-based retrieval — to handle synonyms and paraphrasing that word counting misses

---

## 7. Responsible Use

**Where could this cause real-world harm?**

Developers might trust incorrect answers when configuring security-critical things like authentication or API access controls. The system can also miss important warnings buried in sections that didn't score highly. In naive LLM mode specifically, the model can confidently produce plausible-sounding but completely wrong config values or endpoint names — the kind of thing that only breaks at runtime, not during code review.

**What instructions would you give developers using DocuBot safely?**

- Always verify security-critical information against the actual source file before using it
- Use RAG mode instead of naive LLM when accuracy matters
- Treat every answer as a starting point to investigate, not a final authority
- If RAG doesn't cite a source file, that's a signal the answer may not be grounded

---