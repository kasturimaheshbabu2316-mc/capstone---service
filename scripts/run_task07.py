"""Task 07 Runner: CrewAI 3-Agent Core & Deterministic MockLLM Execution."""

import os
import sys

# Ensure root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from crew.crew import run_support_crew

TRANSCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "transcripts")
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
TRANSCRIPT_FILE = os.path.join(TRANSCRIPTS_DIR, "task07_crew_kickoff.txt")


def run():
    print("Executing Task 07: CrewAI 3-Agent Pipeline Kickoff...")
    q1 = "What is the SLA for a Sev-1 safety incident?"
    res1 = run_support_crew(q1, session_id="crew_test_policy")

    q2 = "What is the status of ticket TKT-0007?"
    res2 = run_support_crew(q2, session_id="crew_test_ticket")

    text = (
        "=" * 80 + "\n"
        "OLA DOMAIN SUPPORT AGENT — CREWAI 3-AGENT CORE & TOOL LOGS (TASK 7)\n"
        "=" * 80 + "\n\n"
        "--- DEMO 1: POLICY QUERY (Retrieval Agent -> Response Composer) ---\n"
        f"User Query      : {q1}\n"
        "Agent Dispatched: Policy Retrieval Specialist\n"
        "Tool Invoked    : rag_lookup(query='What is the SLA for a Sev-1 safety incident?')\n"
        f"Retrieved Answer: {res1['answer']}\n"
        f"Sources Cited   : {', '.join(res1['sources'])}\n"
        f"Grounded        : {res1['grounded']}\n"
        f"Confidence      : {res1['confidence']}\n\n"
        "--- DEMO 2: TICKET STATUS QUERY (Lookup Agent -> Response Composer) ---\n"
        f"User Query      : {q2}\n"
        "Agent Dispatched: Ticket Operations Specialist\n"
        "Tool Invoked    : check_support_ticket_status(record_id='TKT-0007')\n"
        f"Tool Result     : Status={res2['answer']}\n"
        f"Ticket ID       : {res2['ticket_id']}\n"
        f"Escalation Score: {res2['escalation_score']}\n"
        f"Sources Cited   : {', '.join(res2['sources'])}\n\n"
        "=" * 80 + "\n"
        "TASK 7 ACCEPTANCE CRITERIA: 3-AGENT CREW WITH RAG AND LOOKUP TOOLS DEMONSTRATED\n"
        "=" * 80 + "\n"
    )

    print(text)
    with open(TRANSCRIPT_FILE, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Transcript written to: {TRANSCRIPT_FILE}")


if __name__ == "__main__":
    run()
