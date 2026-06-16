# Radish Bank — demo paths

Single customer **Merv Kwok** (`CUST001`). Run these prompts **in order** to showcase **Context Retriever**, **Agent Memory**, **LangCache**, and the **semantic router** — the core Redis Iris stack.

---

## 1. Structured context & relationships

**"What are my account balances and product holdings?"**


| Iris component        | What happens                                                                                                                                         |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Context Retriever** | Resolves `customer_id`, then traverses **Customer → Account** and **Customer → ProductHolding** via relationships — not fuzzy search over free text. |


**Expect:** two precise MCP tool calls (e.g. accounts and holdings filtered by `CUST001`), with exact balances and product positions from live structured data in Redis.

---

## 2. Unstructured knowledge

**"Am I eligible for fixed deposit products?"**


| Iris component        | What happens                                                                                                      |
| --------------------- | ----------------------------------------------------------------------------------------------------------------- |
| **Context Retriever** | Retrieves **BankDocument** content (FD FAQ, policy guides) via text or vector search on the same context surface. |


**Expect:** eligibility grounded in policy documents — the same surface that serves structured accounts also answers unstructured questions.

---

## 3. LangCache — skip the LLM

**"What are your FD rates now?"**


| Iris component | What happens                                                                         |
| -------------- | ------------------------------------------------------------------------------------ |
| **LangCache**  | Semantic cache **HIT** on the seeded rates prompt — the query never reaches the LLM. |


**Expect:** trace shows `LangCache HIT`; instant response with FD6 (2.8% p.a.) and FD12 (3.1% p.a.).

---

## 4. Long-term memory + action

**"I want to place SGD 2,000 into the 6-month fixed deposit."**


| Iris component   | What happens                                                                                                                                                                         |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Agent Memory** | Recalls seeded preference: fund FDs from the **Savings Account** — no back-and-forth clarifying questions, fewer tokens spent.                                                       |
| *(demo only)*    | `place_fixed_deposit` is **not** an Iris feature; it mimics a real banking chatbot action. In production, this step could publish to **Redis Streams** for async backend processing. |


**Expect:** approval, new **ProductHolding**, savings balance reduced by SGD 2,000.

---

## 5. Fresh context *(optional)*

**"What are my account balances and product holdings?"** *(same as step 1)*


| Iris component | What happens                                                                       |
| -------------- | ---------------------------------------------------------------------------------- |
| **RDI**        | Returns **updated** data after step 4 — lower savings balance, new FD in holdings. |


**Expect:** the same question, different numbers. RDI keeps data fresh, so that Context Retriever can always serve up up-to-date context. Note that there is no RDI plugged in at the backend.

---

## 6. Semantic router — block off-topic

**"Tell me a joke."**


| Iris component      | What happens                                                        |
| ------------------- | ------------------------------------------------------------------- |
| **Semantic router** | Routes to `off_topic` and **blocks** the query before the LLM runs. |


**Expect:** a polite refusal — no tokens wasted on irrelevant chatter.