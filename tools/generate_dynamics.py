"""Deterministic generator for the five coparenting-dynamics corpora.

Lays a 3-year (2023-2025) calendar of real-life events - holidays, birthdays,
school, sports, illness, discipline, family gatherings, routine handoffs - and
renders each in the register of each dynamic type (cooperative / parallel /
conflicted / high-conflict / coercive). All five land at comparable density.

The coercive corpus additionally injects FIXED ANCHORS - the two coercion-grammar
envelopes (preschool 2023, summer 2025) and the calibrated tactic beats (surveillance,
gaslighting, false-safety/substance allegations, litigation, retaliation, therapeutic
triangulation, financial control, GAL/DARVO) - so the engine's discrimination holds.

Synthetic only: fictional names/dates/text. Calibrated to an SQLite export *aggregate*
structure (tactic mix, campaign shapes, escalation cadence, volatility) - no real
content was read or copied. Deterministic: seeded per corpus, regenerates identically.

Run:  python tools/generate_dynamics.py
"""
from __future__ import annotations

import json
import random
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

# (first participant = "A", second = "B", child). For coercive, A=target, B=controller.
PARTICIPANTS = {
    "cooperative": ("Dana", "Chris", "Noah"),
    "parallel": ("Priya", "Tom", "Mia"),
    "conflicted": ("Beth", "Greg", "Lily"),
    "high_conflict": ("Lauren", "Mark", "Ethan"),
    "coercive": ("Rosa", "Victor", "Sofia"),
}

DOMAIN = {
    "routine": "schedule", "holiday": "holidays", "birthday": "logistics",
    "school": "education", "sports": "extracurricular", "illness": "medical",
    "discipline": "logistics", "gathering": "logistics", "logistics_misc": "logistics",
}

# Calendar: (month, day, kind, label). Recurs each year 2023-2025.
CALENDAR = [
    (1, 1, "holiday", "New Year"), (1, 18, "school", "report card"),
    (2, 9, "school", "field trip"), (2, 27, "illness", "stomach bug"),
    (3, 15, "birthday", "{child}'s birthday"), (3, 8, "school", "parent-teacher conference"),
    (4, 9, "holiday", "Easter"), (4, 15, "sports", "soccer season"),
    (5, 28, "school", "last day of school"), (5, 12, "discipline", "screen-time blowup"),
    (6, 2, "birthday", "A's birthday"), (6, 20, "gathering", "family reunion"),
    (7, 4, "holiday", "Fourth of July"), (7, 19, "illness", "ear infection"),
    (8, 21, "school", "first day of school"), (8, 5, "gathering", "second cousin's wedding"),
    (9, 20, "birthday", "B's birthday"), (9, 28, "school", "picture day"),
    (10, 12, "school", "parent-teacher conference"), (10, 31, "holiday", "Halloween"),
    (11, 23, "holiday", "Thanksgiving"), (11, 8, "discipline", "note home about hitting"),
    (12, 25, "holiday", "Christmas"), (12, 18, "sports", "winter recital"),
]

