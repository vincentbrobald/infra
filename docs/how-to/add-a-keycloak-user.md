# Add a Keycloak user

> How-to · [Documentation](../../README.md#documentation)

Give a person an account for the clusters and the site's services. Groups and
what they grant: [oauth](../reference/vms/oauth.md#realm-example).

1. Log in to `https://oauth.example.org/admin/` as `admin` (password in
   `/root/lab/lab-secrets/oauth/keycloak-admin-password`), realm **example**.
2. Users > Add user: a username (it is also their Forgejo name), e-mail
   verified. Credentials > Set password, not temporary.
3. Groups, as needed:

   | Group | Grants |
   |---|---|
   | `k8s-admins` | cluster-admin on the clusters; the platform Tekton Dashboard |
   | `argocd-admins` | Argo CD admin |
   | `registry-admins` | Harbor and Artifact Keeper admin |
   | `grafana-admins` | Grafana admin |

   Membership of a team (`team-<team>`) is not set here: add the user to
   `members` in the team's `team.yaml` in gitops, or Crossplane removes them.
4. Check: the user logs in with `KUBECONFIG=/root/lab/lab-cluster/kubeconfig-oidc kubectl get nodes`
   (with `k8s-admins`), or at `https://argocd.apps.lab.example.org`.

A user's Forgejo account is created at their first login to Forgejo through
Keycloak; Omni only admits users added in Omni (Settings > Users).
