#!/usr/bin/env python3
"""Give a worktree its own copy of the app's Convex dev database (backend: copy).

  branch-db.py up <worktree> [<app-dir>]   app-dir: the folder with convex.json, relative
                                           to the worktree; default the worktree itself
  branch-db.py diff <worktree> [<app-dir>]  before pushing this branch's functions to shared
                                           dev, and before landing: the functions only
                                           shared dev has (a push drops them), only the
                                           branch's copy has, and on both with other args,
                                           returns or visibility. Exit 1 when the push
                                           would drop any.
  branch-db.py push <worktree> [<app-dir>]  push the worktree's functions to that app-dir's
                                           own copy (after an edit under convex/ or an
                                           absorb), with up's flags so no tracked file is
                                           regenerated; refuses an app-dir still on shared dev
  branch-db.py check <worktree>             say so, and exit 1, while no app-dir in the worktree
                                           has a copy yet; stage.sh runs it at each flip from
                                           stage 0's to `land`, route.py at each task logged
  branch-db.py --selftest

`up` creates a cloud dev deployment `dev/<branch>` in the same Convex project, expiring in
7 days, copies dev's environment variables (piped, never written to disk), pushes the
worktree's functions, imports dev's data and stored files, then points every .env* file in
the worktree at the copy. Convex's docs recommend a dev deployment per agent worktree; the
expiry is the cleanup, since the CLI has no delete. Run it again and it says the worktree is
already on its copy. It refuses anything but a dev deployment, so prod is never read.
"""
import os, re, shutil, subprocess, sys, tempfile, time

EXPIRY = os.environ.get("BRANCH_DB_EXPIRY", "in 7 days")
# Either one makes the CLI ignore --deployment and use the key's deployment, prod included.
KEYS = ("CONVEX_DEPLOY_KEY", "CONVEX_DEPLOYMENT_TOKEN")


def env_value(path, key):
    try:
        lines = open(path).read().splitlines()
    except OSError:
        return None
    val = None
    for line in lines:
        m = re.match(rf"\s*(?:export\s+)?{key}\s*=\s*(.*)$", line)
        if m:
            val = m.group(1).split(" #")[0].strip().strip("'\"")
    return val


def slug(branch):
    return re.sub(r"[^a-z0-9]+", "-", branch.lower()).strip("-")[:40].strip("-")


def env_files(root):
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in ("node_modules", ".git", ".next", ".vercel")]
        if d[len(root):].count(os.sep) >= 3:
            dirs[:] = []
        for f in files:
            if f.startswith(".env") and not os.path.islink(os.path.join(d, f)):
                yield os.path.join(d, f)


def repoint(root, src, new):
    """Swap the dev deployment's name for the copy's in every env file; returns files changed."""
    pat = re.compile(rf"(?<![\w-]){re.escape(src)}(?![\w-])")
    changed = []
    for p in env_files(root):
        text = open(p).read()
        out = pat.sub(new, text)
        if out != text:
            open(p, "w").write(out)
            changed.append(os.path.relpath(p, root))
    return changed


def source(app_env, main_env):
    """The dev deployment to copy, or why not. Returns (name, None) or (None, reason)."""
    app_dir = os.path.dirname(app_env)
    for f in (app_env, os.path.join(app_dir, ".env")):
        for k in KEYS:
            if env_value(f, k):
                return None, f"{k} in {f} would redirect every call to its deployment; remove it first"
    dep = env_value(app_env, "CONVEX_DEPLOYMENT")
    if not dep:
        return None, f"no CONVEX_DEPLOYMENT in {app_env}"
    kind, _, name = dep.partition(":")
    if kind != "dev":
        return None, f"{dep} is not a dev deployment; branch-db copies dev only"
    main_dep = env_value(main_env, "CONVEX_DEPLOYMENT")
    if not main_dep:
        return None, f"no CONVEX_DEPLOYMENT in {main_env}; is the app-dir right?"
    if main_dep != dep:
        return None, f"already on its own copy ({dep})"
    return name, None


def clean_env(**extra):
    env = {k: v for k, v in os.environ.items() if k not in KEYS}
    env.update(extra)
    return env