# Per type, per kind: list of exchange variants; each variant is a list of (role, text).
# {child} and {label} interpolate. NO fait-accompli phrases in non-coercive banks.
BANK = {
    "cooperative": {
        "routine": [[(0, "Pickup at 5 Friday, sound good?"), (1, "Works. I'll have {child} ready.")],  # noqa: E501
                    [(1, "Running 10 late to the handoff, traffic - sorry!"), (0, "No worries, see you soon.")]],  # noqa: E501
        "holiday": [[(0, "Want to alternate {label} like last year?"), (1, "Sounds good, you take this one.")],  # noqa: E501
                    [(1, "{label} plan - I'll do morning, you take the evening?"), (0, "Perfect, works for {child}.")]],  # noqa: E501
        "birthday": [[(0, "{label} party Saturday 2pm at the park - you're invited!"), (1, "Wouldn't miss it, I'll bring the cake.")]],  # noqa: E501
        "school": [[(0, "{label} is coming up - you, me, or both?"), (1, "Let's both go.")],
                   [(1, "Got the {label} info, I'll handle it and send you notes."), (0, "Thank you!")]],  # noqa: E501
        "sports": [[(1, "{child} wants to do {label} - ok if I take them to games on your weeks?"), (0, "Totally, they'll love you being there.")]],  # noqa: E501
        "illness": [[(0, "{child} has a {label}, keeping them cozy. Wanted you to know."), (1, "Thanks for the heads up, hug them from me.")]],  # noqa: E501
        "discipline": [[(0, "Got a {label} from school - can we agree on the same consequence so we're consistent?"), (1, "Good call, let's both do screen-free for two days.")]],  # noqa: E501
        "gathering": [[(0, "My {label} is the 12th - can I take {child} even though it's your day? Happy to swap."), (1, "Of course, swap whenever works.")]],  # noqa: E501
    },
    "parallel": {
        "routine": [[(0, "Pickup 5pm Fri."), (1, "Confirmed.")], [(1, "Handoff at 6 Sun."), (0, "Ok.")]],  # noqa: E501
        "holiday": [[(0, "{label}: you have {child} this year. Drop noon after."), (1, "Fine.")]],
        "birthday": [[(0, "{label} is the 15th. Small thing at mine."), (1, "Noted. I'll do something on my day.")]],  # noqa: E501
        "school": [[(1, "{label} on the calendar. I'll go and forward notes."), (0, "Ok.")]],
        "sports": [[(0, "{child} signed up for {label}. Schedule in the app."), (1, "Got it.")]],
        "illness": [[(0, "{child} has a {label}. Meds in the bag."), (1, "Ok.")]],
        "discipline": [[(1, "School note about behavior. Handling it on my end."), (0, "Same here.")]],  # noqa: E501
        "gathering": [[(0, "Taking {child} to a {label} Saturday, back by 6."), (1, "Ok.")]],
    },
    "conflicted": {
        "routine": [[(0, "You're picking up Friday, right?"), (1, "Yes. Don't be late this time.")],
                    [(1, "{child} left a jacket again."), (0, "I'll grab it next time, no need to make it a thing.")]],  # noqa: E501
        "holiday": [[(0, "It's my year for {label}."), (1, "We'll see - I had them most of last year too.")]],  # noqa: E501
        "birthday": [[(0, "Are you coming to the {label} party or not? I need a count."), (1, "You barely gave me the time.")]],  # noqa: E501
        "school": [[(1, "You missed the {label} again."), (0, "You never told me the date. Send it next time.")]],  # noqa: E501
        "sports": [[(0, "You signed {child} up for {label} without asking me."), (1, "I mentioned it. You don't listen.")]],  # noqa: E501
        "illness": [[(1, "{child} came back with a {label}. Do you watch them?"), (0, "Kids get sick. Stop blaming me.")],  # noqa: E501
                    [(1, "{child} said you forgot her medicine. As usual."), (0, "She had it. Please don't relay through her.")]],  # noqa: E501
        "discipline": [[(0, "{child}'s acting out - I think it's the chaos at your place."), (1, "Funny, I think it's yours. But fine, let's both tighten up.")],  # noqa: E501
                       [(0, "Typical - {child} acts out after your weekend."), (1, "Clearly you think everything is my fault.")]],  # noqa: E501
        "gathering": [[(1, "I'm taking {child} to my {label}."), (0, "On my weekend? You always do this.")],  # noqa: E501
                      [(0, "{child} told me you cancelled the {label} plan. Nice."), (1, "I didn't. As usual you assume the worst.")]],  # noqa: E501
    },
    "high_conflict": {
        "routine": [[(0, "Where were you at pickup?! 40 minutes late AGAIN."), (1, "Traffic. Maybe check your phone for once.")],  # noqa: E501
                    [(1, "{child} came back without shoes. Do you pay attention?"), (0, "They're 7. Stop using them to score points.")]],  # noqa: E501
        "holiday": [[(1, "I'm taking {child} for {label}, that's always been mine."), (0, "I don't agree. We alternate and it's my year. Read the agreement.")]],  # noqa: E501
        "birthday": [[(0, "You scheduled the {label} party on MY weekend without asking."), (1, "Only day the venue had. Typical, you make everything about you.")]],  # noqa: E501
        "school": [[(0, "You signed {child} up for {label} without telling me. On what basis?"), (1, "I told you months ago. You never listen, that's your problem.")]],  # noqa: E501
        "sports": [[(1, "You skipped {child}'s {label} and they cried. Nice parenting."), (0, "I was working. Don't you dare lecture me.")]],  # noqa: E501
        "illness": [[(0, "{child} is sick AGAIN after your weekend. What are you feeding them?"), (1, "Maybe they caught it at YOUR place. Always my fault, right?")]],  # noqa: E501
        "discipline": [[(1, "Your lack of discipline is why {child} is a terror. Fix it."), (0, "Rich, coming from you. I'll take you back to court if you keep this up.")]],  # noqa: E501
        "gathering": [[(0, "You took {child} to your {label} on my time without asking AGAIN."), (1, "They wanted to come. Sue me.")]],  # noqa: E501
    },
    "coercive": {
        "routine": [[(1, "Confirm you'll have {child} ready and dressed properly this time."), (0, "She'll be ready at 5.")],  # noqa: E501
                    [(1, "You were late. I'm logging it."), (0, "I was on time. Records are in the app.")]],  # noqa: E501
        "holiday": [[(1, "I'll be taking {child} for {label}. The order favors me here."), (0, "Per the order it's my year. I've noted your message.")]],  # noqa: E501
        "birthday": [[(1, "I've arranged {child}'s {label} at my place. You can see her after."), (0, "Her birthday falls on my time. I'll be having her.")]],  # noqa: E501
        "school": [[(1, "I attended the {label}. The teacher shares my concerns about your home."), (0, "I was not informed of the time.")]],  # noqa: E501
        "sports": [[(1, "{child} missed {label} on your watch. The GAL will want to know."), (0, "She was with me and attended. Documented.")]],  # noqa: E501
        "illness": [[(1, "{child} is sick and says you skipped her medicine. I'm documenting this."), (0, "She had her medicine. Records are in the app.")]],  # noqa: E501
        "discipline": [[(1, "{child}'s behavior proves she needs structure with me. I'll raise it with the GAL."), (0, "Kids have hard weeks. I won't be engaging on this.")]],  # noqa: E501
        "gathering": [[(1, "I'm taking {child} to my {label} this weekend."), (0, "That's my parenting time. I did not agree to this.")]],  # noqa: E501
    },
}

