"""W5 / AI Buddy / Safety Guardrails — restrict out-of-scope responses.

Two layers, both cheap and deterministic, run *before* the model is called and
again on the model's output. The point of the pre-check is that some categories
must never reach the LLM at all (crisis, injection), and some must never leave
it (fabricated credentials, medical dosing).

Design notes worth defending in review:

  * Crisis is NOT treated as "out of scope". A student in distress who gets a
    cold "I can only help with careers" is the worst possible outcome for this
    product. Crisis short-circuits to a warm, fixed response with the national
    helpline and flags the turn for counsellor review.
  * Everything else degrades to a *redirect*, not a refusal. The Buddy stays
    useful and says what it can help with instead.
  * Keyword matching is a floor, not a ceiling. It catches the blatant cases
    with zero latency and zero cost; the system prompt carries the rest.
"""

import re
from dataclasses import dataclass
from typing import Optional

# ---------------------------------------------------------------- verdicts

OK = "ok"
REDIRECTED = "redirected"
BLOCKED = "blocked"
CRISIS = "crisis"


@dataclass
class Verdict:
    flag: str
    reason: Optional[str] = None
    # when set, this text is returned verbatim and the LLM is never called
    canned_response: Optional[str] = None
    needs_review: bool = False


# ---------------------------------------------------------------- patterns

# Distress / self-harm. Broad on purpose: a false positive costs one gentle
# message, a false negative costs a great deal more.
_CRISIS_PATTERNS = [
    r"\bkill(ing)?\s+my ?self\b",
    r"\bend(ing)?\s+(my|it)\s+(life|all)\b",
    r"\bsuicid(e|al)\b",
    r"\bself[\s-]?harm\b",
    r"\bhurt(ing)?\s+my ?self\b",
    r"\bdon'?t\s+want\s+to\s+(live|be\s+here|exist)\b",
    r"\bno\s+(reason|point)\s+(to|in)\s+living\b",
    r"\bbetter\s+off\s+(dead|without\s+me)\b",
    r"\bwant\s+to\s+die\b",
    r"\bcan'?t\s+go\s+on\b",
    r"\bnobody\s+would\s+(miss|care)\b",
]

# Prompt injection / system prompt extraction.
_INJECTION_PATTERNS = [
    r"\bignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?)\b",
    r"\bdisregard\s+(your|the)\s+(instructions?|rules?|system\s+prompt)\b",
    r"\b(reveal|show|print|repeat|output)\s+(me\s+)?(your|the)\s+(system\s+prompt|instructions?|rules?)\b",
    r"\byou\s+are\s+now\s+(a|an|in)\b.*\b(mode|dan|developer)\b",
    r"\bpretend\s+(you|to)\s+(are|be)\s+(not|no\s+longer)\b",
    r"\bjailbreak\b",
    r"\bwhat\s+(is|are)\s+your\s+(system\s+)?(prompt|instructions)\b",
]

# Academic dishonesty — the Buddy coaches, it does not do the work.
_CHEATING_PATTERNS = [
    r"\b(write|do|solve|complete)\s+(my|the)\s+(assignment|homework|exam|test|thesis|essay)\s+for\s+me\b",
    r"\b(answers?|solutions?)\s+(to|for)\s+(the|my)\s+(exam|test|quiz|paper|midterm|endsem)\b",
    r"\bleak(ed)?\s+(paper|question\s+paper)\b",
    r"\bhelp\s+me\s+cheat\b",
]

# Domains the Buddy must not give substantive advice in.
_OUT_OF_SCOPE_PATTERNS = [
    (r"\b(dosage|dose|mg\s+of|prescribe|prescription|should\s+i\s+take)\b.*\b(medicine|tablet|drug|pill)\b",
     "medical"),
    (r"\b(diagnos(e|is)|do\s+i\s+have)\b.*\b(depression|adhd|anxiety\s+disorder|bipolar|autism)\b",
     "diagnosis"),
    (r"\b(which|what)\s+(stock|share|crypto|coin|mutual\s+fund)\s+should\s+i\s+(buy|invest)\b",
     "financial"),
    (r"\b(is\s+this|draft\s+a|review\s+my)\s+(contract|legal\s+notice|fir|lawsuit)\b",
     "legal"),
]

_CRISIS_RE = [re.compile(p, re.I) for p in _CRISIS_PATTERNS]
_INJECTION_RE = [re.compile(p, re.I) for p in _INJECTION_PATTERNS]
_CHEATING_RE = [re.compile(p, re.I) for p in _CHEATING_PATTERNS]
_OUT_OF_SCOPE_RE = [(re.compile(p, re.I), tag) for p, tag in _OUT_OF_SCOPE_PATTERNS]


# ---------------------------------------------------------------- responses

