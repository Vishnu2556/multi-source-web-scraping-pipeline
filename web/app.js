/**
 * DataScrape Studio Frontend Application Logic
 */

let currentPage = 1;
let currentPageSize = 25;
let currentSource = "all";
let currentCategory = "all";
let currentRating = "all";
let currentSearch = "";
let searchDebounceTimer = null;

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initModals();
  initDataExplorer();
  loadSummary();
  loadTableData();
  initLogs();
});

/* ==========================================================================
   Tab Navigation
   ========================================================================== */

function initTabs() {
  const tabs = document.querySelectorAll(".tab-btn");

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      document
        .querySelectorAll(".tab-pane")
        .forEach((p) => p.classList.remove("active"));

      tab.classList.add("active");

      const targetId = tab.dataset.tab;
      const targetPane = document.getElementById(targetId);

      if (targetPane) targetPane.classList.add("active");

      if (targetId === "tab-logs") {
        loadLogs();
      }
    });
  });
}

/* ==========================================================================
   Summary Report & KPI Metrics (Real Backend Data)
   ========================================================================== */

async function loadSummary() {
  try {
    const res = await fetch("/api/summary");

    if (!res.ok) throw new Error("Failed to load summary");

    const data = await res.json();

    const overall = data.overall || {};
    const books = data.books || {};
    const quotes = data.quotes || {};
    const quality = data.data_quality_metrics || {};

    // 1. Total Consolidated
    document.getElementById("kpiTotalRecords").textContent =
      (overall.final_record_count || 0).toLocaleString();

    // 2. Books Count & Sub-label
    document.getElementById("kpiBooksCount").textContent = (
      books.final_records !== undefined
        ? books.final_records
        : books.records_collected || 0
    ).toLocaleString();

    if (document.getElementById("kpiBooksSub")) {
      const p =
        books.pages_scraped !== undefined
          ? `${books.pages_scraped} pages`
          : "Catalogue";

      document.getElementById("kpiBooksSub").textContent =
        `${p} (${books.records_collected || 0} scraped)`;
    }

    // 3. Quotes Count & Sub-label
    document.getElementById("kpiQuotesCount").textContent = (
      quotes.final_records !== undefined
        ? quotes.final_records
        : quotes.records_collected || 0
    ).toLocaleString();

    if (document.getElementById("kpiQuotesSub")) {
      const p =
        quotes.pages_scraped !== undefined
          ? `${quotes.pages_scraped} pages`
          : "Quotes";

      document.getElementById("kpiQuotesSub").textContent =
        `${p} (${quotes.records_collected || 0} scraped)`;
    }

    // 4. Duplicates Count & Sub-label
    document.getElementById("kpiDuplicatesCount").textContent =
      (overall.total_duplicates || 0).toLocaleString();

    if (document.getElementById("kpiDuplicatesSub")) {
      document.getElementById("kpiDuplicatesSub").textContent =
        data.deduplication_mode === "flag"
          ? "Flagged (is_duplicate=True)"
          : "Filtered & removed";
    }

    // 5. Validation Pass Rate & Sub-label
    const vRate =
      overall.validation_rate !== undefined
        ? overall.validation_rate
        : 100.0;

    document.getElementById("kpiValidationRate").textContent = `${vRate}%`;

    if (document.getElementById("kpiValidationSub")) {
      document.getElementById("kpiValidationSub").textContent =
        `${overall.total_records_rejected || 0} rejected / ${overall.total_records_cleaned || 0
        } cleaned`;
    }

    // 6. Execution Duration & Sub-label
    const dur =
      data.execution_time_seconds !== undefined
        ? `${data.execution_time_seconds}s`
        : "-";

    document.getElementById("kpiDuration").textContent = dur;

    if (document.getElementById("kpiDurationSub")) {
      document.getElementById("kpiDurationSub").textContent =
        data.execution_mode || "Multi-source crawl";
    }

    // Source-Aware Field Completeness Bars
    renderSourceAwareCompleteness(
      quality.source_aware_completeness || {}
    );

    // Statistical Distributions
    renderStatMetrics(quality);
  } catch (err) {
    console.warn("Summary load issue:", err);
  }
}

