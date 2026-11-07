---
name: checks
description: How to prove a change to <repo> works, the way Pete would check it by hand. Start the app, sign in, walk the screens a change can touch, and meet the pass lines below. Use before calling any change in this repo done, inside a ship run or not.
---

# Checks for <repo>

What every session that proves a change here starts from. A QA run reads it first and
writes back what it learned, in the same branch as the change.

**One line per lesson, about 300 characters.** A new lesson on a subject a line already
covers replaces that line. **Cap: 150 lines and 40 KB.** A run that takes the file over it
prunes in the same edit: merge lines on one subject, drop a line whose screen or code is
gone, or move a subject to `checks/<topic>.md` behind one line saying when to read it.

## Start it

- `<command>` from the worktree; it prints its URL. Ready when `<what answers>`.

## Sign in

- `<the test-auth path, step by step, with any trick a fresh account needs>`

## Walk

One line per screen a change can touch: how to reach it from nothing, and what a person
should see when it works.

- **<screen>**: <steps> → <what you should see>

## Pass lines

| Check | When | Passes when | On a fail |
|---|---|---|---|
| <name> | <which changes run it> | <a number or a yes/no a tool can read> | <where to look first> |

## Noise

What every run sees that is not the change: skip it, never chase it.

| Noise | Where it shows | Why it isn't the change |
|---|---|---|
| <console line or false alarm> | <console, a Lighthouse audit, a log> | <its known cause> |

## Learned

- <subject>: <the thing a run had to discover, so the next one doesn't> (<slug>, <YYYY-MM-DD>)
