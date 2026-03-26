/**
 * scroll.js — Scrollama-driven chart loading for the Sing scrollytelling site.
 * Dependencies: Plotly 2.27+, Scrollama 3.2+
 */

(function () {
  "use strict";

  // ── Chart cache ──────────────────────────────────────────────────
  var chartCache = {};

  /**
   * Fetch a Plotly JSON spec and render it into the given container.
   * Caches specs so repeat scrolls don't re-fetch.
   */
  function loadChart(chartName, containerId) {
    var container = document.getElementById(containerId);
    if (!container) return;

    if (chartCache[chartName]) {
      renderChart(chartCache[chartName], container);
      return;
    }

    fetch("charts/" + chartName + ".json")
      .then(function (res) {
        if (!res.ok) throw new Error("Chart fetch failed: " + chartName);
        return res.json();
      })
      .then(function (spec) {
        chartCache[chartName] = spec;
        renderChart(spec, container);
      })
      .catch(function (err) {
        console.error(err);
      });
  }

  function renderChart(spec, container) {
    var data = spec.data || [];
    var layout = spec.layout || {};
    Plotly.react(container, data, layout, {
      responsive: true,
      displayModeBar: false,
    });
  }

  // ── Section-to-container mapping ─────────────────────────────────
  var sectionToContainer = {
    sound1: "chart-sound1",
    sound2: "chart-sound2",
    sound3: "chart-sound3",
    color1: "chart-color1",
    color2: "chart-color2",
    appendix: "chart-appendix",
  };

  // ── Scrollama initialisation ─────────────────────────────────────
  function initScrollama() {
    var sectionIds = Object.keys(sectionToContainer);

    sectionIds.forEach(function (sectionId) {
      var section = document.getElementById(sectionId);
      if (!section) return;

      var steps = section.querySelectorAll(".step");
      if (steps.length === 0) return;

      var containerId = sectionToContainer[sectionId];
      var scroller = scrollama();

      scroller
        .setup({
          step: "#" + sectionId + " .step",
          offset: 0.5,
        })
        .onStepEnter(function (response) {
          // Toggle active class
          steps.forEach(function (s) {
            s.classList.remove("is-active");
          });
          response.element.classList.add("is-active");

          // Load chart from data attribute
          var chartName = response.element.getAttribute("data-chart");
          if (chartName) {
            loadChart(chartName, containerId);
          }
        });
    });

    // Handle window resize for all scrollers
    window.addEventListener("resize", function () {
      // Scrollama handles resize internally in v3
    });
  }

  // ── Counter animation ────────────────────────────────────────────
  function animateCounter() {
    var el = document.getElementById("counter");
    if (!el) return;

    var start = 13;
    var end = 3000;
    var duration = 2000; // ms
    var hasAnimated = false;

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting && !hasAnimated) {
            hasAnimated = true;
            var startTime = null;

            function tick(timestamp) {
              if (!startTime) startTime = timestamp;
              var elapsed = timestamp - startTime;
              var progress = Math.min(elapsed / duration, 1);

              // ease-out: 1 - (1 - t)^3
              var eased = 1 - Math.pow(1 - progress, 3);
              var current = Math.round(start + (end - start) * eased);

              el.textContent = current.toLocaleString() + "+";

              if (progress < 1) {
                requestAnimationFrame(tick);
              }
            }

            requestAnimationFrame(tick);
          }
        });
      },
      { threshold: 0.5 }
    );

    observer.observe(el);
  }

  // ── Boot ──────────────────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", function () {
    initScrollama();
    animateCounter();
  });
})();