function renderSourceAwareCompleteness(sourceAware) {
  const container = document.getElementById("completenessBars");

  if (!container) return;

  container.innerHTML = "";

  const booksComp = sourceAware.books || {};
  const quotesComp = sourceAware.quotes || {};

  const fields = [
    { label: "Book Title (Books)", val: booksComp.name_or_title },
    { label: "Book Category (Books)", val: booksComp.category },
    { label: "Book Price (Books)", val: booksComp.price },
    { label: "Book Rating (Books)", val: booksComp.rating },
    { label: "Book Availability (Books)", val: booksComp.availability },
    { label: "Quote Text (Quotes)", val: quotesComp.name_or_title },
    { label: "Quote Author (Quotes)", val: quotesComp.author },
    { label: "Quote Tags (Quotes)", val: quotesComp.tags },
  ];

  fields.forEach(({ label, val }) => {
    const isNA =
      val === undefined ||
      val === null ||
      val === "N/A";

    const pct = isNA ? 0 : parseFloat(val);
    const displayVal = isNA ? "N/A" : `${pct}%`;

    const row = document.createElement("div");

    row.className = "bar-row";

    row.innerHTML = `
      <span class="bar-label">${label}</span>

      <div class="bar-track">
        <div
          class="bar-fill"
          style="width: ${pct}%; background: ${isNA ? "rgba(255,255,255,0.1)" : ""
      }"
        ></div>
      </div>

      <span
        class="bar-pct"
        style="${isNA ? "color: var(--text-muted);" : ""}"
      >${displayVal}</span>
    `;

    container.appendChild(row);
  });
}

function renderStatMetrics(quality) {
  const container = document.getElementById("statMetricsList");

  if (!container) return;

  container.innerHTML = "";

  const priceStats = quality.numeric_price_statistics || {};
  const ratingStats = quality.numeric_rating_statistics || {};

  const metrics = [
    {
      label: "Avg Book Price",
      value: priceStats.avg
        ? `£${priceStats.avg.toFixed(2)}`
        : "N/A",
    },
    {
      label: "Book Price Range",
      value:
        priceStats.min !== undefined
          ? `£${priceStats.min} – £${priceStats.max}`
          : "N/A",
    },
    {
      label: "Avg Book Rating",
      value: ratingStats.avg
        ? `★ ${ratingStats.avg.toFixed(2)} / 5`
        : "N/A",
    },
    {
      label: "Total Books Evaluated",
      value: priceStats.count
        ? priceStats.count.toLocaleString()
        : "N/A",
    },
  ];

  metrics.forEach((m) => {
    const item = document.createElement("div");

    item.className = "stat-item";

    item.innerHTML = `
      <div class="stat-item-label">${m.label}</div>
      <div class="stat-item-value">${m.value}</div>
    `;

    container.appendChild(item);
  });
}

/* ==========================================================================
   Dataset Explorer Table, Filtering & Pagination
   ========================================================================== */

function initDataExplorer() {
  const searchInput = document.getElementById("searchInput");
  const sourceFilter = document.getElementById("filterSource");
  const categoryFilter = document.getElementById("filterCategory");
  const ratingFilter = document.getElementById("filterRating");
  const pageSizeSelect = document.getElementById("filterPageSize");
  const btnPrev = document.getElementById("btnPrevPage");
  const btnNext = document.getElementById("btnNextPage");

  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      clearTimeout(searchDebounceTimer);

      searchDebounceTimer = setTimeout(() => {
        currentSearch = e.target.value.trim();
        currentPage = 1;
        loadTableData();
      }, 300);
    });
  }

  if (sourceFilter) {
    sourceFilter.addEventListener("change", (e) => {
      currentSource = e.target.value;
      currentPage = 1;
      loadTableData();
    });
  }

  if (categoryFilter) {
    categoryFilter.addEventListener("change", (e) => {
      currentCategory = e.target.value;
      currentPage = 1;
      loadTableData();
    });
  }

  if (ratingFilter) {
    ratingFilter.addEventListener("change", (e) => {
      currentRating = e.target.value;
      currentPage = 1;
      loadTableData();
    });
  }

  if (pageSizeSelect) {
    pageSizeSelect.addEventListener("change", (e) => {
      currentPageSize = parseInt(e.target.value, 10);
      currentPage = 1;
      loadTableData();
    });
  }

  if (btnPrev) {
    btnPrev.addEventListener("click", () => {
      if (currentPage > 1) {
        currentPage--;
        loadTableData();
      }
    });
  }

  if (btnNext) {
    btnNext.addEventListener("click", () => {
      currentPage++;
      loadTableData();
    });
  }
}

