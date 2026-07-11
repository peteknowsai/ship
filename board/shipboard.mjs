#!/usr/bin/env node
// shipboard — the /ship departure board, published to board.cells.md
// Polls GitHub (gh CLI) + local worktrees, renders one HTML page, puts it to R2.
// Usage: node shipboard.mjs           render + upload
//        node shipboard.mjs --dry     render to /tmp/shipboard.html, no upload
// Runs on Pete's Mac (needs local worktrees + gh + wrangler auth). launchd runs
// it every 60s — see board/md.cells.shipboard.plist.

import { execFileSync } from "node:child_process";
import { readFileSync, existsSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

const REPOS = [
  {
    name: "homezero",
    path: join(homedir(), "Projects/Zero/homezero"),
    gh: "home0-xyz/homezero",
    lane: "dev.homezero.md",
    laneUrl: "https://dev.homezero.md",
  },
  {
    name: "ship",
    path: join(homedir(), "Projects/ship"),
    gh: "peteknowsai/ship",
    lane: "plugin cache",
    laneUrl: null,
  },
];

const BUCKET = "shipboard";
const ACCOUNT = "5a6fef07a998d84ec047ef43d0543342"; // PKAI — same account as the cells.md zone

function sh(cmd, args, opts = {}) {
  try {
    return execFileSync(cmd, args, { encoding: "utf8", timeout: 30000, ...opts });
  } catch {
    return null; // a dead source renders as "unknown", never kills the board
  }
}

function ago(iso) {
  if (!iso) return "";
  const m = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (m < 60) return `${m}m`;
  if (m < 60 * 24) return `${Math.floor(m / 60)}h ${m % 60}m`;
  return `${Math.floor(m / 1440)}d`;
}

const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// ---------- collectors ----------

function collectPRs(repo) {
  const raw = sh("gh", ["pr", "list", "-R", repo.gh, "--json", "number,title,isDraft,createdAt,url,headRefName", "--limit", "30"]);
  const prs = raw ? JSON.parse(raw) : [];
  const inLine = prs.filter((p) => !p.isDraft).sort((a, b) => a.createdAt.localeCompare(b.createdAt));
  const claims = prs.filter((p) => p.isDraft);
  return { inLine, claims };
}

function collectDeploy(repo) {
  const raw = sh("gh", ["run", "list", "-R", repo.gh, "--branch", "main", "--limit", "8", "--json", "workflowName,status,conclusion,headSha,createdAt,url"]);
  const runs = raw ? JSON.parse(raw) : [];
  return runs.find((r) => /deploy/i.test(r.workflowName)) ?? runs[0] ?? null;
}

function collectMain(repo) {
  const raw = sh("gh", ["api", `repos/${repo.gh}/commits/main`, "--jq", '{sha: .sha[0:7], msg: .commit.message | split("\n")[0], date: .commit.committer.date}']);
  return raw ? JSON.parse(raw) : null;
}

function collectWorktrees(repo) {
  const raw = sh("git", ["-C", repo.path, "worktree", "list", "--porcelain"]);
  if (!raw) return [];
  const out = [];
  let cur = {};
  for (const line of raw.split("\n")) {
    if (line.startsWith("worktree ")) cur = { path: line.slice(9) };
    else if (line.startsWith("branch ")) cur.branch = line.slice(7).replace("refs/heads/", "");
    else if (line === "" && cur.path) { out.push(cur); cur = {}; }
  }
  if (cur.path) out.push(cur);
  return out
    .filter((w) => w.path !== repo.path && w.branch && w.branch !== "main")
    .map((w) => {
      const marker = join(w.path, ".ship-stage");
      let stage = null, mtime = null;
      if (existsSync(marker)) {
        stage = readFileSync(marker, "utf8").trim();
        mtime = sh("stat", ["-f", "%m", marker]);
      }
      return { ...w, stage, since: mtime ? new Date(Number(mtime) * 1000).toISOString() : null };
    });
}

function stageChip(stage) {
  if (!stage) return { cls: "c-line", label: "WORKTREE" };
  if (stage.startsWith("gate:")) return { cls: "c-gate", label: stage === "gate:1" ? "GATE 1 · you" : "GATE 2 · you", needsYou: true };
  if (stage.startsWith("build:")) { const [, n, m] = stage.split(":"); return { cls: "c-build", label: `BUILD ${n}/${m}` }; }
  if (stage === "review") return { cls: "c-review", label: "REVIEW" };
  if (stage === "discover") return { cls: "c-build", label: "DISCOVER" };
  if (stage === "plan") return { cls: "c-build", label: "PLAN" };
  return { cls: "c-line", label: stage.toUpperCase().slice(0, 14) };
}

function deployChip(run, repo) {
  if (repo.name === "ship") {
    try {
      const v = JSON.parse(readFileSync(join(homedir(), ".claude/plugins/installed_plugins.json"), "utf8")).plugins["ship@ship"][0].version;
      return { cls: "c-good", label: `PLUGIN ${v.slice(0, 7)}` };
    } catch { /* fall through */ }
  }
  if (!run) return { cls: "c-line", label: "NO RUNS" };
  if (run.status !== "completed") return { cls: "c-merge", label: "DEPLOYING" };
  if (run.conclusion === "success") return { cls: "c-good", label: `${repo.lane === "plugin cache" ? "GREEN" : "DEV GREEN"}` };
  return { cls: "c-bad", label: "DEV RED", needsYou: true };
}

// ---------- render ----------

function repoCard(repo) {
  const { inLine, claims } = collectPRs(repo);
  const run = collectDeploy(repo);
  const main = collectMain(repo);
  const wts = collectWorktrees(repo);
  const dep = deployChip(run, repo);

  const qRows = inLine.map((p, i) => `
    <div class="qrow">
      <div class="pos ${i === 0 ? "front" : ""}">${i + 1}</div>
      <div class="ship"><div class="t"><a href="${esc(p.url)}">#${p.number} · ${esc(p.title)}</a></div><div class="s">${esc(p.headRefName)}</div></div>
      <span class="chip ${i === 0 ? "c-merge" : "c-line"}"><span class="dot"></span>${i === 0 ? "NEXT TO LAND" : "IN LINE"}</span>
      <div class="age">${ago(p.createdAt)}</div>
    </div>`).join("");

  const claimRows = claims.map((p) => `
    <div class="qrow">
      <div class="pos">—</div>
      <div class="ship"><div class="t"><a href="${esc(p.url)}">#${p.number} · ${esc(p.title)}</a></div><div class="s">draft — claim, not in line</div></div>
      <span class="chip c-line"><span class="dot"></span>CLAIM</span>
      <div class="age">${ago(p.createdAt)}</div>
    </div>`).join("");

  const wtRows = wts.map((w) => {
    const c = stageChip(w.stage);
    return `
    <div class="qrow ${c.needsYou ? "needsyou" : ""}">
      <div class="pos">—</div>
      <div class="ship"><div class="t">${esc(w.branch)}</div><div class="s">${esc(w.path.split("/").pop())}</div></div>
      <span class="chip ${c.cls}"><span class="dot"></span>${c.label}</span>
      <div class="age">${ago(w.since)}</div>
    </div>`;
  }).join("");

  return `
  <div class="board">
    <div class="bhead">
      <span class="repo">${esc(repo.name)}</span>
      <span class="chip ${dep.cls}"><span class="dot"></span>${dep.label}</span>
      <span class="lane mono">${repo.laneUrl ? `<a href="${repo.laneUrl}">${esc(repo.lane)}</a>` : esc(repo.lane)}</span>
    </div>
    ${main ? `<div class="mainline mono">main ← ${esc(main.msg.slice(0, 64))} <span class="sha">${esc(main.sha)} · ${ago(main.date)} ago</span></div>` : ""}
    <div class="sect">In line — lands in this order</div>
    ${qRows || `<div class="quiet">Track clear — nothing waiting to land.</div>`}
    ${claimRows}
    <div class="sect">Still drafting — private worktrees</div>
    ${wtRows || `<div class="quiet">No worktrees open.</div>`}
  </div>`;
}

function page(cards) {
  const now = new Date().toLocaleString("en-US", { timeZone: "America/Denver", hour: "numeric", minute: "2-digit", month: "short", day: "numeric" });
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="60"><title>shipboard</title>
<style>
  :root{--bg:#0d1117;--surface:#161b22;--surface2:#1c2330;--line:#2d3543;--ink:#e6edf3;--ink2:#9aa7b4;--ink3:#5f6b78;
    --good:#3fb950;--warn:#d29922;--bad:#f85149;--move:#58a6ff;--queue:#8b949e;
    --amber-bg:rgba(210,153,34,.10);--move-bg:rgba(88,166,255,.10);--good-bg:rgba(63,185,80,.10);--bad-bg:rgba(248,81,73,.10)}
  *{box-sizing:border-box;margin:0}
  body{background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,"SF Pro Text",Segoe UI,sans-serif;padding:0 0 70px}
  a{color:inherit;text-decoration:none} a:hover{text-decoration:underline}
  .mono{font-family:ui-monospace,"SF Mono",Menlo,monospace}
  .wrap{max-width:1060px;margin:0 auto;padding:0 28px}
  header{padding:36px 0 20px;display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
  h1{font-size:24px;letter-spacing:-.4px}
  header .rule{color:var(--ink3);font-size:13px}
  header .stamp{margin-left:auto;color:var(--ink3);font-size:12.5px}
  .chip{display:inline-flex;align-items:center;gap:6px;padding:2px 10px;border-radius:999px;font-size:11.5px;font-weight:600;letter-spacing:.04em;white-space:nowrap}
  .chip .dot{width:7px;height:7px;border-radius:50%}
  .c-merge{background:var(--move-bg);color:var(--move)} .c-merge .dot{background:var(--move);animation:pulse 1.2s infinite}
  .c-line{background:rgba(139,148,158,.12);color:var(--queue)} .c-line .dot{background:var(--queue)}
  .c-gate{background:var(--amber-bg);color:var(--warn)} .c-gate .dot{background:var(--warn);animation:pulse 1.6s infinite}
  .c-build{background:var(--move-bg);color:var(--move)} .c-build .dot{background:var(--move)}
  .c-review{background:rgba(163,113,247,.12);color:#a371f7} .c-review .dot{background:#a371f7}
  .c-good{background:var(--good-bg);color:var(--good)} .c-good .dot{background:var(--good)}
  .c-bad{background:var(--bad-bg);color:var(--bad)} .c-bad .dot{background:var(--bad);animation:pulse 1s infinite}
  @keyframes pulse{50%{opacity:.35}}
  .boards{display:grid;grid-template-columns:1fr 1fr;gap:20px}
  @media(max-width:900px){.boards{grid-template-columns:1fr}}
  .board{background:var(--surface);border:1px solid var(--line);border-radius:14px;overflow:hidden;align-self:start}
  .bhead{display:flex;align-items:center;gap:10px;padding:14px 18px;border-bottom:1px solid var(--line);background:var(--surface2)}
  .bhead .repo{font-weight:700;font-size:16px}
  .bhead .lane{color:var(--ink3);font-size:12.5px;margin-left:auto}
  .mainline{padding:10px 18px;border-bottom:1px solid var(--line);font-size:12.5px;color:var(--ink2);display:flex;gap:8px;align-items:center}
  .mainline .sha{color:var(--ink3);margin-left:auto;white-space:nowrap}
  .qrow{display:grid;grid-template-columns:34px 1fr auto auto;gap:12px;align-items:center;padding:13px 18px;border-bottom:1px solid var(--line)}
  .qrow:last-child{border-bottom:none}
  .qrow.needsyou{background:var(--amber-bg)}
  .pos{font-size:15px;color:var(--ink3);font-weight:700;text-align:center}
  .pos.front{color:var(--move)}
  .ship .t{font-weight:600;font-size:14.5px}
  .ship .s{font-size:12px;color:var(--ink3);margin-top:1px}
  .age{font-size:12px;color:var(--ink3);text-align:right;min-width:52px}
  .sect{padding:8px 18px 6px;font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink3);border-bottom:1px solid var(--line);background:var(--surface2)}
  .quiet{padding:16px 18px;color:var(--ink3);font-size:13.5px;font-style:italic}
  h2{font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:var(--ink3);margin:44px 0 14px}
  .guide{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}
  @media(max-width:900px){.guide{grid-template-columns:1fr 1fr}}
  .card{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:16px 18px;font-size:13.5px;color:var(--ink2)}
  .card h3{color:var(--ink);font-size:14px;margin-bottom:8px}
  .card ul{list-style:none;padding:0;display:grid;gap:5px}
  .doors{margin-top:16px;display:flex;gap:10px 22px;flex-wrap:wrap;align-items:center;background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:14px 18px;font-size:13.5px}
  .doors .k{color:var(--ink3);font-size:11px;letter-spacing:.12em;text-transform:uppercase}
  .doors a{color:var(--move)}
  code{font-family:ui-monospace,Menlo,monospace;font-size:.92em;background:var(--surface2);padding:1px 6px;border-radius:5px;color:var(--ink)}
</style></head><body><div class="wrap">
<header>
  <h1>shipboard</h1>
  <span class="rule">one track per repo — sidings are parallel, the main line admits one train, the next departs when deploy clears</span>
  <span class="stamp mono">updated ${esc(now)} · auto-refreshes</span>
</header>
<div class="boards">${cards.join("\n")}</div>

<h2>Field guide — how the railway runs</h2>
<div class="guide">
  <div class="card"><h3>Your controls</h3><ul>
    <li><code>/ship &lt;idea&gt;</code> — sizes itself</li>
    <li><code>/ship express</code> — small, straight through</li>
    <li><code>/ship design</code> — full walk, your taste</li>
    <li><code>/ship next</code> — ship the Next column</li></ul></div>
  <div class="card"><h3>When you're needed</h3><ul>
    <li><span class="chip c-gate"><span class="dot"></span>GATE 1</span> design direction</li>
    <li><span class="chip c-gate"><span class="dot"></span>GATE 2</span> go?</li>
    <li><span class="chip c-gate"><span class="dot"></span>REVIEW</span> merge? (it's running)</li>
    <li style="color:var(--ink3)">everything else is automatic</li></ul></div>
  <div class="card"><h3>Who does the work</h3><ul>
    <li><b style="color:var(--ink)">Fable</b> — judgment, design, git</li>
    <li><b style="color:var(--ink)">GPT-5.6 sol</b> — all drafting + review</li>
    <li><b style="color:var(--ink)">Opus 4.8</b> — browser QA only</li></ul></div>
  <div class="card"><h3>Landing rules</h3><ul>
    <li>one train on the track</li>
    <li>re-sync at the signal</li>
    <li>deploy runs to completion</li>
    <li>ends at dev · <b style="color:var(--ink)">Done is your drag</b></li></ul></div>
</div>
<div class="doors">
  <span class="k">Doors</span>
  <a href="https://linear.app/homezero-md">Linear board →</a>
  <a href="https://github.com/peteknowsai/ship/issues?q=is%3Aissue+label%3Aship-retro">retro inbox →</a>
  <a href="https://dev.homezero.md">dev.homezero.md →</a>
  <a href="https://specs.homezero.md/ship/2026-07-11-merge-queue-board.html">this board's design →</a>
</div>
</div></body></html>`;
}

// ---------- main ----------

const html = page(REPOS.map(repoCard));
const out = "/tmp/shipboard.html";
writeFileSync(out, html);

if (process.argv.includes("--dry")) {
  console.log(`dry: wrote ${out} (${html.length} bytes), no upload`);
} else {
  const r = sh("npx", ["wrangler", "r2", "object", "put", `${BUCKET}/index.html`, "--file", out, "--content-type", "text/html; charset=utf-8", "--remote"], {
    env: { ...process.env, CLOUDFLARE_ACCOUNT_ID: ACCOUNT },
    cwd: homedir(),
    timeout: 60000,
  });
  console.log(r ? "published board.cells.md" : "UPLOAD FAILED (rendered fine)");
}
