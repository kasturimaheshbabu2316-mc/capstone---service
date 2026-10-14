---
description: Step 7 - MockLLM (BaseLLM) and the 3-agent CrewAI crew (Task 7)
---
STEP 7 - CrewAI crew under MOCK_LLM (Task 7).
1. crew/mock_llm.py: class MockLLM(crewai.llms.base_llm.BaseLLM) (the documented
   extension point; do not try to intercept litellm). Implement call() so it produces
   ReAct-format output deterministically: decide the tool from the user's task, emit
   "Thought / Action / Action Input", then after the tool result arrives emit
   "Thought: I now know the final answer / Final Answer: ...".
   KNOWN SILENT PITFALLS - handle both:
   (a) CrewAI's own system prompt template contains the text "Observation: the result of
       the action". Do NOT search the whole conversation for "Observation:". Parse only
       the model's own generated turns / the latest tool result message.
   (b) Do NOT pick the tool by checking whether its NAME contains "lookup" or similar.
       Dispatch from the tool's declared args schema (e.g. a tool with a "query" arg is
       RAG, a tool with a "record_id" arg is the ticket tool).
2. crew/crew.py: three agents (Retrieval Agent with the RAG tool, Lookup Agent with
   check_support_ticket_status, Response Composer with no tools), sequential Process,
   run via crew.kickoff(). Set CREWAI_DISABLE_TELEMETRY before import.
3. Demo: one policy query (RAG tool invoked) and one "status of TKT-0007" query (lookup
   tool invoked). Log which tool ran for each. Add a test that fails if the final answer
   is placeholder text.
Save the output to transcripts/07_crew.txt.
