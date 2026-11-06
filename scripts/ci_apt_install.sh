#!/usr/bin/env bash
# ================================================================
# Install Ubuntu packages in CI without letting a mirror stall eat the job (#1871)
# ================================================================
# Usage: scripts/ci_apt_install.sh PACKAGE...
#
# A stalled Azure Ubuntu mirror can hang `apt-get install` until the job
# timeout cancels the job. This wrapper bounds every network wait:
#   - apt retries each failed fetch (Acquire::Retries) and gives up on a
#     silent connection after 30 seconds (Acquire::http(s)::Timeout);
#   - each apt-get or dpkg command is stopped if it runs longer than
#     APT_ATTEMPT_TIMEOUT seconds (default 120), and killed 30 seconds later
#     if it ignores the stop signal;
#   - the whole update + install is attempted APT_INSTALL_ATTEMPTS times
#     (default 2) before the script fails. Before each retry,
#     `dpkg --configure -a` finishes any package configuration a stopped
#     install left half done; otherwise the retry fails at once on
#     "dpkg was interrupted" or the dpkg lock.
# Worst case with the defaults: 5 bounded commands (update + install, then
# dpkg --configure + update + install) x (120 s + 30 s) + 10 s delay = 760 s.
# Workflow steps set timeout-minutes above that and below their job timeout.
# ================================================================

set -uo pipefail

if [[ $# -eq 0 ]]; then
    echo "usage: $0 PACKAGE..." >&2
    exit 2
fi

ATTEMPTS="${APT_INSTALL_ATTEMPTS:-2}"
ATTEMPT_TIMEOUT="${APT_ATTEMPT_TIMEOUT:-120}"
RETRY_DELAY="${APT_RETRY_DELAY:-10}"
APT_OPTIONS=(
    -o Acquire::Retries=3
    -o Acquire::http::Timeout=30
    -o Acquire::https::Timeout=30
)

for (( attempt = 1; attempt <= ATTEMPTS; attempt++ )); do
    echo "apt install attempt ${attempt}/${ATTEMPTS}: $*"
    if (( attempt > 1 )); then
        # A stopped install can leave dpkg mid-configure; repair it, bounded
        # like the other commands. A failure here is reported, and any real
        # problem then surfaces from apt-get below.
        if ! sudo timeout --kill-after=30 "${ATTEMPT_TIMEOUT}" dpkg --configure -a; then
            echo "warning: dpkg --configure -a did not complete before attempt ${attempt}" >&2
        fi
    fi
    if sudo timeout --kill-after=30 "${ATTEMPT_TIMEOUT}" apt-get "${APT_OPTIONS[@]}" update \
        && sudo timeout --kill-after=30 "${ATTEMPT_TIMEOUT}" apt-get "${APT_OPTIONS[@]}" \
            install -y --no-install-recommends "$@"; then
        echo "apt install succeeded on attempt ${attempt}"
        exit 0
    else
        status=$?
    fi
    # timeout(1) exits 124 when it had to stop a stalled apt-get.
    echo "apt install attempt ${attempt} failed or stalled (exit ${status})" >&2
    if (( attempt < ATTEMPTS )); then
        sleep "${RETRY_DELAY}"
    fi
done

echo "apt install failed after ${ATTEMPTS} attempts" >&2
exit 1
