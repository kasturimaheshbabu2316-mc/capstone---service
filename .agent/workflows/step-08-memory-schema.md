---
description: Step 8 - session memory and Pydantic structured output (Tasks 8, 9)
---
STEP 8 - Session memory and Pydantic output (Tasks 8, 9).
1. crew/memory.py: InMemoryChatMessageHistory + RunnableWithMessageHistory with a
   session_id store. (The LangChainDeprecationWarning is expected; do not silence it.)
   Wrap the crew call so history is injected into the task (for pronoun resolution like
   "what about its SLA?" after asking about a ticket or policy).
2. Demo transcripts: (a) a multi-turn exchange in one session where turn 2 depends on
   turn 1, (b) a SEPARATE fresh session showing the same follow-up fails or resets.
3. crew/schemas.py: class CrewResponse(BaseModel) with answer, route (rag|lookup|both),
   sources, ticket (optional), grounded, escalation_recommended. Use it as the
   crew's response format and validate every response in code with
   CrewResponse.model_validate; raise a clear error on a mismatch.
Save the output to transcripts/08_memory.txt and transcripts/09_schema.txt.
