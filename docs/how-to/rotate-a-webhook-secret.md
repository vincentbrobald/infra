# Rotate a webhook secret

> How-to · [Documentation](../../README.md#documentation)

Replace the secret a repository's webhook to Pipelines-as-Code is signed with.
Forgejo never shows a webhook's secret and ignores a new one on edit, so the
hook is re-created.

## A repository whose webhook Crossplane manages

(`pac-demo`, `gitops-scanner`, `provider-artifact-keeper`, and the teams'
repositories.)

1. Change the secret in both gitops Secrets of the repository's namespace:
   `forgejo-pac` (key `webhook.secret`) and `forgejo-webhook` (key `secret`),
   with `sops edit`. For a team, delete `ci-webhook.enc.yaml` and
   `ci-webhook-pac.enc.yaml` (and `ci-bot.enc.yaml`) and run
   `tools/teams.py generate` instead.
2. Merge, and wait for the sync.
3. Delete the hook in Forgejo (repository Settings > Webhooks): Crossplane
   finds it gone and creates it with the new secret.
4. Check: Recent deliveries of the new hook answer 2xx after a push.

## A repository whose webhook Ansible manages

(`gitops`, `provider-forgejo`.)

1. Write the new secret to `/root/lab/lab-secrets/forgejo/<repo>-webhook-secret`
   and to the repository's gitops Secret `forgejo-pac` (`webhook.secret`); the
   playbook takes the secret from Git first.
2. Merge the gitops change, then `ansible-playbook forgejo.yml`: the role sees
   the secret changed (its record in `/etc/forgejo/webhooks/`) and re-creates
   the hook.
3. Check as above.
