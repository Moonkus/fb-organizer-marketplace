#!/usr/bin/env bash
# fb-standards — PreToolUse(Bash) guard for `git push`: EGRESS and FORCE.
#
#   FORCE (core rule 6): refuse `--force`, `-f` (also in combined short flags), `--mirror` and `+refspec`
#   anywhere in the push — permission rules only match a `git push --force` PREFIX. `--force-with-lease`
#   (with or without `--force-if-includes`) is allowed for your own feature branch after a rebase, and
#   refused when it targets the default branch.
#
#   EGRESS (rules/security.md): refuse pushing to a remote that is not
#      github.com/<ALLOWED_OWNER>/. Project settings deny
#      curl/wget/ssh/scp but NOT git, so for the git egress vector this hook is
#      the PRIMARY client-side control. It RAISES THE BAR against accidental and
#      common arbitrary-remote pushes — `git push https://elsewhere/x …`, a
#      `remote set-url --push` swap, `--repo <url>`, and named remotes — but it
#      is NOT a hard boundary (see "Known residuals" below).
#
# The guard makes a single allow/block decision for the WHOLE Bash command, so it
# splits the command on shell separators and checks EVERY `git push` segment —
# otherwise a chained `git push <evil-url> … && git push origin …` would slip the
# first push past a check that only saw the last one. A separator inside quotes or
# after a backslash is not a separator (`cd "/a;b" && git push` is ONE cd). Heredoc
# bodies are removed before the quotes are read, so an apostrophe in one is not an
# unmatched quote; a quote that is still unmatched refuses the push. A `cd`
# whose target the guard cannot read literally (`cd $DIR`, `cd a\;b`) does not make
# it guess: a push governed by it is refused with the fix spelled out.
#
# Known residuals (NOT caught — inherent to a bash command-string guard):
#   - a wrapper/prefix that isn't a command boundary: `env git push …`,
#     `command git push …`, `/usr/bin/git …`, `\git …`, or a shell alias.
#   (an inline config override, `git -c remote.origin.pushurl=<evil> push origin`, used
#   to be one: it is now refused, as is every leading option other than `-C <dir>`.)
#   Documented, not chased; a determined caller wins, so server-side controls
#   and code review remain the backstop.
#
# Known limitations (safe direction — may false-block, never false-allow):
#   - a userless scp remote (`github.com:Moonkus/x.git`, no user@) falls into
#     the unresolvable-remote path and fails CLOSED. Quoted `-C` / `cd` operands
#     (paths with spaces) are parsed.
#   - a `cd` whose target is not a literal path (a variable, a subshell) leaves
#     the target repository unresolved; a push governed by it is refused, not guessed.
#   - a quote left unmatched outside a heredoc body makes the command unparsable;
#     a push in such a command is refused rather than evaluated on a guessed split.
#
# Convention: block with exit 2 + an explanatory message on stderr; allow with
# exit 0. Any command without a `git push` passes straight through.
set -euo pipefail

# Allowed push destination: github.com/<owner>/… (case-insensitive).
ALLOWED_HOST="github.com"
ALLOWED_OWNER="${FB_STANDARDS_GH_OWNER:-Moonkus}"

input="$(cat)"

# jq parses the tool command. If it is absent, the sibling secret-scan hook
# already fails closed and blocks all Bash, so here we simply pass through.
command -v jq >/dev/null 2>&1 || exit 0
cmd="$(printf '%s' "$input" | jq -r '.tool_input.command // empty')"
[ -z "$cmd" ] && exit 0

