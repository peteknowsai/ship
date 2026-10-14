#!/usr/bin/env python3
"""Give a worktree its own copy of the app's Convex dev database (backend: copy).

  branch-db.py up <worktree> [<app-dir>]   app-dir: the folder with convex.json, relative
                                           to the worktree; default the worktree itself
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
    lst = subprocess.run(["npx", "convex", "env", "list", "--deployment", src], cwd=app,
                         capture_output=True, text=True, env=clean_env())
    if lst.returncode or not lst.stdout.strip():
        sys.exit(f"branch-db: couldn't read dev's settings from {src}; the copy {new} is left to expire")
    npx(["env", "set", "--force", "--deployment", new], app, input=lst.stdout)
    tmp = tempfile.mkdtemp(prefix="branch-db-")
    # `convex dev` rewrites the app's .env.local to the copy and adds a .gitignore when there
    # is none; put the env file back if the copy fails, so a rerun starts over.
    app_env, gitignore = os.path.join(app, ".env.local"), os.path.join(app, ".gitignore")
    env_before, had_gitignore = open(app_env).read(), os.path.exists(gitignore)
    try:
        snap = os.path.join(tmp, "dev.zip")
        export(src, snap, app)
        # The process env beats .env.local, so the push goes to the copy.
        npx(["dev", "--once", "--typecheck", "disable", "--codegen", "disable"], app,
            env=clean_env(CONVEX_DEPLOYMENT=f"dev:{new}"))
        npx(["import", "--replace-all", "-y", "--deployment", new, snap], app)
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
    else:
        sys.exit(__doc__)
