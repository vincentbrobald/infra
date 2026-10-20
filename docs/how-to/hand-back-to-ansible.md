# Hand an object back to Ansible

> How-to · [Documentation](../../README.md#documentation)

Stop Crossplane managing objects it took over from Ansible, and let the
playbooks manage them again. Why the split exists:
[Ansible and Crossplane](../explanation/ansible-and-crossplane.md). Crossplane
never deletes these objects, so handing back loses nothing.

## Only stop Crossplane changing it

Set the objects' `managementPolicies` to `[Observe]` in gitops and merge:
Crossplane keeps reporting them but changes nothing.

## Keycloak client `tekton-lab`

Undo points: tag `pre-crossplane-tekton-lab` in gitops and in this
repository; branches `undo/crossplane-tekton-lab` in both hold the undo (rebase
them on `main` if it moved). Backup: `lab-secrets/oauth/backups/tekton-lab-20261015.json`.

1. **gitops** first (stops Crossplane): a pull request from
   `undo/crossplane-tekton-lab`, or by hand
   `git checkout pre-crossplane-tekton-lab -- clusters/lab/tekton/dashboard`.
   It puts the Client back to Observe, drops the mapper resource (it stays in
   Keycloak) and points oauth2-proxy at the SOPS Secret again (same client
   secret). After the sync: `kubectl -n tekton-dashboard delete secret tekton-lab-oidc`.
2. **infra**: merge `undo/crossplane-tekton-lab` (or `git checkout
   pre-crossplane-tekton-lab -- ansible/inventory/group_vars/keycloak.yml`),
   then `ansible-playbook keycloak.yml`: Ansible manages the client again,
   with its secret from the gitops Secret.
3. Check: the Tekton Dashboard's login still works.

## Keycloak clients `headlamp-lab`, `grafana-lab`, group `grafana-admins`

These go back to deploy-talos.py, not Ansible:

1. Set `oidc.crossplane.enabled: false` in `/root/lab/lab.yaml`.
2. `deploy-talos.py argocd -f /root/lab/lab.yaml`: the objects leave Git, Argo
   CD prunes them, Keycloak keeps the clients, and the script manages them
   through the API again, with the same secrets from Git.
3. Check: Headlamp's and Grafana's Keycloak logins work.

Backup: `lab-secrets/oauth/backups/headlamp-grafana-lab-20261016.json`.

## Forgejo repository settings (`pac-demo`, `gitops-scanner`)

Undo points: tag `pre-crossplane-forgejo` in gitops and here; branches
`undo/crossplane-forgejo` in both. State before, without secrets:
`lab-secrets/forgejo/backups/repos-20261015.json`.

1. **gitops**: a pull request from `undo/crossplane-forgejo`: it removes the
   `forgejo:` sections of `clusters/lab/ci/<repo>/repository.yaml` and the
   `forgejo-webhook` Secrets; everything stays in Forgejo.
2. **infra**: merge `undo/crossplane-forgejo` (the inventory as at the tag),
   then `ansible-playbook forgejo.yml`. Its records of the webhook secrets
   (`/etc/forgejo/webhooks/`) still match, so it keeps the hooks.
3. Check: a push to the repository still gets a CI status.

## If an object is gone or damaged in Keycloak

Recreate it from its backup, with the same ID and secret (admin token as in
`roles/keycloak_realm/tasks/token.yml`; delete the damaged one first):

```sh
jq '.[0] | del(.access)' <backup> \
  | curl --cacert /root/lab/infra/pki/root_ca.crt -H "Authorization: Bearer $TOKEN" \
      -H 'Content-Type: application/json' -d @- https://oauth.example.org/admin/realms/example/clients
```
