"""The impact label set: dimensions, values and their definitions.

v1 comes from the Fable discovery pass over 30 diverse threads
(docs/taxonomy.md), starting from the brief's seed scale (none / cosmetic /
functional / significant / blocked / specification). Changing anything here
that reaches the prompt must bump VERSION so classify relabels.

Each value is (key, label, definition, on_scale). on_scale=False values of an
ordinal dimension sit outside the ordering (drawn neutral in the dashboard).
"""

VERSION = "v1"
# Label files from these versions are valid. v2 (2026-11-11) briefly dropped the verdict question;
# it came back, word for word, for the inferred stance, so the prompt is v1 again. No v2 labels exist.
ACCEPTED_VERSIONS = {"v1"}
REASON_MAX = 300
PLANNED_NOTE = ("changes for change_magnitude and change_type, but record them as promised_only in "
                "change_locus unless the thread shows them landing")

DIMENSIONS = [
    {
        "key": "change", "label": "Design change", "multi": False, "ordinal": True,
        "description": "The largest change to the proposal after the TAG's first substantive feedback, whoever caused it.",
        "values": [
            ("none", "None", "No change to the design, spec or explainer is shown or promised after TAG feedback "
             "(the requester may push back, ignore it, or never respond). Also for threads that aren't reviews.", True),
            ("documentation", "Docs only", "Only prose changed or was promised: explainer sections, use cases, the "
             "security & privacy questionnaire, considerations sections, examples, clarifications. Behaviour and API "
             "surface unchanged.", True),
            ("cosmetic", "Cosmetic", "Surface API change without changing behaviour: renaming, ergonomics, syntax.", True),
            ("functional", "Functional", "A meaningful change to how the feature behaves or what it exposes within the "
             "same overall approach: an added permission, mitigation or verification step, a capability added or "
             "removed, changed defaults.", True),
            ("significant", "Significant", "Redesigned around a different architecture or approach (e.g. imperative to "
             "declarative, a new underlying model) and continuing under the same review.", True),
            ("abandoned", "Abandoned", "The proposal as reviewed was withdrawn, not pursued, or replaced by a "
             "different proposal (whatever the reason; see attribution).", True),
            ("undetermined", "Undetermined", "The thread implies a change may have happened but doesn't show what, "
             "or the thread is open with changes pending, or evidence is cut from the thread.", False),
        ],
    },
    {
        "key": "change_type", "label": "Kind of change", "multi": True, "ordinal": False,
        "description": "Every kind of change visible after TAG feedback; 'none' only when nothing changed.",
        "values": [
            ("naming", "Naming", "An identifier, property or feature name changed or was promised to change.", True),
            ("api_shape", "API shape", "Method, attribute, parameter, event or sync/async structure changed, beyond "
             "pure renames.", True),
            ("privacy_security", "Privacy/security", "New or changed privacy or security protections: permissions, "
             "noise, origin checks, user mediation, substantive threat-model text.", True),
            ("scope_reduction", "Scope cut", "Part of the proposal was removed, deferred or moved out of scope.", True),
            ("architecture", "Architecture", "The underlying model or approach changed, or the proposal was replaced "
             "by a differently-architected successor.", True),
            ("documentation", "Documentation", "Explainer or spec prose, examples, use cases or motivation added or "
             "revised without changing behaviour.", True),
            ("venue_or_process", "Venue/process", "Work moved to another group, venue or standards track, or a new "
             "review was opened elsewhere at the TAG's prompting.", True),
            ("none", "None", "No change of any kind is visible after TAG feedback.", True),
        ],
    },
    {
        "key": "change_locus", "label": "Where it landed", "multi": True, "ordinal": False,
        "description": "Where the change(s) landed. A link to a PR, commit or merged text counts as landed; a "
                       "statement of intent is promised_only.",
        "values": [
            ("explainer", "Explainer", "Explainer or README text was updated.", True),
            ("spec_text", "Spec text", "Specification text was edited.", True),
            ("implementation", "Implementation", "Shipped or trial behaviour changed: a trial ended or started, a "
             "feature was removed or flipped in a browser, a rename landed in code.", True),
            ("issue_filed", "Issue filed", "An issue was filed in the feature's repo or another venue to track TAG "
             "feedback.", True),
            ("promised_only", "Promised only", "The requester committed to a specific change but the thread doesn't "
             "show it landing.", True),
            ("none", "None", "No change landed or was promised.", True),
        ],
    },
    {
        "key": "attribution", "label": "Credit to the TAG", "multi": False, "ordinal": False,
        "description": "Whether the recorded change can be credited to the TAG review, from the thread alone.",
        "values": [
            ("tag_explicit", "Explicit", "The requester ties the change to TAG feedback ('as requested', 'per your "
             "feedback', addresses TAG points one by one), or the TAG thanks them for incorporating its feedback and "
             "nothing else is credited.", True),
            ("tag_implicit", "Implicit", "The change matches a specific TAG ask and follows it, but nobody says so "
             "and no other cause is named.", True),
            ("shared", "Shared", "The TAG is credited alongside other causes (WG discussion, other reviewers, other "
             "implementers, security teams).", True),
            ("external", "External", "The change is credited to someone other than the TAG.", True),
            ("unclear", "Unclear", "A change (including withdrawal) happened but the thread gives no reason.", True),
            ("not_applicable", "No change", "No change occurred, or it is undetermined with no stated driver.", True),
        ],
    },
    {
        # Asked of the model but not published as is: build.py reduces it to the three-way inferred
        # stance (STANCE below). Fine-grained, it disagrees with the TAG's own Resolution labels too
        # often (satisfied vs with concerns); coarsely it agrees 93% of the time (docs/taxonomy.md).
        "key": "verdict", "label": "TAG verdict", "multi": False, "ordinal": False, "publish": False,
        "description": "The TAG's final disposition, from the last substantive TAG comment; Resolution labels only "
                       "break ties.",
        "values": [
            ("satisfied", "Satisfied", "Happy, no (major) outstanding concerns.", True),
            ("satisfied_with_concerns", "With concerns", "Doesn't block but records unresolved concerns or "
             "ambivalence.", True),
            ("unsatisfied", "Unsatisfied", "Still fundamentally disagrees with the design, without saying the "
             "feature shouldn't exist.", True),
            ("recommends_against", "Recommends against", "Says the feature shouldn't be part of the web platform or "
             "standardised in its current form.", True),
            ("deferred", "Deferred/redirected", "No verdict for now: too early, wrong or missing venue, remanded to a "
             "WG, outside TAG competence; invited to return.", True),
            ("withdrawn", "Withdrawn/superseded", "The requester withdrew, abandoned or replaced the proposal before a "
             "verdict.", True),
            ("no_verdict", "No verdict", "Still open, or closed as stalled or timed out without a stated position.", True),
            ("not_a_review", "Not a review", "Not a design review of a feature or spec (TAG process, templates, "
             "meta discussion, charters).", True),
        ],
    },
]

