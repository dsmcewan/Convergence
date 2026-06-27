# Coparenting-dynamics corpora — design and grounding

Five synthetic 3-year coparenting records (`data/dyn_*.json`), one per dynamic type
along the validated spectrum **cooperative → parallel → conflicted → high-conflict →
coercive-controlling**. They are produced at **comparable density (~288 messages
each; ~1,480 total)** by a deterministic, seeded generator (`tools/generate_dynamics.py`)
that lays a 3-year calendar of real-life events — holidays, birthdays, school terms,
sports, illness, discipline incidents, family gatherings, routine handoffs — and
renders each in the register of each type. The coercive corpus additionally injects
fixed anchors (the two coercion-grammar envelopes plus the calibrated tactic beats),
so volume rises without disturbing the engine's discrimination. Each is anchored to a named type and framework so the corpus
maps to the literature, not caricature, and each varies the *validated dimensions*
(frequency, conflict, support/undermining, triangulation, accountability/repair) as
**independent knobs** — not a single warmth dial.

> **Synthetic only.** Fictional parents and children; no real records. The names
> differ per corpus precisely so they cannot be read as the same people.

## The five corpora

| Corpus | Type / framework anchor | Parents (child) | Freq | Conflict | Support / undermining | Triangulation | Repair | 3-yr trajectory |
|---|---|---|---|---|---|---|---|---|
| `dyn_cooperative` | Cooperative — Maccoby & Mnookin "cooperative"; Ahrons "Cooperative Colleagues" | Dana & Chris (Noah) | high | low | high support | none | present | settles early, absorbs triggers |
| `dyn_parallel` | Parallel / disengaged — M&M "disengaged" (largest group); Stahl parallel-parenting | Priya & Tom (Mia) | low | low | neutral (low both) | none | n/a | flat, stable, app-confined |
| `dyn_conflicted` | Conflicted / mixed — M&M "conflicted"; Ahrons "Angry Associates" | Beth & Greg (Lily) | moderate | moderate, intermittent | undermining present | intermittent (leading indicator) | inconsistent | flares & recovers, drifts toward parallel |
| `dyn_high_conflict` | High-conflict — Ahrons "Fiery Foes"; Johnston & Campbell impasse | Mark & Lauren (Ethan) | high | high, chronic | mutual undermining | routine | absent | persists/cycles, no settling — **bilateral** |
| `dyn_coercive` | Coercive control — Kelly & Johnson CCV; Stark; Bancroft & Silverman | Rosa (target) & Victor (controller) (Sofia) | strategically variable | asymmetric | unilateral undermining | via child + surveillance | absent / tactical | does not settle; volatile; re-spikes at autonomy/litigation — **unilateral** |

## The centerpiece: high-conflict vs. coercive control

Per Kelly & Johnson (2008) and Stark (2007), the distinction that matters is **not
"more conflict"** but **asymmetry**: high-conflict is bilateral (both initiate,
escalate, recover); coercive control is unilateral (one party manufactures conflict
and deploys DARVO / surveillance / paper abuse while the other defends). The two can
share vocabulary and differ only by *who initiates, who escalates, who de-escalates,
and whether fear/control is unidirectional* — so the corpora are built to be
distinguishable by **structure, not word choice**.

The engine demonstrates exactly this (`demo.py --corpus dynamics`): the
coercion-grammar envelope (`1 Action → [(2⇄3)⇄(4⇄5)]^n → 6 fait accompli`, by **one**
actor) completes **only** for the coercive corpus:

```
  type            msgs  stage-hits  complete-envelopes
  cooperative       16           1                   0
  parallel          18           0                   0
  conflicted        20           1                   0
  high_conflict     22           3                   0   <- hot, but bilateral: no envelope
  coercive          32          15                   2   <- COERCIVE CONTROL
```

high-conflict registers stage *activity* (it is hostile) yet completes **zero**
envelopes; coercive completes two — the 2023 unilateral preschool enrollment and the
2025 relocation/summer fait accompli. The discriminator is the *shape*, not the heat.

## What each corpus encodes (design notes)

- **Cooperative** — joint decisions ("let's enroll him together"), unsolicited
  flexibility ("even though it's mine"), specific complaints not character attacks,
  child never a messenger. SCV/no-violence that settles.
- **Parallel** — bare logistics ("Pickup Friday 5pm." / "Confirmed."), low affect
  *and* low hostility, decisions made independently, conflict avoided by minimizing
  the contact surface — the realistic settling endpoint for families that can't
  cooperate (the Beckmeyer "individual parenting buffers" case).
- **Conflicted** — civil stretches punctuated by flares; criticism ("you always…")
  with *inconsistent but present* repair; triangulation as a **leading indicator**
  (Petren et al. 2020 — covert conflict at T1 precedes overt); drifts back toward
  parallel by year 3.
- **High-conflict** — all four Gottman horsemen, **mutual**: both use contempt, both
  threaten court, both stonewall; no repair; no settling. Stage hits appear on both
  sides, but no single actor runs the action→war→fait-accompli envelope.
