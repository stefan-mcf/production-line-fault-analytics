const element = (id) => document.getElementById(id);

const dayFormat = new Intl.DateTimeFormat("en-GB", {
  day: "numeric", month: "short", timeZone: "UTC",
});
const timeFormat = new Intl.DateTimeFormat("en-GB", {
  hour: "2-digit", minute: "2-digit", second: "2-digit", timeZone: "UTC",
});

function tag(name, content, className) {
  const node = document.createElement(name);
  node.textContent = content;
  if (className) node.className = className;
  return node;
}

function sentenceCase(value) {
  const text = value.toLowerCase().replaceAll("_", " ");
  return text[0].toUpperCase() + text.slice(1);
}

function definition(label, value, className) {
  const group = tag("div", "", className);
  group.append(tag("dt", label), tag("dd", value));
  return group;
}

function sourceLink(origin) {
  const link = tag("a", `${origin.batch} · row ${origin.row}`, "source");
  link.href = `https://github.com/stefan-mcf/production-line-fault-analytics/blob/main/data/${encodeURIComponent(origin.batch)}#L${origin.row}`;
  return link;
}

function timeRow(records, lookback) {
  const [first] = records;
  const row = tag("div", "", "time-row");
  const track = tag("div", "", "time-track");
  const label = tag("span", sentenceCase(first.code), "time-label");
  if (records.length > 1) label.append(tag("span", ` ×${records.length}`, "time-count"));
  for (const record of records) {
    const mark = tag("span", "", "time-mark");
    mark.classList.add(record.code.toLowerCase().replaceAll("_", "-"));
    mark.style.setProperty("--position", `${100 * (1 - (record.lead_seconds ?? 0) / lookback)}%`);
    track.append(mark);
  }
  row.append(label, track);
  return row;
}

function evidenceRow(record) {
  const row = tag("li", "");
  const label = tag("div", "");
  const sources = tag("div", "");
  label.append(tag("strong", sentenceCase(record.code)), tag("span", record.event_id, "identifier"));
  sources.append(...record.origins.map(sourceLink));
  row.append(
    label,
    tag("span", record.lead_seconds === undefined ? "Abort start" : `${record.lead_seconds} s earlier`, "timing"),
    sources,
  );
  return row;
}

function showEpisode(episode, lookback) {
  const {event, preceding} = episode;
  const lanes = new Map();
  for (const record of [...preceding, event]) {
    const key = `${record.station}/${record.code}`;
    if (!lanes.has(key)) lanes.set(key, []);
    lanes.get(key).push(record);
  }
  const duration = event.duration_seconds;
  element("event-id").textContent = event.event_id;
  element("event-context").textContent = `${sentenceCase(event.station)} · ${dayFormat.format(new Date(event.started_at))} · ${timeFormat.format(new Date(event.started_at))} UTC`;
  element("event-duration").replaceChildren(
    tag("strong", duration === null ? "Clear time unknown" : `${duration} s`),
    tag("span", duration === null ? "" : "Recorded interval"),
  );
  const axis = tag("div", "", "time-row time-axis-row");
  const ticks = tag("div", "", "time-axis");
  for (let fraction = 4; fraction >= 0; fraction -= 1) {
    const minutes = fraction * lookback / 240;
    ticks.append(tag("span", minutes === 0 ? "0" : `−${minutes} min`));
  }
  axis.append(tag("span", ""), ticks);
  const rows = Array.from(lanes.values(), (records) => timeRow(records, lookback));
  element("timeline").replaceChildren(...rows, axis);
  element("evidence").replaceChildren(...[event, ...preceding].map(evidenceRow));
}

function render(report, comparison) {
  const {ingestion, investigation, review} = report;
  const {episodes, lookback_seconds: lookback} = investigation;
  if (!episodes.length) throw new Error("No abort episodes in the investigation report.");
  const defaultEpisode = episodes.find(({event}) => event.event_id === "ABORT-610") ?? episodes[0];

  element("metrics").replaceChildren(
    definition("Input rows", ingestion.input_rows, "metric"),
    definition("Accepted events", ingestion.accepted_events, "metric"),
    definition("Distinct aborts", episodes.length, "metric"),
    definition("Quarantined rows", ingestion.invalid_rows + ingestion.conflict_rows, "metric"),
  );
  element("lookback").textContent = `${lookback / 60}-minute lookback`;
  const selector = element("episode-select");
  const episodeById = new Map(episodes.map((episode) => [episode.event.event_id, episode]));
  selector.replaceChildren(...Array.from(episodeById.keys(), (eventId) => {
    const option = tag("option", eventId);
    option.value = eventId;
    return option;
  }));
  selector.value = defaultEpisode.event.event_id;
  selector.addEventListener("change", () => showEpisode(episodeById.get(selector.value), lookback));
  showEpisode(defaultEpisode, lookback);

  element("review-mode").textContent = `${sentenceCase(review.state)} · all aborts`;
  element("assessment").textContent = review.assessment === "insufficient_evidence"
    ? "Not enough information"
    : sentenceCase(review.assessment);
  element("review-eligibility").textContent = review.state === "practice" ? "Excluded from training" : "";
  element("next-check").textContent = review.next_check;

  const reload = comparison.profile_reload;
  const accepted = reload.as_reconciled;
  const alternatives = reload.if_admitted;
  const [alternative] = alternatives;
  const equalCounts = alternatives.every(({support, total_episodes}) => (
    support === alternative.support && total_episodes === alternative.total_episodes
  ));
  element("comparison-context").textContent = `${reload.quarantined_event_id} · aborts preceded by reload`;
  element("comparison-values").replaceChildren(
    definition("Both versions quarantined", `${accepted.support} of ${accepted.total_episodes}`),
    ...(equalCounts
      ? [definition("Either version admitted", `${alternative.support} of ${alternative.total_episodes}`)]
      : alternatives.map(({support, total_episodes, origin}) =>
        definition(`Admit ${origin.batch}`, `${support} of ${total_episodes}`))),
  );
}

async function readReport(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`HTTP ${response.status} for ${path}`);
  return response.json();
}

async function loadDashboard() {
  try {
    const [report, comparison] = await Promise.all([
      readReport("../report/example-report.json"),
      readReport("../report/reconciliation-check.json"),
    ]);
    render(report, comparison);
    element("dashboard").hidden = false;
    element("status").hidden = true;
  } catch (error) {
    const status = element("status");
    status.replaceChildren(
      "The investigation reports could not be loaded. From the repository root, run ",
      tag("code", "python3 -m http.server"),
      " and open ",
      tag("code", "http://localhost:8000/demo/"),
      ".",
    );
    console.error(error);
  }
}

loadDashboard();
