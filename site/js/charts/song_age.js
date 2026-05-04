// site/js/charts/song_age.js
// Histogram of (Sing year - song release year) across all songs in scope.
const NS = "http://www.w3.org/2000/svg";
function svg(tag, attrs) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; }

const BUCKETS = [
  { label: "0–4 yrs", min: 0, max: 4 },
  { label: "5–9", min: 5, max: 9 },
  { label: "10–14", min: 10, max: 14 },
  { label: "15–19", min: 15, max: 19 },
  { label: "20–29", min: 20, max: 29 },
  { label: "30–49", min: 30, max: 49 },
  { label: "50+", min: 50, max: 999 },
];

export function render(root, acts, options = {}) {
  let activeMatch = options.match || null;

  function build() {
    while (root.firstChild) root.removeChild(root.firstChild);

    // Collect all songs with ages, optionally filtered to a single act
    const songs = [];
    acts.forEach(a => {
      if (activeMatch && !activeMatch(a)) return;
      (a.song_ages || []).forEach(s => songs.push({ ...s, act: a }));
    });

    const counts = BUCKETS.map(() => 0);
    songs.forEach(s => {
      for (let i = 0; i < BUCKETS.length; i++) {
        if (s.age >= BUCKETS[i].min && s.age <= BUCKETS[i].max) {
          counts[i]++; return;
        }
      }
    });
    const max = Math.max(...counts, 1);

    const W = 700, H = 280, PAD_L = 50, PAD_R = 20, PAD_T = 20, PAD_B = 50;
    const innerW = W - PAD_L - PAD_R, innerH = H - PAD_T - PAD_B;

    const svgEl = svg("svg", { width: "100%", viewBox: `0 0 ${W} ${H}`, style: "display:block;" });
    root.appendChild(svgEl);

    const bw = innerW / BUCKETS.length - 6;
    counts.forEach((count, i) => {
      const x = PAD_L + i * (innerW / BUCKETS.length) + 3;
      const h = (count / max) * innerH;
      const y = PAD_T + innerH - h;
      svgEl.appendChild(svg("rect", { x, y, width: bw, height: h, fill: "var(--gold-dim)", rx: 1 }));
      if (count > 0) {
        const cnt = svg("text", { x: x + bw / 2, y: y - 4, class: "ta-value", "text-anchor": "middle" });
        cnt.textContent = String(count);
        svgEl.appendChild(cnt);
      }
      const lab = svg("text", { x: x + bw / 2, y: PAD_T + innerH + 14, class: "ta-label", "text-anchor": "middle" });
      lab.textContent = BUCKETS[i].label;
      svgEl.appendChild(lab);
    });
    const ax = svg("text", { x: W / 2, y: H - 12, class: "chart-axis-label", "text-anchor": "middle" });
    ax.textContent = "Years between song release and Sing performance";
    svgEl.appendChild(ax);

    // Stats / context
    const note = document.createElement("p");
    note.className = "song-age-note";
    if (songs.length === 0) {
      note.textContent = "No song-age data for this selection.";
    } else {
      const avg = songs.reduce((s, x) => s + x.age, 0) / songs.length;
      const min = Math.min(...songs.map(s => s.age));
      const max = Math.max(...songs.map(s => s.age));
      note.textContent = `${songs.length} songs · average age ${avg.toFixed(1)} yrs · range ${min}–${max}`;
    }
    root.appendChild(note);
  }
  build();

  return {
    highlight(matchFn) { activeMatch = matchFn; build(); },
    reset() { activeMatch = null; build(); },
  };
}