def npx(args, cwd, input=None, env=None):
    r = subprocess.run(["npx", "convex", *args], cwd=cwd, input=input, text=True,
                       capture_output=True, env=env or clean_env())
    if r.returncode:
        sys.exit(f"branch-db: npx convex {args[0]} failed: {(r.stdout + r.stderr)[-800:]}")
    return r.stdout + r.stderr


def settings(src, app):
    """dev's settings as NAME=value lines, or (None, why). Under an agent (AI_AGENT, CLAUDECODE)
    the CLI lists names only unless asked for values (convex 1.48); a CLI older than the flag
    has no agent check, so it is asked again without one."""
    for flags in (["--include-values"], []):
        r = subprocess.run(["npx", "convex", "env", "list", *flags, "--deployment", src], cwd=app,
                           capture_output=True, text=True, env=clean_env())
        if not (r.returncode and "unknown option" in r.stderr):
            break
    return check_settings(r.returncode, r.stdout, r.stderr, src)


def check_settings(code, text, err, src):
    """A names-only list starts with a bare name; a values list starts NAME=..., and only a
    multiline value's later lines lack the `=`. No settings at all prints to stderr only."""
    if code:
        return None, f"couldn't read dev's settings from {src}"
    if not text.strip():
        return ("", None) if "No environment variables" in err else (None, f"couldn't read dev's settings from {src}")
    first = next(l for l in text.splitlines() if l.strip())
    if "=" not in first or "Listed names only" in err:
        return None, f"dev's settings came back as names without values ({first.strip()} first)"
    return text, None


def create_cmd(ref):
    return ["npx", "convex", "deployment", "create", ref, "--type", "dev", "--expiration", EXPIRY]


def export(src, snap, app, tries=40, wait=15):
    """Dev allows one snapshot export at a time, so a second worktree copying waits its turn."""
    for _ in range(tries):
        r = subprocess.run(["npx", "convex", "export", "--include-file-storage", "--deployment", src,
                            "--path", snap], cwd=app, capture_output=True, text=True, env=clean_env())
        out = r.stdout + r.stderr
        if os.path.getsize(snap) if os.path.exists(snap) else 0:
            return
        if "already requested or in progress" not in out:
            raise SystemExit(f"branch-db: npx convex export failed: {out[-800:]}")
        time.sleep(wait)
    raise SystemExit(f"branch-db: dev's export stayed busy for {tries * wait // 60} minutes")


