#!/usr/bin/env bash
# ================================================================
# Install Ubuntu packages in CI without failing on a slow or stalled mirror (#1871)
# ================================================================
# Usage: scripts/ci_apt_install.sh PACKAGE...
# CI calls this through .github/actions/apt-install, which restores and saves
# the .deb cache.
#
# azure.archive.ubuntu.com sometimes serves packages at about 40 KB/s while
# still making progress; a 38-minute install on develop exited 0. The script
# therefore stops a stalled download but never a slow, live one on the final
# attempt:
#   - apt drops a connection that sends no data for 30 seconds
#     (Acquire::http(s)::Timeout covers the connection and the data timeout)
#     and retries the fetch (Acquire::Retries). That is the stall detector.
#   - Attempt 1 uses the runner's primary mirror. Its network phases (update
#     and install --download-only) stop after APT_ATTEMPT_TIMEOUT seconds
#     (default 120), so a slow mirror hands over early. Downloaded .deb files
#     stay in the archive directory and the retry reuses them.
#   - Before each retry, `dpkg --configure -a` finishes anything a stopped
#     install left half configured, and APT_PRIMARY_MIRROR_HOST is replaced by
#     APT_FALLBACK_MIRROR_HOST in the mirror list and the sources files.
#   - The final attempt's network phases share one wall-clock budget of
#     APT_FINAL_NETWORK_TIMEOUT seconds (default 2700, 45 minutes). That is
#     above the slowest install seen to finish (38m36s, whole step, on
#     develop), so a slow but live download completes, while a trickle that
#     never trips the stall detector cannot hold the runner for the six-hour
#     job default.
#   - Installing from the downloaded files (the dpkg phase), the dpkg repair
#     and autoclean stop after APT_DPKG_TIMEOUT seconds (default 300) on every
#     attempt, so a hang that is not a download stays bounded.
#
# .deb cache: when APT_ARCHIVE_CACHE_DIR is set, its .deb files are copied into
# the archive directory before attempt 1; apt checks each one against the
# package index and downloads anything stale or absent. After an install that
# exits 0, obsolete files are autocleaned, the directory is refreshed from the
# archive, and `cache-ready=true` is written to GITHUB_OUTPUT so the action
# saves it.
# ================================================================

set -uo pipefail
shopt -s nullglob