# The TAG's verdict comes from its own `Resolution:` labels (latency.resolution), not from a model:
# v1 also asked the model for a verdict, which agreed with the labels 75% of the time and never
# contradicted them outright (docs/taxonomy.md). Descriptions are the labels' own, from GitHub,
# 2026-11-11; the ones GitHub leaves blank are ours. Labels started in May 2019, so earlier reviews
# mostly have none.
RESOLUTIONS = [
    ("satisfied", "Satisfied", "The TAG is satisfied with this design."),
    ("validated", "Validated", "For early reviews where the TAG largely supports the direction the work is going in."),
    ("satisfied with concerns", "With concerns", "The TAG is satisfied with this work overall but requires changes."),
    ("ambivalent", "Ambivalent", "The TAG is neither satisfied nor unsatisfied (no description on GitHub)."),
    ("unsatisfied", "Unsatisfied", "The TAG does not feel the design meets required quality standards."),
    ("object", "Object", "The TAG has resolved this should not proceed towards Recommendation."),
    ("lack of consensus", "Lack of consensus", "The TAG does not have consensus about this."),
    ("decline", "Decline", "The TAG declines to review this work: its review wouldn't add much. It doesn't object."),
    ("too early", "Too early", "Possibly too early for review, or not enough information provided."),
    ("too late", "Too late", "The review was filed too late to make any difference."),
    ("out of scope", "Out of scope", "Outside what the TAG reviews (no description on GitHub)."),
    ("timed out", "Timed out", "The TAG requested more information but didn't receive it."),
    ("withdrawn", "Withdrawn", "The requester withdrew the proposal."),
    ("overtaken", "Overtaken", "For example, another proposal emerged covering the same use cases with broader support."),
    ("none", "No label", "No Resolution label. Usual before the labels were introduced in May 2019."),
]
# The inferred three-way stance: the model's verdict, grouped so it agrees with the TAG's own labels
# (93% on the 650 labelled reviews, 2026-11-11). Finer splits (satisfied vs with concerns) don't.
STANCES = [
    ("no_objection", "No objection", "Satisfied, validated, satisfied with concerns or ambivalent: the TAG doesn't "
     "object to the design.", "var(--seq-4)"),
    ("objection", "Objection", "Unsatisfied, or recommends the feature not proceed.", "var(--series-2)"),
    ("no_position", "No position", "No stance on the design: declined, deferred, too early, timed out, withdrawn or "
     "overtaken.", "var(--series-3)"),
    ("not_a_review", "Not a review", "Not a design review of a feature or spec.", "var(--unknown)"),
]
VERDICT_STANCE = {"satisfied": "no_objection", "satisfied_with_concerns": "no_objection",
                  "unsatisfied": "objection", "recommends_against": "objection",
                  "deferred": "no_position", "withdrawn": "no_position", "no_verdict": "no_position",
                  "not_a_review": "not_a_review"}