def up(worktree, app_rel="."):
    worktree = os.path.abspath(worktree)
    app = os.path.join(worktree, app_rel)
    main = subprocess.run(["git", "-C", worktree, "worktree", "list", "--porcelain"],
                          capture_output=True, text=True).stdout.split("\n")[0].removeprefix("worktree ")
    branch = subprocess.run(["git", "-C", worktree, "branch", "--show-current"],
                            capture_output=True, text=True).stdout.strip()
    if os.path.realpath(main) == os.path.realpath(worktree) or not branch:
        sys.exit("branch-db: run it on a linked worktree with a branch, never the main checkout")
    src, why = source(os.path.join(app, ".env.local"), os.path.join(main, app_rel, ".env.local"))
    if not src:
        print(f"branch-db: {why}")
        return 0 if why.startswith("already") else 1
    # Read the settings before making the copy, so a failed read leaves nothing to expire.
    env_lines, why = settings(src, app)
    if why:
        sys.exit(f"branch-db: {why}; no copy made")
    ref = f"dev/{slug(branch)}"
    r = subprocess.run(create_cmd(ref), cwd=app, capture_output=True, text=True, env=clean_env())
    if r.returncode and "exist" in (r.stdout + r.stderr).lower():
        # A failed earlier run left this reference behind until it expires.
        ref = f"{ref}-{time.strftime('%H%M%S')}"
        r = subprocess.run(create_cmd(ref), cwd=app, capture_output=True, text=True, env=clean_env())
    out = r.stdout + r.stderr
    if r.returncode:
        sys.exit(f"branch-db: npx convex deployment create failed: {out[-800:]}")
    m = re.search(r"https://([a-z]+-[a-z]+-\d+)\.convex\.cloud", out)
    if not m:
        sys.exit(f"branch-db: couldn't read the new deployment from: {out[-400:]}")
    new = m.group(1)
    # Settings go straight from one deployment to the other, never through a file.
    if env_lines:
        npx(["env", "set", "--force", "--deployment", new], app, input=env_lines)
    tmp = tempfile.mkdtemp(prefix="branch-db-")
    # `convex dev` rewrites the app's .env.local to the copy and adds a .gitignore when there
    # is none; put the env file back if the copy fails, so a rerun starts over.
    app_env, gitignore = os.path.join(app, ".env.local"), os.path.join(app, ".gitignore")
    env_before, had_gitignore = open(app_env).read(), os.path.exists(gitignore)
    try:
        snap = os.path.join(tmp, "dev.zip")
        export(src, snap, app)
        # Data first, onto the empty copy, so it keeps dev's table numbers; a table the
        # branch adds then numbers after them. Pushing first collided once main had a
        # table dev lacked: both claimed one number and the import refused.
        npx(["import", "--replace-all", "-y", "--deployment", new, snap], app)
        # The process env beats .env.local, so the push goes to the copy.
        npx(["dev", "--once", "--typecheck", "disable", "--codegen", "disable"], app,
            env=clean_env(CONVEX_DEPLOYMENT=f"dev:{new}"))
    except BaseException:
        open(app_env, "w").write(env_before)
        raise
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        if not had_gitignore and os.path.exists(gitignore):
            os.remove(gitignore)
    # Only a finished copy repoints the worktree, so a failed run reruns from scratch.
    changed = repoint(worktree, src, new) or ["by convex dev"]
    print(f"branch-db: {app_rel} dev:{src} -> dev:{new} ({ref}, expires {EXPIRY}); "
          f"repointed {', '.join(changed)}")
    return 0


def specs(deployment, cwd):
    """Each function's name and its whole spec: args, returns, type and visibility."""
    import json
    out = npx(["function-spec", "--deployment", deployment], cwd)
    spec = json.JSONDecoder().raw_decode(out, out.index("{"))[0]  # npx() appends stderr after the JSON
    # HTTP routes carry a method and path instead of an identifier
    return {f.get("identifier") or f"{f.get('method')} {f.get('path')}": json.dumps(f, sort_keys=True)
            for f in spec["functions"]}


def compare(shared, branch):
    """Lines for the two sides of a function-spec diff, and whether a push drops anything.
    cel-360 added an optional arg to feed:setBrief that main's server sends once it lands, and
    a diff of names alone printed nothing to push."""
    gone, new = sorted(shared.keys() - branch.keys()), sorted(branch.keys() - shared.keys())
    changed = sorted(i for i in shared.keys() & branch.keys() if shared[i] != branch[i])
    lines = [f"only on shared dev, a push from this branch drops these ({len(gone)}):"]
    lines += [f"  {i}" for i in gone] + [f"only on the branch copy ({len(new)}):"] + [f"  {i}" for i in new]
    lines += [f"on both, with other args, returns or visibility on the branch ({len(changed)}):"]
    lines += [f"  {i}" for i in changed]
    if new or changed:
        lines.append("main's server calls these on shared dev once the branch lands; one this branch didn't "
                     "touch is shared dev behind main, or a sibling's push, which a push from here reverts")
    return lines, bool(gone)


def main_of(worktree):
    return subprocess.run(["git", "-C", worktree, "worktree", "list", "--porcelain"],
                          capture_output=True, text=True).stdout.split("\n")[0].removeprefix("worktree ")


def push_target(app_env, main_env):
    """(deployment, None) when app_env names a dev copy of its own, else (None, why): a plain
    `convex dev --once` pushes wherever .env.local points, and an app-dir up never copied (or
    one whose env was restored) still points at the dev database every preview shares."""
    mine, shared = env_value(app_env, "CONVEX_DEPLOYMENT"), env_value(main_env, "CONVEX_DEPLOYMENT")
    if not mine or not shared:
        return None, f"no CONVEX_DEPLOYMENT in {app_env if not mine else main_env}; is the app-dir right?"
    if not mine.startswith("dev:"):
        return None, f"{mine} is not a dev deployment"
    if mine == shared:
        return None, "this app-dir is on shared dev, not a copy: run up for it first, never push the branch there"
    return mine, None