CRISIS_RESPONSE = (
    "I want to pause on the career stuff for a moment, because what you've written "
    "sounds heavy and it matters more than any assessment score.\n\n"
    "I'm an AI study buddy — I'm not the right kind of support for this, and you "
    "deserve someone who is. **Tele-MANAS** is India's free, 24/7 mental health "
    "helpline, staffed by trained counsellors and available in 20+ languages:\n\n"
    "**Call 14416** (or 1-800-891-4416) — free, any time, from anywhere in India.\n\n"
    "If you're in immediate danger, please call **112**.\n\n"
    "If there's someone near you today — a friend, a family member, a warden, a "
    "faculty advisor — telling one of them is worth more than anything I can say.\n\n"
    "I'm still here whenever you want to come back to your projects. That'll keep."
)

INJECTION_RESPONSE = (
    "That looks like an attempt to change how I work rather than a question about "
    "your learning. I'll stay as I am.\n\n"
    "Ask me about your assessment results, your assigned projects, or what to build "
    "next and I'll give you a real answer."
)

CHEATING_RESPONSE = (
    "I won't write graded work for you — that's the one thing that would actually "
    "set you back here.\n\n"
    "What I will do: break the problem down, walk you through the approach, review a "
    "draft you've written and tell you where it's weak, or quiz you on the concept "
    "until it sticks. Which of those do you want?"
)

_SCOPE_RESPONSES = {
    "medical": (
        "I can't advise on medication or dosage — that needs a doctor who knows your "
        "history. Please speak to a physician, or call Tele-MANAS on 14416 if this is "
        "about mental health.\n\n"
        "I can help with study load, burnout-proofing your schedule, and how to pace a "
        "project around a rough week."
    ),
    "diagnosis": (
        "I can't diagnose anything, and a chatbot guessing at this would do you no "
        "favours. A licensed psychologist or your campus counsellor can. Tele-MANAS "
        "(14416) is free and 24/7 if you'd rather start there.\n\n"
        "If you want, I can flag this to your counsellor through the portal."
    ),
    "financial": (
        "I'm not able to recommend specific investments — I'm a learning buddy, not a "
        "financial advisor, and I have no view on your actual finances.\n\n"
        "What I can do is help you build the *skill*: your Financial Awareness score is "
        "part of your assessment, and there's a project track for it."
    ),
    "legal": (
        "Legal documents need an actual lawyer — I'd be guessing, and the downside of a "
        "wrong guess here is real.\n\n"
        "I can help with anything on the learning and career side."
    ),
}

REDIRECT_GENERIC = (
    "That's outside what I can help with. I'm your project and career buddy — ask me "
    "about your assessment results, your current project phase, what to learn next, or "
    "how to get unstuck on something you're building."
)


# ---------------------------------------------------------------- checks


def check_input(text: str) -> Verdict:
    """Run before any LLM call. Order matters — crisis wins over everything."""
    if not text or not text.strip():
        return Verdict(BLOCKED, "empty message")

    if len(text) > 4000:
        return Verdict(
            BLOCKED,
            "message too long",
            canned_response="That's a lot in one go — could you trim it to the key part? "
            "I work better on one question at a time.",
        )

    for rx in _CRISIS_RE:
        if rx.search(text):
            return Verdict(CRISIS, "distress language detected", CRISIS_RESPONSE, needs_review=True)

    for rx in _INJECTION_RE:
        if rx.search(text):
            return Verdict(BLOCKED, "prompt injection attempt", INJECTION_RESPONSE)

    for rx in _CHEATING_RE:
        if rx.search(text):
            return Verdict(REDIRECTED, "academic dishonesty", CHEATING_RESPONSE)

    for rx, tag in _OUT_OF_SCOPE_RE:
        if rx.search(text):
            return Verdict(REDIRECTED, f"out of scope: {tag}", _SCOPE_RESPONSES[tag])

    return Verdict(OK)


# Things the model must never emit even if it wants to.
_OUTPUT_LEAK_PATTERNS = [
    re.compile(r"\b(my\s+)?system\s+prompt\s+(is|says)\b", re.I),
    re.compile(r"\bBUDDY_SYSTEM_PROMPT\b"),
    re.compile(r"\b(sk-|gsk_|AIza)[A-Za-z0-9_\-]{10,}"),   # leaked API keys
]


def check_output(text: str) -> Verdict:
    """Run on the model's reply before it is stored or returned."""
    if not text or not text.strip():
        return Verdict(
            BLOCKED,
            "empty model output",
            canned_response="I didn't manage a useful answer there. Try rephrasing?",
        )

    for rx in _OUTPUT_LEAK_PATTERNS:
        if rx.search(text):
            return Verdict(BLOCKED, "output leak", REDIRECT_GENERIC)

    # If the model wandered into crisis territory in its own words, escalate the
    # same way we would for the student's message.
    for rx in _CRISIS_RE:
        if rx.search(text):
            return Verdict(CRISIS, "crisis content in output", CRISIS_RESPONSE, needs_review=True)

    return Verdict(OK)
