const state = {
  index: null,
  corpus: null,
  dynamics: null,
  selectedCorpus: "contractor",
  activeFindingIndex: 0,
  activeSlideIndex: 0,
  slides: [],
  voice: "blanc",
  localApi: false
};

const LAYER_LABELS = {
  L1: "borrowed authority",
  L2: "record cut",
  L3: "external contradiction",
  L4: "domain convergence",
  L5: "register shift",
  L6: "cross-channel split"
};

const FRAGMENT_RULES = [
  { pattern: /let'?s/ig, label: "soft entry", tone: "entry", purpose: "make the ask sound casual instead of consequential" },
  { pattern: /not get into/ig, label: "defer the terms", tone: "deferral", purpose: "move past the condition that would limit the later denial" },
  { pattern: /cost/ig, label: "money anchor", tone: "resource", purpose: "name the contested resource while refusing to settle it" },
  { pattern: /invoice|quote|original quote|higher than the quote/ig, label: "price frame", tone: "resource", purpose: "move the disagreement onto what should be paid" },
  { pattern: /right now/ig, label: "temporal dodge", tone: "time", purpose: "postpone clarity until after the action begins" },
  { pattern: /can you just/ig, label: "pressure minimizer", tone: "pressure", purpose: "make the requested commitment feel smaller than it is" },
  { pattern: /start it/ig, label: "action extraction", tone: "action", purpose: "convert ambiguity into work already underway" },
  { pattern: /never/ig, label: "absolute denial", tone: "denial", purpose: "turn the earlier ambiguity into a clean rejection" },
  { pattern: /agreed/ig, label: "consent term", tone: "consent", purpose: "move the fight onto whether permission existed" },
  { pattern: /ok, you can swap/ig, label: "permission granted", tone: "consent", purpose: "create the reliance the later denial will attack" },
  { pattern: /this weekend for next/ig, label: "specific exchange", tone: "resource", purpose: "make the weekend trade concrete enough to rely on" },
  { pattern: /that works/ig, label: "reliance cue", tone: "action", purpose: "close the permission loop as settled" },
  { pattern: /thanks|appreciate it/ig, label: "reliance receipt", tone: "consent", purpose: "show the other person treated the permission as settled" },
  { pattern: /full-width|hero|scope change|adds about 3 hours|change order/ig, label: "scope boundary", tone: "resource", purpose: "mark the work boundary the later dispute depends on" },
  { pattern: /policy says|lawyer says|pediatrician says|attorney says|accountant says/ig, label: "borrowed authority", tone: "authority", purpose: "make a personal position sound externally required" },
  { pattern: /attached that thread|you did on the 3rd|fully informed|not authorizing|send me the accountant'?s basis|check last week|you said ok/ig, label: "record pressure", tone: "record", purpose: "anchor the claim against a second record" },
  { pattern: /extra hours|revisions are included|swap weekends|swap this weekend|travel this weekend|current arrangement|every appointment|dentist|weekend/ig, label: "dispute object", tone: "resource", purpose: "name the contested resource the pattern is trying to control" },
  { pattern: /always kept you fully informed|withheld|not authorizing the swap|i won'?t be approving|i'?m keeping her/ig, label: "control move", tone: "split", purpose: "present control as recordkeeping or necessity" }
];

const PATTERN_MIN_UNIQUE_RECORDS = 4;

const $ = (id) => document.getElementById(id);

document.addEventListener("DOMContentLoaded", init);

async function init() {
  state.localApi = await probeApi();
  state.index = await loadJson(state.localApi ? "/api/index" : "data/index.json");
  state.selectedCorpus = state.index.default_corpus || "contractor";
  state.dynamics = await loadJson(state.localApi ? "/api/dynamics" : "data/dynamics.json");
  renderTabs();
  bindControls();
  bindChat();
  await selectCorpus(state.selectedCorpus);
}

async function probeApi() {
  try {
    const response = await fetch("/api/health", { cache: "no-store" });
    return response.ok;
  } catch {
    return false;
  }
}

async function loadJson(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error(`Could not load ${url}`);
  return response.json();
}

function renderTabs() {
  const tabs = $("corpus-tabs");
  tabs.setAttribute("role", "tablist");
  tabs.setAttribute("aria-label", "communication record");
  tabs.innerHTML = "";
  state.index.corpora.forEach((corpus) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = corpus.label;
    button.dataset.corpus = corpus.name;
    const active = corpus.name === state.selectedCorpus;
    button.className = active ? "is-active" : "";
    button.setAttribute("role", "tab");
    button.setAttribute("aria-selected", String(active));
    button.setAttribute("aria-pressed", String(active));
    button.addEventListener("click", () => selectCorpus(corpus.name));
    tabs.append(button);
  });
}

async function selectCorpus(name) {
  state.selectedCorpus = name;
  document.querySelectorAll("[data-corpus]").forEach((button) => {
    const active = button.dataset.corpus === name;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-selected", String(active));
    button.setAttribute("aria-pressed", String(active));
  });
  const url = state.localApi ? `/api/corpus/${encodeURIComponent(name)}` : `data/${name}.json`;
  state.corpus = await loadJson(url);
  state.activeFindingIndex = firstElevatedIndex();
  state.activeSlideIndex = 0;
  state.slides = buildSlides(activeFinding());
  renderSlide();
  showToast(`${state.corpus.corpus.label} loaded into Blanc lecture mode.`);
}

function firstElevatedIndex() {
  const index = state.corpus.findings.findIndex((finding) => finding.confidence === "elevated");
  return index >= 0 ? index : 0;
}

function activeFinding() {
  return state.corpus.findings[state.activeFindingIndex] || state.corpus.findings[0];
}

function activeSlide() {
  return state.slides[state.activeSlideIndex] || state.slides[0];
}

function buildSlides(finding) {
  const messages = finding.messages.length ? finding.messages : [];
  const firstTwo = messages.slice(0, 2);
  const patterns = relatedPatterns(finding);
  const campaigns = relatedCampaigns(finding);
  return [
    ...firstTwo.map((message, index) => ({ type: "message", message, ordinal: index + 1 })),
    { type: "behavior", finding },
    { type: "pattern", finding, pattern: patterns[0] },
    { type: "campaign", finding, campaign: campaigns[0] },
    { type: "phase", finding },
    { type: "review", finding },
    { type: "dynamics" },
    { type: "scorecard" }
  ];
}

function renderSlide() {
  const slide = activeSlide();
  const finding = activeFinding();
  const isReview = slide.type === "review";
  document.querySelector(".demo-frame").classList.toggle("is-review-slide", isReview);
  $("slide-stage").innerHTML = slideMarkup(slide, finding);
  $("review-title").textContent = titleForSlide(slide, finding);
  $("panel-mode").textContent = isReview ? "interactive review" : "Blanc lecture";
  $("review-body").innerHTML = isReview ? reviewMarkup(finding) : lectureMarkup(slide, finding);
  $("chat-form").classList.toggle("is-available", isReview);
  $("chat-answer").classList.toggle("is-available", isReview);
  renderProgress();
  bindMessageSlideInteractions();
  updateNavState();
}

function renderProgress() {
  $("slide-progress").innerHTML = state.slides.map((slide, index) => `
    <button type="button" class="${index === state.activeSlideIndex ? "is-active" : ""}" data-slide="${index}" aria-label="go to ${escapeHtml(slide.type)} slide">
      <span>${String(index + 1).padStart(2, "0")}</span>
      <strong>${escapeHtml(progressLabel(slide))}</strong>
    </button>
  `).join("");
  $("slide-progress").querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      state.activeSlideIndex = Number(button.dataset.slide);
      renderSlide();
    });
  });
}