def owed(worktree, main):
    """How many of the worktree's app-dirs still name the main checkout's dev deployment, when
    all of them do; 0 once any has a copy, or where the contract's backend isn't `copy`.
    save-files-to-mac never ran `up`, and its dev server and smoke ran on shared dev until
    TEST. One copy is enough to stay quiet: cells-app copies only the pack the branch runs.
    With no `backend:` line the default is copy only beside a convex.json (contract.md):
    homezero has a dev deployment and none, and shares dev on purpose."""
    contract = ""
    for f in ("CLAUDE.md", "AGENTS.md"):
        try:
            contract += open(os.path.join(worktree, f)).read()
        except OSError:
            pass
    said = re.search(r"backend\W+(copy|shared-dev|per-branch)", contract, re.I)
    if said and said.group(1).lower() != "copy":
        return 0
    same = 0
    for p in env_files(worktree):
        if os.path.basename(p) != ".env.local":
            continue
        if not said and not os.path.exists(os.path.join(os.path.dirname(p), "convex.json")):
            continue
        dep = env_value(p, "CONVEX_DEPLOYMENT")
        # No twin in main is a new app-dir's env file, which says nothing about a copy.
        twin = env_value(os.path.join(main, os.path.relpath(p, worktree)), "CONVEX_DEPLOYMENT")
        if not dep or not dep.startswith("dev:") or not twin:
            continue
        if dep != twin:
            return 0
        same += 1
    return same


def check(worktree):
    worktree = os.path.abspath(worktree)
    main = main_of(worktree)
    n = 0 if os.path.realpath(main) == os.path.realpath(worktree) else owed(worktree, main)
    if n:
        print(f"branch-db: this worktree has no copy yet: its .env.local files ({n}) all still name the main "
              "checkout's shared dev. Let `branch-db.py up <worktree> [<app-dir>]` finish, or start it if "
              "it isn't running, before any convex command, dev server or smoke.")
    return 1 if n else 0


def push(worktree, app_rel="."):
    worktree = os.path.abspath(worktree)
    app = os.path.join(worktree, app_rel)
    target, why = push_target(os.path.join(app, ".env.local"), os.path.join(main_of(worktree), app_rel, ".env.local"))
    if not target:
        sys.exit(f"branch-db: {why}")
    # The process env beats .env.local and a shell's export alike, so the push goes to the copy.
    npx(["dev", "--once", "--typecheck", "disable", "--codegen", "disable"], app,
        env=clean_env(CONVEX_DEPLOYMENT=target))
    print(f"branch-db: pushed {app_rel} to its copy {target.partition(':')[2]}")
    return 0


def diff(worktree, app_rel="."):
    worktree = os.path.abspath(worktree)
    main = main_of(worktree)
    mine = env_value(os.path.join(worktree, app_rel, ".env.local"), "CONVEX_DEPLOYMENT")
    shared = env_value(os.path.join(main, app_rel, ".env.local"), "CONVEX_DEPLOYMENT")
    if not mine or not shared:
        sys.exit("branch-db: no CONVEX_DEPLOYMENT in the worktree's or the main checkout's .env.local")
    if mine == shared:
        sys.exit("branch-db: this worktree is on shared dev itself, with no copy to compare (run up first)")
    app = os.path.join(worktree, app_rel)
    lines, drops = compare(specs(shared.partition(":")[2], app), specs(mine.partition(":")[2], app))
    print("\n".join(lines))
    return 1 if drops else 0


