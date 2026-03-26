/**
 * dashboard.js — Interactive explorer for the Sing dataset.
 * Pure vanilla JS. Uses DOM methods (no innerHTML) for safe rendering.
 */

(function () {
  "use strict";

  var allActs = [];
  var filteredActs = [];

  // ── Data loading ─────────────────────────────────────────────────
  function loadDashboardData() {
    fetch("charts/dashboard_data.json")
      .then(function (res) {
        if (!res.ok) throw new Error("Failed to load dashboard data");
        return res.json();
      })
      .then(function (data) {
        allActs = data;
        filteredActs = allActs.slice();
        setupFilters();
        renderGrid();
      })
      .catch(function (err) {
        console.error(err);
      });
  }

  // ── Grid rendering ───────────────────────────────────────────────
  function renderGrid() {
    var grid = document.getElementById("act-grid");
    if (!grid) return;

    // Clear existing cards
    while (grid.firstChild) {
      grid.removeChild(grid.firstChild);
    }

    filteredActs.forEach(function (act, idx) {
      var card = document.createElement("div");
      card.className = "act-card";

      // Find the original index for showDetail
      var originalIndex = allActs.indexOf(act);
      card.setAttribute("data-index", originalIndex);

      // Year
      var yearEl = document.createElement("span");
      yearEl.className = "card-year";
      yearEl.textContent = act.Year || "";
      card.appendChild(yearEl);

      // Group name
      var groupEl = document.createElement("strong");
      groupEl.className = "card-group";
      groupEl.textContent = act.Group || "";
      card.appendChild(groupEl);

      // Theme
      if (act.Theme && act.Theme !== "") {
        var themeEl = document.createElement("em");
        themeEl.className = "card-theme";
        themeEl.textContent = act.Theme;
        card.appendChild(themeEl);
      }

      // Palette bar
      if (act.palette_hex && act.palette_hex !== "") {
        var colors = act.palette_hex.split(";");
        var paletteBar = document.createElement("div");
        paletteBar.className = "palette-bar";
        colors.forEach(function (hex) {
          hex = hex.trim();
          if (hex) {
            var swatch = document.createElement("div");
            swatch.className = "palette-bar-segment";
            swatch.style.backgroundColor = hex;
            paletteBar.appendChild(swatch);
          }
        });
        card.appendChild(paletteBar);
      }

      card.addEventListener("click", function () {
        showDetail(originalIndex);
      });

      grid.appendChild(card);
    });
  }

  // ── Detail panel ─────────────────────────────────────────────────
  function showDetail(index) {
    var detail = document.getElementById("act-detail");
    if (!detail) return;

    var act = allActs[index];
    if (!act) return;

    // Clear existing content
    while (detail.firstChild) {
      detail.removeChild(detail.firstChild);
    }

    // Close button
    var closeBtn = document.createElement("button");
    closeBtn.className = "detail-close";
    closeBtn.textContent = "\u00D7"; // multiplication sign as X
    closeBtn.addEventListener("click", function () {
      detail.classList.add("hidden");
    });
    detail.appendChild(closeBtn);

    // Year + Placement badge
    var headerRow = document.createElement("div");
    headerRow.className = "detail-header";

    var yearSpan = document.createElement("span");
    yearSpan.className = "detail-year";
    yearSpan.textContent = act.Year || "";
    headerRow.appendChild(yearSpan);

    if (act.Placement && act.Placement !== "") {
      var badge = document.createElement("span");
      badge.className = "detail-badge";
      badge.textContent = act.Placement;
      headerRow.appendChild(badge);
    }

    detail.appendChild(headerRow);

    // Group name
    var groupH3 = document.createElement("h3");
    groupH3.className = "detail-group";
    groupH3.textContent = act.Group || "";
    detail.appendChild(groupH3);

    // Theme
    if (act.Theme && act.Theme !== "") {
      var themeP = document.createElement("p");
      themeP.className = "detail-theme";
      themeP.textContent = act.Theme;
      detail.appendChild(themeP);
    }

    // Audio stats
    var statsFields = [
      { key: "energy", label: "Energy" },
      { key: "valence", label: "Valence" },
      { key: "danceability", label: "Danceability" },
    ];

    var hasStats = statsFields.some(function (f) {
      return act[f.key] !== "" && act[f.key] !== null && act[f.key] !== undefined;
    });

    if (hasStats) {
      var statsRow = document.createElement("div");
      statsRow.className = "detail-stats";

      statsFields.forEach(function (f) {
        var val = act[f.key];
        if (val === "" || val === null || val === undefined) return;

        var statBlock = document.createElement("div");
        statBlock.className = "stat-block";

        var numEl = document.createElement("span");
        numEl.className = "stat-number";
        numEl.textContent = typeof val === "number" ? val.toFixed(3) : val;
        statBlock.appendChild(numEl);

        var labelEl = document.createElement("span");
        labelEl.className = "stat-label";
        labelEl.textContent = f.label;
        statBlock.appendChild(labelEl);

        statsRow.appendChild(statBlock);
      });

      detail.appendChild(statsRow);
    }

    // Palette swatches
    if (act.palette_hex && act.palette_hex !== "") {
      var swatchContainer = document.createElement("div");
      swatchContainer.className = "detail-palette";

      var swatchLabel = document.createElement("span");
      swatchLabel.className = "detail-palette-label";
      swatchLabel.textContent = "Palette";
      swatchContainer.appendChild(swatchLabel);

      var swatchRow = document.createElement("div");
      swatchRow.className = "detail-swatch-row";

      var colors = act.palette_hex.split(";");
      colors.forEach(function (hex) {
        hex = hex.trim();
        if (hex) {
          var swatch = document.createElement("div");
          swatch.className = "detail-swatch";
          swatch.style.backgroundColor = hex;
          swatch.style.width = "40px";
          swatch.style.height = "40px";
          swatchRow.appendChild(swatch);
        }
      });

      swatchContainer.appendChild(swatchRow);
      detail.appendChild(swatchContainer);
    }

    // Song list
    if (act.Songs && act.Songs !== "") {
      var songsContainer = document.createElement("div");
      songsContainer.className = "detail-songs";

      var songsLabel = document.createElement("span");
      songsLabel.className = "detail-songs-label";
      songsLabel.textContent = "Songs";
      songsContainer.appendChild(songsLabel);

      var songList = document.createElement("ul");
      var songs = act.Songs.split(";");
      songs.forEach(function (song) {
        song = song.trim();
        if (song) {
          var li = document.createElement("li");
          li.textContent = song;
          songList.appendChild(li);
        }
      });

      songsContainer.appendChild(songList);
      detail.appendChild(songsContainer);
    }

    // Show the panel
    detail.classList.remove("hidden");
  }

  // ── Filters ──────────────────────────────────────────────────────
  function setupFilters() {
    var yearStart = document.getElementById("year-start");
    var yearEnd = document.getElementById("year-end");
    var yearStartLabel = document.getElementById("year-start-label");
    var yearEndLabel = document.getElementById("year-end-label");
    var placementFilter = document.getElementById("placement-filter");
    var searchInput = document.getElementById("search-input");

    function applyFilters() {
      var minYear = yearStart ? parseInt(yearStart.value, 10) : 1953;
      var maxYear = yearEnd ? parseInt(yearEnd.value, 10) : 2026;

      // Ensure min <= max
      if (minYear > maxYear) {
        var tmp = minYear;
        minYear = maxYear;
        maxYear = tmp;
      }

      // Update labels
      if (yearStartLabel) yearStartLabel.textContent = minYear;
      if (yearEndLabel) yearEndLabel.textContent = maxYear;

      var placement = placementFilter ? placementFilter.value : "all";
      var query = searchInput ? searchInput.value.toLowerCase().trim() : "";

      filteredActs = allActs.filter(function (act) {
        // Year range
        if (act.Year < minYear || act.Year > maxYear) return false;

        // Placement
        if (placement !== "all") {
          var p = (act.Placement || "").toLowerCase();
          if (placement === "1") {
            if (!p.startsWith("1st")) return false;
          } else if (placement === "top3") {
            if (
              !p.startsWith("1st") &&
              !p.startsWith("2nd") &&
              !p.startsWith("3rd")
            )
              return false;
          } else if (placement === "pigskin") {
            if (p.indexOf("pigskin") === -1) return false;
          }
        }

        // Search
        if (query) {
          var haystack = [
            act.Group || "",
            act.Theme || "",
            act.Songs || "",
            act.genres || "",
          ]
            .join(" ")
            .toLowerCase();
          if (haystack.indexOf(query) === -1) return false;
        }

        return true;
      });

      renderGrid();
    }

    if (yearStart) yearStart.addEventListener("input", applyFilters);
    if (yearEnd) yearEnd.addEventListener("input", applyFilters);
    if (placementFilter)
      placementFilter.addEventListener("change", applyFilters);
    if (searchInput) searchInput.addEventListener("input", applyFilters);
  }

  // ── Boot ──────────────────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", function () {
    loadDashboardData();
  });
})();
