# Change a service with Ansible

> Tutorial · [Documentation](../../README.md#documentation)

In this tutorial you change a setting of one of the shared services the way
every change to them is made: in the inventory, previewed with check mode,
applied with the service's playbook, and confirmed by a second run that
changes nothing. The setting is harmless and visible: the name Forgejo shows
in its title bar. At the end you put it back.

You need: a shell on the hypervisor host as root, and this repository in
`/root/lab/infra`. Applying restarts Forgejo for a few seconds: Git pushes
and Argo CD's polls fail meanwhile and are retried. Host names use the example
domain `example.org`: replace it with the site's (`site_domain` in
`ansible/inventory/group_vars/all.yml`).

## 1. Prepare

```sh
export PATH=~/.venvs/ansible/bin:$PATH
cd /root/lab/infra/ansible
git status --short
```

You should see nothing from `git status`: the inventory is as committed. Look
at the current name:

```sh
grep forgejo_app_name inventory/group_vars/forgejo.yml
```

You should see `forgejo_app_name: Forgejo (test)`, the name in Forgejo's
browser tab.

## 2. Change the setting

Edit `inventory/group_vars/forgejo.yml` and set:

```yaml
forgejo_app_name: Forgejo (tutorial)
```

`group_vars/forgejo.yml` holds the settings of the `forgejo` group; the role
`forgejo` turns them into the service's configuration.

## 3. Preview it

```sh
ansible-playbook forgejo.yml --check --diff
```

Check mode connects to the VM and compares, changing nothing. It takes a
minute or two. You should see, among many `ok` tasks:

```
TASK [forgejo : app.ini] ****
changed: [forgejo.example.org]
...
RUNNING HANDLER [forgejo : Restart forgejo] ****
changed: [forgejo.example.org]
```

and a recap with `changed=2` for the Forgejo host. The configuration file
would change and Forgejo would restart. The file's content isn't shown: the
role hides diffs of `app.ini`, which can hold secrets.

Check mode has a limit worth knowing: tasks that call a service's API (a
Keycloak group, a Forgejo user) are skipped in it, so they never appear as
changes in a preview.

## 4. Apply it

```sh
ansible-playbook forgejo.yml
```

The recap shows `changed=2` again, this time for real. Then:

```sh
curl -s --cacert /root/lab/infra/pki/root_ca.crt https://forgejo.example.org/ | grep -o '<title>[^<]*</title>'
```

You should see `<title>Forgejo (tutorial)</title>`.

## 5. Run it again

```sh
ansible-playbook forgejo.yml
```

You should see `changed=0` for every host. A playbook brings a VM to the
state the inventory describes; when it is there already, a run changes
nothing. That second run is the check that a change is complete.

## 6. Put it back

```sh
git checkout inventory/group_vars/forgejo.yml
ansible-playbook forgejo.yml
```

Forgejo restarts once more, and the title is `Forgejo (test)` again. A change
meant to stay is committed and pushed instead: the inventory in Git is the
description of the site.

## What you did

You changed a service through its inventory, saw the change before making
it, applied it, and proved the result with a run that changed nothing.
Unlike Crossplane on the cluster, Ansible doesn't watch: an edit made on a VM
by hand stays until the next run of its playbook puts the inventory's value
back.

## Next steps

- Everyday versions: [Run the playbooks](../how-to/run-the-playbooks.md),
  [Upgrade the services](../how-to/upgrade-the-services.md).
- What each playbook does: [Playbooks](../reference/playbooks.md).
- Who manages what, Ansible or Crossplane: [Ansible and Crossplane](../explanation/ansible-and-crossplane.md).
