"""Root credential stores shared by file and subprocess path policies.

These absolute paths preserve the existing /root policy. Each caller adds its
own system paths and applies its own containment, alias, and prefix checks.
"""

ROOT_CREDENTIAL_STORES: frozenset[str] = frozenset({
    '/root/.ssh',
    '/root/.aws',
    '/root/.netrc',
    '/root/.kube',
    '/root/.docker',
    '/root/.git-credentials',
    '/root/.pgpass',
    '/root/.gnupg',
    '/root/.vault-token',
    '/root/.config/gh',
    '/root/.npmrc',
    '/root/.config/gcloud',
})
