# Pipelines on the cluster

> Explanation · [Documentation](../../README.md#documentation)

Why CI is Pipelines-as-Code on the cluster, and the choices behind its
security. The pieces: [CI](../reference/ci.md).

## Pipelines next to the code, runs on the cluster

Each repository keeps its pipelines in `.tekton/`. Forgejo calls
Pipelines-as-Code's webhook on a push or pull request; PaC runs the matching
PipelineRuns in the repository's namespace on cluster `lab` and reports back
as a commit status. No separate CI server, no runners to maintain: the cluster
is the runner, and the platform's guardrails (namespaces, quotas, Pod
Security) apply to CI like to everything else.

## An HTTPS webhook

The webhook goes to `https://pac.apps.lab.example.org`, on a gateway listener
of its own with a step-ca certificate, which Forgejo verifies against the
site CA. Each delivery is also signed with the repository's webhook secret,
and PaC rejects unsigned or wrongly signed ones. The signature alone would
keep deliveries from being forged, but over plain HTTP anyone on the LAN
could read them (commit metadata, pull request contents); HTTPS costs one
more host name in the cluster file. Forgejo refuses webhooks to private
addresses unless allowed, hence `ALLOWED_HOST_LIST`.

## The gate can't be changed by what it gates

The merge checks of the GitOps repository run their PipelineRun **from
`main`**, never from the pull request (`pipelinerun_provenance:
default_branch`): a pull request can't change the check that gates it, nor
read its token. The render-only Argo CD it uses has no controller, so nothing
it renders can sync, and its ksops is a stand-in, so nothing is decrypted.

## Tokens only where they belong

PaC sends tokens to `forgejo.example.org` only (`trusted-provider-hostnames`),
and copies the account's token into a short-lived Secret for each run. Teams'
pipelines run as their own Forgejo user, whose token reaches only their
repositories; the platform's run as `pac-bot`.

## Building images without privileges

Talos disables user namespaces (`user.max_user_namespaces=0`), which buildah
and BuildKit need, and the CI namespaces' Pod Security (`baseline`) refuses
privileged pods, rightly for code from pull requests. kaniko builds without
either: it runs `RUN` steps inside its own container, as root there but
without mounts or user namespaces.

## Scanning twice

The pipeline scans before pushing and fails on HIGH or CRITICAL
vulnerabilities that have a fix: a vulnerable image never reaches the
registry, and a pull request can't introduce one. Unfixed vulnerabilities
don't fail the run, since nothing can be done about them yet; Harbor scans
every pushed image again and lists them, so they stay visible. Images use
their base through the registry's mirror, and drop what they don't need at
runtime (pip and its wheels, for one), which is also what keeps scans clean.