RESOLUTION_STANCE = {"satisfied": "no_objection", "validated": "no_objection", "satisfied with concerns": "no_objection",
                     "ambivalent": "no_objection", "unsatisfied": "objection", "object": "objection",
                     "lack of consensus": "objection"}   # every other label: no_position


def stance(verdict):
    """The inferred stance for a model verdict, or None."""
    return VERDICT_STANCE.get(verdict)


def resolution_stance(label):
    """The same grouping for a Resolution label (None when there is no label)."""
    return None if label is None else RESOLUTION_STANCE.get(label, "no_position")


RESOLUTION_COLORS = {
    "satisfied": "var(--seq-5)", "validated": "var(--seq-4)", "satisfied with concerns": "var(--seq-2)",
    "ambivalent": "var(--seq-1)", "unsatisfied": "var(--series-2)", "object": "var(--series-2)",
    "none": "var(--none)",
}

GUIDANCE = """\
Pitfalls to avoid:
- Count only changes made AFTER the TAG's first substantive feedback.
- Explainer and questionnaire edits are the commonest change. They are 'documentation', not 'functional',
  unless behaviour or API surface changed.
- Renames and redesigns often come from the working group, other browsers or security teams. Credit the TAG
  (tag_explicit) only when the thread says so; otherwise use shared, external, tag_implicit or unclear.
- Withdrawal is not the same as the TAG blocking it: use attribution to say why it was abandoned.
- Labels and closing text can disagree; prefer the TAG's closing comment for the verdict.
- An open thread gets verdict no_verdict even if TAG members voiced strong views.
- If evidence was cut from the thread, prefer 'undetermined' to guessing.
- The [TAG]/[REQUESTER] tags come from GitHub metadata and are usually right, but judge by what people say:
  someone tagged [TAG] may be speaking for the proposal."""


def _values(d):
    return [v[0] for v in d["values"]]


def prompt_definitions():
    out = []
    for d in DIMENSIONS:
        kind = "choose all that apply" if d["multi"] else "choose exactly one"
        out.append(f"{d['key']} ({kind}): {d['description']}")
        out += [f"  - {k}: {defn}" for k, _, defn, _ in d["values"]]
    return "\n".join(out) + "\n\n" + GUIDANCE


def schema():
    props, req = {}, []
    for d in DIMENSIONS:
        enum = {"type": "string", "enum": _values(d)}
        props[d["key"]] = ({"type": "array", "items": enum, "minItems": 1, "maxItems": len(d["values"])}
                           if d["multi"] else enum)
        req.append(d["key"])
    props["reason"] = {"type": "string", "maxLength": REASON_MAX * 2}
    props["evidence_comments"] = {"type": "array", "items": {"type": "integer", "minimum": 0}, "maxItems": 5}
    return {"type": "object", "additionalProperties": False, "required": req + ["reason", "evidence_comments"],
            "properties": props}


def validate(raw):
    """Only known dimensions and values; single-choice -> str or None, multi -> list in definition order."""
    out = {}
    for d in DIMENSIONS:
        allowed = _values(d)
        v = raw.get(d["key"]) if isinstance(raw, dict) else None
        if d["multi"]:
            vals = v if isinstance(v, list) else [v]
            out[d["key"]] = [x for x in allowed if x in vals]
        else:
            out[d["key"]] = v if v in allowed else None
    return out