# A real `git [-C dir]* push` at a command boundary — so prose that merely
# mentions "push" (e.g. a commit message) does not trip the guard.
# A `-C` operand may be quoted and contain spaces; the pattern must accept that,
# otherwise `git -C "a b" push <evil>` never matches and the hook exits 0 without
# looking - a silent bypass, not a fail-closed refusal.
q="'"
# Any leading option is accepted by the DETECTOR (`-C dir`, `-c k=v`, `--git-dir=x`, `--bare`…)
# so the segment reaches the evaluation, where only `-C <dir>` is allowed and the rest refused.
gitpush_re='(^|[;&|(`]|&&|\|\|)[[:space:]]*git([[:space:]]+-[^[:space:]]+([[:space:]]+("[^"]*"|'"$q"'[^'"$q"']*'"$q"'|[^-[:space:]][^[:space:]]*))?)*[[:space:]]+push([[:space:]]|$)'
printf '%s' "$cmd" | grep -Eq "$gitpush_re" || exit 0
# one leading `-C <operand>` (quoted or bare) followed by the rest of the invocation
c_opt_re='^-C[[:space:]]+("([^"]*)"|'"$q"'([^'"$q"']*)'"$q"'|([^[:space:]]+))[[:space:]]+(.*)$'

# WHICH REPOSITORY the check runs against has to be resolved deliberately. The
# hook is a separate process: its own cwd is the session's project root, and a
# `cd` that runs INSIDE the command is invisible to it. Getting this wrong would
# check a different repository than the one being pushed, letting a push whose
# configured remote is not an allowed host through.
#
# Precedence, most explicit first:
#   1. `git -C <dir>` on the invocation - stated per call, always wins
#   2. the literal `cd <dir> &&` / `cd <dir>;` in force at that point of the command
#      (relative targets chain; a subshell's cd ends at its `)`)
#   3. `.cwd` from the tool payload (the session's working directory)
#   4. the hook's own cwd (last resort)
# A non-literal `cd` target (variable, subshell, glob) is NOT guessed - we warn.
hook_cwd="$(printf '%s' "$input" | jq -r '.cwd // empty')"

# The effective `cd` is tracked PER SEGMENT, in command order, inside the loop
# below: a bare literal `cd <dir>` takes effect only if the separator that follows
# it is `&&` or `;` (a `cd` before `|`, `||` or `&` runs in a subshell or on the
# failure branch), and a later `cd` replaces an earlier one. Computing a single
# "last cd" for the whole command let `cd A && <push>; cd B && <push>` resolve
# BOTH pushes from B.