def selftest():
    t = tempfile.mkdtemp()
    try:
        wt, mn = os.path.join(t, "wt"), os.path.join(t, "main")
        for d in (wt, mn, os.path.join(wt, "packs/a"), os.path.join(wt, "node_modules/x")):
            os.makedirs(d, exist_ok=True)
        dev = "CONVEX_DEPLOYMENT=dev:charming-caiman-61 # team: pkai\nCONVEX_URL=https://charming-caiman-61.convex.cloud\nOTHER=charming-caiman-610\n"
        for p in (f"{wt}/.env.local", f"{wt}/packs/a/.env.local", f"{mn}/.env.local", f"{wt}/node_modules/x/.env"):
            open(p, "w").write(dev)
        assert source(f"{wt}/.env.local", f"{mn}/.env.local") == ("charming-caiman-61", None)
        lines, drops = compare({"a.js:x": "1", "b.js:y": "1"}, {"a.js:x": "1", "c.js:z": "1"})
        assert drops and lines[1] == "  b.js:y" and lines[3] == "  c.js:z", lines
        assert compare({"a.js:x": "1"}, {"a.js:x": "1", "c.js:z": "1"})[1] is False
        lines, drops = compare({"a.js:x": "1"}, {"a.js:x": "2"})
        assert not drops and "  a.js:x" in lines and lines[-1].startswith("main's server calls these"), lines
        assert not compare({"a.js:x": "1"}, {"a.js:x": "1"})[0][-1].startswith("main's"), "nothing reshaped"
        assert slug("feature/Desk Doorway!") == "feature-desk-doorway"
        assert len(slug("x" * 80)) == 40
        changed = repoint(wt, "charming-caiman-61", "brainy-otter-615")
        assert sorted(changed) == [".env.local", "packs/a/.env.local"], changed
        text = open(f"{wt}/.env.local").read()
        assert "dev:brainy-otter-615" in text and "https://brainy-otter-615.convex.cloud" in text
        assert "OTHER=charming-caiman-610" in text, "a longer name that contains the old one is left alone"
        assert "brainy" not in open(f"{wt}/node_modules/x/.env").read()
        name, why = source(f"{wt}/.env.local", f"{mn}/.env.local")
        assert name is None and why.startswith("already"), why
        open(f"{wt}/.env.local", "w").write("CONVEX_DEPLOYMENT=prod:gallant-starling-747\n")
        name, why = source(f"{wt}/.env.local", f"{wt}/.env.local")
        assert name is None and "not a dev deployment" in why
        name, why = source(f"{wt}/missing", f"{mn}/.env.local")
        assert name is None and "no CONVEX_DEPLOYMENT" in why
        open(f"{wt}/.env.local", "w").write(dev)
        name, why = source(f"{wt}/.env.local", f"{mn}/absent")
        assert name is None and "is the app-dir right" in why, why
        open(f"{wt}/.env.local", "w").write(dev + "CONVEX_DEPLOY_KEY=prod:x|y\n")
        name, why = source(f"{wt}/.env.local", f"{mn}/.env.local")
        assert name is None and "CONVEX_DEPLOY_KEY" in why, why
        os.environ["CONVEX_DEPLOY_KEY"] = "prod:x|y"
        assert "CONVEX_DEPLOY_KEY" not in clean_env() and clean_env(A="1")["A"] == "1"
        del os.environ["CONVEX_DEPLOY_KEY"]
        assert check_settings(0, "A=1\nB=two\n", "", "s") == ("A=1\nB=two\n", None)
        pem = "KEY='-----BEGIN KEY-----\nabc\n-----END KEY-----'\nB=2\n"
        assert check_settings(0, pem, "", "s") == (pem, None), "a multiline value passes"
        assert "names without values (A first)" in check_settings(0, "A\nB\n", "", "s")[1]
        assert check_settings(0, "", "No environment variables set", "s") == ("", None)
        assert check_settings(1, "A=1\n", "", "s")[0] is None and check_settings(0, " \n", "", "s")[0] is None
        open(f"{wt}/packs/a/.env.local", "w").write("CONVEX_DEPLOYMENT=dev:brainy-otter-615\n")
        assert push_target(f"{wt}/packs/a/.env.local", f"{mn}/.env.local") == ("dev:brainy-otter-615", None)
        same = push_target(f"{wt}/.env.local", f"{mn}/.env.local")
        assert same[0] is None and "shared dev" in same[1], "an app-dir up never copied is refused"
        open(f"{wt}/packs/a/.env.local", "w").write("CONVEX_DEPLOYMENT=prod:gallant-starling-747\n")
        assert "not a dev deployment" in push_target(f"{wt}/packs/a/.env.local", f"{mn}/.env.local")[1]
        assert push_target(f"{wt}/packs/a/.env.local", f"{mn}/absent")[0] is None
        ow, om = os.path.join(t, "ow"), os.path.join(t, "om")
        for d in (f"{ow}/packs/a", f"{ow}/packs/b", f"{om}/packs/a", f"{om}/packs/b", f"{ow}/packs/new"):
            os.makedirs(d)
            open(f"{d}/.env.local", "w").write(f"CONVEX_DEPLOYMENT=dev:{os.path.basename(d)}-cow-1\n")
        assert owed(ow, om) == 0, "no backend line and no convex.json: the default is shared dev"
        for d in (f"{ow}/packs/a", f"{ow}/packs/b", f"{ow}/packs/new"):
            open(f"{d}/convex.json", "w").write("{}")
        open(f"{ow}/packs/a/.env", "w").write("CONVEX_DEPLOYMENT=dev:a-cow-1\n")
        assert owed(ow, om) == 2, "up never ran: both app-dirs main knows are on shared dev, the new one aside"
        for d in (ow, om):
            open(f"{d}/.env.local", "w").write("CONVEX_DEPLOYMENT=dev:root-cow-1\n")
        assert owed(ow, om) == 2, "a root env file with no convex.json beside it isn't an app-dir"
        open(f"{ow}/CLAUDE.md", "w").write("- **Backend:** `copy packs/<pack>` (was backend: shared-dev)\n")
        assert owed(ow, om) == 3, "a copy contract counts every dev env file, and its first word wins"
        open(f"{ow}/CLAUDE.md", "w").write("- backend: shared-dev. Convex dev for localhost\n")
        assert owed(ow, om) == 0, "a shared-dev contract owes no copy"
        os.remove(f"{ow}/CLAUDE.md")
        for d in (ow, om):
            open(f"{d}/packs/b/.env.local", "w").write("CONVEX_DEPLOYMENT=prod:gallant-starling-747\n")
        assert owed(ow, om) == 1, "a prod deployment is never shared dev"
        open(f"{ow}/packs/a/.env.local", "w").write("CONVEX_DEPLOYMENT=dev:brainy-otter-615\n")
        assert owed(ow, om) == 0, "one copied pack is enough"
        import contextlib, io
        gm, gw = os.path.join(t, "gm"), os.path.join(t, "gw")
        for a in (["init", "-q", "-b", "main", gm],
                  ["-C", gm, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "root"],
                  ["-C", gm, "worktree", "add", "-q", gw, "-b", "x"]):
            subprocess.run(["git", *a], check=True, capture_output=True)
        for d in (gm, gw):
            open(f"{d}/convex.json", "w").write("{}")
            open(f"{d}/.env.local", "w").write("CONVEX_DEPLOYMENT=dev:calm-cow-1\n")
        said = io.StringIO()
        with contextlib.redirect_stdout(said):
            assert check(gw) == 1 and check(gm) == 0, "a worktree owes a copy, the main checkout never does"
        assert said.getvalue().count("no copy yet") == 1, said.getvalue()
        cmd = create_cmd("dev/x-1")
        assert cmd[3:5] == ["create", "dev/x-1"] and cmd.count("dev/x-1") == 1, cmd
        print("branch-db selftest: ok")
    finally:
        shutil.rmtree(t)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--selftest"]:
        selftest()
    elif a[:1] == ["up"] and len(a) in (2, 3):
        sys.exit(up(*a[1:]))
    elif a[:1] == ["diff"] and len(a) in (2, 3):
        sys.exit(diff(*a[1:]))
    elif a[:1] == ["push"] and len(a) in (2, 3):
        sys.exit(push(*a[1:]))
    elif a[:1] == ["check"] and len(a) == 2:
        sys.exit(check(a[1]))
    else:
        sys.exit(__doc__)