# Derived summaries the dashboard leads with.
TAG_CREDIT = {"tag_explicit", "tag_implicit", "shared"}
CHANGED = {"documentation", "cosmetic", "functional", "significant"}
MAJOR = {"functional", "significant"}

# A derived dimension combining change and attribution: "did the review change the feature?"
OUTCOME = {
    "key": "outcome", "label": "TAG impact", "multi": False, "ordinal": True, "derived": True,
    "description": "Did the review change the feature, and does the thread credit the TAG? Derived from how "
                   "much the design changed after the TAG's first feedback and from Credit to the TAG.",
    "values": [
        ("no_change", "No change", "Nothing changed after the TAG's feedback.", "var(--none)"),
        ("other_credit", "Changed, not credited", "Something changed, but the thread credits others or gives no "
         "reason.", "var(--seq-1)"),
        ("minor", "Docs/cosmetic, TAG credited", "Documentation or cosmetic change credited to the TAG (explicitly, "
         "implicitly or shared).", "var(--seq-3)"),
        ("major", "Functional+, TAG credited", "Functional or significant change credited to the TAG.",
         "var(--seq-5)"),
        ("blocked", "Blocked", "Abandoned, with the TAG credited (alone or shared) for it.", "var(--series-2)"),
        ("abandoned_other", "Abandoned, other reason", "Abandoned for reasons not credited to the TAG.",
         "var(--series-3)"),
        ("undetermined", "Undetermined", "The thread doesn't show what changed.", "var(--unknown)"),
    ],
}


def outcome(labels):
    c, a = labels.get("change"), labels.get("attribution")
    if c is None:
        return None
    if c == "none":
        return "no_change"
    if c == "undetermined":
        return "undetermined"
    credited = a in TAG_CREDIT
    if c == "abandoned":
        return "blocked" if credited else "abandoned_other"
    if not credited:
        return "other_credit"
    return "major" if c in MAJOR else "minor"


def _color(d, i, k, on_scale):
    """Colour tokens by role (style.css): ordinal values on a single-hue ramp, the rest neutral or accent."""
    if not d["ordinal"]:
        return "var(--series-1)"
    if k == "abandoned":
        return "var(--series-2)"
    if not on_scale:
        return "var(--unknown)"
    if k == "none":
        return "var(--none)"
    return f"var(--seq-{min(6, 1 + 2 * (i - 1))})"


def public():
    dims = [{"key": OUTCOME["key"], "label": OUTCOME["label"], "description": OUTCOME["description"],
             "multi": False, "ordinal": True, "derived": True,
             "values": [{"key": k, "label": label, "definition": defn, "color": color}
                        for k, label, defn, color in OUTCOME["values"]]}]
    for d in DIMENSIONS:
        if d.get("publish") is False:
            continue
        dims.append({"key": d["key"], "label": d["label"], "description": d["description"], "multi": d["multi"],
                     "ordinal": d["ordinal"], "derived": False,
                     "values": [{"key": k, "label": label, "definition": defn, "color": _color(d, i, k, on)}
                                for i, (k, label, defn, on) in enumerate(d["values"])]})
    dims.append({"key": "stance", "label": "Inferred TAG stance", "multi": False, "ordinal": False, "derived": True,
                 "description": "The TAG's stance as the model reads the thread, in three groups. Inferred for every "
                                "review, so it covers the years before Resolution labels; a separate axis from the "
                                "TAG's own label below.",
                 "values": [{"key": k, "label": label, "definition": defn, "color": color}
                            for k, label, defn, color in STANCES]})
    # Not a model label: read from the review's `resolution` field (the GitHub label).
    dims.append({"key": "resolution", "label": "TAG resolution (GitHub label)", "field": "resolution",
                 "description": "The TAG's own Resolution label on the issue. Labels started in May 2019; most "
                                "earlier reviews have none.",
                 "multi": False, "ordinal": False, "derived": False,
                 "values": [{"key": k, "label": label, "definition": defn,
                             "color": RESOLUTION_COLORS.get(k, "var(--unknown)")} for k, label, defn in RESOLUTIONS]})
    return {"version": VERSION, "dimensions": dims}
