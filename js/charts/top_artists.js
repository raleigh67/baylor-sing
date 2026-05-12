// site/js/charts/top_artists.js
const NS = "http://www.w3.org/2000/svg";
function svg(tag, attrs) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; }

export function render(root, acts) {
  let activeMatch = null;

  function build() {
    while (root.firstChild) root.removeChild(root.firstChild);

    // Filter to focused act if any
    const scope = activeMatch ? acts.filter(activeMatch) : acts;
    const isSingle = !!activeMatch;

    // For "all acts": count artist appearances across acts (top 20).
    // For a single act: list every song in that act with its artist.
    if (isSingle) {
      const songs = [];
      scope.forEach(a => {
        if (!a.songs) return;
        a.songs.split(";").forEach(s => {
          s = s.trim();
          if (!s) return;
          const m = s.match(/^(.+?)\s*\(([^)]+)\)\s*$/);
          if (m) songs.push({ title: m[1].trim(), artist: m[2].trim() });
          else songs.push({ title: s, artist: "" });
        });
      });
      if (songs.length === 0) {
        const p = document.createElement("p");
        p.className = "song-age-note";
        p.textContent = "No songs listed for this act.";
        root.appendChild(p);
        return;
      }
      const W = 700, ROW_H = 24, PAD = 16;
      const H = songs.length * ROW_H + PAD * 2 + 30;
      const svgEl = svg("svg", { width: "100%", viewBox: `0 0 ${W} ${H}`, style: "display:block;" });
      root.appendChild(svgEl);
      const head = svg("text", { x: PAD, y: PAD + 12, class: "ta-label" });
      head.textContent = `${scope[0].year} ${scope[0].group} — ${songs.length} songs`;
      head.setAttribute("fill", "var(--gold)");
      svgEl.appendChild(head);
      songs.forEach((s, i) => {
        const y = PAD + 30 + i * ROW_H;
        const t = svg("text", { x: PAD, y: y + 16, class: "ta-label" });
        t.textContent = s.title;
        svgEl.appendChild(t);
        if (s.artist) {
          const a = svg("text", { x: W - PAD, y: y + 16, class: "ta-value", "text-anchor": "end" });
          a.textContent = s.artist;
          svgEl.appendChild(a);
        }
      });
      return;
    }

    const counts = new Map();
    scope.forEach(a => {
      if (!a.songs) return;
      a.songs.split(";").forEach(s => {
        const m = s.match(/\(([^)]+)\)\s*$/);
        if (m) {
          const artist = m[1].trim();
          counts.set(artist, (counts.get(artist) || 0) + 1);
        }
      });
    });
    const top = [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 20);
    if (top.length === 0) return;
    const max = top[0][1];
    const W = 700, BAR_H = 22, GAP = 4, LABEL_W = 200, PAD = 16;
    const H = top.length * (BAR_H + GAP) + PAD * 2;
    const svgEl = svg("svg", { width: "100%", viewBox: `0 0 ${W} ${H}`, style: "display:block;" });
    root.appendChild(svgEl);
    top.forEach(([artist, n], i) => {
      const y = PAD + i * (BAR_H + GAP);
      const barW = (n / max) * (W - LABEL_W - PAD - 60);
      svgEl.appendChild(svg("rect", { x: LABEL_W, y, width: barW, height: BAR_H, fill: "var(--gold)", rx: 2 }));
      const lbl = svg("text", { x: LABEL_W - 8, y: y + BAR_H * 0.7, class: "ta-label", "text-anchor": "end" });
      lbl.textContent = artist;
      svgEl.appendChild(lbl);
      const val = svg("text", { x: LABEL_W + barW + 6, y: y + BAR_H * 0.7, class: "ta-value", "text-anchor": "start" });
      val.textContent = String(n);
      svgEl.appendChild(val);
    });
  }

  build();

  return {
    highlight(matchFn) { activeMatch = matchFn; build(); },
    reset() { activeMatch = null; build(); },
  };
}
