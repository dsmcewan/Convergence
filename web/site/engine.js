// Plain, read-only generic engine view. Loads the generic core of each corpus
// payload and renders findings as exhibit cards with convergence traces.
// Reads only generic core fields — the lecture section is not accessed here.
const $ = (id) => document.getElementById(id);

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

async function loadJson(url) {
  const r = await fetch(url, { cache: "no-store" });
  if (!r.ok) throw new Error(`failed to load ${url}`);
  return r.json();
}

// Build the convergence trace for an elevated finding card.
// Positions a vertical rail and layer nodes over signal rows, driven entirely
// by f.signals — no hardcoded content.
function buildTrace(card) {
  const body = card.querySelector(".card-body");
  if (!body) return;
  body.querySelectorAll(".trace-rail,.layer-node").forEach((el) => el.remove());

  const rows = [...body.querySelectorAll(".signal-row[data-layer]")];
  if (rows.length < 2) return;

  const rail = document.createElement("span");
  rail.className = "trace-rail";
  rail.setAttribute("aria-hidden", "true");
  body.appendChild(rail);

  const sorted = rows.slice().sort((a, b) => a.offsetTop - b.offsetTop);
  const centers = sorted.map((el) => el.offsetTop + el.offsetHeight / 2);
  const top = centers[0];
  const bottom = centers[centers.length - 1];
  rail.style.top = top + "px";
  rail.style.height = bottom - top + "px";

  sorted.forEach((row, i) => {
    const node = document.createElement("span");
    const isAnchor = row.dataset.anchor === "true";
    node.className = "layer-node" + (isAnchor ? " anchor" : "");
    node.textContent = isAnchor ? "" : (row.dataset.layer || "");
    node.style.top = centers[i] - 8 + "px";
    node.setAttribute("aria-hidden", "true");
    body.appendChild(node);
  });
}

function toggleTrace(card, btn, legend) {
  const on = btn.getAttribute("aria-pressed") === "true";
  const next = !on;
  btn.setAttribute("aria-pressed", String(next));
  btn.textContent = next ? "▾ hide trace" : "▸ trace convergence";
  card.classList.toggle("tracing", next);
  if (legend) legend.classList.toggle("show", next);
  card.querySelectorAll(".signal-row").forEach((r) => r.classList.toggle("on", next));
  if (next) buildTrace(card);
}

// Determine the convergence anchor: the signal anchor seq most cited across signals.
// Driven entirely by real data — never hardcoded.
function resolveAnchorSeq(signals) {
  if (!signals.length) return null;
  const counts = {};
  for (const s of signals) {
    counts[s.anchor] = (counts[s.anchor] || 0) + 1;
  }
  return Object.keys(counts).reduce(
    (a, b) => (counts[b] > counts[a] ? b : a),
    Object.keys(counts)[0]
  );
}

