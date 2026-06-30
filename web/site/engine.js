// Plain, read-only generic engine view. Loads the generic core of each corpus
// payload and renders findings with their layers, confidence, seqs, and evidence.
// It reads only the generic core fields; the lecture section is not used here.
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

function renderFindings(data) {
  const ol = $("findings");
  ol.innerHTML = "";
  for (const f of data.findings) {
    const li = document.createElement("li");
    li.className = `finding ${f.confidence}`;
    const sigs = f.signals
      .map((s) => `${s.layer} ${escapeHtml(s.kind)} — ${escapeHtml(s.detail)} (seq ${s.anchor}, ${escapeHtml(s.thread)})`)
      .join("<br>");
    li.innerHTML =
      `<div class="finding-head"><span class="badge">${f.confidence}</span>` +
      `<span class="layers">${f.layers.join(" · ")}</span>` +
      `<span class="seqs">seqs ${f.seqs.join(", ")}</span></div>` +
      `<p class="finding-summary">${escapeHtml(f.summary)}</p>` +
      `<div class="finding-signals">${sigs}</div>`;
    ol.appendChild(li);
  }
}

function renderCorpus(data) {
  const c = data.corpus;
  $("corpus-summary").textContent =
    `${c.label} · ${c.message_count} messages · ${c.finding_count} findings ` +
    `(${c.elevated_count} elevated, ${c.low_count} low)`;
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