- **Coercive** (fictional matter: *Sun Tzu v. Machiavelli*) — the Lux & Gill /
  Bancroft tactic set, channel-matched: love-bombing open; surveillance-through-child
  ("Sofia said you dropped her… who were you with?"); **gaslighting** ("that never
  happened, you're remembering it wrong") and the mental-health attack; **false
  safety / substance allegations** ("wine bottles at your place… documenting safety
  concerns"); **letter-of-rules** for her while flouting it; **DARVO written past the
  target to the GAL/court audience**; **litigation / paper abuse** ("filing a motion
  to modify… my attorney has everything documented"); **retaliation** after she sets
  a boundary (access-gatekeeping — "Sofia is staying with me, she doesn't want to go");
  **therapeutic triangulation**, **financial control**, and a **communication-harassment
  burst** (three messages in hours, then weaponized silence); the evidence-aware
  writing/phone split; the target's **grey-rock/BIFF** replies; and escalating
  **rigidity + court-order reliance** over time. Two complete envelopes encode the
  **fait accompli sets the status quo** mechanic.

## Calibration to real aggregate structure

The coercive corpus's *distributions* (not its content) are calibrated against the
aggregate structure of a real coercive-control case database, read **read-only,
aggregates only — no message text, names, or dates were read or copied.** What was
drawn from the aggregates:

| Signal | Real aggregate | How the synthetic corpus reflects it |
|---|---|---|
| Tactic mix | `behavior_taxonomy`: coercive_control > alienation > contempt; top-severity behaviors = False Safety Allegations, Third-Party Weaponization, Child as Messenger, Unilateral Medical/Education, Access Gatekeeping, Communication Harassment, Therapeutic Triangulation, Control Masked as Civility | every one of those behaviors now appears, weighted toward coercive-control |
| Campaign types | `detected_campaigns`: schedule and **allegation** dominate (then comms, therapy, financial) | schedule + education *envelopes* plus an **allegation** (false-safety) campaign, a comms-harassment burst, therapy and financial beats |
| Campaign size | message_count median ~4, max 21 | tactic bursts kept short (3–9 messages), not sprawls |
| Escalation cadence | `escalation_pairs`: median ~19h between escalating messages (≤48h); mostly EXTREME/RAPID | war-burst messages spaced hours–2 days apart, not weeks; a same-day 3-message flood |
| Volatility | `consolidated_timeline`: events spike sharply in the peak year | routine baseline runs throughout; the anchored campaigns (envelopes, allegations, retaliation, litigation) cluster as bursts, with a calm beat amid escalation |
| Grammar shape | `bcla_steps` 7-step sequence (select end → choose leverage domain → facially-reasonable tactic → civility as optics shield → narrow choices → **convert resistance into documentation** → preserve appearance of cooperation) | validates the engine's coercion grammar; step 6 = the documentation war, steps 4+7 = the performative for-the-record bookends |

The label set comes from the real taxonomy; **every word, name, and date in the
corpus is fictional** (the matter caption *Sun Tzu v. Machiavelli* is itself a tell
that no real case is depicted). This keeps the demo's synthetic-only guarantee while
making the coercive surface ring true.

## Decision rules used to label the corpora

From the references (Kelly & Johnson 2008; Hardesty et al. 2017/2023):

1. Escalation **mutual and recovers** → high-conflict; **unilateral, fear-inducing,
   child/court as leverage, no genuine repair** → coercive control.
2. Conflict **declines and stabilizes by ~18–24 months** → cooperative/parallel;
   **stays elevated and volatile** → high-conflict/coercive.
3. Contact **minimal but civil, decisions independent** → parallel (not cooperative).
4. CCV is classified by **dominance/frequency** (PMWI Dominance–Isolation logic), not
   the severity of any single incident or a body-count of tactics.

## Caveats (carried from the literature)

- **Asymmetric error.** If these ever train/test a classifier, design against the
  **CCV→SCV false negative** — labeling coercive control as mere situational conflict
  is the documented "dangerous misuse" direction (Hardesty et al. 2023).
- **Type ≠ child outcome.** The coparenting *type* is a category of the inter-adult
  relationship, not a deterministic predictor of child adjustment (Beckmeyer et al.
  2014 found the direct link weak). Child-harm here is encoded as **mechanism**
  (triangulation, the child as instrument/informant), not as a label.
- **Prototypes, not boxes.** The conflicted corpus deliberately *drifts* toward
  parallel; real records mix and move along the spectrum.
- **Gender-neutral by construction.** The controller/target roles are not tied to a
  gender; sample-dependent gender patterns in the literature are not encoded.
- **Communication patterns, not clinical verdicts.** The corpora represent observable
  message structure; they do not adjudicate contested forensic constructs
  (parental-alienation, etc.).

## Sources

Maccoby & Mnookin (1992) *Dividing the Child*; Ahrons (1994) *The Good Divorce*;
Feinberg (2003); McHale; Kelly & Johnson (2008) *Family Court Review* 46(3); Stark
(2007) *Coercive Control*; Bancroft & Silverman (2002) *The Batterer as Parent*;
Miller & Smolter (2011) "paper abuse"; Freyd (1997) DARVO; Harsey & Freyd (2020);
Beckmeyer, Coleman & Ganong (2014) *Family Relations*; Reim et al. (2024); Petren et
al. (2020); Hardesty et al. (2017) *J. Family Psychology* 31(7); Hardesty, Ogolsky &
Akinbode (2023) *Family Court Review*; Lux & Gill (2021); Markwick et al. (2019);
Dragiewicz et al. (2018). See the two reference addenda for full citations and URLs.