if [[ $# -eq 0 ]]; then
    echo "usage: $0 PACKAGE..." >&2
    exit 2
fi

ATTEMPTS="${APT_INSTALL_ATTEMPTS:-2}"
ATTEMPT_TIMEOUT="${APT_ATTEMPT_TIMEOUT:-120}"
FINAL_NETWORK_TIMEOUT="${APT_FINAL_NETWORK_TIMEOUT:-2700}"
DPKG_TIMEOUT="${APT_DPKG_TIMEOUT:-300}"
RETRY_DELAY="${APT_RETRY_DELAY:-10}"
PRIMARY_MIRROR_HOST="${APT_PRIMARY_MIRROR_HOST:-azure.archive.ubuntu.com}"
FALLBACK_MIRROR_HOST="${APT_FALLBACK_MIRROR_HOST:-archive.ubuntu.com}"
APT_DIR="${APT_CONFIG_DIR:-/etc/apt}"
ARCHIVES_DIR="${APT_ARCHIVES_DIR:-/var/cache/apt/archives}"
CACHE_DIR="${APT_ARCHIVE_CACHE_DIR:-}"
APT_OPTIONS=(
    -o Acquire::Retries=3
    -o Acquire::http::Timeout=30
    -o Acquire::https::Timeout=30
    -o APT::Keep-Downloaded-Packages=true
)

# run_apt CAP ARGS...: apt-get with the shared options, stopped after CAP
# seconds (and killed 30 seconds later if it ignores the stop signal).
run_apt() {
    local cap=$1
    shift
    sudo timeout --kill-after=30 "${cap}" apt-get "${APT_OPTIONS[@]}" "$@"
}

# Seconds left before NETWORK_DEADLINE, at least 1 so an exhausted budget
# still runs (and stops) the command rather than skipping it silently.
network_budget_left() {
    local left=$(( NETWORK_DEADLINE - SECONDS ))
    if (( left < 1 )); then
        left=1
    fi
    echo "${left}"
}

seed_archive_cache() {
    [[ -n "${CACHE_DIR}" ]] || return 0
    local debs=( "${CACHE_DIR}"/*.deb )
    if (( ${#debs[@]} == 0 )); then
        echo "apt archive cache: no cached .deb files; everything is downloaded"
        return 0
    fi
    if sudo cp "${debs[@]}" "${ARCHIVES_DIR}/"; then
        echo "apt archive cache: seeded ${#debs[@]} .deb files into ${ARCHIVES_DIR}"
    else
        echo "warning: could not seed ${ARCHIVES_DIR} from ${CACHE_DIR}; packages are downloaded instead" >&2
    fi
}

refresh_archive_cache() {
    [[ -n "${CACHE_DIR}" ]] || return 0
    if ! run_apt "${DPKG_TIMEOUT}" autoclean; then
        echo "warning: apt-get autoclean did not complete; the cache may keep obsolete .deb files" >&2
    fi
    local debs=( "${ARCHIVES_DIR}"/*.deb )
    if (( ${#debs[@]} == 0 )); then
        echo "apt archive cache: no .deb files in ${ARCHIVES_DIR}; nothing to cache"
        return 0
    fi
    local stale=()
    if mkdir -p "${CACHE_DIR}"; then
        stale=( "${CACHE_DIR}"/*.deb )
    else
        echo "warning: could not create ${CACHE_DIR}; the .deb cache is not saved" >&2
        return 0
    fi
    if (( ${#stale[@]} > 0 )) && ! rm -f "${stale[@]}"; then
        echo "warning: could not clear ${CACHE_DIR}; the .deb cache is not saved" >&2
        return 0
    fi
    if ! cp "${debs[@]}" "${CACHE_DIR}/"; then
        echo "warning: could not copy .deb files to ${CACHE_DIR}; the .deb cache is not saved" >&2
        return 0
    fi
    echo "apt archive cache: staged ${#debs[@]} .deb files in ${CACHE_DIR}"
    if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
        echo "cache-ready=true" >> "${GITHUB_OUTPUT}"
    fi
}

# Replace the primary mirror host in the runner's mirror list (mirror+file:
# sources) and in any sources file that names it directly.
switch_to_fallback_mirror() {
    local escaped file tmp switched=0
    escaped="$(printf '%s' "${PRIMARY_MIRROR_HOST}" | sed 's/[.]/\\./g')"
    for file in "${APT_DIR}/apt-mirrors.txt" "${APT_DIR}/sources.list" \
        "${APT_DIR}"/sources.list.d/*.list "${APT_DIR}"/sources.list.d/*.sources; do
        if [[ ! -f "${file}" ]] || ! grep -qF "//${PRIMARY_MIRROR_HOST}/" "${file}"; then
            continue
        fi
        if ! tmp="$(mktemp "${TMPDIR:-/tmp}/ci-apt-sources.XXXXXX")"; then
            echo "warning: could not create a temporary file to rewrite ${file}" >&2
            continue
        fi
        if sed "s#//${escaped}/#//${FALLBACK_MIRROR_HOST}/#g" "${file}" > "${tmp}" \
            && sudo cp "${tmp}" "${file}"; then
            echo "apt sources: ${file} now uses ${FALLBACK_MIRROR_HOST} instead of ${PRIMARY_MIRROR_HOST}"
            switched=1
        else
            echo "warning: could not rewrite ${file} to ${FALLBACK_MIRROR_HOST}" >&2
        fi
        rm -f "${tmp}"
    done
    if (( switched == 0 )); then
        echo "warning: no apt source names ${PRIMARY_MIRROR_HOST}; retrying with the current sources" >&2
    fi
}

seed_archive_cache

# Wall-clock cap for the next network phase: ATTEMPT_TIMEOUT per command
# before the final attempt, then whatever is left of the final budget.
network_cap() {
    if (( final )); then
        network_budget_left
    else
        echo "${ATTEMPT_TIMEOUT}"
    fi
}

mirror_switched=0
for (( attempt = 1; attempt <= ATTEMPTS; attempt++ )); do
    final=0
    if (( attempt == ATTEMPTS )); then
        final=1
        echo "apt install attempt ${attempt}/${ATTEMPTS}: $* (final: downloads stop on a 30 s stall" \
            "or after ${FINAL_NETWORK_TIMEOUT} s in total)"
    else
        echo "apt install attempt ${attempt}/${ATTEMPTS}: $* (downloads stop after ${ATTEMPT_TIMEOUT} s)"
    fi
    if (( attempt > 1 )); then
        # A stopped install can leave dpkg mid-configure; repair it, bounded.
        # A failure here is reported, and any real problem then surfaces from
        # apt-get below.
        if ! sudo timeout --kill-after=30 "${DPKG_TIMEOUT}" dpkg --configure -a; then
            echo "warning: dpkg --configure -a did not complete before attempt ${attempt}" >&2
        fi
        if (( mirror_switched == 0 )); then
            switch_to_fallback_mirror
            mirror_switched=1
        fi
    fi
    # The final budget starts after the repair and the mirror switch.
    NETWORK_DEADLINE=$(( SECONDS + FINAL_NETWORK_TIMEOUT ))
    if run_apt "$(network_cap)" update \
        && run_apt "$(network_cap)" install -y --no-install-recommends --download-only "$@" \
        && run_apt "${DPKG_TIMEOUT}" install -y --no-install-recommends "$@"; then
        echo "apt install succeeded on attempt ${attempt}"
        refresh_archive_cache
        exit 0
    else
        status=$?
    fi
    # timeout(1) exits 124 when it had to stop an apt-get command.
    echo "apt install attempt ${attempt} failed or stalled (exit ${status})" >&2
    if (( attempt < ATTEMPTS )); then
        sleep "${RETRY_DELAY}"
    fi
done

echo "apt install failed after ${ATTEMPTS} attempts" >&2
exit 1
