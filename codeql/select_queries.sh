#!/usr/bin/env bash
# Turn the security-extended suite name into a suite that also runs the
# in-source alert-suppression query. The security-extended selectors omit
# that kind, so a lgtm or noqa mark never reaches the SARIF upload.
set -euo pipefail

language="${CODEQL_LANGUAGE:-}"
requested="${CODEQL_QUERIES:-security-extended}"
config="${CODEQL_CONFIG_FILE:-}"

write_output() {
  if [ -n "${GITHUB_OUTPUT:-}" ]; then
    printf 'path=%s\n' "$1" >> "$GITHUB_OUTPUT"
  else
    printf '%s\n' "$1"
  fi
}

if [ -n "$config" ] || [ "$requested" != "security-extended" ]; then
  write_output "$requested"
  exit 0
fi

case "$language" in
  python)
    pack=codeql/python-queries
    ;;
  javascript | javascript-typescript)
    pack=codeql/javascript-queries
    ;;
  *)
    write_output "$requested"
    exit 0
    ;;
esac

# The codescanning config rejects an absolute path outside the repository.
# The suite file has to live in the workspace, and the queries input is relative.
root="${GITHUB_WORKSPACE:-.}"
mkdir -p "${root}/.codeql-suites"
dest="${root}/.codeql-suites/codeql-${language}-security-extended.qls"
cat > "$dest" << EOF
- description: Security-extended queries plus in-source alert suppressions
- queries: .
  from: ${pack}
- apply: security-extended-selectors.yml
  from: codeql/suite-helpers
- include:
    kind: alert-suppression
EOF
write_output "./.codeql-suites/codeql-${language}-security-extended.qls"
