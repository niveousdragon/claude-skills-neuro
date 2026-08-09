#!/bin/sh
# Structural census: mechanical, language-agnostic measurements over a whole repo.
# Produces the evidence a structural-debt audit reasons from. Reads only; never writes.
#
#   sh census.sh [--since "6 months ago"] [--src PREFIX] [--ext "py,js,ts,go,rs"]
#
# Requires: git, awk, sort, grep, sed. Degrades outside a git repo (skips history sections).
# Every section is bounded — this is meant to fit in an agent's context.

SINCE="6 months ago"; SRC=""; EXT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --since) SINCE="$2"; shift 2 ;;
    --src)   SRC="$2";   shift 2 ;;
    --ext)   EXT="$2";   shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

Q=$(printf '\047')
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then GIT=1; else GIT=0; fi
[ "$GIT" = 0 ] && echo "!! not a git repo - sections 3,4,5 (history) skipped"

# Dominant source extensions, unless told.
if [ -z "$EXT" ]; then
  EXT=$(git ls-files 2>/dev/null | sed -n 's/.*\.\([a-zA-Z0-9]\{1,6\}\)$/\1/p' \
      | grep -Ex 'py|js|jsx|ts|tsx|go|rs|java|kt|rb|php|cs|c|cc|cpp|h|hpp|swift|scala|ex|clj|html|vue|svelte' \
      | sort | uniq -c | sort -rn | head -6 | awk '{printf "%s%s", sep, $2; sep=","}')
fi
[ -z "$EXT" ] && { echo "no source files detected"; exit 1; }

set --
for e in $(echo "$EXT" | tr ',' ' '); do
  if [ -n "$SRC" ]; then set -- "$@" "$SRC/*.$e"; else set -- "$@" "*.$e"; fi
done

echo "### structural census | ext=$EXT | since=$SINCE ${SRC:+| src=$SRC}"
echo

echo "== 1. SCALE (lines per area) =="
git grep -c '' -- "$@" 2>/dev/null | awk -F: '
{ n=split($1,p,"/"); d=(n>2 ? p[1]"/"p[2] : (n>1 ? p[1] : "(root)"))
  lines[d]+=$NF; files[d]++ }
END { for (k in lines) printf "%8d lines %5d files  %s\n", lines[k], files[k], k }' | sort -rn | head -12
echo

echo "== 2. SIZE OUTLIERS =="
git grep -c '' -- "$@" 2>/dev/null | sort -t: -k2 -rn | head -12 | awk -F: '{printf "%7d  %s\n", $2, $1}'
echo

if [ "$GIT" = 1 ]; then
echo "== 3. HOTSPOTS (churn x size - where debt actually costs) =="
git grep -c '' -- "$@" 2>/dev/null > "/tmp/_cen_sz.$$"
git log --since="$SINCE" --format='' --name-only -- "$@" 2>/dev/null \
  | grep -v '^$' | sort | uniq -c | sort -rn > "/tmp/_cen_ch.$$"
awk 'NR==FNR { split($0,a,":"); sz[a[1]]=a[2]; next }
     { f=$2; if (f in sz) printf "%9d  churn %3d x %5d lines  %s\n", $1*sz[f], $1, sz[f], f }' \
  "/tmp/_cen_sz.$$" "/tmp/_cen_ch.$$" | sort -rn | head -12
rm -f "/tmp/_cen_sz.$$" "/tmp/_cen_ch.$$"
echo

echo "== 4. GROWTH vs PRUNING per month =="
echo "   the ratio moves a lot with scope, so the scope is part of the number."
echo "   Record the SCOPE LINE below verbatim in the ledger trend row; a ratio"
echo "   compared against one measured over a different scope means nothing."
_ratio() {
  git log --since="$SINCE" --pretty=format:'@@%ad' --date=format:'%Y-%m' --numstat -- $1 2>/dev/null | awk '
  /^@@/ { m=substr($0,3); next }
  NF==3 && $1 != "-" { add[m]+=$1; del[m]+=$2; tA+=$1; tD+=$2 }
  END { for (k in add) printf "  %s  +%-7d -%-6d  net %+-7d  del/add %.2f\n", k, add[k], del[k], add[k]-del[k], del[k]/(add[k]?add[k]:1)
        printf "  WINDOW  +%-7d -%-6d  net %+-7d  del/add %.3f\n", tA, tD, tA-tD, tD/(tA?tA:1) }' | sort
}
ALLPS=""
for e in $(echo "$EXT" | tr ',' ' '); do ALLPS="$ALLPS *.$e"; done
echo "SCOPE LINE: all tracked source | ext=$EXT | since=$SINCE"
_ratio "$ALLPS"
if [ -n "$SRC" ]; then
  echo "SCOPE LINE: $SRC only | ext=$EXT | since=$SINCE"
  _ratio "$*"