function progressLabel(slide) {
  if (slide.type === "message") return `fragment ${slide.ordinal}`;
  return slide.type;
}

function slideMarkup(slide, finding) {
  if (slide.type === "message") return messageSlideMarkup(slide, finding);
  if (slide.type === "behavior") return behaviorSlideMarkup(finding);
  if (slide.type === "pattern") return patternSlideMarkup(slide.pattern);
  if (slide.type === "campaign") return campaignSlideMarkup(slide.campaign);
  if (slide.type === "phase") return phaseSlideMarkup(finding);
  if (slide.type === "dynamics") return dynamicsSlideMarkup();
  if (slide.type === "scorecard") return scorecardSlideMarkup();
  return reviewSlideMarkup(finding);
}

function messageSlideMarkup(slide, finding) {
  const specimen = specimenForSlide(slide, finding);
  const fragments = fragmentsForText(specimen.body);
  return `
    <article class="lecture-slide message-slide">
      <div class="slide-label">slide ${slide.ordinal} / phrase fragments</div>
      <div class="message-canvas">
        <div class="message-tabs" aria-label="message slide panels">
          <button type="button" class="is-active" data-message-tab="message">message</button>
          <button type="button" data-message-tab="signals">engine signals</button>
        </div>
        <div class="message-panel is-active" data-message-panel="message">
          <div class="fragment-purpose-list" aria-label="fragment purpose cards">
            <div class="fragment-hover-prompt">Hover or tab through a highlighted phrase.</div>
            ${fragments.map((fragment, index) => `
              <button type="button" class="purpose-chip tone-${escapeHtml(fragment.tone)}" data-fragment-id="${escapeHtml(fragment.id)}" style="--d:${index * 95}ms">
                <strong>${escapeHtml(fragment.label)}</strong>
                <span>${escapeHtml(fragment.purpose)}</span>
              </button>
            `).join("") || `<div class="purpose-chip is-active"><strong>context fragment</strong><span>This message is included because it sits inside the corroborated sequence.</span></div>`}
          </div>
          <div class="message-card">
            <span>${escapeHtml(specimen.label)}</span>
            <p>${highlightMessage(specimen.body, fragments)}</p>
            ${translationMarkup(fragments, finding)}
          </div>
        </div>
        <div class="message-panel signal-panel" data-message-panel="signals">
          ${signalPanelMarkup(finding)}
        </div>
      </div>
      <div class="outcome-strip">
        <span>method</span>
        <strong>${escapeHtml(outcomeMethodForFinding(finding))}</strong>
        <p>${escapeHtml(outcomeForFinding(finding))}</p>
      </div>
    </article>
  `;
}

function translationMarkup(fragments, finding) {
  if (!fragments.length) return "";
  const translation = translationSegmentsForFinding(finding, fragments);
  return `
    <div class="message-translation" aria-label="translated message intent">
      <span>what it's actually doing</span>
      <p>${translation.map((part) => `
        <mark tabindex="0" class="translation-part tone-${escapeHtml(part.tone)} ${escapeHtml(part.position)}" data-fragment-id="${escapeHtml(part.fragmentId)}" title="${escapeHtml(part.source)}">${escapeHtml(part.text)}</mark>
      `).join(" ")}</p>
    </div>
  `;
}

