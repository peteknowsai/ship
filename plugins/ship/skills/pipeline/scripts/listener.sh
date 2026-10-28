#!/bin/bash
# listener.sh <port> [seconds]: wait for a server to listen on <port> (default 300 s: under
# load cells-app's dev took about 4 minutes to open its port, CEL-175), then
# print "pid <pid> cwd <dir>": the checkout it serves. A Next server's own cwd reads "/",
# so it walks up the parent processes to the first real one. Exit 1 if nothing listens.
# listener.sh --selftest
set -u
if [ "${1:-}" = --selftest ]; then
  dir=$(mktemp -d); port=$((20000 + RANDOM % 20000))
  (cd "$dir" && exec python3 -m http.server "$port" --bind 127.0.0.1 >/dev/null 2>&1) & server=$!
  trap 'kill $server 2>/dev/null; rm -rf "$dir"' EXIT
  got=$("$0" "$port" 10)
  real=$(cd "$dir" && pwd -P)
  case "$got" in *"cwd $real") echo "listener self-test: 0 failed" ;; *) echo "listener self-test: 1 failed ($got)"; exit 1 ;; esac
  "$0" 1 1 >/dev/null 2>&1 && { echo "listener self-test: an empty port should fail"; exit 1; }
  exit 0
fi
port=${1:?usage: listener.sh <port> [seconds]}; wait=${2:-300}
for ((i = 0; i < wait; i++)); do
  pid=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null | head -1)
  [ -n "$pid" ] && break
  sleep 1
done
[ -z "${pid:-}" ] && { echo "listener: nothing listening on $port after ${wait}s" >&2; exit 1; }
p=$pid
while :; do
  cwd=$(lsof -a -p "$p" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p')
  [ -n "$cwd" ] && [ "$cwd" != / ] && break
  p=$(ps -o ppid= -p "$p" | tr -d ' ')
  [ -z "$p" ] || [ "$p" -le 1 ] && { cwd=/; break; }
done
echo "pid $pid cwd $cwd"