fi
echo

echo "== 5. CROSS-BOUNDARY CO-CHANGE (tests excluded) =="
echo "   high % between different areas = one concept smeared across a seam"
git log --since="$SINCE" --pretty=format:'@@' --name-only -- "$@" 2>/dev/null | awk '
function flush(  i,j,a,b,t) {
  if (n>1 && n<=25) for (i=0;i<n;i++) for (j=i+1;j<n;j++) {
    a=f[i]; b=f[j]; if (a>b) { t=a; a=b; b=t }; pair[a"\t"b]++ }
  for (i=0;i<n;i++) cnt[f[i]]++; n=0 }
/^@@/ { flush(); next }
NF { if ($0 !~ /(^|\/)(tests?|spec|__tests__)\//) f[n++]=$0 }
END { flush()
  for (p in pair) { split(p,s,"\t")
    da=s[1]; sub(/\/[^\/]*$/,"",da); db=s[2]; sub(/\/[^\/]*$/,"",db)
    if (da != db) {
      m=(cnt[s[1]] < cnt[s[2]] ? cnt[s[1]] : cnt[s[2]])
      if (pair[p] >= 5 && m >= 8)
        printf "%3d%%  (%d of %d)  %s  <->  %s\n", pair[p]*100/m, pair[p], m, s[1], s[2] } } }' \
  | sort -rn | head -12
echo
fi

echo "== 6. INTERNAL IMPORT DIRECTION (look for arrows that should not exist) =="
echo "   third-party and stdlib filtered out; only edges between this repo's own modules"
git ls-files -- "$@" 2>/dev/null | awk '
{ n=split($0,p,"/")
  for (i=1;i<n;i++) print p[i]
  leaf=p[n]; sub(/\.[A-Za-z0-9]+$/,"",leaf); print leaf }' | sort -u > "/tmp/_cen_int.$$"
git grep -nE "^[[:space:]]*(from|import)[[:space:]]+[.A-Za-z_]|require\(|^[[:space:]]*use " -- "$@" 2>/dev/null | awk '
NR==FNR { internal[$0]=1; next }
{ i=index($0,":"); file=substr($0,1,i-1); rest=substr($0,i+1); j=index(rest,":"); line=substr(rest,j+1)
  src=file; sub(/\/[^\/]*$/,"",src)
  if (match(line, /(from|import|require\(|use)[[:space:]("\047]+[.A-Za-z_0-9@\/-]+/)) {
    t=substr(line, RSTART, RLENGTH); sub(/^(from|import|require\(|use)[[:space:]("\047]+/, "", t)
    gsub(/^[.\/]+/, "", t); nq=split(t, q, /[.\/]/)
    if (!(q[1] in internal)) next
    tgt=q[1]; if (nq > 1 && (q[2] in internal)) tgt=q[1]"."q[2]
    if (tgt != "") seen[src"  ->  "tgt]++ } }
END { for (k in seen) printf "%5d  %s\n", seen[k], k }' "/tmp/_cen_int.$$" - | sort -rn | head -18
rm -f "/tmp/_cen_int.$$"
echo

echo "== 7. SAME NAME DEFINED IN SEVERAL FILES (drift risk) =="
git grep -nE '^[[:space:]]*(def|class|function|func|fn|type|interface)[[:space:]]+[A-Za-z_]' -- "$@" 2>/dev/null \
 | grep -vE '(^|/)(tests?|spec|__tests__)/' | awk '
{ i=index($0,":"); file=substr($0,1,i-1); rest=substr($0,i+1); j=index(rest,":"); line=substr(rest,j+1)
  if (match(line, /(def|class|function|func|fn|type|interface)[[:space:]]+[A-Za-z_][A-Za-z_0-9]*/)) {
    t=substr(line, RSTART, RLENGTH); sub(/^[a-z]+[[:space:]]+/, "", t)
    if (t ~ /^(__init__|__repr__|__str__|__eq__|main|run|setUp|toString)$/) next
    k=t"\t"file; if (!(k in u)) { u[k]=1; n[t]++; w[t]=w[t]" "file } } }
END { for (t in n) if (n[t] >= 3) printf "%2d  %-24s %s\n", n[t], t, w[t] }' | sort -rn | head -10
echo

echo "== 8. CLONED BLOCKS (7 identical normalized lines, 2+ sites) =="
git grep -n '' -- "$@" 2>/dev/null | awk '
{ i=index($0,":"); file=substr($0,1,i-1); rest=substr($0,i+1); j=index(rest,":")
  ln=substr(rest,1,j-1); l=substr(rest,j+1)
  if (file ~ /(^|\/)(tests?|spec|__tests__)\//) next
  gsub(/^[ \t]+|[ \t]+$/, "", l); if (l == "" || l ~ /^(#|\/\/|\*|--)/) next
  if (file != pf) { n=0; pf=file }
  buf[n%7]=l; pos[n%7]=ln; n++
  if (n >= 7) { k=""; for (x=n-7; x<n; x++) k=k buf[x%7] "|"
    if (length(k) > 180) { site=file":"pos[(n-7)%7]
      if (!(k in seen)) seen[k]=site
      else if (seen[k] != site) {
        a=seen[k]; b=site; fa=a; sub(/:[0-9]+$/,"",fa); fb=b; sub(/:[0-9]+$/,"",fb)
        key=fa"|"fb; if (!(key in best)) best[key]=a"  <=>  "b } } } }
END { for (k in best) print best[k] }' | head -10
echo

echo "== 9. DEFINED BUT NEVER REFERENCED ELSEWHERE (dead-code CANDIDATES) =="
echo "   decorated definitions are skipped; still verify each - dynamic dispatch,"
echo "   entry points and template-side references do not appear as source tokens"
git grep -n '' -- "$@" 2>/dev/null | awk '
{ i=index($0,":"); file=substr($0,1,i-1); rest=substr($0,i+1); j=index(rest,":"); l=substr(rest,j+1)
  if (file ~ /(^|\/)(tests?|spec|__tests__)\//) { dec=0; next }
  gsub(/^[ \t]+|[ \t]+$/, "", l)
  isdef = match(l, /^(export[[:space:]]+)?(def|class|function|func|fn)[[:space:]]+[A-Za-z_][A-Za-z_0-9]*/)
  if (isdef && !dec) {
    t=substr(l, RSTART, RLENGTH); sub(/^(export[[:space:]]+)?[a-z]+[[:space:]]+/, "", t)
    if (!(t ~ /^_/) && length(t) >= 4) print t }
  dec = (l ~ /^@/ || l ~ /^#\[/) }' | sort -u > "/tmp/_cen_def.$$"
git grep -how '[A-Za-z_][A-Za-z_0-9]*' 2>/dev/null | sort | uniq -c > "/tmp/_cen_use.$$"
awk 'NR==FNR { c[$2]=$1; next } { if (c[$1] <= 1) print "  " $1 }' \
  "/tmp/_cen_use.$$" "/tmp/_cen_def.$$" | head -20
rm -f "/tmp/_cen_def.$$" "/tmp/_cen_use.$$"
echo

echo "== 10. CONFIGURATION SURFACE (every knob is a branch you must keep working) =="
ENVPAT="(environ(\.get)?\[?[\"${Q}][A-Z_0-9]+|getenv\([\"${Q}][A-Z_0-9]+|process\.env\.[A-Z_0-9]+)"
git grep -hoE "$ENVPAT" -- "$@" 2>/dev/null | grep -oE '[A-Z_0-9]{3,}' | sort -u > "/tmp/_cen_env.$$"
tr '\n' ' ' < "/tmp/_cen_env.$$" | fold -s -w 100
echo
echo "distinct env vars: $(wc -l < "/tmp/_cen_env.$$")"
echo "cli flags:         $(git grep -hoE '\"--[a-z][a-z0-9-]+\"' -- "$@" 2>/dev/null | sort -u | wc -l)"
rm -f "/tmp/_cen_env.$$"
