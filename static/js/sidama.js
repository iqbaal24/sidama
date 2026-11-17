/* SIDAMA — small interaction layer (no framework needed). */
(function () {
  "use strict";

  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  function formatIDR(value) {
    return "Rp " + Math.round(Number(value) || 0).toLocaleString("id-ID");
  }

  window.sidamaFormatIDR = formatIDR;

  ready(function () {
    /* Sidebar (internal app) */
    var sidebar = document.getElementById("sidebar");
    var backdrop = document.getElementById("sidebar-backdrop");
    document.querySelectorAll("[data-sidebar-toggle]").forEach(function (button) {
      button.addEventListener("click", function () {
        if (!sidebar) return;
        sidebar.classList.toggle("is-open");
        if (backdrop) backdrop.classList.toggle("is-open");
      });
    });
    if (backdrop) {
      backdrop.addEventListener("click", function () {
        sidebar.classList.remove("is-open");
        backdrop.classList.remove("is-open");
      });
    }

    /* Public mobile navigation */
    var navToggle = document.querySelector("[data-nav-toggle]");
    var siteNav = document.getElementById("site-nav");
    if (navToggle && siteNav) {
      navToggle.addEventListener("click", function () {
        var open = siteNav.classList.toggle("is-open");
        navToggle.setAttribute("aria-expanded", open ? "true" : "false");
      });
    }

    /* Destructive actions ask for confirmation */
    document.querySelectorAll("form[data-confirm]").forEach(function (form) {
      form.addEventListener("submit", function (event) {
        if (!window.confirm(form.getAttribute("data-confirm"))) {
          event.preventDefault();
        }
      });
    });

    /* Filter selects submit their form on change */
    document.querySelectorAll("[data-auto-submit]").forEach(function (element) {
      element.addEventListener("change", function () {
        if (element.form) element.form.submit();
      });
    });

    /* Zakat calculator: show only the relevant inputs */
    var zakatInputs = document.querySelectorAll("[data-zakat-group]");
    if (zakatInputs.length) {
      var sync = function () {
        var selected = document.querySelector('input[name="zakat_type"]:checked');
        var type = selected ? selected.value : "mal";
        zakatInputs.forEach(function (group) {
          var show = group.getAttribute("data-zakat-group") === type;
          group.hidden = !show;
        });
      };
      document.querySelectorAll('input[name="zakat_type"]').forEach(function (input) {
        input.addEventListener("change", sync);
      });
      sync();
    }
  });

  /* ---------------------------------------------------------------------
     Charts (Chart.js is bundled locally in static/vendor)
     --------------------------------------------------------------------- */
  function chartData(scriptId) {
    var node = document.getElementById(scriptId);
    if (!node) return null;
    try {
      return JSON.parse(node.textContent);
    } catch (error) {
      return null;
    }
  }

  function baseOptions() {
    return {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#0f3a22",
          padding: 10,
          cornerRadius: 8,
          titleFont: { size: 11 },
          bodyFont: { size: 12 },
          callbacks: {
            label: function (context) {
              return context.dataset.label + ": " + formatIDR(context.parsed.y);
            },
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          border: { display: false },
          ticks: {
            color: "#63706a",
            font: { size: 10 },
            maxRotation: 0,
            autoSkip: true,
            autoSkipPadding: 6,
          },
        },
        y: {
          grace: "6%",
          grid: { color: "rgba(20, 83, 45, 0.07)" },
          border: { display: false },
          ticks: {
            color: "#63706a",
            font: { size: 10 },
            callback: function (value) {
              if (value >= 1000000) return (value / 1000000).toFixed(0) + " jt";
              if (value >= 1000) return (value / 1000).toFixed(0) + " rb";
              return value;
            },
          },
        },
      },
    };
  }

  window.renderCashflowChart = function (canvasId, scriptId) {
    var canvas = document.getElementById(canvasId);
    var series = chartData(scriptId);
    if (!canvas || !series || typeof Chart === "undefined") return;
    var options = baseOptions();
    var chart = new Chart(canvas, {
      type: "bar",
      data: {
        labels: series.map(function (row) { return row.label; }),
        datasets: [
          {
            label: "Pemasukan",
            data: series.map(function (row) { return row.income; }),
            backgroundColor: "#24884a",
            borderRadius: 5,
            maxBarThickness: 18,
          },
          {
            label: "Pengeluaran",
            data: series.map(function (row) { return row.expense; }),
            backgroundColor: "#b8933f",
            borderRadius: 5,
            maxBarThickness: 18,
          },
        ],
      },
      options: options,
    });
    chart.draw();
    return chart;
  };

  window.renderDoughnutChart = function (canvasId, scriptId) {
    var canvas = document.getElementById(canvasId);
    var rows = chartData(scriptId);
    if (!canvas || !rows || typeof Chart === "undefined") return;
    var palette = ["#14532d", "#24884a", "#5aa56f", "#b8933f", "#7c6120", "#0f3a22"];
    var chart = new Chart(canvas, {
      type: "doughnut",
      data: {
        labels: rows.map(function (row) { return row.name; }),
        datasets: [{
          data: rows.map(function (row) { return row.total; }),
          backgroundColor: palette,
          borderWidth: 0,
          hoverOffset: 4,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        cutout: "66%",
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: "#0f3a22",
            padding: 10,
            cornerRadius: 8,
            callbacks: {
              label: function (context) {
                return context.label + ": " + formatIDR(context.parsed);
              },
            },
          },
        },
      },
    });
    chart.draw();
    return chart;
  };

  window.renderProjectionChart = function (canvasId, scriptId, projected) {
    var canvas = document.getElementById(canvasId);
    var series = chartData(scriptId);
    if (!canvas || !series || typeof Chart === "undefined") return;
    var labels = series.map(function (row) { return row.label; });
    var balances = [];
    var running = 0;
    series.forEach(function (row) {
      running += row.income - row.expense;
      balances.push(running);
    });
    labels.push("Proyeksi");
    balances.push(projected);
    var chart = new Chart(canvas, {
      type: "line",
      data: {
        labels: labels,
        datasets: [{
          label: "Saldo kumulatif",
          data: balances,
          borderColor: "#24884a",
          backgroundColor: "rgba(36, 136, 74, 0.10)",
          fill: true,
          tension: 0.35,
          pointRadius: 3,
          pointBackgroundColor: "#14532d",
        }],
      },
      options: (function () {
        var options = baseOptions();
        options.scales.x.ticks.color = "#63706a";
        return options;
      })(),
    });
    chart.draw();
    return chart;
  };
})();