function translationSegmentsForFinding(finding, fragments) {
  if (isWeekendSwapDenial(finding)) {
    return [
      translationPart("Not only refusing the weekend,", findFragment(fragments, ["dispute object", "absolute denial"])),
      translationPart("but making you wrong", findFragment(fragments, ["absolute denial", "consent term"])),
      translationPart("for counting on", findFragment(fragments, ["reliance cue", "permission granted"])),
      translationPart("what they said would happen.", findFragment(fragments, ["permission granted", "specific exchange"]))
    ];
  }

  const body = findingBody(finding);
  const use = (text, labels) => translationPart(text, findFragment(fragments, labels));

  if (body.includes("let's not get into cost") && body.includes("never agreed to extra hours")) {
    return [
      use("It gets the work started before the cost is settled,", ["action extraction", "pressure minimizer"]),
      use("then treats the extra work", ["dispute object", "price frame"]),
      use("as something that was never agreed to.", ["absolute denial", "consent term"])
    ];
  }

  if (body.includes("billing policy says revisions are included")) {
    return [
      use("It turns a billing dispute into policy,", ["borrowed authority"]),
      use("so refusing extra hours", ["control move", "dispute object"]),
      use("sounds required instead of chosen.", ["borrowed authority", "price frame"])
    ];
  }

  if (body.includes("you did on the 3rd") || body.includes("attached that thread")) {
    return [
      use("It pulls the earlier ask back into view,", ["record pressure"]),
      use("making the denial answer the record", ["record pressure", "action extraction"]),
      use("instead of just the argument.", ["consent term", "dispute object"])
    ];
  }

  if (body.includes("pediatrician says")) {
    return [
      use("It turns a parenting choice into medical necessity,", ["borrowed authority"]),
      use("then uses that authority", ["borrowed authority"]),
      use("to keep the weekend.", ["control move", "dispute object"])
    ];
  }

  if (body.includes("custody order") || body.includes("not authorizing the swap")) {
    return [
      use("It moves the swap into legal language,", ["borrowed authority", "record pressure"]),
      use("so the refusal feels procedural", ["control move"]),
      use("instead of personal.", ["dispute object"])
    ];
  }

  if (body.includes("always kept you fully informed")) {
    return [
      use("It writes a clean public record,", ["control move", "record pressure"]),
      use("while the missing private channel", ["two-channel split", "dispute object"]),
      use("carries the contradiction.", ["record pressure"])
    ];
  }

  if (body.includes("lawyer says") || body.includes("attorney says") || body.includes("accountant says")) {
    return [
      use("It borrows an outside voice,", ["borrowed authority"]),
      use("so the speaker's preference", ["dispute object"]),
      use("sounds like someone else's rule.", ["borrowed authority"])
    ];
  }

  if (body.includes("scope change") || body.includes("change order") || body.includes("full-width")) {
    return [
      use("It names the work boundary,", ["scope boundary"]),
      use("so the later cost", ["price frame", "dispute object"]),
      use("has a record to stand on.", ["record pressure", "scope boundary"])
    ];
  }

  if (body.includes("why is it higher") || body.includes("original quote")) {
    return [
      use("It frames the added cost as a surprise,", ["price frame"]),
      use("pulling attention away", ["temporal dodge", "record pressure"]),
      use("from the earlier change.", ["scope boundary"])
    ];
  }

  if (body.includes("can we swap") || body.includes("you agreed") || body.includes("you said ok") || body.includes("you take this weekend")) {
    return [
      use("It treats the swap as settled,", ["consent term", "permission granted"]),
      use("then points back", ["record pressure"]),
      use("to the moment it was relied on.", ["reliance cue", "specific exchange"])
    ];
  }

  if (body.includes("thanks") || body.includes("appreciate it")) {
    return [
      use("It reads like closure,", ["reliance receipt"]),
      use("because the permission has been treated as settled.", ["reliance cue", "permission granted"])
    ];
  }

  return fallbackTranslationSegments(finding, fragments);
}

function fallbackTranslationSegments(finding, fragments) {
  if (!fragments.length) return [];
  const use = (text, labels) => translationPart(text, findFragment(fragments, labels));
  if (finding.confidence === "low") {
    return [
      use("It carries a signal,", [fragments[0].label]),
      use("but the record has not corroborated it yet.", [fragments.at(-1).label])
    ];
  }
  return fragments.slice(0, 3).map((fragment) => translationPart(translationForFragment(fragment), fragment));
}

function translationPart(text, fragment, position = "") {
  return {
    text,
    fragmentId: fragment?.id || "fragment-0",
    position,
    tone: fragment?.tone || "entry",
    source: fragment?.text || text
  };
}

function findFragment(fragments, labels) {
  return labels.map((label) => fragments.find((fragment) => fragment.label === label)).find(Boolean) || fragments[0];
}

function isWeekendSwapDenial(finding) {
  const body = findingBody(finding);
  return body.includes("ok, you can swap this weekend for next") && body.includes("never agreed to swap weekends");
}

function findingBody(finding) {
  return finding.messages.map((message) => message.body).join(" ").toLowerCase();
}

function translationForFragment(fragment) {
  const map = {
    "soft entry": "lower the stakes",
    "defer the terms": "leave the limit undefined",
    "money anchor": "keep the cost boundary open",
    "temporal dodge": "delay clarity",
    "pressure minimizer": "make the ask feel small",
    "action extraction": "get the action started",
    "absolute denial": "erase the earlier permission",
    "consent term": "move the fight to agreement",
    "dispute object": "aim it at the extra work",
    "permission granted": "create reliance",
    "specific exchange": "make the trade concrete",
    "reliance cue": "make it safe to count on",
    "reliance receipt": "treat it as settled",
    "borrowed authority": "make preference sound required",
    "record pressure": "pin the claim to another record",
    "two-channel split": "separate the record from the conduct"
  };
  return map[fragment.label] || fragment.purpose;
}

