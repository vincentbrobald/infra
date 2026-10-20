# CI

> Reference · [Documentation](../../README.md#documentation)

The CI's pieces as they stand on the site. How its repositories, pipelines
and teams are configured is the gitops repository's ([Platform CI repositories](https://github.com/vincentbrobald/gitops/blob/main/docs/reference/ci-repository.md),
[CI runs](https://github.com/vincentbrobald/gitops/blob/main/docs/reference/ci-runs.md), [Build with CI](https://github.com/vincentbrobald/gitops/blob/main/docs/how-to/build-with-ci.md)). Why it is built
this way: [Pipelines on the cluster](../explanation/ci.md).

```
Forgejo ──webhook (HTTPS, HMAC-signed)──> https://pac.apps.lab.example.org ──> PaC controller
   ^                                          (ingress gateway .204)        │ PipelineRun
   └──── commit status, clone (HTTPS, token) ───────────────────────────────┘ in <repo namespace>
```

| Piece | Value |
|---|---|
| Tekton Pipelines | v1.17.0, namespace `tekton-pipelines` (gitops `base/tekton/pipelines`) |
| Pipelines-as-Code | v0.52.0, namespace `pipelines-as-code` (gitops `base/tekton/pipelines-as-code`; Forgejo support is a technology preview) |
| Webhook URL | `https://pac.apps.lab.example.org` (HTTPRoute on the gateway's listener `https-pac`, certificate from the cluster file's `certManager.extraHosts`); health `curl -s https://pac.apps.lab.example.org/live` |
| Token scope | `trusted-provider-hostnames: forgejo.example.org`: the only host PaC sends tokens to |
| Forgejo setting | `[webhook] ALLOWED_HOST_LIST = pac.apps.lab.example.org` |
| Dashboard | Tekton Dashboard v0.73.0 (read-only), `https://tekton.apps.lab.example.org`, behind oauth2-proxy (client `tekton-lab`, group `k8s-admins`); teams have their own |
| Platform account | `pac-bot` (write collaborator; token `pipelines-as-code`: `write:repository`, `write:issue`, `read:user`) |
| Teams' accounts | `ci-<team>`, made by Crossplane |

## Platform repositories served

| Repository | Namespace | Runs |
|---|---|---|
| `alice/gitops` | `gitops-ci` | the merge checks (`pipelinerun_provenance: default_branch`) |
| `alice/gitops-scanner` | `gitops-scanner` | build of the merge checks' image |
| `alice/provider-forgejo`, `alice/provider-artifact-keeper` | same names | provider package builds |
| `alice/pac-demo` | `pac-demo` | the demo: lint and test |

## Merge-check credentials (namespace `gitops-ci`, SOPS in gitops)

| Secret | Holds |
|---|---|
| `forgejo-pac` | pac-bot's token, the webhook secret |
| `argocd-preview` | the render-only Argo CD's URL and a token of its account `ci` (create, read, delete Applications; generate ApplicationSets) |

## Images

| Item | Value |
|---|---|
| Builder | kaniko (`ghcr.io/osscontainertools/kaniko`; `-debug` image for the shell) |
| Scan in the pipeline | Trivy (`ghcr.io/aquasecurity/trivy`, pinned): fails on fixable HIGH or CRITICAL (`--ignore-unfixed`); database through the registry's `ghcr.io` mirror |
| Scan in the registry | Harbor scans every push (Trivy), unfixed CVEs listed too |
| Push credentials | Secret `registry-push` in the repository's namespace: `registry`, `username`, `password` (the Harbor robot) |
