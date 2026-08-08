"""W6 / Project Module / Template Library — 18 seeded project templates.

Each template is keyed to one of the ten assessment categories so the
auto-assignment engine (routers/projects.py) can match a student's three
weakest categories to concrete work.

Every template carries a four-phase brief matching the lifecycle:
    discover -> design -> build -> present

Seed with:  python -m data.project_templates
"""

import json

PHASE_ORDER = ["discover", "design", "build", "present"]

PHASE_LABELS = {
    "discover": "Discover",
    "design": "Design",
    "build": "Build",
    "present": "Present",
}

TEMPLATES = [
    # ---------------------------------------- Cognitive & Creative Skills
    {
        "slug": "constraint-redesign",
        "title": "Redesign Something You Use Daily",
        "summary": "Pick one everyday object or app you find frustrating, diagnose exactly why, and produce a redesign that fixes it under a hard constraint you set yourself.",
        "focus_category": "Cognitive & Creative Skills",
        "secondary_categories": ["Subject Interest & Domain Curiosity"],
        "domain": None,
        "difficulty": "starter",
        "estimated_hours": 8,
        "deliverables": ["Annotated before/after", "One-page rationale"],
        "phase_briefs": {
            "discover": [
                "Use the thing for three days and log every moment of friction with a timestamp",
                "Interview two other users — ask what they gave up on, not what they like",
                "Write the single sentence that states the real problem",
            ],
            "design": [
                "Set one hard constraint (no new screens / no extra cost / one-handed use)",
                "Sketch three different fixes, not three versions of one fix",
                "Pick one and write down what you are deliberately making worse",
            ],
            "build": [
                "Produce the redesign — mockup, physical model, or working prototype",
                "Test it against your original friction log, item by item",
                "Record which frictions you actually removed and which you didn't",
            ],
            "present": [
                "Make a before/after that a stranger understands in 30 seconds",
                "Write 300 words on the trade-off you chose and why",
                "Get one person to critique it and note what you'd change next",
            ],
        },
    },
    {
        "slug": "problem-reframe-lab",
        "title": "The Reframe Lab",
        "summary": "Take one problem in your college or community and produce five genuinely different framings of it, then argue for the one that unlocks the best solutions.",
        "focus_category": "Cognitive & Creative Skills",
        "secondary_categories": ["Communication & Language Preference"],
        "domain": None,
        "difficulty": "core",
        "estimated_hours": 12,
        "deliverables": ["Five-framing document", "Recommendation memo"],
        "phase_briefs": {
            "discover": [
                "Pick a real problem you have personally hit this semester",
                "Collect evidence it exists — data, quotes, photos, not opinion",
                "Write the problem as most people state it",
            ],
            "design": [
                "Rewrite it five ways: as a resource problem, an incentive problem, an information problem, a design problem, a people problem",
                "For each framing, list the solutions it makes obvious",
                "Score each framing on how tractable its solutions are",
            ],
            "build": [
                "Pick the highest-scoring framing and prototype its cheapest solution",
                "Run it with at least five real people",
                "Record what happened, including what failed",
            ],
            "present": [
                "Write a two-page memo: original framing, chosen reframe, evidence, recommendation",
                "Present it to someone who could actually act on it",
                "Log their objections",
            ],
        },
    },
    # ---------------------------------------- Digital & Technological Orientation
    {
        "slug": "automate-your-week",
        "title": "Automate One Hour of Your Week",
        "summary": "Find a repetitive task you do every week and automate it end to end, then measure whether it actually saved time.",
        "focus_category": "Digital & Technological Orientation",
        "secondary_categories": ["Personal Management & Wellness"],
        "domain": "softwareEngineering",
        "difficulty": "starter",
        "estimated_hours": 10,
        "deliverables": ["Working script or workflow", "Time-saved log"],
        "phase_briefs": {
            "discover": [
                "Track one week of routine tasks and time each one",
                "Pick the one with the best (time × frequency) ÷ difficulty ratio",
                "Write down exactly what the manual process is, step by step",
            ],
            "design": [
                "Choose your tooling and justify it in one line each",
                "Draw the input → transform → output flow",
                "Decide what happens when it fails — silent failure is not allowed",
            ],
            "build": [
                "Build it, smallest working version first",
                "Run it live for two weeks",
                "Add error handling for the failure you actually hit",
            ],
            "present": [
                "Publish the code with a README a stranger could follow",
                "Report real time saved vs. time spent building — be honest if it lost",
                "Note one thing you'd automate next",
            ],
        },
    },
    {
        "slug": "data-story-local",
        "title": "One Chart That Changes a Local Mind",
        "summary": "Find open data about your city, district or campus, and build a single visualisation that changes what someone believes about it.",
        "focus_category": "Digital & Technological Orientation",
        "secondary_categories": ["Communication & Language Preference", "Cognitive & Creative Skills"],
        "domain": "dataScience",
        "difficulty": "core",
        "estimated_hours": 15,
        "deliverables": ["Cleaned dataset", "Final chart", "500-word writeup"],
        "phase_briefs": {
            "discover": [
                "Find a real open dataset (data.gov.in, census, municipal portals, your college)",
                "Write down three questions you can actually answer with it",
                "Check the data quality before you fall in love with a question",
            ],
            "design": [
                "Pick the one question with a surprising answer",
                "Sketch three chart forms on paper before touching code",
                "Decide what the reader should believe differently afterwards",
            ],
            "build": [
                "Clean the data and document every cleaning decision",
                "Build the chart; iterate until it needs no verbal explanation",
                "Show it to two people cold and note what they misread",
            ],
            "present": [
                "Write 500 words: question, method, finding, caveats",
                "Publish it somewhere public",
                "State one limitation honestly — this is the part most students skip",
            ],
        },
    },
    {
        "slug": "ml-baseline-honest",
        "title": "The Honest Baseline",
        "summary": "Build a machine learning model on a real dataset and then spend equal effort proving where it fails.",
        "focus_category": "Digital & Technological Orientation",
        "secondary_categories": ["Academic Aptitude & Learning Style", "Risk Appetite & Ambiguity Tolerance"],
        "domain": "dataScience",
        "difficulty": "stretch",
        "estimated_hours": 25,
        "deliverables": ["Repo with reproducible pipeline", "Failure analysis"],
        "phase_briefs": {
            "discover": [
                "Choose a dataset and a decision the model would actually inform",
                "Establish a dumb baseline first (majority class, mean, last value)",
                "Define your metric before you see any results",
            ],
            "design": [
                "Design the train/validation/test split so it matches real deployment",
                "List the leakage risks specific to this dataset",
                "Decide the minimum lift over baseline that would make the model worth using",
            ],
            "build": [
                "Build the pipeline end to end and make it reproducible from a clean clone",
                "Beat the baseline, or document clearly why you couldn't",
                "Slice the errors — find the subgroup where it fails worst",
            ],
            "present": [
                "Write a model card: intended use, metric, failure modes, who it would hurt",
                "Present the failure analysis before the accuracy number",
                "Recommend deploy or don't deploy, and defend it",
            ],
        },
    },
    # ---------------------------------------- Communication & Language Preference
    {
        "slug": "explain-it-twice",
        "title": "Explain It Twice",
        "summary": "Take the hardest concept from your field and explain it two ways — once to an expert, once to a twelve-year-old — and get both audiences to confirm you succeeded.",
        "focus_category": "Communication & Language Preference",
        "secondary_categories": ["Academic Aptitude & Learning Style"],
        "domain": None,
        "difficulty": "starter",
        "estimated_hours": 8,
        "deliverables": ["Two explanations", "Audience feedback"],
        "phase_briefs": {
            "discover": [
                "Pick the concept you understand least well but need most",
                "Read two sources and note every place you were confused",
                "Write down what makes it hard, specifically",
            ],
            "design": [
                "Draft the expert version: precise, no analogies, correct",
                "Draft the twelve-year-old version: one analogy, no jargon",
                "Identify what the simple version has to sacrifice",
            ],
            "build": [
                "Test the expert version on someone in your field — ask them to find an error",
                "Test the simple version on someone outside it — ask them to explain it back",
                "Rewrite both based on where they broke",
            ],
            "present": [
                "Publish both side by side",
                "Add a short note on what the simplification costs",
                "Record yourself giving the simple version in under two minutes",
            ],
        },
    },
    {
        "slug": "weekly-writing-streak",
        "title": "Eight Weeks in Public",
        "summary": "Publish one short piece a week for eight weeks on what you're learning, and track how the writing itself changes.",
        "focus_category": "Communication & Language Preference",
        "secondary_categories": ["Personal Management & Wellness", "Risk Appetite & Ambiguity Tolerance"],
        "domain": None,
        "difficulty": "core",
        "estimated_hours": 16,
        "deliverables": ["Eight published posts", "Retrospective"],
        "phase_briefs": {
            "discover": [
                "Choose a narrow topic you'll still care about in two months",
                "Pick the platform and commit to a fixed publishing day",
                "Read three writers you admire in that space; note what they do structurally",
            ],
            "design": [
                "Draft eight titles up front so you never face a blank page",
                "Set a hard word cap (400-600) so shipping beats polishing",
                "Decide your one non-negotiable quality bar",
            ],
            "build": [
                "Publish weekly. Missing a week means posting late, not skipping",
                "Log time spent and engagement for each post",
                "Note which posts were hardest and why",
            ],
            "present": [
                "Write a retrospective comparing post 1 and post 8 honestly",
                "Identify the habit that made shipping possible",
                "Decide whether to continue, and say why either way",
            ],
        },
    },
    # ---------------------------------------- Emotional & Social Competence
    {
        "slug": "feedback-loop",
        "title": "The Feedback Loop",
        "summary": "Run a structured feedback cycle on yourself — collect it, sit with it, act on one item, and measure whether anything changed.",
        "focus_category": "Emotional & Social Competence",
        "secondary_categories": ["Personal Management & Wellness"],
        "domain": None,
        "difficulty": "starter",
        "estimated_hours": 8,
        "deliverables": ["Feedback synthesis", "Change log"],
        "phase_briefs": {
            "discover": [
                "Pick five people who have seen you work: peers, a teacher, a family member",
                "Ask each the same two questions, one of which must invite criticism",
                "Collect responses in writing so you can re-read them when less defensive",
            ],
            "design": [
                "Group the feedback into themes rather than reacting item by item",
                "Find the one theme that appears from more than one source",
                "Define one behaviour change and how you'd know it worked",
            ],
            "build": [
                "Run the change for four weeks with a weekly self-check",
                "Note every time you defaulted back to the old behaviour",
                "Ask one of the original five for a mid-point read",
            ],
            "present": [
                "Write up what you heard, what you changed, and what you chose to ignore",
                "Be explicit about the feedback you disagreed with and why",
                "Share the result with at least one person who gave it",
            ],
        },
    },
    {
        "slug": "run-a-small-thing",
        "title": "Run a Small Thing With Other People",
        "summary": "Organise something real involving at least six people — a study group, a workshop, a cleanup — and take responsibility when it wobbles.",
        "focus_category": "Emotional & Social Competence",
        "secondary_categories": ["Values & Lifestyle Priorities", "Communication & Language Preference"],
        "domain": None,
        "difficulty": "core",
        "estimated_hours": 14,
        "deliverables": ["Event/session record", "Participant feedback", "Retrospective"],
        "phase_briefs": {
            "discover": [
                "Find something people around you actually want but nobody has organised",
                "Talk to six potential participants before committing",
                "Define what success looks like in one measurable sentence",
            ],
            "design": [
                "Plan logistics: date, place, roles, what happens if half don't show",
                "Assign at least two roles to other people, not yourself",
                "Write the message you'll send to invite people",
            ],
            "build": [
                "Run it. Adapt live when something goes wrong",
                "Collect feedback the same day while memory is fresh",
                "Note the moment it was hardest and what you did",
            ],
            "present": [
                "Write a retrospective: what worked, what you'd change, what you'd delegate",
                "Thank participants specifically, not generically",
                "Decide whether to run it again",
            ],
        },
    },
    # ---------------------------------------- Personal Management & Wellness
    {
        "slug": "energy-audit",
        "title": "Four-Week Energy Audit",
        "summary": "Instrument your own week, find where your focus actually goes, and restructure one part of it based on evidence rather than intention.",
        "focus_category": "Personal Management & Wellness",
        "secondary_categories": ["Academic Aptitude & Learning Style"],
        "domain": None,
        "difficulty": "starter",
        "estimated_hours": 8,
        "deliverables": ["Time/energy dataset", "Restructured schedule", "Results"],
        "phase_briefs": {
            "discover": [
                "Log time and energy (1-5) in blocks for one full week — no changes yet",
                "Note sleep, meals and screen time alongside",
                "Find your two highest-energy hours and what currently occupies them",
            ],
            "design": [
                "Move your hardest work into your best hours",
                "Cut or batch one recurring low-value block",
                "Decide the one metric that tells you it worked",
            ],
            "build": [
                "Run the new structure for three weeks, still logging",
                "Record every week you broke it and what caused the break",
                "Adjust once, mid-way, based on data not mood",
            ],
            "present": [
                "Chart week 1 against week 4",
                "Write what actually changed and what was just noise",
                "Keep the one habit worth keeping; drop the rest deliberately",
            ],
        },
    },
    {
        "slug": "hard-thing-90",
        "title": "One Hard Thing, Ninety Days",
        "summary": "Commit to a single measurable skill target for 90 days with public checkpoints, and finish it whether or not you feel like it.",
        "focus_category": "Personal Management & Wellness",
        "secondary_categories": ["Risk Appetite & Ambiguity Tolerance"],
        "domain": None,
        "difficulty": "stretch",
        "estimated_hours": 40,
        "deliverables": ["Weekly checkpoint log", "Final proof of the target"],
        "phase_briefs": {
            "discover": [
                "Pick one skill with an unambiguous finish line you cannot fake",
                "Baseline yourself honestly today",
                "Name the two things most likely to derail you",
            ],
            "design": [
                "Break 90 days into 12 weekly targets, front-loaded harder",
                "Pick one person who will actually ask you about it weekly",
                "Pre-decide your minimum on a bad day — the version you do when ill or busy",
            ],
            "build": [
                "Log every week including the ones you missed",
                "Recover from a missed week within 48 hours, not next month",
                "Re-baseline at day 45 and adjust the remaining targets",
            ],
            "present": [
                "Demonstrate the finish line, don't describe it",
                "Publish the full log including gaps",
                "Write what the process taught you that the skill didn't",
            ],
        },
    },
    # ---------------------------------------- Financial Awareness & Constraints
    {
        "slug": "cost-of-a-goal",
        "title": "Cost the Thing You Want",
        "summary": "Take a real goal — a degree, a laptop, a move to another city — and build a defensible financial model of what it actually costs and how you'd fund it.",
        "focus_category": "Financial Awareness & Constraints",
        "secondary_categories": ["Cognitive & Creative Skills"],
        "domain": "finance",
        "difficulty": "starter",
        "estimated_hours": 10,
        "deliverables": ["Spreadsheet model", "Funding plan"],
        "phase_briefs": {
            "discover": [
                "Pick one goal with a real price tag",
                "List every cost, including the ones people forget: travel, deposits, lost income",
                "Source each number and note how confident you are in it",
            ],
            "design": [
                "Build three scenarios: lean, expected, and something goes wrong",
                "Model the funding side: savings, earning, scholarship, loan",
                "Make the assumptions explicit and editable in one place",
            ],
            "build": [
                "Build the spreadsheet so changing one assumption updates everything",
                "Stress test it: what if the cost is 30% higher?",
                "Check two of your numbers against a real source",
            ],
            "present": [
                "Write a one-page recommendation to yourself",
                "State the single assumption the whole plan depends on",
                "Show it to someone financially literate and note what they challenge",
            ],
        },
    },
    {
        "slug": "unit-economics-teardown",
        "title": "Unit Economics Teardown",
        "summary": "Pick a business you use and reverse-engineer whether a single customer actually makes them money.",
        "focus_category": "Financial Awareness & Constraints",
        "secondary_categories": ["Cognitive & Creative Skills", "Digital & Technological Orientation"],
        "domain": "finance",
        "difficulty": "core",
        "estimated_hours": 14,
        "deliverables": ["Unit economics model", "Written teardown"],
        "phase_briefs": {
            "discover": [
                "Pick a business with visible pricing — a café, a delivery app, a coaching centre",
                "Identify the unit: one order, one student, one subscription",
                "Gather every public number you can find",
            ],
            "design": [
                "Map revenue per unit and every cost that scales with it",
                "Separate fixed from variable costs carefully",
                "Mark which numbers are sourced and which are your estimates",
            ],
            "build": [
                "Build the model and compute contribution margin",
                "Find the break-even volume",
                "Test how sensitive it is to your two shakiest assumptions",
            ],
            "present": [
                "Write the teardown: how they make money, where it's fragile",
                "Show the sensitivity clearly",
                "Say what you would change if you ran it",
            ],
        },
    },
    # ---------------------------------------- Academic Aptitude & Learning Style
    {
        "slug": "teach-to-learn",
        "title": "Teach a Topic You Just Learned",
        "summary": "Learn something new in four weeks and prove it by teaching it to a real audience who can ask you questions.",
        "focus_category": "Academic Aptitude & Learning Style",
        "secondary_categories": ["Communication & Language Preference"],
        "domain": None,
        "difficulty": "core",
        "estimated_hours": 16,
        "deliverables": ["Teaching materials", "Recorded session", "Q&A log"],
        "phase_briefs": {
            "discover": [
                "Pick a topic you genuinely do not know yet",
                "Find three sources at different levels and one primary source",
                "Write the five questions you cannot yet answer",
            ],
            "design": [
                "Build a 30-minute outline that answers those five questions",
                "Design one exercise the audience does, not watches",
                "Decide what you will deliberately leave out",
            ],
            "build": [
                "Teach it to at least three people, live",
                "Write down every question you couldn't answer",
                "Go back, learn those, and revise the material",
            ],
            "present": [
                "Publish the revised materials",
                "Include the questions that stumped you and their answers",
                "Note what teaching revealed that reading hadn't",
            ],
        },
    },
    # ---------------------------------------- Subject Interest & Domain Curiosity
    {
        "slug": "field-scan",
        "title": "Map Your Field in Twenty Interviews",
        "summary": "Systematically map what people in your target field actually do all day, and revise your career assumption based on what you find.",
        "focus_category": "Subject Interest & Domain Curiosity",
        "secondary_categories": ["Emotional & Social Competence", "Communication & Language Preference"],
        "domain": None,
        "difficulty": "core",
        "estimated_hours": 18,
        "deliverables": ["Interview notes", "Field map", "Revised career hypothesis"],
        "phase_briefs": {
            "discover": [
                "Write your current assumption about what this job involves — date it",
                "Build a list of 20 people in the field at different levels",
                "Draft five questions, none of which are 'any advice?'",
            ],
            "design": [
                "Write the outreach message; make it short and specific to each person",
                "Decide how you'll record and compare answers",
                "Set a target: at least eight actual conversations",
            ],
            "build": [
                "Run the conversations over four weeks",
                "After each one, note what contradicted your assumption",
                "Follow up with a thank-you that references something they said",
            ],
            "present": [
                "Produce a one-page map: roles, daily reality, entry paths, what people warn about",
                "Compare against your dated original assumption",
                "State your revised hypothesis and what would change it again",
            ],
        },
    },
    # ---------------------------------------- Risk Appetite & Ambiguity Tolerance
    {
        "slug": "ship-in-public",
        "title": "Ship Something Unfinished",
        "summary": "Put a deliberately incomplete thing in front of real users in two weeks, and let their reaction decide what you build next.",
        "focus_category": "Risk Appetite & Ambiguity Tolerance",
        "secondary_categories": ["Digital & Technological Orientation", "Emotional & Social Competence"],
        "domain": "softwareEngineering",
        "difficulty": "core",
        "estimated_hours": 20,
        "deliverables": ["Live prototype", "User reactions", "Decision log"],
        "phase_briefs": {
            "discover": [
                "Pick a problem you can put something in front of someone within 14 days",
                "Identify five people who'd try it",
                "Write down what you're most afraid they'll say",
            ],
            "design": [
                "Cut scope to the single thing that must work",
                "Decide what 'good enough to show' means, in writing",
                "Plan how you'll collect reactions without leading them",
            ],
            "build": [
                "Ship on day 14 regardless of how it feels",
                "Watch at least three people use it without helping them",
                "Log every point of confusion",
            ],
            "present": [
                "Report what you got wrong most usefully",
                "Decide: continue, pivot, or stop — and justify it",
                "Note how the fear from phase one compared to reality",
            ],
        },
    },
    # ---------------------------------------- Values & Lifestyle Priorities
    {
        "slug": "values-tradeoff",
        "title": "The Trade-off You're Actually Making",
        "summary": "Interrogate a career choice you're drifting toward by making its real trade-offs explicit and testing them against people living each option.",
        "focus_category": "Values & Lifestyle Priorities",
        "secondary_categories": ["Subject Interest & Domain Curiosity"],
        "domain": None,
        "difficulty": "starter",
        "estimated_hours": 9,
        "deliverables": ["Trade-off matrix", "Decision memo"],
        "phase_briefs": {
            "discover": [
                "Name the two paths you're actually choosing between",
                "List what each costs you: time, money, location, relationships, risk",
                "Rank your five values before looking at the options",
            ],
            "design": [
                "Build a matrix scoring each path against your ranked values",
                "Identify where your gut and your matrix disagree",
                "Write down what the disagreement tells you",
            ],
            "build": [
                "Talk to one person living each path for at least three years",
                "Ask what they gave up, not what they gained",
                "Revise the matrix with what you learned",
            ],
            "present": [
                "Write a decision memo to yourself, dated",
                "State the conditions under which you'd reverse it",
                "Set a calendar reminder to re-read it in six months",
            ],
        },
    },
    # ---------------------------------------- domain-specific extras
    {
        "slug": "ux-teardown-fix",
        "title": "Usability Teardown and Fix",
        "summary": "Run a real usability test on an app people use, find the three worst failures, and redesign the flow that fails hardest.",
        "focus_category": "Cognitive & Creative Skills",
        "secondary_categories": ["Emotional & Social Competence", "Digital & Technological Orientation"],
        "domain": "uxDesign",
        "difficulty": "core",
        "estimated_hours": 16,
        "deliverables": ["Test recordings/notes", "Redesigned flow", "Rationale"],
        "phase_briefs": {
            "discover": [
                "Pick an app with a task you can define precisely",
                "Recruit five people who have never used it",
                "Write the task script — no hints, no leading",
            ],
            "design": [
                "Run the tests; record where each person hesitates or fails",
                "Rank failures by severity × frequency",
                "Pick the worst one and diagnose the cause, not the symptom",
            ],
            "build": [
                "Redesign that flow end to end",
                "Re-test with three new people",
                "Compare failure rates before and after",
            ],
            "present": [
                "Present findings with evidence clips or quotes",
                "Show the before/after numbers",
                "Note what you couldn't fix within the constraint",
            ],
        },
    },
    {
        "slug": "campaign-from-zero",
        "title": "A Campaign With a Real Number Attached",
        "summary": "Run a small marketing campaign for something real, with a target you commit to before starting.",
        "focus_category": "Communication & Language Preference",
        "secondary_categories": ["Financial Awareness & Constraints", "Risk Appetite & Ambiguity Tolerance"],
        "domain": "marketing",
        "difficulty": "core",
        "estimated_hours": 15,
        "deliverables": ["Campaign assets", "Results dashboard", "Post-mortem"],
        "phase_briefs": {
            "discover": [
                "Find something real to promote — a club event, a friend's shop, your own project",
                "Define the audience narrowly enough to name three real examples",
                "Commit to one number before you start",
            ],
            "design": [
                "Write three messages testing different angles, not different wording",
                "Pick channels where your named audience actually is",
                "Set a budget, even if it's zero, and a stop date",
            ],
            "build": [
                "Run it. Track every channel separately",
                "Kill the worst-performing angle at the halfway point",
                "Double down on what's working",
            ],
            "present": [
                "Report against the number you committed to, hit or miss",
                "Explain which angle won and your best guess why",
                "Write what you'd do with ten times the budget",
            ],
        },
    },
]


def seed(db) -> int:
    """Insert or update every template. Idempotent — safe to run repeatedly."""
    from models.models import ProjectTemplate

    written = 0
    for t in TEMPLATES:
        row = db.query(ProjectTemplate).filter(ProjectTemplate.slug == t["slug"]).first()
        if row is None:
            row = ProjectTemplate(slug=t["slug"])
            db.add(row)
        row.title = t["title"]
        row.summary = t["summary"]
        row.focus_category = t["focus_category"]
        row.secondary_categories = json.dumps(t.get("secondary_categories", []))
        row.domain = t.get("domain")
        row.difficulty = t["difficulty"]
        row.estimated_hours = t["estimated_hours"]
        row.phase_briefs = json.dumps(t["phase_briefs"])
        row.deliverables = json.dumps(t.get("deliverables", []))
        row.is_active = True
        written += 1
    db.commit()
    return written


if __name__ == "__main__":
    from database import Base, SessionLocal, engine

    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        print(f"seeded {seed(session)} project templates")
    finally:
        session.close()
