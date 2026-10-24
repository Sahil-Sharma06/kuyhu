#!/usr/bin/env bash
# Pre-submission hygiene check. Exits non-zero if anything needs fixing.
#
# Usage:
#   PERSONAL_PATTERNS='realname|real.email@example.com' scripts/check_submission.sh
#
# PERSONAL_PATTERNS (an extended regex, case-insensitive) is passed in the environment so your
# personal details are never written into the repository itself.
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"

fail=0
ok()   { printf '  \033[32mOK\033[0m   %s\n' "$1"; }
bad()  { printf '  \033[31mFAIL\033[0m %s\n' "$1"; fail=1; }

echo "== Git identities (authors and committers in all history)"
idents="$(git log --all --format='%an <%ae>%n%cn <%ce>' | sort -u)"
echo "$idents" | sed 's/^/       /'
if echo "$idents" | grep -qviE 'noreply|anonymous|example\.com'; then
  bad "history contains non-anonymous identities (see docs/SUBMISSION_CHECKLIST.md, step 1)"
else
  ok "all identities are anonymous / noreply"
fi

echo "== Personal info in tracked files and commit messages"
if [[ -n "${PERSONAL_PATTERNS:-}" ]]; then
  hits="$(git grep -I -n -i -E "$PERSONAL_PATTERNS" -- . ':!frontend/package-lock.json' || true)"
  msg_hits="$(git log --all --format='%H %s%n%b' | grep -i -E "$PERSONAL_PATTERNS" || true)"
  hist_hits="$(git rev-list --all | xargs -I{} git grep -I -l -i -E "$PERSONAL_PATTERNS" {} -- . 2>/dev/null | sort -u || true)"
  [[ -z "$hits" ]] && ok "no matches in tracked files" || { bad "matches in tracked files:"; echo "$hits" | head -20; }
  [[ -z "$msg_hits" ]] && ok "no matches in commit messages" || { bad "matches in commit messages:"; echo "$msg_hits" | head; }
  [[ -z "$hist_hits" ]] && ok "no matches in any historical file" || { bad "matches in history:"; echo "$hist_hits" | head; }
else
  echo "       (set PERSONAL_PATTERNS to scan for your name/email/username)"
fi
emails="$(git grep -I -h -o -E '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' -- . ':!frontend/package-lock.json' | grep -viE 'noreply|example\.(com|org)' | sort -u || true)"
[[ -z "$emails" ]] && ok "no email addresses in tracked files" || { bad "email addresses found:"; echo "$emails"; }
paths="$(git grep -I -n -E '[A-Za-z]:\\\\Users\\\\|/Users/[A-Za-z]|/home/[a-z]' -- . || true)"
[[ -z "$paths" ]] && ok "no local home-directory paths" || { bad "local paths found:"; echo "$paths" | head; }
tracked_junk="$(git ls-files | grep -E '(^|/)(\.coverage|\.env|.*\.pem|.*\.key|node_modules/|\.venv/)' || true)"
[[ -z "$tracked_junk" ]] && ok "no coverage DBs, env files, keys or dependency dirs tracked" || { bad "should not be tracked:"; echo "$tracked_junk"; }

echo "== README contents"
readme="README.md"
check_readme() { grep -qiE "$2" "$readme" && ok "$1" || bad "README missing: $1"; }
check_readme "file / directory structure" "^## (Repository|Project|File).*structure"
check_readme "how to run locally"         "^### Locally"
check_readme "how to run with Docker"     "^### Docker"
check_readme "how to run tests"           "^### Tests|^## Testing"
check_readme "AI-usage statement"         "AI (tools|assistance).*Claude Code|Claude Code"
if grep -qE 'https://[a-z0-9-]+\.vercel\.app' "$readme" && ! grep -q '<your-project>' "$readme"; then
  ok "live Vercel link present"
else
  bad "live Vercel link is still a placeholder"
fi

echo
[[ $fail == 0 ]] && echo "All submission checks passed." || echo "Some checks failed: see docs/SUBMISSION_CHECKLIST.md."
exit $fail
