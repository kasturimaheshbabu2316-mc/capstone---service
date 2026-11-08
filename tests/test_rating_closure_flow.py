"""Test suite for idle rating timer and conversational closure behavior.

Verifies:
1. No rating prompt attached to every assistant response.
2. 3-minute inactivity timer definition, delay value (3 * 60 * 1000 = 180,000 ms),
   and exposure of window.__triggerRatingPrompt and window.__idleRatingTimerDelay.
3. Conversational closure detection for all required phrases, case variations,
   punctuation, and non-closure differentiation.
4. Exact polite closing message text and idle rating prompt message text.
5. Strict verification that forbidden privacy substring 'feedback' does not appear
   in static/app.js.
6. Reset flow resets idle timer and active rating flags.
"""

from pathlib import Path
import re
import shutil
import subprocess
import pytest

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
APP_JS = STATIC_DIR / "app.js"


@pytest.fixture(scope="module")
def app_js_content() -> str:
    assert APP_JS.exists(), "static/app.js must exist"
    return APP_JS.read_text(encoding="utf-8")


def test_no_rating_prompt_on_every_assistant_response(app_js_content: str):
    """Verifies that rating card is no longer appended inside appendAssistantResponse."""
    fn_start = app_js_content.find("function appendAssistantResponse(")
    assert fn_start != -1, "appendAssistantResponse must exist"
    # Find the end of appendAssistantResponse
    fn_end = app_js_content.find("function scrollToBottom()", fn_start)
    assert fn_end != -1
    fn_body = app_js_content[fn_start:fn_end]

    # Must NOT append ratingCard to bubble in every response
    assert "bubble.appendChild(ratingCard)" not in fn_body
    # Must cache latestInteractionContext
    assert "latestInteractionContext = {" in fn_body
    assert "ticketId:" in fn_body
    # Must start the idle timer after response is rendered
    assert "startIdleRatingTimer()" in fn_body


def test_idle_timer_constants_and_exposed_hooks(app_js_content: str):
    """Verifies idle timer delay is 3 minutes (180,000 ms) and exposed on window object."""
    assert "const IDLE_RATING_DELAY_MS = 3 * 60 * 1000;" in app_js_content
    assert "let idleRatingTimer = null;" in app_js_content
    assert "let hasActiveRatingPrompt = false;" in app_js_content
    assert "let isRatingSubmittedForSession = false;" in app_js_content

    # Exposed hooks for testing and verification
    assert "window.__triggerRatingPrompt = presentIdleRatingPrompt;" in app_js_content
    assert "window.__idleRatingTimerDelay = IDLE_RATING_DELAY_MS;" in app_js_content


def test_idle_rating_prompt_text(app_js_content: str):
    """Verifies presentIdleRatingPrompt uses the exact required polite prompt."""
    expected_text = (
        "We hope your inquiry was resolved to your satisfaction! "
        "Since you've been away for a moment, could you please take a moment to rate our service today?"
    )
    assert expected_text in app_js_content
    assert "function presentIdleRatingPrompt" in app_js_content


def test_conversational_closure_closing_message_text(app_js_content: str):
    """Verifies closing conversational response presents exact required text and rating card."""
    expected_text = (
        "You're very welcome! We're glad we could assist you today. "
        "Please take a moment to rate our service:"
    )
    assert expected_text in app_js_content
    assert "isClosureQuery(queryText)" in app_js_content


def test_reset_clears_timer_and_rating_state(app_js_content: str):
    """Verifies resetChatDesk clears idle timer and resets all rating session flags."""
    fn_start = app_js_content.find("function resetChatDesk()")
    assert fn_start != -1
    fn_end = app_js_content.find("window.resetChatDesk = resetChatDesk;", fn_start)
    assert fn_end != -1
    fn_body = app_js_content[fn_start:fn_end]

    assert "clearIdleRatingTimer()" in fn_body
    assert "hasActiveRatingPrompt = false;" in fn_body
    assert "isRatingSubmittedForSession = false;" in fn_body
    assert "latestInteractionContext = null;" in fn_body


def test_input_listener_postpones_timer_while_typing(app_js_content: str):
    """Verifies chatInput input listener resets timer if active."""
    input_idx = app_js_content.find('chatInput.addEventListener("input"')
    assert input_idx != -1
    input_block = app_js_content[input_idx:input_idx + 300]
    assert "if (idleRatingTimer)" in input_block
    assert "startIdleRatingTimer()" in input_block


def test_no_forbidden_privacy_strings_in_app_js(app_js_content: str):
    """Strictly checks that the forbidden privacy word 'feedback' is absent from static/app.js."""
    assert "feedback" not in app_js_content


def test_closure_detection_logic_via_node(app_js_content: str):
    """Executes closure detection logic extracted directly from app.js in Node.js."""
    node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("Node.js binary not installed on this system")

    # Extract CLOSURE_PHRASES and isClosureQuery directly from app.js
    start_pos = app_js_content.find("const CLOSURE_PHRASES = [")
    assert start_pos != -1
    end_pos = app_js_content.find("async function dispatchQuery(", start_pos)
    assert end_pos != -1
    extracted_code = app_js_content[start_pos:end_pos].strip()

    test_harness = (
        extracted_code
        + "\n\n"
        + """
// 1. All mandatory closure phrases
const requiredPhrases = [
  "thank you", "thanks", "thank you so much", "thx", "that helps", "that helped",
  "all good", "resolved", "issue resolved", "bye", "goodbye", "done", "im done",
  "i am done", "thats all", "that is all", "no more questions", "no further questions",
  "perfect thanks"
];

for (const phrase of requiredPhrases) {
  if (!isClosureQuery(phrase)) {
    console.error(`FAIL: expected '${phrase}' to match closure`);
    process.exit(1);
  }
}

// 2. Variations: punctuation, casing, apostrophes
const variations = [
  "Thanks!",
  "THANK YOU SO MUCH.",
  "Done!",
  "I'm done",
  "I am done.",
  "That's all!",
  "All good, thanks",
  "ok thanks",
  "okay thank you",
  "resolved.",
  "Issue resolved!",
  "Bye!!",
  "Goodbye :-)"
];

for (const v of variations) {
  if (!isClosureQuery(v)) {
    console.error(`FAIL: expected variation '${v}' to match closure`);
    process.exit(1);
  }
}

// 3. Negative tests: normal inquiries must NOT match closure
const normalQueries = [
  "What is the resolution SLA for a Sev-1 safety incident?",
  "What is the status of TKT-0007?",
  "When does Ola provide monetary refunds for driver cancellations?",
  "What are the benefits and response times for VIP Ola Select customers?",
  "Is my ticket resolved?",
  "How to get ride issue resolved?",
  "Why is the booking done incorrectly?",
  "Hello, I need help"
];

for (const q of normalQueries) {
  if (isClosureQuery(q)) {
    console.error(`FAIL: normal query '${q}' falsely matched closure`);
    process.exit(1);
  }
}

console.log("ALL_CLOSURE_TESTS_PASSED");
"""
    )
    result = subprocess.run(
        [node_bin, "-e", test_harness],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Node script error: {result.stderr}"
    assert "ALL_CLOSURE_TESTS_PASSED" in result.stdout
