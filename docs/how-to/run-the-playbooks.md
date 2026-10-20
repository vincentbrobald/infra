# Run the playbooks

> How-to · [Documentation](../../README.md#documentation)

Bring the VMs in line with the inventory, or deploy one service. What each
playbook does: [Playbooks](../reference/playbooks.md).

1. Use the Ansible venv (ansible-core 2.21):

   ```sh
   export PATH=~/.venvs/ansible/bin:$PATH
   cd /root/lab/infra/ansible
   ```

   Without the venv: `python3 -m venv ~/.venvs/ansible; ~/.venvs/ansible/bin/pip install 'ansible-core>=2.21,<2.22'`.
2. See what would change:

   ```sh
   ansible-playbook site.yml --check --diff
   ```

3. Apply, everything or one service:

   ```sh
   ansible-playbook site.yml           # all, in dependency order
   ansible-playbook registry.yml       # one service (and its VM if missing)
   ansible-playbook site.yml --tags vm # only create missing VMs
   ```

4. Check: a second run reports no change (`changed=0` for every host).

## Change a setting

Edit `ansible/inventory/group_vars/<service>.yml` (or `all.yml` for site
values), run the service's playbook with `--check --diff` first, then without.
Credentials are never written there: put the value in its file under
`/root/lab/lab-secrets` ([Secrets tree](../reference/secrets.md)).

## Grow a VM's disk

Raise `vm.disk` for the host in `ansible/inventory/hosts.yml` and run its
playbook: the disk, partition and file system grow while it runs. A smaller
value is reported, never applied.

## Add a VM for a new service

Add the host to `hosts.yml` with its `vm:` settings (name, memory, vCPUs,
disk; `network: static` and `address` for a fixed address outside the DHCP
pool .100-.199), a group and its `group_vars`, a role and a playbook importing
`gitops.yml` if it needs credentials from Git; add the playbook to `site.yml`.