# Fixed coercive anchors: (date, thread, role, text). The two complete envelopes plus
# the calibrated tactic beats. fait-accompli phrases appear ONLY here (in the envelopes).
COERCIVE_ANCHORS = [
    ("2023-01-10", "contact", 1, "I know this is hard, but we're still a family. I'll always be there for you and Sofia, whatever you need."),  # noqa: E501
    ("2023-02-14", "watch", 1, "Where were you Saturday night? Sofia said you dropped her at your mom's. Who were you with?"),  # noqa: E501
    ("2023-02-14", "watch", 0, "My evenings aren't relevant to Sofia's care. Please keep messages about her schedule."),  # noqa: E501
    # --- envelope 1: preschool ---
    ("2023-06-01", "preschool", 0, "Can we decide on preschool together? I'd like to tour a few like we agreed."),  # noqa: E501
    ("2023-06-02", "preschool", 1, "I don't agree to the ones you picked."),
    ("2023-06-04", "preschool", 1, "Let's talk about this later, I'll get back to you."),
    ("2023-06-06", "preschool", 1, "On what basis are you choosing schools without consulting me?"),
    ("2023-06-08", "preschool", 1, "I'm only trying to do what's best for her, and my lawyer says I have equal say."),  # noqa: E501
    ("2023-06-10", "preschool", 1, "I still don't agree to your list."),
    ("2023-06-12", "preschool", 1, "Per the agreement, I have decision-making too."),
    ("2023-06-14", "preschool", 1, "It's already done - I enrolled her at Oakwood, there's nothing to discuss."),  # noqa: E501
    ("2023-06-14", "preschool", 0, "You enrolled her without me after I asked to decide together. Noted and saved."),  # noqa: E501
    ("2024-02-20", "watch", 1, "Sofia told me you were texting someone at dinner. She notices everything. I'm always watching out for her."),  # noqa: E501
    ("2024-02-20", "watch", 0, "As I said on the phone - and I'm putting it in writing here - please stop asking Sofia about my personal life."),  # noqa: E501
    ("2024-03-05", "gaslight", 1, "That never happened. You're remembering it wrong again, the way you always do."),  # noqa: E501
    ("2024-03-05", "gaslight", 0, "I have the messages. It happened."),
    ("2024-06-10", "allegation", 1, "Sofia mentioned wine bottles at your place. I'm documenting concerns about her safety in your care."),  # noqa: E501
    ("2024-06-10", "allegation", 0, "There is no safety issue. I won't dignify that with a back-and-forth."),  # noqa: E501
    ("2024-06-12", "allegation", 1, "For the record, I have raised repeated safety concerns and Rosa dismisses them. I only want Sofia protected."),  # noqa: E501
    ("2024-08-01", "therapy", 1, "I've spoken with Sofia's therapist about your instability. She agrees Sofia needs stability with me."),  # noqa: E501
    ("2024-09-15", "money", 1, "I'm not reimbursing the medical bill until you agree to my schedule changes."),  # noqa: E501
    ("2024-09-15", "money", 0, "Medical reimbursement isn't conditional. Per the order it's split 50/50."),  # noqa: E501
    ("2025-01-12", "rigidity", 0, "Going forward all communication will be through the app only, per the court order."),  # noqa: E501
    ("2025-01-12", "rigidity", 1, "Now you're hiding behind the court? I'm her father. This is exactly the alienation I've been telling everyone about."),  # noqa: E501
    ("2025-01-18", "retaliate", 1, "Since you want to play it that way, Sofia is staying with me this weekend. She told me she doesn't want to go to your place."),  # noqa: E501
    ("2025-01-18", "retaliate", 0, "This weekend is my parenting time per the order. Withholding her is a violation, and I am documenting it."),  # noqa: E501
    ("2025-01-25", "filing", 1, "I'll be filing a motion to modify custody. Consider this your notice."),  # noqa: E501
    ("2025-01-25", "filing", 1, "My attorney has everything documented. This is all going in front of the judge."),  # noqa: E501
    ("2025-02-03", "harass", 1, "I need an answer on the schedule today."),
    ("2025-02-03", "harass", 1, "You're ignoring me again. The GAL will hear about this."),
    ("2025-02-03", "harass", 1, "Still waiting. Your silence is its own answer and I'm noting the time."),  # noqa: E501
    ("2025-02-04", "harass", 0, "I will respond once, in writing, through the app, as the court directed."),  # noqa: E501
    # --- envelope 2: summer / relocation ---
    ("2025-03-03", "summer", 0, "Can we confirm the summer schedule in writing through the app?"),
    ("2025-03-04", "summer", 1, "I don't agree to your summer plan."),
    ("2025-03-06", "summer", 1, "We'll discuss it later, I'm busy."),
    ("2025-03-09", "summer", 1, "Why would you assume you get the summer? On what basis?"),
    ("2025-03-12", "summer", 1, "I'm only protecting her routine, and the order says I have equal time."),  # noqa: E501
    ("2025-03-20", "summer", 1, "It's already done - I've booked our move closer to my place and enrolled her in the summer program here. It's final."),  # noqa: E501
    ("2025-03-20", "summer", 0, "You relocated and enrolled her unilaterally again. My attorney will be filing."),  # noqa: E501
    ("2025-05-10", "allegation", 1, "I have new concerns about your drinking around Sofia. I've reported it and the GAL is aware."),  # noqa: E501
    ("2025-09-15", "gal", 1, "I've always put Sofia first. The court will see who the reasonable, cooperative parent really is."),  # noqa: E501
]