function signalPanelMarkup(finding) {
  return `
    <div class="signal-board">
      ${finding.signals.map((signal, index) => `
        <article class="signal-card layer-${escapeHtml(signal.layer)}" style="--d:${index * 95}ms">
          <span>${escapeHtml(signal.layer)} / ${escapeHtml(LAYER_LABELS[signal.layer] || "signal")}</span>
          <strong>${escapeHtml(signal.kind)}</strong>
          <p>${escapeHtml(signal.detail)}</p>
          <small>seqs ${escapeHtml(signal.seqs.join(", "))}</small>
        </article>
      `).join("")}
    </div>
  `;
}

function behaviorSlideMarkup(finding) {
  const behavior = behaviorPatternForFinding(finding);
  const steps = behaviorStepsForFinding(finding);
  return `
    <article class="lecture-slide synthesis-slide">
      <div class="slide-label">behavior / what the fragments do</div>
      <h2>${escapeHtml(behavior.title)}</h2>
      <p class="behavior-summary">${escapeHtml(behavior.summary)}</p>
      <div class="behavior-flow" aria-label="behavior escalation path">
        ${steps.map((step, index) => `
          <article class="behavior-node intensity-${index}" tabindex="0" style="--d:${index * 120}ms">
            <span>${escapeHtml(step.stage)}</span>
            <strong>${escapeHtml(step.label)}</strong>
            <p>${escapeHtml(step.detail)}</p>
            <div class="behavior-source" aria-label="source fragments for ${escapeHtml(step.label)}">
              ${step.sources.map((source) => `
                <div class="source-fragment">
                  <small>${escapeHtml(source.date)} / ${escapeHtml(source.sender)}</small>
                  <p>${highlightMessage(source.body, fragmentsForText(source.body))}</p>
                </div>
              `).join("")}
            </div>
          </article>
          ${index < steps.length - 1 ? `<span class="behavior-arrow" aria-hidden="true">-></span>` : ""}
        `).join("")}
      </div>
    </article>
  `;
}

function behaviorStepsForFinding(finding) {
  const signals = compressedSignals(finding);
  const usedSeqs = new Set();
  const steps = signals.map((signal) => {
    const sources = behaviorSourcesForSignal(signal, finding, usedSeqs);
    sources.forEach((source) => usedSeqs.add(source.seq));
    return {
      label: behaviorLabelForSignal(signal),
      detail: behaviorDetailForSignal(signal),
      sources
    };
  }).filter((step) => step.sources.length);
  return steps.map((step, index) => ({
    ...step,
    stage: behaviorStage(index, steps.length)
  }));
}

