# Citi Tampa: public communication and attention comparison
**Preliminary research dated November 12, 2026. Not an incident-liability finding.**

## Main result
A deliberately selected sample shows a difference in **topics**, not proof of diversion. Official and personally authored public statements predominantly discuss memorialization, courage, mutual care, and specific post-event support. Public forum participants also raised explicit questions about pre-attack warning, lockdown, perimeter barriers, security reviews, and leadership decisions.

**The existence of active prevention discussion is counterevidence to a sweeping claim that institutional communications silenced or displaced that topic everywhere.**

The repository input, public_discourse_discovery_20261112.json, contains 17 selected evidence units. The analyzer at convergence/cross_channel_discourse.py reports only **within-sample** observations.

| Selected cohort | Units | Units tagged prevention_question |
|---|---:|---:|
| Institutional | 3 | 0 |
| Separate personal posts | 6 | 0 |
| Public forum comments/posts | 8 | 6 |

This is **purposeful discovery**, not random sampling. These ratios cannot be interpreted as platform-wide proportions or comparable prevalence estimates. Nor does the absence of a prevention question in a partial post prove it wasn't addressed elsewhere.

## Institutional communications
- [Citi's official post](https://ib.linkedin.com/company/citi) memorializes LeAnne, announces $250,000 for performing arts, and praises security.
- [Jane Fraser's employee memo](https://www.fox13seattle.com/news/heavy-law-enforcement-presence-outside-brandon-citibank-triggers-traffic-alert), reproduced by news media, recognizes the security response and mentions counseling and other-site security.
- [Edward Skyler's post, indexed in another employee's activity](https://pl.linkedin.com/in/adrian-koscielniak-b2a2511), separately announces the **same** $250,000 memorial fund. This is not a second contribution.

These support identifying concrete reported actions, but don't independently answer how Citi escalated the threat before the breach.

## Distinct personal accounts: not one interchangeable PR statement
- [Zo Amani](https://ae.linkedin.com/in/atharahmed): personal experience and gratitude for security and law enforcement.
- [J. Marshall Moorhead](https://in.linkedin.com/in/vineet-b-465b4857): first-person account from the café, explicitly in a personal capacity.
- [Tom Lahoud](https://uk.linkedin.com/in/charlotte-taylor-a77643a1): personal tribute and discussion of LeAnne's protective-action/fire-safety training work.
- [Xiomara Váquiro](https://uk.linkedin.com/in/charlotte-taylor-a77643a1): thanks coworkers and leaders for support and emphasizes community.
- [Gabriel Rincon](https://do.linkedin.com/in/rocio-velarde-citi): reports specific personal outreach from leadership.
- Former Tampa site executive: user-provided screenshot; author name, original public URL, full post and hashtags unverified.

For named posts reproduced in other people's LinkedIn reaction feeds, the original author attribution is observable but **the original post permalink and its comments are not authenticated**. Reaction feeds must not be counted as new authored posts.

## Public discussion *of* Fraser's memo
The [r/citibank thread asking about the CEO email](https://www.reddit.com/r/citibank/comments/1xohb6t/who_was_the_shooter/) includes readers asking for specific counseling resources, a third-party security assessment, notification of other offices, and whether leadership's response was generic.

This constitutes observable **cross-platform discussion about an executive communication**. It is not a verified direct LinkedIn reply, a complete survey of readers, or proof the memo caused a topic change.

## Prevention-focused discussions, with unverified personal claims
- [r/tampa Citi Bank shooting update](https://www.reddit.com/r/tampa/comments/1xosoky/citi_bank_shooting_update/): questions concerning advance warning, lockdown, and vehicle protection.
- [r/tampa Citi Responsible for the death of employee](https://www.reddit.com/r/tampa/comments/1xp5pux/citi_responsible_for_the_death_of_employee/): questions separating heroic intervention from prior preventive decisions.

Forum posts establish that questions were publicly asked. They **do not** establish that commenters work at Citi, that every alleged notification failure is a verified fact, or that any specific institutional duty was violated.

## Limits: what this does not establish
The sample does **not** show centralized coordination, executive intent to divert, AI authorship, a successful audience shift, a proven policy breach, or negligence. It also doesn't establish the precise time Citi first received the initial threat, which pre-attack warnings were issued, or the design requirements governing perimeter barriers.

What would support a stronger audience-effects analysis: complete original executive post URLs, full thread replies and timestamps, their distribution/reach evidence, consistent sampling before/after messages, and controls for simultaneous incident news. Cross-platform selection effects are substantial.

## Reproduce
From the repository root, run:

    python -m pytest tests/test_cross_channel_discourse.py -q
    PYTHONPATH=. python examples/citi_tampa_2026/run_cross_channel.py

The output distinguishes selected unit and source counts, topic incidence, and references to the CEO memo. Population attention shift, corporate-message causation, and coordinated publication are all explicitly **not established**.

No posts, comments, or external outreach were made on the user's behalf.


## Follow-through: nine public prevention and support questions

The new ledger in question_followthrough_20261112.json traces each issue to topic-related executive statements, independent incident reporting, and attributed but unauthenticated forum claims. It does not pretend Citi directly replied to any individual Reddit commenter. Missing public records cannot prove internal nonaction.

| Question | Public material located | Remaining evidence needed |
|---|---|---|
| First Citi knowledge and severity | Skyler reported serious assessment and change in posture | Original security intake and classification timestamps |
| Internal escalation | HCSO confirmed Citi notified deputies shortly before noon | Citi escalation and protective-action decision logs |
| Employee warning before breach | Commenters say no pre-breach warning reached them | Notification and delivery logs |
| Alert timing | Commenters report 12:40 text and 12:56 recorded call | Sender logs and actual device receipts |
| Vehicle perimeter | HCSO established that the gate was breached | Vehicle rating, threat model and design acceptance |
| Independent security review | Forum commenter requested an external assessment | Formal commissioned scope and report, if any |
| Counseling | Fraser announced counseling resources | Eligibility, access and delivery evidence |
| Work-location relief | Skyler reported an immediate remote-work accommodation | Full notice and duration/extension terms |
| Armed intervention | HCSO documented Fraley's intervention | Independent reconstruction if evaluating completeness |

Every issue has an explicit evidence-status classification, and none is assumed to have a complete verified institutional answer. Announcement, delivery and effectiveness are separate questions.

## Two real linked reply chains, not hypothetical examples

The new reddit_linked_discussion_20261112.json retains six selected, anchored statements across four real reply links, as visible in the public r/citibank threads.

- A question about Fraser's memo generated a request for accessible resources and an independent security assessment. The next response agreed with the need for protective action. The discussion moved toward examination of prevention, not away from it.
- A prevention-focused comment contrasted heroic intervention with pre-attack safeguards. A reply mentioned added security at other sites but still addressed the existence of earlier warning. It did not supply Citi's intake or decision logs; a further reply's asserted three-hour window conflated the law firm's initial threat with the unverified time Citi actually learned of it.

The existing attention-trajectory engine therefore records topic changes, unanswered issues, and continued prevention attention. In this selected set it must **not** emit a prevention-to-response displacement classification. That would overstate the evidence.

## Reproduce the full follow-through review

    python -m pytest tests/test_cross_channel_discourse.py tests/test_question_followthrough.py tests/test_public_discourse_linked.py -q
    PYTHONPATH=. python examples/citi_tampa_2026/run_cross_channel.py

The output includes source-bounded question statuses and four selected Reddit reply transitions. It establishes no authenticated LinkedIn audience replies, overall attention trend, concealment, institutional negligence or coordination.