warn() {
  {
    echo "WARNING  fb-standards git-push guard: $1"
    [ $# -gt 1 ] && printf '%s\n' "$2"
  } >&2
}

block() {
  {
    echo "==============================="
    echo "🛑 fb-standards git-push guard: BLOCKED"
    echo "==============================="
    printf '%s\n' "$1"
  } >&2
  exit 2
}

# True only when a push URL's HOST authority is $ALLOWED_HOST and its path is under
# the $ALLOWED_OWNER namespace. Parses the URL instead of substring-matching, so a
# decoy like https://evil.com/github.com/Moonkus/x.git does NOT pass.
is_allowed_remote() {
  local url="$1" rest authority host path
  case "$url" in
    *://*)
      rest="${url#*://}"                          # strip scheme
      authority="${rest%%/*}"                     # authority = up to the first / (before the path)
      authority="${authority#*@}"                 # strip userinfo from the AUTHORITY only —
                                                  # stripping from the whole remainder would let a
                                                  # path '@' (evil.com/@github.com/…) forge the host
      host="${authority%%:*}"                     # drop an optional :port
      path="${rest#*/}"                            # path = after the first /
      [ "$path" = "$rest" ] && path="" ;;          # no / → no path
    *:*)
      # scp-style [user@]host:path — isolate the authority (up to the FIRST ':')
      # BEFORE stripping user@, so a 'user@host' later in the path can't forge the
      # host (evil.com:foo@github.com:…). No port in scp form.
      authority="${url%%:*}"                       # [user@]host
      authority="${authority#*@}"                  # strip optional user@ from the authority only
      host="$authority"
      path="${url#*:}" ;;                          # path = after the first :
    *)
      return 1 ;;                                  # no scheme and no ':' → local path / bare token
  esac
  host="$(printf '%s' "$host" | tr 'A-Z' 'a-z')"
  path="$(printf '%s' "$path" | tr 'A-Z' 'a-z')"
  local owner
  owner="$(printf '%s' "$ALLOWED_OWNER" | tr 'A-Z' 'a-z')"
  [ "$host" = "$ALLOWED_HOST" ] || return 1
  case "$path" in "$owner"/*) return 0 ;; *) return 1 ;; esac
}

git_c() { if [ -n "$cdir" ]; then git -C "$cdir" "$@"; else git "$@"; fi; }

# Evaluate each command segment independently. Splitting on ; & | && || means a
# chained command can't hide an earlier push behind a later legitimate one.
# `while … done <<<` runs in THIS shell (not a pipe subshell) so block()'s exit
# propagates. Every pipeline gets `|| true`: under pipefail a failing/SIGPIPE'd
# stage would otherwise abort the whole hook via set -e.
# The `&` inside a redirection (`2>&1`, `&>file`) is not a separator; mask it with a
# control byte before splitting and restore it per segment.
RD="$(printf '\001')"
# Separators inside quotes or after a backslash are masked with control bytes so
# the split below leaves them alone; `unmask` restores them per segment. Bash 3.2
# safe (no associative arrays); the replacement is quoted so bash 5.2's
# patsub_replacement does not read a literal `&` as "the match".
M_SEMI=$'\002'; M_AMP=$'\003'; M_PIPE=$'\004'; M_LP=$'\005'; M_RP=$'\006'; M_NL=$'\007'; M_SP=$'\010'
mask_quoted() {
  # Quote states: "" (none), '"', "'", and "$'" for Bash ANSI-C quoting, where a
  # backslash escapes the next character (so `$'x\' # y'` is one word, not a quote
  # followed by a comment). A comment runs from an unquoted word-initial `#` to the
  # end of its line and is inert.
  local str="$1" out="" q="" esc=0 cmt=0 prev i c m n="${#1}"
  for ((i = 0; i < n; i++)); do
    c="${str:i:1}"
    case "$c" in ';') m="$M_SEMI" ;; '&') m="$M_AMP" ;; '|') m="$M_PIPE" ;; '(') m="$M_LP" ;; ')') m="$M_RP" ;; $'\n') m="$M_NL" ;; ' '|$'\t') m="$M_SP" ;; *) m="$c" ;; esac
    if [ "$esc" = 1 ]; then esc=0; out+="$m"; continue; fi
    if [ "$cmt" = 1 ]; then
      if [ "$c" = $'\n' ]; then cmt=0; out+="$c"; else out+=" "; fi
      continue
    fi
    if [ -z "$q" ]; then
      if [ "$c" = '#' ]; then
        prev=""; [ "$i" -gt 0 ] && prev="${str:i-1:1}"
        case "$prev" in ''|' '|$'\t'|';'|'&'|'|'|'('|')') cmt=1; out+=" "; continue ;; esac
      fi
      if [ "$c" = '$' ] && [ "${str:i+1:1}" = "'" ]; then q="\$'"; out+="\$'"; i=$((i + 1)); continue; fi
      case "$c" in '\') esc=1 ;; '"'|"'") q="$c" ;; esac
      out+="$c"
    elif [ "$q" = '"' ]; then
      case "$c" in '\') esc=1; out+="$c" ;; '"') q=""; out+="$c" ;; *) out+="$m" ;; esac
    elif [ "$q" = "\$'" ]; then
      case "$c" in '\') esc=1; out+="$c" ;; "'") q=""; out+="$c" ;; *) out+="$m" ;; esac
    else
      case "$c" in "'") q=""; out+="$c" ;; *) out+="$m" ;; esac
    fi
  done
  # A quote still open at the end: the command cannot be split reliably, and a
  # guessed split can separate a quoted option value from the destination it hides
  # (`--push-option="x;y" <url>`). Fail, and let the caller refuse.
  if [ -n "$q" ]; then return 1; fi
  printf '%s' "$out"
}
# Heredoc bodies are data, not shell: an apostrophe in one is not an unmatched quote,
# and a `git push` line in one is not a push. Drop every body (and its terminator)
# before the quotes are read; the operator line itself stays. Only a real operator
# opens a body: not `<<` inside quotes, not the `<<<` here-string.
strip_heredocs() {
  # A `<<` inside quotes or a comment is text, not an operator, and `<<<` is a
  # here-string. The operators are found in a copy of the line with every quoted,
  # escaped or commented character blanked - the quote state carries across lines -
  # and each delimiter is read from the original line as ONE shell word after quote
  # removal. A line may open several heredocs (`cat <<ONE <<TWO`): their bodies
  # follow in order, so the delimiters are queued and consumed one by one.
  local out="" q="" esc=0 line probe vis rest i c n pre op prev off sub
  local wq wesc wansi wseen wn wi wc delim
  local -a hd_delim=() hd_tabs=()
  local hd_i=0
  while IFS= read -r line || [ -n "$line" ]; do
    if [ "$hd_i" -lt "${#hd_delim[@]}" ]; then
      probe="$line"; [ "${hd_tabs[$hd_i]}" = 1 ] && probe="${probe#"${probe%%[!$'\t']*}"}"
      [ "$probe" = "${hd_delim[$hd_i]}" ] && hd_i=$((hd_i + 1))
      continue
    fi
    hd_delim=(); hd_tabs=(); hd_i=0
    out+="$line"$'\n'
    vis=""; n="${#line}"
    for ((i = 0; i < n; i++)); do
      c="${line:i:1}"
      if [ "$esc" = 1 ]; then esc=0; vis+=" "; continue; fi
      if [ -z "$q" ] && [ "$c" = '#' ]; then
        prev=""; [ "$i" -gt 0 ] && prev="${line:i-1:1}"
        case "$prev" in ''|' '|$'\t'|';'|'&'|'|'|'('|')') break ;; esac
      fi
      if [ -z "$q" ]; then
        if [ "$c" = '$' ] && [ "${line:i+1:1}" = "'" ]; then q="\$'"; vis+="  "; i=$((i + 1)); continue; fi
        case "$c" in '\') esc=1; vis+=" " ;; '"'|"'") q="$c"; vis+=" " ;; *) vis+="$c" ;; esac
      elif [ "$q" = '"' ]; then
        case "$c" in '\') esc=1 ;; '"') q="" ;; esac; vis+=" "
      elif [ "$q" = "\$'" ]; then
        case "$c" in '\') esc=1 ;; "'") q="" ;; esac; vis+=" "
      else
        [ "$c" = "'" ] && q=""; vis+=" "
      fi
    done
    off=0
    while sub="${vis:off}"; [[ "$sub" =~ (^|[^\<])(\<\<-?)([^\<]|$) ]]; do
      op="${BASH_REMATCH[1]}${BASH_REMATCH[2]}"
      pre="${sub%%"$op"*}"
      off=$((off + ${#pre} + ${#op}))
      rest="${line:off}"
      rest="${rest#"${rest%%[![:space:]]*}"}"
      off=$(( ${#line} - ${#rest} ))
      # one shell WORD after quote removal - `E"OF"`, `'E'OF` and `E\OF` all terminate on `EOF`
      delim=""; wq=""; wesc=0; wansi=0; wseen=0; wn="${#rest}"
      for ((wi = 0; wi < wn; wi++)); do
        wc="${rest:wi:1}"
        if [ "$wesc" = 1 ]; then wesc=0; delim+="$wc"; continue; fi
        if [ -z "$wq" ]; then
          if [ "$wc" = '$' ] && [ "${rest:wi+1:1}" = "'" ]; then wq="\$'"; wseen=1; wi=$((wi + 1)); continue; fi   # ANSI-C $'…'
          case "$wc" in
            '\') wesc=1; wseen=1 ;;
            '"'|"'") wq="$wc"; wseen=1 ;;     # `<<''` is a valid EMPTY delimiter: the body ends at the next empty line
            ' '|$'\t'|';'|'&'|'|'|'<'|'>'|'('|')') break ;;
            *) delim+="$wc"; wseen=1 ;;
          esac
        elif [ "$wq" = '"' ]; then
          case "$wc" in '\') wesc=1 ;; '"') wq="" ;; *) delim+="$wc" ;; esac
        elif [ "$wq" = "\$'" ]; then
          case "$wc" in '\') wesc=1; wansi=1 ;; "'") wq="" ;; *) delim+="$wc" ;; esac
        else
          if [ "$wc" = "'" ]; then wq=""; else delim+="$wc"; fi
        fi
      done
      off=$((off + wi))
      # `$'\x45OF'` decodes to EOF in bash; the guard does not decode C escapes and will
      # not guess where such a body ends - the caller refuses the command
      [ "$wansi" = 1 ] && return 1
      if [ "$wseen" = 1 ]; then
        hd_delim+=("$delim")
        case "$op" in *'<<-'*) hd_tabs+=(1) ;; *) hd_tabs+=(0) ;; esac
      fi
      [ "$off" -lt "${#vis}" ] || break
    done
  done <<< "$1"
  [ "$hd_i" -lt "${#hd_delim[@]}" ] && return 2
  printf '%s' "${out%$'\n'}"
}
unmask() {
  local str="$1"
  str="${str//$M_SEMI/";"}"; str="${str//$M_AMP/"&"}"; str="${str//$M_PIPE/"|"}"
  str="${str//$M_LP/"("}";   str="${str//$M_RP/")"}";  str="${str//$M_NL/$'\n'}"; str="${str//$M_SP/" "}"; str="${str//$RD/"&"}"
  printf '%s' "$str"
}
cmd_split="$cmd"
case "$cmd" in *'<<'*)
  set +e; cmd_split="$(strip_heredocs "$cmd")"; hd_rc=$?; set -e
  case "$hd_rc" in
    1) block "A heredoc delimiter uses ANSI-C quoting with escapes (\$'…' containing a backslash). The guard does
not decode C escapes and will not guess where that body ends — refused. Use a plain or quoted delimiter
(<<EOF, <<'EOF')." ;;
    2) block "A heredoc in this command is never terminated, so the guard cannot tell where its body ends and
the commands resume — refused. Close the heredoc with its delimiter on a line of its own." ;;
  esac ;;
esac
case "$cmd_split" in
  *['"'"'"\\]*)
    if ! cmd_split="$(mask_quoted "$cmd_split")"; then
      block "Cannot parse the quoting of this command: a quote is left unmatched outside any heredoc
body, so the push destination cannot be determined — refused rather than evaluated on a guessed split.
Balance the quotes, or run the push as a separate command."
    fi ;;
esac

state_cd=""   # effective literal `cd` for the current chain (always absolute once set); "?" = unresolvable
prev_cd=""    # target of the previous segment, if it was a bare literal `cd`
scope=()      # saved state_cd per open `(` - a subshell's cd dies at its `)`
while IFS= read -r line; do
  case "$line" in
    '&&'|';')
      if [ -n "$prev_cd" ]; then
        # a relative target is relative to the directory in force, not to the session;
        # an unresolvable cd ("?") poisons the chain until an absolute cd or a `)`
        case "$prev_cd" in
          '?') new_cd='?' ;;
          /*) new_cd="$prev_cd" ;;
          *) if [ "$state_cd" = '?' ]; then new_cd='?'; else new_cd="${state_cd:-$hook_cwd}/$prev_cd"; fi ;;
        esac
        if [ "$new_cd" != '?' ] && [ ! -d "$new_cd" ]; then
          # `cd missing` fails and the shell STAYS where it was; with `;` the push still
          # runs there. Never fall back to the session cwd - that is a different repository.
          warn "cannot resolve the target directory of 'cd $prev_cd' - $new_cd does not exist;" \
               "    the shell stays in ${state_cd:-$hook_cwd}, so the push is evaluated there."
        else
          state_cd="$new_cd"
        fi
      fi
      prev_cd=""; continue ;;
    '|'|'||'|'&') prev_cd=""; continue ;;   # a cd followed by these never reaches the push
    '(') scope+=("$state_cd"); prev_cd=""; continue ;;
    ')') if [ ${#scope[@]} -gt 0 ]; then state_cd="${scope[${#scope[@]}-1]}"; unset 'scope[${#scope[@]}-1]'; fi
         prev_cd=""; continue ;;
  esac
  raw="$(printf '%s' "$line" | tr '\t' ' ')"           # still masked - safe to parse structurally
  seg="$(unmask "$raw")"                                  # what bash will actually see
  [ -n "${seg// /}" ] || continue                        # empty piece between separators

  # A bare `cd <literal>` segment becomes the pending cd; it is committed by the
  # next `&&`/`;`, dropped by `|`, `||`, `&`, and scoped by `(` … `)`.
  # Trailing redirections (`>/dev/null`, `2>&1`) do not stop it being a cd.
  target="$(printf '%s' "$raw" \
    | sed -nE 's/^[[:space:]]*cd[[:space:]]+("([^"]*)"|'"$q"'([^'"$q"']*)'"$q"'|([^;&|()`<>[:space:]]+))([[:space:]]+[0-9]*[<>]+[^[:space:]]*)*[[:space:]]*$/\2\3\4/p')"
  if [ -n "$target" ]; then
    target="$(unmask "$target")"
    case "$target" in '-'|*'$'*|*'`'*|*'*'*|*'~'*|*'\'*) target='?' ;; esac   # not literal - do not guess
    prev_cd="$target"
    continue
  fi
  case "$raw" in
    cd|cd[[:space:]]*|[[:space:]]*cd|[[:space:]]*cd[[:space:]]*)
      prev_cd='?'; continue ;;   # a `cd` we could not parse (`cd -`, `cd "$(…)"`, two operands): unknown directory
  esac
  prev_cd=""
  printf '%s' "$seg" | grep -Eq "$gitpush_re" || continue

  # A segment holding an ODD number of quotes was produced by splitting INSIDE a
  # quoted string - it is not a command boundary, and its "arguments" are
  # fragments of someone's prose. Skip it. This is why a log entry quoting an
  # earlier push, and any echo of a command containing one, used to be refused:
  # a guard that fires on prose DESCRIBING a command pushes people toward vaguer
  # records, which is the opposite of what it is for.
  # ...but NEVER skip a segment that names a destination. A URL, an scp-style
  # host:path, or --repo is a real push target whatever the quoting around it;
  # an unbalanced quote in such a segment must not become a bypass.
  has_dest=0
  case "$seg" in *://*|*--repo*) has_dest=1 ;; esac
  if [ "$has_dest" = 0 ] && printf '%s' "$seg" \
       | grep -Eq '([A-Za-z0-9._-]+@[A-Za-z0-9.-]+:|[A-Za-z0-9-]+\.[A-Za-z]{2,}:[^[:space:]])'; then
    has_dest=1
  fi
  q1="$(printf '%s' "$seg" | tr -cd "'" | wc -c | tr -d ' ')"
  q2="$(printf '%s' "$seg" | tr -cd '"' | wc -c | tr -d ' ')"
  if [ "$has_dest" = 0 ] && { [ $((q1 % 2)) -ne 0 ] || [ $((q2 % 2)) -ne 0 ]; }; then continue; fi

  # Git applies EVERY leading `-C` in order, a relative one from the directory the
  # previous ones selected (`git -C /safe -C ../other push` runs in /safe/../other).
  # Read them all the same way; the first alone would validate the wrong repository.
  cdir=""; cdir_src="git -C"
  if [[ "$seg" =~ (^|[\;\&\|\(\`]|\&\&|\|\|)[[:space:]]*git[[:space:]]+(.*)$ ]]; then
    rest="${BASH_REMATCH[2]}"
    while :; do
      if ! [[ "$rest" =~ $c_opt_re ]]; then
        # Any other leading option is refused. `-c remote.origin.pushurl=<url>` and
        # `--config-env` redirect the push behind the URL check; `--git-dir`/`--work-tree`
        # move it to a repository the guard is not looking at. Fail closed, name it.
        if [[ "$rest" =~ ^(-[^[:space:]]*) ]]; then
          block "Refused: '${BASH_REMATCH[1]}' before 'push' is not supported by the guard. Inline configuration
(-c, --config-env) can redirect a push behind the destination check, and --git-dir/--work-tree move it to a
repository the guard is not looking at. Use 'git [-C <dir>] push …' with the repository's configured remote or
an explicit git@github.com:$ALLOWED_OWNER/… URL."
        fi
        break
      fi
      d="${BASH_REMATCH[2]}${BASH_REMATCH[3]}${BASH_REMATCH[4]}"; rest="${BASH_REMATCH[5]}"
      base="${cdir:-${state_cd:-$hook_cwd}}"
      case "$d" in
        /*) cdir="$d" ;;
        *) if [ "$base" = '?' ]; then cdir='?'; break; fi; cdir="$base/$d" ;;
      esac
    done
  fi
  if [ -z "$cdir" ]; then
    if [ -n "$state_cd" ]; then cdir="$state_cd"; cdir_src="cd in the command"
    else cdir="$hook_cwd"; cdir_src="session cwd"; fi
  fi
  if [ "$cdir" = '?' ]; then
    block "Cannot tell which repository this push runs in: a preceding 'cd' has a target the guard
cannot read literally (a variable, a glob, a backslash escape, or a form it does not parse), so the
push destination cannot be checked — refused rather than guessed.
Use 'git -C <absolute-dir> push …' or 'cd <absolute literal path> && git push …'."
  fi
  if [ -n "$cdir" ] && [ ! -d "$cdir" ]; then
    block "The directory this push would run in does not exist ($cdir_src -> $cdir).
The guard cannot verify a destination in a directory that is not there, and will not measure a
different repository instead — refused. Check the path, or use 'git -C <existing-dir> push …'."
  fi
  # Args = everything after the FIRST " push" (bash shortest-prefix strip). Anchoring
  # to the first occurrence, not a greedy last one, matters: a trailing word "push"
  # (e.g. a `# … push` comment or an argument) must not redirect parsing to the tail,
  # or the guard would validate the wrong destination.
  # Split on the MASKED text so a quoted value containing spaces (`--push-option="a b"`,
  # `$'x\' # note'`) stays one token; each token is unmasked before it is read.
  pushpart="${raw#* push}"
  [ "$pushpart" = "$raw" ] && pushpart=""      # no " push" found (defensive) → treat as bare push

  # ---- EGRESS -------------------------------------------------------------
  # Find the push destination. Skip flags AND the separate value after a
  # value-taking flag that is NOT a destination (-o ci.skip, --push-option v,
  # --receive-pack p, --exec e). `--repo <url>` / `--repo=<url>` is different:
  # its value IS a push destination — but per git-push(1) the positional
  # <repository> argument TAKES PRECEDENCE when both are given, so mirror that
  # exactly: keep scanning for a positional and only fall back to --repo.
  remote_tok=""
  repo_tok=""
  skip_next=0
  take_next=0
  while IFS= read -r tok; do
    [ -z "$tok" ] && continue
    tok="$(unmask "$tok")"
    if [ "$take_next" = 1 ]; then repo_tok="$tok"; take_next=0; continue; fi   # value of --repo
    if [ "$skip_next" = 1 ]; then skip_next=0; continue; fi
    case "$tok" in
      --repo=*) repo_tok="${tok#--repo=}"; continue ;;            # --repo=<destination>
      --repo)   take_next=1; continue ;;                           # --repo <destination>
      -o|--push-option|--receive-pack|--exec) skip_next=1; continue ;;
      -*) continue ;;
      # Shell redirection is not a push destination. A token ENDING in '>' takes
      # its target as the next word ('> log', '2> log'); one that merely contains
      # '>' or '<' is self-contained ('2>&1', '2>/dev/null'). Without this, an
      # ordinary push piped to tail resolved its "remote" to '2>' and was refused
      # - a false block, and the reason people stop capturing command output.
      *'>') skip_next=1; continue ;;
      *'>'*|*'<'*) continue ;;
    esac
    remote_tok="$tok"
    # Strip one layer of quoting so a quoted URL is still parsed as a URL rather
    # than falling into the unresolvable-remote path.
    case "$remote_tok" in
      \'*\')   remote_tok="${remote_tok#\'}";  remote_tok="${remote_tok%\'}" ;;
      '"'*'"') remote_tok="${remote_tok#\"}"; remote_tok="${remote_tok%\"}" ;;
    esac
    break                                                          # positional — wins over --repo
  done <<< "$(printf '%s' "$pushpart" | tr ' ' '\n')"
  [ -n "$remote_tok" ] || remote_tok="$repo_tok"                   # no positional → --repo is the target

  # ---- FORCE ---------------------------------------------------------------
  force=""; lease=0; seen_remote=0; refspecs=(); skip_next=0
  while IFS= read -r tok; do
    [ -z "$tok" ] && continue
    tok="$(unmask "$tok")"
    if [ "$skip_next" = 1 ]; then skip_next=0; continue; fi
    case "$tok" in
      --force|--mirror) force="$tok" ;;
      --force-with-lease|--force-with-lease=*|--force-if-includes) lease=1 ;;
      --repo|-o|--push-option|--receive-pack|--exec) skip_next=1 ;;
      --*) : ;;
      -*) case "$tok" in *f*) force="$tok" ;; esac ;;
      *'>') skip_next=1 ;;
      *'>'*|*'<'*) : ;;
      *) if [ "$seen_remote" = 0 ]; then seen_remote=1
         else refspecs+=("$tok"); case "$tok" in +*) force="$tok" ;; esac; fi ;;
    esac
  done <<< "$(printf '%s' "$pushpart" | tr ' ' '\n')"
  if [ -n "$force" ]; then
    block "Force push ($force) is refused — it rewrites published history (core rule 6).
After rebasing your own feature branch, use: git push --force-with-lease"
  fi
  if [ "$lease" = 1 ]; then
    def="$(git_c symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || true)"
    def="${def#origin/}"; [ -n "$def" ] || def=main
    cur="$(git_c rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
    to_def=0
    if [ ${#refspecs[@]} -eq 0 ]; then
      [ "$cur" = "$def" ] && to_def=1
    else
      for rs in "${refspecs[@]}"; do
        dst="${rs##*:}"; [ "$dst" = "HEAD" ] && dst="$cur"; dst="${dst#refs/heads/}"
        [ "$dst" = "$def" ] && to_def=1
      done
    fi
    if [ "$to_def" = 1 ]; then
      block "--force-with-lease to '$def' is refused — $def's history is never rewritten.
Lease-force only your own feature branch."
    fi
  fi

  target_url=""
  resolved=1
  case "$remote_tok" in
    *://*|*@*:*)
      target_url="$remote_tok" ;;                                    # explicit URL
    "")
      br="$(git_c rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
      rmt="$(git_c config --get "branch.${br}.remote" 2>/dev/null || echo origin)"
      target_url="$(git_c remote get-url --push "$rmt" 2>/dev/null || true)" ;;  # bare push → branch's PUSH url
    *)
      target_url="$(git_c remote get-url --push "$remote_tok" 2>/dev/null || true)"  # named remote → resolve PUSH url
      [ -n "$target_url" ] || resolved=0 ;;                          # named but unresolvable
  esac

  if [ "$resolved" = 0 ]; then
    # An explicit remote name we cannot resolve to a URL — fail closed rather
    # than treat "unknown" as "allowed".
    block "Cannot resolve push remote '$remote_tok' to a URL, so its destination
can't be verified against github.com/$ALLOWED_OWNER — refused (rules/security.md).
Use the repo's configured origin or an explicit git@github.com:$ALLOWED_OWNER/… URL."
  fi
  if [ -n "$target_url" ] && ! is_allowed_remote "$target_url"; then
    block "Push target is not under github.com/$ALLOWED_OWNER:
    $target_url
Pushing to an arbitrary remote is a data-exfiltration path and is refused by policy
(rules/security.md). Push to the repo's github.com/$ALLOWED_OWNER/… remote."
  fi
done <<< "$(printf '%s' "$cmd_split" | tr '\n' ';' \
  | sed -E "s/([<>])&([0-9])/\1${RD}\2/g; s/&>/${RD}>/g" \
  | sed -E 's/(&&|\|\||[;&|()])/\n\1\n/g')"

exit 0
