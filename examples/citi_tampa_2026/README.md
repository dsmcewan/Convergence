# Citi Tampa — public-record communications and causal-control review

**Preliminary research snapshot: November 11, 2026. This is not a liability finding.**

This case distinguishes the memorial of LeAnne Selman and recognition of John Fraley from an investigation of the decisions and protective controls preceding the November 4, 2026 shooting. The key question is what was known, when it was known, what protective actions were required and implemented, and what records could prove the difference.

## Reproduce

From the repository root:

    python -m pytest tests/test_corporate_review.py tests/test_causal_audit.py tests/test_framing_comparison.py -q
    PYTHONPATH=. python examples/citi_tampa_2026/run_review.py > citi_audit.json

The three observational modules use the standard library. They do not change the existing six-layer engine or any verdict. The repository's full test workflow passed on Python 3.10, 3.11, and 3.12 before this extension; the updated workflow must be rechecked.

## Why this is not just sentiment analysis

- **Wording and response ledger:** Seven sourced excerpts capture repeated employee-solidarity language alongside concrete post-event announcements: counseling, workplace flexibility, a memorial fund and individual outreach. Cross-author wording is a recurrence, not evidence of coordination.
- **Incident sequence:** The initial armed threat reached a contracted law firm around 9 a.m.; Citi's exact receipt time is unconfirmed. Citi notified Hillsborough deputies shortly before noon. The attacker breached the gate at 12:10 p.m. and began firing at 12:11 p.m. A security officer stopped the attacker after shots began.
- **Causal comparison:** The observed perimeter breach is distinct from the unknown design standard. The reported security-posture change is distinct from proof that protective measures activated before the breach. A courtyard occupied at lunchtime is not, alone, evidence that a warning was never sent.
- **No guilt by omission:** An individual condolence post is not expected to publish a security postmortem. The missing **institutional causal account across reviewed materials** is the research question; a missing document in this search set is not proof that it doesn't exist.
- **Origin de-duplication:** Multiple articles quoting the same sheriff briefing or executive remark share one underlying reporting origin.


## Response substitution: memorial versus mechanism

**Question, not verdict:** Does repeated emphasis on individual courage, community solidarity and institutional virtue shift the audience's attention from the organization's decisions **before** the attacker reached employees to people's actions **after** the shooting began?

LeAnne's life deserves memorialization, and Fraley's intervention deserves recognition. Those are real and separate from questions about preventive control effectiveness. The observed **framing** can nevertheless be compared with the documented exposure and open questions. This is not a claim that condolences themselves are deceptive or that employees were responsible for preventing the attack.

The `framing_comparison` output makes this distinction explicit:

1. **Response foregrounding observed:** The statement excerpt contains recognition of security, directives for coworkers to look after one another, or claims of institutional virtue; the exact source and text cue travel with the observation.
2. **Unresolved preventive-control questions:** Independently sourced gaps remain about initial Citi notification, internal escalation, employee warning, and pre-breach security-posture activation. The perimeter breach itself is documented, but its design obligation remains unknown.
3. **Responsibility/attention hypothesis:** When celebratory response framing coexists with unanswered institutional-control questions, *response substitution* is a candidate effect for further investigation, **not an elevated finding or proven audience effect**.
4. **Counterevidence:** Statements describing real accommodations or committing financial resources remain visible; statements expressly addressing pre-attack prevention are recognized rather than coded as one-way deflection.
5. **Validation:** Assess complete originals, sequence of public communications, relevant media/audience responses, and actual security records before claiming messaging displaced public attention, concealed facts, or sought to protect the institution.

The hypothesis is **not** that an executive tribute was obliged to be a security postmortem. It is that the **organization-wide communication record**, combined with the absence of a verified causal account in the materials reviewed, merits examination for what it leads readers to consider and what remains unaddressed. A missing public record cannot establish internal nonaction.

**No audience-attention measurements, motive findings, negligence findings or causal verdicts have been generated.**

## Seven control questions

| Gate | Public evidence status | Records needed |
|---|---|---|
| First Citi threat intake/classification | Unresolved | Law-firm contact record and Citi incident creation/severity logs |
| Internal campus escalation/decision authority | Unresolved | Escalation and protective-action decision timestamps |
| Pre-breach employee warning or shelter | Unresolved | PA, SMS, mass notification and delivery logs |
| Perimeter vehicle intrusion | Gate breached; design requirements unresolved | Site assessment, barrier ratings/design basis and inspections |
| Security-posture activation before breach | Unresolved | Security-posture checklist, guard and dispatch logs |
| Armed intervention once shooting started | Reported by sheriff | Independent response reconstruction and after-action record |
| Post-event support | Announcements/reported accommodations | Counseling delivery and workplace-return records |

**Causal attribution is not determined.** The attacker is responsible for the intentional shooting; the institution's pre-attack performance requires separate evidence. No finding here establishes a failure to follow a specific Citi policy, a deliberate failure to warn, a rejected cost-based security upgrade, coordination of executive messaging, or intentional omission.

The roughly three hours from a threat *to a law firm* to the breach do not establish a three-hour window of Citi knowledge. The exact notification chain matters.

## Sources

- [Hillsborough County Sheriff's Office — November 5, release 26-186](https://www.teamhcso.com/News/PressRelease/484cefde-4e2b-4566-a12e-751d0cba3d1e/es-US): primary account of threat, deputy notification, breach, death and intervention.
- [FOX 13 — November 5 incident timeline](https://www.fox13news.com/news/citibank-center-tampa-shooting-timeline-what-happened-minute-minute): sheriff-attributed detail, not an independently originated timeline.
- [Tampa Bay 28 — sheriff and Citi remarks](https://www.tampabay28.com/news/region-hillsborough/shooting-at-citibank-corporate-campus-sparked-by-2-500-debt-threat-made-hours-before-gunfire-sheriff-says): collection-law-firm contact and employee-return reporting.
- [ABC News — Ed Skyler's response](https://abcnews.com/US/suspect-deadly-citibank-shooting-irate-court-summons-2500/story?id=137888575): executive report of changes in security posture as the attack began.
- [FOX 13 — further executive response reporting](https://www.fox13news.com/news/citibank-shooting-new-details-emerge-law-enforcement-response): same Skyler remarks, not independent corroboration.
- [FOX-reproduced memo from Jane Fraser](https://www.fox5ny.com/news/heavy-law-enforcement-presence-outside-brandon-citibank-triggers-traffic-alert): post-event employee communication.
- [Official Citi LinkedIn company feed](https://sj.linkedin.com/company/citi): memorial and announced performing-arts contribution.
- User-provided cropped LinkedIn screenshot of former site executive: original post URL and full contents not independently authenticated.

The case data contains **short excerpts and paraphrases**, not complete copyrighted articles, full social-media posts or redistributed screenshots. Researchers should verify every source, publication date and quotation against its original before public accusations.

## Integrity controls

The corporate wording adapter reports observed fragments and deduplicated announcements; it never promotes them as findings. The incident adapter reports evidence categories and unanswered questions; it does not transform missing documentation into verified nonaction. The framing comparator combines those two ledgers to surface a hypothesis about attention shifts without asserting that a shift occurred.

Negative tests establish that ordinary condolences remain unflagged, repeated expressions of support are not labeled coordinated, multiple announcements of one gift do not create multiple actions, screenshot excerpts cannot prove omissions, the results are deterministic, heroism does not erase unresolved preventive-control questions, ordinary tributes remain unflagged, prevention-aware statements are treated as counterexamples, and the framing output never upgrades to a motive or causal verdict.
