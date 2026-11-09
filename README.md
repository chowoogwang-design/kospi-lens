# KOSPI Lens — GitHub Pages edition

**No Render, Vercel, or running server is required.** GitHub Pages hosts `site/` and GitHub Actions runs the Python refresh on weekdays at **19:00 KST** (10:00 UTC). Prices are **latest available daily closes**, not intraday prices. No historical/real-market data is bundled. The site initially shows an empty universe until the first successful API refresh.

## Publish

1. Create a GitHub repository named `kospi-lens` (public repository on GitHub Free). Upload the **contents** of this folder, including `.github/workflows/pages.yml`, to its `main` branch.
2. In repository **Settings → Secrets and variables → Actions**, add repository secrets `KRX_API_KEY` and `DART_API_KEY`. KRX requires explicit approval for **KOSPI daily trading data**; having a general API key alone may not grant access. OpenDART is at https://opendart.fss.or.kr/ .
3. In **Settings → Pages**, set **Build and deployment → Source → GitHub Actions**.
4. In **Actions → Refresh and publish screener → Run workflow**, trigger the initial data import. Check the workflow logs. The first full KOSPI data refresh may need considerable API time, rate-limit allowance, and DART financial-account caching; a scheduled workflow has a 180-minute job limit here, not a guarantee of completion.
5. Once successful, visit `https://YOUR_USERNAME.github.io/kospi-lens/` (use the URL displayed by GitHub Pages).

**Important:** Every GitHub Pages website is public even when a paid-plan repository is private. Do not use this for proprietary internal investment research or market data requiring restricted redistribution; secure GitHub secrets hide keys from the published site, **not the dataset**. Check KRX's display/redistribution rules. GitHub Pages is not a secure internal hosting system and does not provide password protection.

## Data definitions

- Market capitalization and closing price from KRX, end-of-day, same session as volume and 1-day change.
- P/E = KRX **common-class** market cap ÷ trailing owner-attributable net profit; LTM equals FY + latest YTD − prior year's comparable YTD, otherwise explicit FY basis.
- P/B = common-class market cap ÷ latest parent-attributable book equity.
- Assets = latest available consolidated assets (fallback to individual statements), **not LTM**; universe requires assets strictly above KRW 200bn.
- Industry approximated from DART KSIC. Naver links open issuer details.
- **Preferred-share limitation:** Common-class market cap excludes other listed classes, so P/E/P/B are indicative for issuers with preferred shares.

## Architecture

`site/` static frontend, `site/data/stocks.json` generated snapshot. `app/` Python ETL executed only by GitHub Actions. **No server is running on Pages.** The workflow invokes the existing KRX/OpenDART integration code, but its authenticated API operations have not been validated with keys in this environment. If an authenticated refresh fails, Actions fails rather than publishing fabricated "live" data. GitHub Actions scheduled jobs can be delayed or skipped during high load. 

For local tests: `pip install -r requirements.txt && python -m unittest discover -s tests -v`.

Official references: https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site and https://docs.github.com/en/actions