async function loadTableData() {
  const tbody = document.getElementById("tableBody");

  if (!tbody) return;

  tbody.innerHTML = `
    <tr>
      <td colspan="7" class="loading-state">
        Loading records...
      </td>
    </tr>
  `;

  const url =
    `/api/data?page=${currentPage}` +
    `&page_size=${currentPageSize}` +
    `&source=${currentSource}` +
    `&category=${encodeURIComponent(currentCategory)}` +
    `&rating=${currentRating}` +
    `&q=${encodeURIComponent(currentSearch)}`;

  try {
    const res = await fetch(url);

    if (!res.ok) {
      throw new Error("Failed to fetch data");
    }

    const data = await res.json();

    const records = data.records || [];
    const total = data.total || 0;
    const totalPages = data.total_pages || 1;

    updateCategoryDropdown(data.categories || []);

    renderTableRows(records);

    const startRecord =
      total > 0
        ? (currentPage - 1) * currentPageSize + 1
        : 0;

    const endRecord = Math.min(
      currentPage * currentPageSize,
      total
    );

    document.getElementById(
      "paginationInfo"
    ).textContent =
      `Showing ${startRecord}-${endRecord} of ${total.toLocaleString()} records`;

    document.getElementById(
      "pageIndicator"
    ).textContent =
      `Page ${currentPage} of ${totalPages}`;

    document.getElementById("btnPrevPage").disabled =
      currentPage <= 1;

    document.getElementById("btnNextPage").disabled =
      currentPage >= totalPages;
  } catch (err) {
    tbody.innerHTML = `
      <tr>
        <td
          colspan="7"
          style="
            color: var(--accent-rose);
            text-align:center;
            padding: 24px;
          "
        >
          Failed to load dataset: ${err.message}
        </td>
      </tr>
    `;
  }
}

function updateCategoryDropdown(categories) {
  const select = document.getElementById("filterCategory");

  if (!select || select.options.length > 1) return;

  categories.forEach((cat) => {
    const opt = document.createElement("option");

    opt.value = cat;
    opt.textContent = cat;

    select.appendChild(opt);
  });
}