function compressedSignals(finding) {
  const seen = new Set();
  const priority = {
    claim_contradicted: 1,
    cross_channel_divergence: 1,
    within_thread_omission: 2,
    borrow_authority: 2,
    register_anomaly: 3,
    domain_convergence: 4
  };
  return finding.signals
    .slice()
    .sort((a, b) => (priority[a.kind] || 9) - (priority[b.kind] || 9))
    .filter((signal) => {
      const key = signal.kind;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
}

function behaviorStage(index, total) {
  if (index === 0) return "subtle";
  if (index === total - 1) return "normalized";
  return index === 1 && total > 3 ? "behavior" : "brazen";
}

function behaviorSourcesForSignal(signal, finding, usedSeqs = new Set()) {
  const seqs = new Set(signal.seqs || []);
  const chronological = finding.messages
    .slice()
    .sort((a, b) => String(a.timestamp || "").localeCompare(String(b.timestamp || "")) || a.seq - b.seq);
  let messages = chronological.filter((message) => seqs.has(message.seq) && !usedSeqs.has(message.seq));
  if (!messages.length) {
    messages = chronological.filter((message) => !usedSeqs.has(message.seq)).slice(0, 1);
  } else {
    messages = messages.slice(0, 1);
  }
  return messages.map((message) => ({
    seq: message.seq,
    date: formatMessageDate(message.timestamp),
    sender: message.sender || "Unknown",
    body: message.body
  }));
}

function behaviorPatternForFinding(finding) {
  const body = findingBody(finding);
  if (finding.layers.includes("L3")) {
    return {
      title: "Permission becomes denial",
      summary: "The record first creates reliance, then the later message tries to make that reliance look invented."
    };
  }
  if (finding.layers.includes("L6")) {
    return {
      title: "Clean record, dirty channel",
      summary: "The visible message claims orderly disclosure while another channel carries what the record leaves out."
    };
  }
  if (body.includes("pediatrician says") || body.includes("lawyer says") || body.includes("attorney says") || body.includes("accountant says")) {
    return {
      title: "Preference wears a borrowed badge",
      summary: "The sender moves their own position into someone else's mouth so resistance sounds unreasonable."
    };
  }
  if (body.includes("billing policy says") || body.includes("custody order")) {
    return {
      title: "Choice gets dressed as procedure",
      summary: "The refusal is framed as policy or order, not as a decision the sender is making."
    };
  }
  if (finding.layers.includes("L2")) {
    return {
      title: "The missing middle does the work",
      summary: "The shown message depends on context that the thread itself says should not be skipped."
    };
  }
  if (finding.confidence === "low") {
    return {
      title: "Signal held, not convicted",
      summary: "The phrase has pressure in it, but the system does not call a pattern until another layer backs it up."
    };
  }
  return {
    title: "Pressure moves through the record",
    summary: "The phrase is doing more than carrying information; it is trying to change what the other person can rely on."
  };
}

function behaviorLabelForSignal(signal) {
  const labels = {
    claim_contradicted: "Later claim hits earlier record",
    within_thread_omission: "Context gets skipped",
    domain_convergence: "Same target appears elsewhere",
    register_anomaly: "Voice changes under pressure",
    borrow_authority: "Outside authority is borrowed",
    cross_channel_divergence: "Channels tell different stories"
  };
  return labels[signal.kind] || signal.kind.replace(/_/g, " ");
}

function behaviorDetailForSignal(signal) {
  const details = {
    claim_contradicted: "A later message asks the reader to forget what the earlier record made available.",
    within_thread_omission: "The persuasive force depends on cutting around a relevant middle piece.",
    domain_convergence: "Different topics point back to the same contested object.",
    register_anomaly: "The speaker's voice stiffens when the record becomes useful.",
    borrow_authority: "A personal position is routed through a professional, policy, or legal voice.",
    cross_channel_divergence: "The public-facing version and the other channel cannot both be complete."
  };
  return details[signal.kind] || signal.detail;
}

function patternSlideMarkup(pattern) {
  const behaviors = patternBehaviorsForPattern(pattern);
  return `
    <article class="lecture-slide synthesis-slide">
      <div class="slide-label">pattern / repeated structure</div>
      <h2>${escapeHtml(patternTitle(pattern))}</h2>
      <p class="behavior-summary">${escapeHtml(patternSummary(pattern))}</p>
      ${behaviors.length ? `
        <div class="pattern-ladder" aria-label="pattern behaviors with source messages">
          ${behaviors.map((behavior, index) => `
            <article class="pattern-behavior intensity-${index}" tabindex="0" style="--d:${index * 120}ms">
              <span>${escapeHtml(behavior.date)} / ${escapeHtml(behavior.sender)}</span>
              <strong>${escapeHtml(behavior.label)}</strong>
              <p>${escapeHtml(behavior.detail)}</p>
              <div class="behavior-source" aria-label="source message for ${escapeHtml(behavior.label)}">
                <div class="source-fragment">
                  <small>${escapeHtml(behavior.date)} / ${escapeHtml(behavior.sender)}</small>
                  <p>${highlightMessage(behavior.body, fragmentsForText(behavior.body))}</p>
                </div>
              </div>
            </article>
            ${index < behaviors.length - 1 ? `<span class="behavior-arrow" aria-hidden="true">-></span>` : ""}
          `).join("")}
        </div>
      ` : ""}
    </article>
  `;
}

function patternBehaviorsForPattern(pattern) {
  if (!qualifiesAsPattern(pattern) || !state.corpus?.findings) return [];
  const allowed = new Set(pattern.seqs || []);
  const usedSeqs = new Set();
  return state.corpus.findings
    .flatMap((finding) => finding.messages.map((message) => ({ finding, message })))
    .filter(({ message }) => allowed.has(message.seq))
    .sort((a, b) => String(a.message.timestamp || "").localeCompare(String(b.message.timestamp || "")) || a.message.seq - b.message.seq)
    .filter(({ message }) => {
      if (usedSeqs.has(message.seq)) return false;
      usedSeqs.add(message.seq);
      return true;
    })
    .map(({ finding, message }) => ({
      date: formatMessageDate(message.timestamp),
      sender: message.sender || "Unknown",
      label: patternBehaviorLabel(pattern, finding, message),
      detail: patternBehaviorDetail(pattern, finding, message),
      body: message.body
    }));
}

function patternBehaviorLabel(pattern, finding, message) {
  const body = message.body.toLowerCase();
  if (pattern?.name === "sanitize-record") {
    if (body.includes("attached that thread") || body.includes("you did on the 3rd") || body.includes("check last week") || body.includes("you said ok")) return "Record gets reattached";
    if (body.includes("pursuant") || body.includes("custody order") || body.includes("lawyer says") || body.includes("not authorizing")) return "Authority shifts the terms";
    if (body.includes("policy says") || body.includes("revisions are included") || body.includes("won't be approving")) return "Terms get narrowed";
    if (body.includes("ok, you can swap") || body.includes("that works")) return "Permission gets recorded";
    if (body.includes("never")) return "Reliance gets denied";
    return "Reliance gets created";
  }
  if (pattern?.name?.startsWith("repeated:borrow_authority")) return "Authority is borrowed";
  if (pattern?.name?.startsWith("repeated:within_thread_omission")) return "Context gets skipped";
  return behaviorPatternForFinding(finding).title;
}

function patternBehaviorDetail(pattern, finding, message) {
  const body = message.body.toLowerCase();
  if (pattern?.name === "sanitize-record") {
    if (body.includes("attached that thread") || body.includes("you did on the 3rd") || body.includes("check last week") || body.includes("you said ok")) {
      return "The earlier message comes back as the anchor the denial has to answer.";
    }
    if (body.includes("pursuant") || body.includes("custody order") || body.includes("lawyer says") || body.includes("not authorizing")) {
      return "The refusal is moved into an official voice, so the changed position sounds required.";
    }
    if (body.includes("policy says") || body.includes("revisions are included") || body.includes("won't be approving")) {
      return "The boundary is reframed as policy, so the refusal can sound procedural.";
    }
    if (body.includes("ok, you can swap") || body.includes("that works")) {
      return "The permission is made concrete enough for the other person to rely on it.";
    }
    if (body.includes("never") || body.includes("not authorizing")) {
      return "The later message asks the reader to treat the earlier reliance as mistaken.";
    }
    return "The earlier message gives the other person something concrete to rely on.";
  }
  return behaviorPatternForFinding(finding).summary;
}

function patternTitle(pattern) {
  if (!qualifiesAsPattern(pattern)) return "Not a pattern yet";
  if (pattern.name === "sanitize-record") return "Sanitize the record";
  if (pattern.name === "two-faced") return "Two records, two faces";
  if (pattern.name?.startsWith("repeated:borrow_authority")) return "Borrow authority until it sounds normal";
  if (pattern.name?.startsWith("repeated:within_thread_omission")) return "Keep skipping the middle";
  return pattern.name.replace(/[-_:]/g, " ");
}

function patternSummary(pattern) {
  if (!qualifiesAsPattern(pattern)) return `A pattern needs more than three unique chronological uses. This is still behavior-level evidence, so the method holds it below pattern.`;
  if (pattern.name === "sanitize-record") return "Four chronological records repeat the same structure: create reliance, shift the terms through authority or procedure, then deny what the earlier record made countable.";
  if (pattern.kind === "recurrence") return "Separate behaviors repeat the same move until it starts to look like the normal way the conversation works.";
  if (pattern.name === "two-faced") return "The pattern forms when one channel performs clarity and another channel carries the missing conduct.";
  return "A pattern is the behavior repeating with enough structure that it stops looking accidental.";
}

function qualifiesAsPattern(pattern) {
  return new Set(pattern?.seqs || []).size >= PATTERN_MIN_UNIQUE_RECORDS;
}

function campaignSlideMarkup(campaign) {
  return `
    <article class="lecture-slide synthesis-slide">
      <div class="slide-label">campaign / sustained direction</div>
      <h2>${escapeHtml(campaign?.summary || "no sustained campaign in this slice")}</h2>
      <p>${escapeHtml(campaign ? campaign.span.join(" .. ") : "The method refuses to invent continuity where the record does not show it.")}</p>
    </article>
  `;
}

function phaseSlideMarkup(finding) {
  return `
    <article class="lecture-slide synthesis-slide phase-slide">
      <div class="slide-label">phase / the named shape</div>
      <h2>${escapeHtml(phaseLabel(finding))}</h2>
      <p>${escapeHtml(finding.narration[state.voice])}</p>
    </article>
  `;
}

function reviewSlideMarkup(finding) {
  return `
    <article class="lecture-slide review-unlock-slide">
      <div class="slide-label">final / review window unlocked</div>
      <h2>Now inspect the locked finding.</h2>
      <p>The lecture is complete. The chat panel is available because the evidence stack has already been built from fragments to phase.</p>
      <div class="unlock-grid">
        <span>${escapeHtml(finding.confidence)}</span>
        <strong>seqs ${escapeHtml(finding.seqs.join(", "))}</strong>
        <em>${escapeHtml(finding.layers.join(" / "))}</em>
      </div>
    </article>
  `;
}

const DYNAMICS_LABELS = {
  cooperative: "cooperative",
  parallel: "parallel",
  conflicted: "conflicted",
  high_conflict: "high-conflict",
  coercive: "coercive control"
};

function dynamicsSlideMarkup() {
  const rows = (state.dynamics && state.dynamics.rows) || [];
  const body = rows.map((row) => `
    <tr class="dynamics-row ${row.coercive ? "is-coercive" : ""}">
      <td>${escapeHtml(DYNAMICS_LABELS[row.name] || row.name)}</td>
      <td>${row.message_count}</td>
      <td>${row.stage_hits}</td>
      <td><strong>${row.complete_envelopes}</strong></td>
    </tr>
  `).join("");
  return `
    <article class="lecture-slide dynamics-slide">
      <div class="slide-label">discriminator / five relationship dynamics</div>
      <h2>The same engine, run across the spectrum.</h2>
      <p>Five synthetic corpora, cooperative to coercive. Hostile language fires
      stage-hits everywhere. Only a true coercion structure closes a complete
      envelope &mdash; the discriminator is the envelope count, not the noise.</p>
      <table class="dynamics-table">
        <thead>
          <tr><th>dynamic</th><th>messages</th><th>stage-hits</th><th>complete envelopes</th></tr>
        </thead>
        <tbody>${body}</tbody>
      </table>
    </article>
  `;
}

function scorecardSlideMarkup() {
  const scorecard = (state.dynamics && state.dynamics.scorecard) || {};
  const hardNegative = state.dynamics && state.dynamics.hard_negative;
  const metric = (label, value) => `
    <div class="scorecard-metric">
      <span>${label}</span>
      <strong>${value == null ? "&mdash;" : value.toFixed(2)}</strong>
    </div>
  `;
  const hardNegativeMarkup = hardNegative ? `
    <div class="hard-negative">
      <span>hard negative / ${escapeHtml(DYNAMICS_LABELS[hardNegative.name] || hardNegative.name)}</span>
      <p>${escapeHtml(hardNegative.summary)}</p>
    </div>
  ` : "";
  return `
    <article class="lecture-slide scorecard-slide">
      <div class="slide-label">scorecard / scored against ground truth</div>
      <h2>The verdict is measured, not asserted.</h2>
      <div class="scorecard-grid">
        ${metric("precision", scorecard.precision)}
        ${metric("recall", scorecard.recall)}
        ${metric("F1", scorecard.f1)}
        ${metric("specificity", scorecard.specificity)}
      </div>
      ${hardNegativeMarkup}
    </article>
  `;
}

function lectureMarkup(slide, finding) {
  if (slide.type === "dynamics") {
    return `<div class="lecture-note"><span>Blanc says</span><strong>One ugly corpus proves nothing.</strong><p>Run the identical engine across five dynamics. The high-conflict record screams and never closes an envelope. The coercive one barely whispers and does.</p></div>`;
  }
  if (slide.type === "scorecard") {
    return `<div class="lecture-note"><span>Blanc says</span><strong>I do not ask you to trust me.</strong><p>Specificity is the honest number: the engine must stay silent on the loud-but-innocent record. It does.</p></div>`;
  }
  if (slide.type === "message") {
    const fragments = fragmentsForText(specimenForSlide(slide, finding).body);
    return `
      <div class="lecture-note">
        <span>Blanc says</span>
        <strong>Do not start with the conclusion. Start with the phrase that is trying to move the room.</strong>
        <p>This message contributes ${fragments.length || 1} fragment${fragments.length === 1 ? "" : "s"} to the outcome pressure. The method marks purpose before it names behavior.</p>
      </div>
    `;
  }
  if (slide.type === "behavior") {
    return `<div class="lecture-note"><span>Blanc says</span><strong>The fragments have begun to behave.</strong><p>Independent layers are now visible. A single ugly sentence is not enough; corroboration is the lock.</p></div>`;
  }
  if (slide.type === "pattern") {
    return `<div class="lecture-note"><span>Blanc says</span><strong>A pattern is a habit.</strong><p>${escapeHtml(patternSummary(slide.pattern || relatedPatterns(finding)[0]))}</p></div>`;
  }
  if (slide.type === "campaign") {
    return `<div class="lecture-note"><span>Blanc says</span><strong>A campaign is a habit with a direction.</strong><p>${escapeHtml(relatedCampaigns(finding)[0]?.summary || "No campaign is invented where the record shows only one event.")}</p></div>`;
  }
  return `<div class="lecture-note"><span>Blanc says</span><strong>The shape is now unmistakable.</strong><p>${escapeHtml(finding.narration[state.voice])}</p></div>`;
}

function reviewMarkup(finding) {
  const signalRows = finding.signals.map((signal) => `
    <li><strong>${escapeHtml(signal.layer)}</strong><span>${escapeHtml(signal.kind)}</span><p>${escapeHtml(signal.detail)}</p></li>
  `).join("");
  const messageRows = finding.messages.map((message) => `
    <li><strong>seq ${message.seq} / ${escapeHtml(message.sender)}</strong><p>${highlightMessage(message.body, fragmentsForText(message.body))}</p></li>
  `).join("");
  return `
    <div class="review-verdict">
      <span>${escapeHtml(finding.confidence)}</span>
      <strong>${escapeHtml(finding.narration[state.voice])}</strong>
    </div>
    <div class="review-section">
      <span>signals</span>
      <ul>${signalRows}</ul>
    </div>
    <div class="review-section">
      <span>messages</span>
      <ul>${messageRows}</ul>
    </div>
  `;
}

function titleForSlide(slide, finding) {
  if (slide.type === "message") return `fragment ${slide.ordinal} / seq ${slide.message.seq}`;
  if (slide.type === "review") return `${state.corpus.corpus.label} / review`;
  if (slide.type === "dynamics") return "discriminator / five dynamics";
  if (slide.type === "scorecard") return "scorecard / scored against ground truth";
  return `${state.corpus.corpus.label} / ${progressLabel(slide)} / seqs ${finding.seqs.join(", ")}`;
}

function fragmentsForMessage(message) {
  return fragmentsForText(message.body);
}

function specimenForSlide(slide, finding) {
  const messages = finding.messages.length ? finding.messages : [slide.message];
  if (slide.ordinal === 1) {
    return {
      label: `annotated record excerpt / seqs ${messages.map((message) => message.seq).join(", ")}`,
      body: formatMessageRecord(messages)
    };
  }
  return {
    label: `purpose stack / seqs ${finding.seqs.join(", ")}`,
    body: formatMessageRecord([slide.message])
  };
}

function formatMessageRecord(messages) {
  const groups = messages.reduce((bySender, message) => {
    const sender = message.sender || "Unknown";
    bySender.set(sender, [...(bySender.get(sender) || []), message]);
    return bySender;
  }, new Map());

  return [...groups.entries()].map(([sender, senderMessages]) => {
    const lines = senderMessages.map((message) =>
      `   ${formatMessageDate(message.timestamp)}:   ${message.body}`
    );
    return `${sender}:\n${lines.join("\n\n")}`;
  }).join("\n\n");
}

function formatMessageDate(value) {
  if (!value) return "date unknown";
  const [datePart, timePart = ""] = String(value).split("T");
  const [, month, day] = datePart.split("-");
  if (!month || !day) return value;
  return `${month.padStart(2, "0")}/${day.padStart(2, "0")}`;
}

function fragmentsForText(text) {
  const found = [];
  FRAGMENT_RULES.forEach((rule) => {
    const matches = [...text.matchAll(rule.pattern)];
    matches.forEach((match) => {
      found.push({
        text: match[0],
        label: rule.label,
        tone: rule.tone,
        purpose: rule.purpose,
        start: match.index,
        end: match.index + match[0].length
      });
    });
  });
  return dedupeFragments(found).map((fragment, index) => ({
    ...fragment,
    id: `fragment-${index}`
  }));
}

function dedupeFragments(fragments) {
  const seen = new Set();
  return fragments
    .sort((a, b) => a.start - b.start || (b.end - b.start) - (a.end - a.start))
    .filter((fragment) => {
    const key = `${fragment.text.toLowerCase()}-${fragment.label}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
    })
    .reduce((kept, fragment) => {
      if (kept.some((existing) => fragment.start < existing.end && existing.start < fragment.end)) return kept;
      kept.push(fragment);
      return kept;
    }, []);
}

function highlightMessage(value, fragments) {
  let cursor = 0;
  let output = "";
  fragments
    .slice()
    .sort((a, b) => a.start - b.start)
    .forEach((fragment) => {
      output += escapeHtml(value.slice(cursor, fragment.start));
      output += `<mark tabindex="0" class="tone-${escapeHtml(fragment.tone)}" data-fragment-id="${escapeHtml(fragment.id)}" title="${escapeHtml(fragment.purpose)}">${escapeHtml(value.slice(fragment.start, fragment.end))}</mark>`;
      cursor = fragment.end;
    });
  output += escapeHtml(value.slice(cursor));
  return output;
}

function bindMessageSlideInteractions() {
  const stage = $("slide-stage");
  const tabs = stage.querySelectorAll("[data-message-tab]");
  const panels = stage.querySelectorAll("[data-message-panel]");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((candidate) => candidate.classList.toggle("is-active", candidate === tab));
      panels.forEach((panel) => panel.classList.toggle("is-active", panel.dataset.messagePanel === tab.dataset.messageTab));
    });
  });

  const marks = stage.querySelectorAll("mark[data-fragment-id]");
  marks.forEach((mark) => {
    const activate = () => setActiveFragment(mark.dataset.fragmentId);
    mark.addEventListener("mouseenter", activate);
    mark.addEventListener("focus", activate);
    mark.addEventListener("click", activate);
  });
  if (marks[0]) setActiveFragment(marks[0].dataset.fragmentId);
}

function setActiveFragment(fragmentId) {
  document.querySelectorAll("[data-fragment-id]").forEach((node) => {
    node.classList.toggle("is-active", node.dataset.fragmentId === fragmentId);
  });
}

function outcomeMethodForFinding(finding) {
  if (finding.layers.includes("L3")) return "Deny earlier record";
  if (finding.layers.includes("L6")) return "Split the record";
  if (finding.layers.includes("L1")) return "Borrow authority";
  return "Move pressure";
}

function outcomeForFinding(finding) {
  if (finding.layers.includes("L3")) return "make the later denial survive contact with the earlier record";
  if (finding.layers.includes("L6")) return "split the public record from the private channel";
  if (finding.layers.includes("L1")) return "borrow authority to turn preference into necessity";
  return "move pressure through the conversation while preserving deniability";
}

function relatedPatterns(finding) {
  const seqs = new Set(finding.seqs);
  return state.corpus.patterns
    .filter((pattern) => qualifiesAsPattern(pattern) && pattern.seqs.some((seq) => seqs.has(seq)))
    .sort((a, b) => overlapCount(b.seqs, seqs) - overlapCount(a.seqs, seqs));
}

function overlapCount(values, seqs) {
  return values.filter((seq) => seqs.has(seq)).length;
}

function relatedCampaigns(finding) {
  const seqs = new Set(finding.seqs);
  return state.corpus.campaigns.filter((campaign) => campaign.finding_seqs?.some((seq) => seqs.has(seq)));
}

function phaseLabel(finding) {
  if (finding.layers.includes("L3") && finding.layers.includes("L4")) return "contradiction converged across domains";
  if (finding.layers.includes("L6")) return "cross-channel split exposed";
  if (finding.layers.length >= 3) return "multi-layer corroboration locked";
  return "single-thread signal held for review";
}

function bindControls() {
  $("previous-finding").addEventListener("click", () => moveSlide(-1));
  $("next-finding").addEventListener("click", () => moveSlide(1));
  $("copy-active-cipher").addEventListener("click", copyActiveCipher);
}

function moveSlide(delta) {
  state.activeSlideIndex = (state.activeSlideIndex + delta + state.slides.length) % state.slides.length;
  renderSlide();
  showToast(`${progressLabel(activeSlide())} slide.`);
}

function updateNavState() {
  $("previous-finding").disabled = !state.slides.length;
  $("next-finding").disabled = !state.slides.length;
  $("next-finding").textContent = state.activeSlideIndex === state.slides.length - 1 ? "restart" : "next slide";
}

async function copyActiveCipher() {
  const finding = activeFinding();
  const text = [
    "Convergence lecture cipher",
    `Corpus: ${state.corpus.corpus.label}`,
    `Finding: seqs ${finding.seqs.join(", ")}`,
    `Current slide: ${progressLabel(activeSlide())}`,
    `Confidence: ${finding.confidence}`,
    `Phase: ${phaseLabel(finding)}`,
    `Layers: ${finding.layers.join(", ")}`,
    `Blanc: ${finding.narration[state.voice]}`,
    "Signals:",
    ...finding.signals.map((signal) => `- ${signal.layer} / ${signal.kind}: ${signal.detail}`)
  ].join("\n");
  try {
    await navigator.clipboard.writeText(text);
    showToast("Lecture cipher copied.");
  } catch {
    showToast("Cipher ready, but clipboard access was blocked.");
  }
}

function bindChat() {
  $("chat-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!state.localApi || activeSlide()?.type !== "review") return;
    const question = $("question").value.trim();
    if (!question) return;
    $("chat-answer").textContent = "thinking...";
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          corpus: state.selectedCorpus,
          question,
          voice: state.voice,
          model: $("model").value
        })
      });
      const payload = await response.json();
      $("chat-answer").textContent = payload.answer || payload.error || "No answer returned.";
    } catch (error) {
      $("chat-answer").textContent = String(error);
    }
  });
}

function showToast(message) {
  const toast = $("interaction-toast");
  toast.textContent = message;
  toast.classList.add("is-visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    toast.classList.remove("is-visible");
  }, 2600);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;"
  }[char]));
}