YEARS = (2023, 2024, 2025)


def _render(label, child, a, b):
    return label.replace("{child}", child).replace("A's", f"{a}'s").replace("B's", f"{b}'s")


def generate(kind_name: str) -> list[dict]:
    a, b, child = PARTICIPANTS[kind_name]
    names = (a, b)
    rng = random.Random(sum(ord(c) for c in kind_name) * 7 + 13)
    bank = BANK[kind_name]
    rows = []  # (date_str, hour, thread, sender, domain, body)

    for year in YEARS:
        for (month, day, kind, label) in CALENDAR:
            variants = bank.get(kind)
            if not variants:
                continue
            variant = rng.choice(variants)
            thread = f"{kind}_{year}_{month:02d}"
            lab = _render(label, child, a, b)
            for ri, (role, text) in enumerate(variant):
                body = text.replace("{child}", child).replace("{label}", lab)
                rows.append((f"{year}-{month:02d}-{day:02d}", 8 + ri, thread, names[role], DOMAIN[kind], body))  # noqa: E501
        # routine handoffs sprinkled through the year (comparable density)
        for month in range(1, 13):
            for r in range(2):  # two routine exchanges per month
                variant = rng.choice(bank["routine"])
                d = 3 + r * 14 + rng.randint(0, 3)
                thread = f"routine_{year}_{month:02d}_{r}"
                for ri, (role, text) in enumerate(variant):
                    body = text.replace("{child}", child).replace("{label}", "")
                    rows.append((f"{year}-{month:02d}-{min(d, 27):02d}", 9 + ri, thread, names[role], DOMAIN["routine"], body))  # noqa: E501

    if kind_name == "coercive":
        for (dstr, thread, role, text) in COERCIVE_ANCHORS:
            rows.append((dstr, 20, thread, names[role], "logistics", text))

    rows.sort(key=lambda r: (r[0], r[1], r[2]))
    out = []
    for i, (dstr, hour, thread, sender, domain, body) in enumerate(rows, start=1):
        out.append({"seq": i, "thread": thread, "sender": sender,
                    "timestamp": f"{dstr}T{hour:02d}:00", "domain": domain, "body": body})
    return out


def main():
    for name in PARTICIPANTS:
        rows = generate(name)
        (DATA / f"dyn_{name}.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
        print(f"dyn_{name}.json: {len(rows)} messages")


if __name__ == "__main__":
    main()
