# CI

Tekton Pipelines-as-Code on cluster `lab` runs the pipelines of the Forgejo
repositories. It is deployed from the GitOps repository, so its configuration
and documentation live there; this repository only holds Forgejo's side.

| What | Where |
|---|---|
| the pieces, versions, accounts | [docs/reference/ci.md](../docs/reference/ci.md) |
| why it is built this way | [Pipelines on the cluster](../docs/explanation/ci.md) |
| when a run fails | [docs/how-to/troubleshoot.md](../docs/how-to/troubleshoot.md#ci) |
| a platform repository's CI | gitops: [Add a platform CI repository](https://github.com/vincentbrobald/gitops/blob/main/docs/how-to/add-a-platform-ci-repository.md) |
| a team's pipelines | gitops: [Build with CI](https://github.com/vincentbrobald/gitops/blob/main/docs/how-to/build-with-ci.md), [CI runs](https://github.com/vincentbrobald/gitops/blob/main/docs/reference/ci-runs.md) |
| Forgejo's side: `pac-bot`, webhooks, `ALLOWED_HOST_LIST` | [docs/reference/vms/forgejo.md](../docs/reference/vms/forgejo.md) |