function renderFindingCard(f, idx) {
  const isElevated = f.confidence === "elevated";
  const anchorSeq = resolveAnchorSeq(f.signals);
  const uniqueLayers = [...new Set(f.signals.map((s) => s.layer))];

  // signal rows
  const sigRows = f.signals
    .map((s) => {
      const isAnchorSig = isElevated && String(s.anchor) === String(anchorSeq);
      return (
        `<div class="signal-row" ` +
        `data-layer="${escapeHtml(s.layer)}" ` +
        `data-anchor="${isAnchorSig ? "true" : "false"}">` +
        `<span class="signal-layer-id${isElevated ? "" : " low-conf"}">${escapeHtml(s.layer)}</span>` +
        `<span class="signal-detail">` +
        `${escapeHtml(s.kind)}` +
        (s.detail ? ` — ${escapeHtml(s.detail)}` : "") +
        `<span class="signal-meta">` +
        `anchor seq ${escapeHtml(String(s.anchor))}` +
        (s.thread ? ` · ${escapeHtml(s.thread)}` : "") +
        (s.actor ? ` · ${escapeHtml(s.actor)}` : "") +
        `</span></span></div>`
      );
    })
    .join("");

  // convergence legend (elevated only): lists the converging layers
  const legendHtml = isElevated
    ? `<div class="conv-legend" id="legend-${idx}"><div class="in">` +
      uniqueLayers.map((l) => `<span class="hl">${escapeHtml(l)}</span>`).join(" + ") +
      (anchorSeq !== null
        ? ` converge on anchor seq <b>${escapeHtml(String(anchorSeq))}</b> —`
        : " —") +
      ` ${uniqueLayers.length} distinct layer${uniqueLayers.length !== 1 ? "s" : ""} → <b>elevated</b>` +
      `</div></div>`
    : "";

  const seqStr = f.seqs.map((s) => escapeHtml(String(s))).join(", ");

  const footerContent = isElevated
    ? `<span>anchor seq ${escapeHtml(String(anchorSeq))} · ${uniqueLayers.length} layers</span>` +
      `<button class="trace-btn" aria-pressed="false" aria-controls="legend-${idx}">▸ trace convergence</button>`
    : `<span>seqs ${seqStr}</span>`;

  const li = document.createElement("li");
  li.className = `exhibit-card finding ${escapeHtml(f.confidence)}`;
  li.innerHTML =
    `<div class="card-head">` +
    `<span class="badge ${escapeHtml(f.confidence)}">${escapeHtml(f.confidence)}</span>` +
    `<span class="layer-chips">` +
    f.layers.map((l) => `<span class="layer-chip${isElevated ? "" : " low-conf"}">${escapeHtml(l)}</span>`).join("") +
    `</span>` +
    `<span class="card-seqs">seqs ${seqStr}</span>` +
    `</div>` +
    `<div class="card-body">${sigRows}</div>` +
    legendHtml +
    `<p class="card-summary">${escapeHtml(f.summary)}</p>` +
    `<div class="card-foot">${footerContent}</div>`;

  if (isElevated) {
    const btn = li.querySelector(".trace-btn");
    const legend = li.querySelector(".conv-legend");
    if (btn) btn.addEventListener("click", () => toggleTrace(li, btn, legend));
    let resizeTimer;
    window.addEventListener("resize", () => {
      if (!li.classList.contains("tracing")) return;
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => buildTrace(li), 120);
    });
  }

  return li;
}

function renderFindings(data) {
  const ol = $("findings");
  ol.innerHTML = "";
  for (let i = 0; i < data.findings.length; i++) {
    ol.appendChild(renderFindingCard(data.findings[i], i));
  }
}

function renderCorpus(data) {
  const c = data.corpus;
  $("corpus-summary").innerHTML =
    `<p class="stamp-corpus-label">${escapeHtml(c.label)}</p>` +
    `<div class="case-stamp-grid">` +
    `<div class="stat-cell"><div class="stat-n">${escapeHtml(String(c.message_count))}</div>` +
    `<div class="stat-label">messages</div></div>` +
    `<div class="stat-cell"><div class="stat-n">${escapeHtml(String(c.finding_count))}</div>` +
    `<div class="stat-label">findings</div></div>` +
    `<div class="stat-cell"><div class="stat-n elevated">${escapeHtml(String(c.elevated_count))}</div>` +
    `<div class="stat-label">elevated</div></div>` +
    `<div class="stat-cell"><div class="stat-n">${escapeHtml(String(c.low_count))}</div>` +
    `<div class="stat-label">low</div></div>` +
    `</div>`;
  renderFindings(data);
  $("narration").textContent = data.narration.plain || "";
}

async function selectCorpus(name) {
  renderCorpus(await loadJson(`data/${name}.json`));
}

async function init() {
  const index = await loadJson("data/index.json");
  const select = $("corpus-select");
  for (const corpus of index.corpora) {
    const opt = document.createElement("option");
    opt.value = corpus.name;
    opt.textContent = corpus.label;
    select.appendChild(opt);
  }
  select.value = index.default_corpus;
  select.addEventListener("change", () => selectCorpus(select.value));
  await selectCorpus(index.default_corpus);
}

init();
