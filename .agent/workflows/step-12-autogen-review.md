---
description: Step 12 - Autogen RoundRobinGroupChat review stage (Task 14)
---
STEP 12 - Autogen review stage (Task 14).
review/autogen_review.py, using autogen-agentchat (v0.4+ API; check the installed
version's docs/source before coding):
1. A deterministic mock ChatCompletionClient (no network) that plays both roles by rule:
   the Policy-Compliance-Reviewer flags any sentence in the draft not supported by the
   retrieved context; the Final-Editor removes the flagged sentences or approves as-is.
2. class ReviewVerdict(BaseModel): approved: bool, final_answer: str, reason: str.
3. Two AssistantAgents; the Final-Editor uses output_content_type=ReviewVerdict.
4. RoundRobinGroupChat([...], max_turns=2, custom_message_types=
   [StructuredMessage[ReviewVerdict]]). (The parameter is max_turns, not max_iterations.
   If MaxMessageTermination is used instead, it must be MaxMessageTermination(3).)
5. Input to the team = the Composer's draft + the original retrieved context.
6. Demo A: an unchanged draft -> approved=True, same text. Demo B: a draft with a
   deliberately injected ungrounded claim (e.g. "refunds are instant for all riders")
   -> approved=False and the claim removed in final_answer.
7. Wire it after the crew in the main pipeline and surface review_status in CrewResponse
   (add the field in schemas.py without breaking earlier tests).
Save the output to transcripts/14_review.txt.