function renderTableRows(records) {
  const tbody = document.getElementById("tableBody");

  if (!tbody) return;

  if (records.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td
          colspan="7"
          style="
            text-align: center;
            color: var(--text-muted);
            padding: 32px;
          "
        >
          No matching records found.
        </td>
      </tr>
    `;

    return;
  }

  tbody.innerHTML = "";

  records.forEach((row) => {
    const tr = document.createElement("tr");

    const isBook = row.source === "Books to Scrape";
    const badgeClass = isBook
      ? "badge-books"
      : "badge-quotes";

    let ratingHtml = `
      <span style="color: var(--text-muted);">-</span>
    `;

    if (row.rating) {
      const numStars = Math.round(parseFloat(row.rating));

      ratingHtml = `
        <span class="rating-stars">
          ${"★".repeat(numStars)}
          ${"☆".repeat(5 - numStars)}
        </span>
      `;
    }

    const priceHtml = row.price
      ? `
        <span class="price-tag">
          £${parseFloat(row.price).toFixed(2)}
        </span>
      `
      : `
        <span style="color: var(--text-muted);">-</span>
      `;

    const title = row.name_or_title || "";

    const titleSnippet =
      title.length > 70
        ? `${title.slice(0, 70)}...`
        : title;

    tr.innerHTML = `
      <td>
        <span class="badge ${badgeClass}">
          ${row.source}
        </span>
      </td>

      <td>
        <strong>${escapeHtml(titleSnippet)}</strong>
      </td>

      <td>${priceHtml}</td>

      <td>${ratingHtml}</td>

      <td>
        ${row.author
        ? escapeHtml(row.author)
        : `<span style="color: var(--text-muted);">-</span>`
      }
      </td>

      <td>
        ${row.category
        ? `
              <span class="badge badge-tag">
                ${escapeHtml(row.category)}
              </span>
            `
        : `
              <span style="color: var(--text-muted);">-</span>
            `
      }
      </td>

      <td>
        <button
          class="btn btn-outline btn-sm btn-view-detail"
          style="padding: 4px 8px; font-size: 0.75rem;"
        >
          View
        </button>
      </td>
    `;

    tr
      .querySelector(".btn-view-detail")
      .addEventListener("click", () => {
        openRecordDetail(row);
      });

    tbody.appendChild(tr);
  });
}
function openRecordDetail(row) {
  const modal = document.getElementById("detailModal");
  const modalBody = document.getElementById("modalBody");
  const modalTitle = document.getElementById("modalTitle");

  modalTitle.textContent =
    `${row.source}: Record Details`;

  let fieldsHtml = `
    <div class="modal-field">
      <div class="modal-field-label">
        Title / Quote
      </div>

      <div
        class="modal-field-value"
        style="font-weight: 600; font-size: 1.05rem;"
      >
        ${escapeHtml(row.name_or_title)}
      </div>
    </div>
  `;

  if (row.author) {
    fieldsHtml += `
      <div class="modal-field">
        <div class="modal-field-label">
          Author
        </div>

        <div class="modal-field-value">
          ${escapeHtml(row.author)}
        </div>
      </div>
    `;
  }

  if (row.category) {
    fieldsHtml += `
      <div class="modal-field">
        <div class="modal-field-label">
          Category / Genre
        </div>

        <div class="modal-field-value">
          <span class="badge badge-tag">
            ${escapeHtml(row.category)}
          </span>
        </div>
      </div>
    `;
  }

  if (row.price) {
    fieldsHtml += `
      <div class="modal-field">
        <div class="modal-field-label">
          Price
        </div>

        <div
          class="modal-field-value price-tag"
          style="font-size: 1.1rem;"
        >
          £${parseFloat(row.price).toFixed(2)}
        </div>
      </div>
    `;
  }

  if (row.rating) {
    const stars = Math.round(parseFloat(row.rating));

    fieldsHtml += `
      <div class="modal-field">
        <div class="modal-field-label">
          Rating
        </div>

        <div
          class="modal-field-value rating-stars"
          style="font-size: 1.1rem;"
        >
          ${"★".repeat(stars)}
          ${"☆".repeat(5 - stars)}
          (${row.rating} / 5.0)
        </div>
      </div>
    `;
  }

  if (row.availability) {
    fieldsHtml += `
      <div class="modal-field">
        <div class="modal-field-label">
          Availability
        </div>

        <div class="modal-field-value">
          ${escapeHtml(row.availability)}
        </div>
      </div>
    `;
  }

  if (row.tags) {
    fieldsHtml += `
      <div class="modal-field">
        <div class="modal-field-label">
          Tags
        </div>

        <div class="modal-field-value">
          ${escapeHtml(row.tags)}
        </div>
      </div>
    `;
  }

  if (row.description) {
    fieldsHtml += `
      <div class="modal-field">
        <div class="modal-field-label">
          Description / Synopsis
        </div>

        <div
          class="modal-field-value"
          style="
            color: var(--text-secondary);
            line-height: 1.6;
          "
        >
          ${escapeHtml(row.description)}
        </div>
      </div>
    `;
  }

  fieldsHtml += `
    <div class="modal-field">
      <div class="modal-field-label">
        Source URL
      </div>

      <div class="modal-field-value">
        <a
          href="${row.source_url}"
          target="_blank"
          rel="noopener noreferrer"
          style="
            color: #818cf8;
            text-decoration: underline;
            word-break: break-all;
          "
        >
          ${escapeHtml(row.source_url)}
        </a>
      </div>
    </div>

    <div class="modal-field">
      <div class="modal-field-label">
        Scraped At (UTC)
      </div>

      <div
        class="modal-field-value"
        style="
          font-family: var(--font-mono);
          font-size: 0.85rem;
          color: var(--text-muted);
        "
      >
        ${escapeHtml(row.scraped_at)}
      </div>
    </div>
  `;

  modalBody.innerHTML = fieldsHtml;

  modal.classList.add("open");
}

/* ==========================================================================
   Modals & Scraper Trigger
   ========================================================================== */

function initModals() {
  const detailModal =
    document.getElementById("detailModal");

  const btnDetailClose =
    document.getElementById("btnDetailClose");

  if (btnDetailClose) {
    btnDetailClose.addEventListener("click", () => {
      detailModal.classList.remove("open");
    });
  }

  const runModal =
    document.getElementById("runModal");

  const btnRunModal =
    document.getElementById("btnRunModal");

  const btnRunClose =
    document.getElementById("btnRunClose");

  const btnRunCancel =
    document.getElementById("btnRunCancel");

  const runForm =
    document.getElementById("runForm");

  if (btnRunModal) {
    btnRunModal.addEventListener("click", () => {
      runModal.classList.add("open");
    });
  }

  if (btnRunClose) {
    btnRunClose.addEventListener("click", () => {
      runModal.classList.remove("open");
    });
  }

  if (btnRunCancel) {
    btnRunCancel.addEventListener("click", () => {
      runModal.classList.remove("open");
    });
  }

  // Close modals when clicking backdrop
  window.addEventListener("click", (e) => {
    if (e.target === detailModal) {
      detailModal.classList.remove("open");
    }

    if (e.target === runModal) {
      runModal.classList.remove("open");
    }
  });

  // Handle Scraper Trigger Form
  if (runForm) {
    runForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const sourceVal =
        document.getElementById("runSources").value;

      const sources =
        sourceVal === "all"
          ? ["books", "quotes"]
          : [sourceVal];

      const maxPages =
        parseInt(
          document.getElementById("runMaxPages").value,
          10
        );

      const dedupAction =
        document.getElementById("runDedupAction").value;

      runModal.classList.remove("open");

      setPipelineStatus(
        true,
        "Scraping in progress..."
      );

      try {
        const res = await fetch("/api/run", {
          method: "POST",

          headers: {
            "Content-Type": "application/json",
          },

          body: JSON.stringify({
            sources,
            max_pages: maxPages,
            dedup_action: dedupAction,
          }),
        });

        const result = await res.json();

        /*
         * IMPORTANT:
         * The backend can return:
         *
         * 1. Normal local execution:
         *    {
         *      status: "success"
         *    }
         *
         * 2. Vercel demo mode:
         *    {
         *      status: "success",
         *      mode: "demo",
         *      final_record_count: 1099
         *    }
         *
         * Both are successful responses.
         */

        if (result.status === "success") {
          setPipelineStatus(
            false,
            "Pipeline Ready"
          );

          // Refresh dashboard information
          await loadSummary();

          // Refresh dataset table
          await loadTableData();

          // Refresh logs
          await loadLogs();

          /*
           * Vercel Demo Mode
           *
           * Vercel should NOT perform the live scraper because
           * serverless execution has time and filesystem limits.
           *
           * Instead, the deployed application serves the
           * pre-generated verified dataset.
           */
          if (result.mode === "demo") {
            const recordCount =
              result.final_record_count ||
              (
                result.summary &&
                result.summary.overall &&
                result.summary.overall.final_record_count
              ) ||
              1099;

            alert(
              "Demo Mode — Using Verified Dataset\n\n" +
              "The deployed Vercel application is using " +
              "the pre-generated verified dataset and " +
              "summary report.\n\n" +
              "Available records: " +
              Number(recordCount).toLocaleString() +
              "\n\n" +
              "Live scraping is available locally with:\n" +
              "python main.py"
            );

            return;
          }

          /*
           * Normal local live scraping completed.
           */
          if (result.message) {
            alert(
              "Pipeline completed successfully.\n\n" +
              result.message
            );
          }

          return;
        }

        /*
         * Backend returned an error.
         */
        setPipelineStatus(
          false,
          "Execution Error"
        );

        alert(
          "Pipeline run error: " +
          (
            result.message ||
            result.detail ||
            "Unknown error"
          )
        );

      } catch (err) {
        /*
         * Network / connection error.
         */
        console.error(
          "Pipeline execution error:",
          err
        );

        setPipelineStatus(
          false,
          "Connection Failed"
        );

        alert(
          "Failed to trigger scraper: " +
          err.message
        );
      }
    });
  }
}

function setPipelineStatus(isRunning, text) {
  const indicator =
    document.getElementById("statusIndicator");

  if (!indicator) return;

  const label =
    indicator.querySelector(".status-label");

  const dot =
    indicator.querySelector(".status-dot");

  if (label) {
    label.textContent = text;
  }

  if (isRunning) {
    indicator.style.borderColor =
      "rgba(245, 158, 11, 0.5)";

    indicator.style.backgroundColor =
      "rgba(245, 158, 11, 0.1)";

    indicator.style.color =
      "var(--accent-amber)";

    if (dot) {
      dot.style.backgroundColor =
        "var(--accent-amber)";

      dot.style.boxShadow =
        "0 0 10px var(--accent-amber)";
    }
  } else {
    indicator.style.borderColor =
      "rgba(16, 185, 129, 0.25)";

    indicator.style.backgroundColor =
      "rgba(16, 185, 129, 0.1)";

    indicator.style.color =
      "var(--accent-emerald)";

    if (dot) {
      dot.style.backgroundColor =
        "var(--accent-emerald)";

      dot.style.boxShadow =
        "0 0 10px var(--accent-emerald)";
    }
  }
}
/* ==========================================================================
   Logs Viewer
   ========================================================================== */

function initLogs() {
  const btnRefresh =
    document.getElementById("btnRefreshLogs");

  if (btnRefresh) {
    btnRefresh.addEventListener(
      "click",
      loadLogs
    );
  }
}

async function loadLogs() {
  const output =
    document.getElementById("logsOutput");

  if (!output) return;

  try {
    const res = await fetch("/api/logs");

    if (!res.ok) {
      throw new Error("Could not retrieve logs");
    }

    const data = await res.json();

    output.textContent =
      data.logs || "No logs available.";

    output.scrollTop =
      output.scrollHeight;

  } catch (err) {
    output.textContent =
      `Error loading logs: ${err.message}`;
  }
}

/* ==========================================================================
   HTML Escape Utility
   ========================================================================== */

function escapeHtml(str) {
  if (!str) return "";

  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}