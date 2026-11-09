/* KOSPI Lens. No client-side data provider or hidden API credentials. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const nf = new Intl.NumberFormat("en-US");
  const compact = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });
  let snapshot = null;
  let matching = [];
  let page = 1;
  const pageSize = 40;
  let sort = { col: "market_cap_bn", dir: -1 };
  const cols = ["name", "sector", "market_cap_bn", "price", "change_pct", "volume", "pe", "pb", "assets_bn", "report_date"];
  const filters = ["sectorSelect", "assetsMin", "marketCapMin", "peMax", "pbMax", "profitableOnly", "searchBox"];

  function escapeText(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }
  const titleAttr = value => escapeText(value || "Not reported");
  function decimal(value, digits = 1) {
    if (value == null || !Number.isFinite(+value)) return "—";
    return new Intl.NumberFormat("en-US", { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(+value);
  }
  function median(list) {
    const v = list.filter(x => Number.isFinite(x) && x > 0).sort((a,b) => a-b);
    if (!v.length) return null;
    return v.length % 2 ? v[(v.length - 1) / 2] : (v[v.length/2 - 1] + v[v.length/2]) / 2;
  }
  function formatDate(iso) {
    if (!iso) return "Not filed";
    const date = String(iso).split("T")[0];
    return /^\d{4}-\d{2}-\d{2}$/.test(date) ? date.replaceAll("-", ".") : date;
  }
  function renderTop() {
    const demo = snapshot.mode !== "live";
    $("demoBanner").hidden = !demo;
    $("sourceMode").textContent = demo ? "Illustrative demo · NOT LIVE" : "KRX + DART · Saved daily snapshot";
    $("priceDate").textContent = demo ? `SAMPLE DATE ${formatDate(snapshot.price_date)}` : `EOD CLOSE ${formatDate(snapshot.price_date)}`;
    $("financialPeriod").textContent = "PER-ISSUER PERIODS";
    $("snapshotStatus").textContent = snapshot.partial ? "PARTIAL DATASET" : demo ? "SYNTHETIC EXAMPLES" : "SAVED DAILY SNAPSHOT";
    $("lastUpdated").textContent = `SNAPSHOT ${formatDate(snapshot.generated_at)}`;
    if (snapshot.partial && !demo) $("sourceMode").textContent += " · PARTIAL COVERAGE";
  }
  function initSectors() {
    const sectors = [...new Set(snapshot.companies.map(r => r.sector || "Other / Unclassified"))].sort();
    $("sectorSelect").innerHTML = `<option value="all">All sectors</option>` + sectors.map(s => `<option value="${escapeText(s)}">${escapeText(s)}</option>`).join("");
  }
  function filterSort() {
    if (!snapshot) return;
    const term = $("searchBox").value.trim().toLowerCase();
    const sector = $("sectorSelect").value;
    const minAssets = Math.max(200, +$("assetsMin").value || 200);
    const minCap = Math.max(0, +$("marketCapMin").value || 0);
    const maxPE = $("peMax").value ? +$("peMax").value : Infinity;
    const maxPB = $("pbMax").value ? +$("pbMax").value : Infinity;
    const profitable = $("profitableOnly").checked;
    matching = snapshot.companies.filter(r => {
      if (sector !== "all" && r.sector !== sector) return false;
      if (!(r.assets_bn > minAssets || (minAssets === 200 && r.assets_bn > 200))) return false;
      if (!(r.market_cap_bn >= minCap)) return false;
      if (maxPE !== Infinity && (r.pe == null || !(r.pe <= maxPE))) return false;
      if (maxPB !== Infinity && (r.pb == null || !(r.pb <= maxPB))) return false;
      if (profitable && !(r.earnings_bn > 0)) return false;
      if (term && ![r.name, r.name_en, r.ticker, r.industry, r.sector].some(v => String(v || "").toLowerCase().includes(term))) return false;
      return true;
    });
    matching.sort((a,b) => {
      let aa = a[sort.col], bb = b[sort.col];
      if (aa == null && bb == null) return a.ticker.localeCompare(b.ticker);
      if (aa == null) return 1;
      if (bb == null) return -1;
      if (typeof aa === "string") return sort.dir * aa.localeCompare(bb, "ko");
      return sort.dir * (aa-bb);
    });
    page = Math.max(1, Math.min(page, Math.ceil(matching.length / pageSize) || 1));
    renderCards(); renderTable(); renderSectors(); renderSort();
  }
  function renderCards() {
    $("resultCount").textContent = nf.format(matching.length);
  }
  function makeRow(r) {
    const name = escapeText(r.name);
    const ticker = escapeText(r.ticker);
    const official = /^\d{6}$/.test(String(r.ticker)) ? `https://finance.naver.com/item/main.naver?code=${ticker}` : "#";
    const sector = escapeText(r.sector || "Unclassified");
    const industry = `${r.industry || "Unclassified"}${r.industry_code ? ` · KSIC ${r.industry_code}` : ""}`;
    const change = +r.change_pct || 0;
    const changeClass = change > 0 ? "up" : change < 0 ? "down" : "flat";
    const changeStr = `${change > 0 ? "+" : ""}${decimal(change,2)}%`;
    const peTag = r.pe != null && r.earnings_basis ? `<span class="metric-tag ${r.earnings_basis === "FY" ? "fy" : ""}">${escapeText(r.earnings_basis)}</span>` : "";
    const peTip = `${r.earnings_period || "Earnings basis unavailable"}\nParent-attributable net income: ${r.earnings_bn == null ? "Not available" : decimal(r.earnings_bn,3)+" KRW bn"}`;
    const pbTip = `Book equity: ${r.equity_bn == null ? "Not available" : decimal(r.equity_bn,3)+" KRW bn"}\nStatement basis: ${r.statement_basis || "Not reported"}`;
    const report = r.report_period || "Not available";
    return `<tr>
      <td class="company-column"><div class="stock-id"><a class="stock-name" href="${official}" target="_blank" rel="noopener noreferrer" title="${titleAttr(r.name_en || r.name)} · Open Naver Finance">${name}<span class="stock-link-icon">↗</span></a><span class="stock-ticker">${ticker}</span></div></td>
      <td><span class="sector-pill" title="${titleAttr(industry)}">${sector}</span></td>
      <td class="number-cell">${decimal(r.market_cap_bn,0)}</td>
      <td class="number-cell">${nf.format(r.price)}</td>
      <td class="number-cell"><span class="change ${changeClass}">${changeStr}</span></td>
      <td class="number-cell">${r.volume == null ? "—" : compact.format(r.volume)}</td>
      <td class="number-cell" title="${titleAttr(peTip)}"><div class="metric-cell">${r.pe == null ? "<span class='muted-val'>N/M</span>" : `${decimal(r.pe,1)}x`}${peTag}</div></td>
      <td class="number-cell" title="${titleAttr(pbTip)}">${r.pb == null ? "<span class='muted-val'>N/M</span>" : `${decimal(r.pb,2)}x`}</td>
      <td class="number-cell">${decimal(r.assets_bn,0)}</td>
      <td class="number-cell end-col" title="${titleAttr('Statement basis: '+(r.statement_basis || 'Unknown'))}"><span class="period-val">${escapeText(report)}</span><span class="period-small">${formatDate(r.report_date)}</span></td>
    </tr>`;
  }
  function renderTable() {
    const pages = Math.max(1, Math.ceil(matching.length / pageSize));
    const start = (page-1)*pageSize;
    $("tableBody").innerHTML = matching.length ? matching.slice(start,start+pageSize).map(makeRow).join("") : `<tr><td class="empty-state" colspan="10">No companies match the current filters. Try widening your criteria.</td></tr>`;
    $("displayFoot").textContent = matching.length ? `Showing ${nf.format(start+1)}–${nf.format(Math.min(start+pageSize, matching.length))} of ${nf.format(matching.length)} matching companies` : "No matching companies";
    $("pageLabel").textContent = `${page} / ${pages}`;
    $("pagePrev").disabled = page <= 1;
    $("pageNext").disabled = page >= pages;
  }
  function renderSectors() {
    const counts = new Map();
    matching.forEach(r => counts.set(r.sector || "Other", (counts.get(r.sector || "Other") || 0) + 1));
    const array = [...counts.entries()].sort((a,b)=>b[1]-a[1]);
    $("sectorsCount").textContent = `${counts.size} sectors`;
    const top = array.slice(0,6);
    const max = Math.max(1, ...top.map(s=>s[1]));
    $("sectorBars").innerHTML = top.length ? top.map(([sector,count]) => `<button class="sector-entry" data-sector="${escapeText(sector)}" title="Filter to ${escapeText(sector)}"><span class="sector-title">${escapeText(sector)}</span><span class="sector-bar-bg"><span class="sector-bar-fill" style="display:block;width:${Math.round(100*count/max)}%"></span></span><span class="sector-count">${count}</span></button>`).join("") : `<span class="stat-sub">No sectors in current selection</span>`;
    $("sectorBars").querySelectorAll("[data-sector]").forEach(btn => btn.addEventListener("click", () => {
      $("sectorSelect").value = btn.dataset.sector;
      page = 1; filterSort(); window.scrollTo({top:0,behavior:"smooth"});
    }));
  }
  function renderSort() {
    document.querySelectorAll(".equities-table thead th[data-sort]").forEach(th => {
      const active = th.dataset.sort === sort.col;
      th.classList.toggle("active-sort", active);
      const arrow = th.querySelector(".sort-arrows");
      if (arrow) arrow.textContent = active ? (sort.dir === 1 ? "↑" : "↓") : "↕";
      th.setAttribute("aria-sort", active ? sort.dir === 1 ? "ascending" : "descending" : "none");
    });
  }
  function exportCSV() {
    if (!snapshot) return;
    const fields = [
      ["Ticker",r=>r.ticker],["Company (Korean)",r=>r.name],["Company (English)",r=>r.name_en],
      ["Sector (KSIC mapped)",r=>r.sector],["Industry",r=>r.industry],["KSIC",r=>r.industry_code],
      ["Market cap (KRW bn)",r=>r.market_cap_bn],["Close (KRW)",r=>r.price],
      ["Daily change (%)",r=>r.change_pct],["Volume (shares)",r=>r.volume],["P/E (x)",r=>r.pe],["P/E basis",r=>r.earnings_basis],
      ["P/E earnings period",r=>r.earnings_period],["P/B (x)",r=>r.pb],
      ["Assets (KRW bn)",r=>r.assets_bn],["Owners equity (KRW bn)",r=>r.equity_bn],
      ["Net income (KRW bn)",r=>r.earnings_bn],["Statement type",r=>r.statement_basis],
      ["Financial report",r=>r.report_period],["Financial period end",r=>r.report_date],
      ["Price date",r=>r.price_date],["Naver Finance",r=>r.naver_url],
      ["Data mode",()=>snapshot.mode],
    ];
    const quote = value => `"${String(value == null ? "" : value).replaceAll('"','""')}"`;
    const rows = [fields.map(f=>quote(f[0])).join(","),...matching.map(r => fields.map(f=>quote(f[1](r))).join(","))];
    const blob = new Blob(["\ufeff"+rows.join("\r\n")],{type:"text/csv;charset=utf-8;"});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");a.href=url;a.download=`kospi_screener_${snapshot.mode}_${snapshot.price_date||'snapshot'}.csv`;document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url);
  }
  function reset() {
    $("sectorSelect").value="all";$("assetsMin").value="200";$("marketCapMin").value="";$("peMax").value="";$("pbMax").value="";$("profitableOnly").checked=false;$("searchBox").value="";
    sort={col:"market_cap_bn",dir:-1};page=1;filterSort();
  }
  function openMethod(){const d=$("methodModal");if(!d.open)d.showModal();}
  function wire() {
    filters.forEach(id => $(id).addEventListener((id === "profitableOnly" || id === "sectorSelect") ? "change" : "input",()=>{page=1;filterSort();}));
    $("clearFilters").addEventListener("click",reset);
    document.querySelectorAll(".equities-table thead th[data-sort]").forEach(th=>th.querySelector("button").addEventListener("click",()=>{
      const col=th.dataset.sort;if (!cols.includes(col)) return;
      sort=sort.col===col?{col,dir:sort.dir*-1}:{col,dir:(col==="name"||col==="sector"||col==="report_date")?1:-1};page=1;filterSort();
    }));
    $("pagePrev").addEventListener("click",()=>{page--;renderTable();});
    $("pageNext").addEventListener("click",()=>{page++;renderTable();});
    $("exportCSV").addEventListener("click",exportCSV);
    ["nav-method","helpTop","columnsHelp","openMethod","demoDetails"].forEach(id=>$(id).addEventListener("click",openMethod));
    ["closeModal","modalDone"].forEach(id=>$(id).addEventListener("click",()=>$("methodModal").close()));
    $("methodModal").addEventListener("click",e=>{if(e.target===$("methodModal"))$("methodModal").close();});
  }
  async function load(){
    wire();
    try{
      // Standalone preview reads its embedded data directly. The hosted app fetches
      // the API as normal. This deliberately avoids network requests from file://.
      let data;
      if (window.__KOSPI_EMBEDDED_SNAPSHOT__ && Array.isArray(window.__KOSPI_EMBEDDED_SNAPSHOT__.companies)) {
        data = window.__KOSPI_EMBEDDED_SNAPSHOT__;
      } else {
        const response = await fetch("./data/stocks.json", {cache:"no-store"});
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        data = await response.json();
      }
      if (!data || !Array.isArray(data.companies)) throw new Error("Invalid snapshot structure");
      snapshot=data;initSectors();renderTop();filterSort();
    }catch(err){
      $("tableBody").innerHTML=`<tr class="loading-row"><td colspan="10">Could not load the data snapshot. Run the GitHub Actions refresh workflow and check its logs.</td></tr>`;
      $("snapshotStatus").textContent="DATA UNAVAILABLE";
      console.error("Screener loading error:",err);
    }
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",load);else load();
})();
