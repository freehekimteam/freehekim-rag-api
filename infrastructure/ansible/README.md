# Ansible Configuration Management

Ansible playbooks for configuring and managing FreeHekim RAG API servers.

## Prerequisites

- [Ansible](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html) >= 2.15
- SSH access to target servers
- Python 3 on target servers

## Installation

```bash
# macOS
brew install ansible

# Ubuntu/Debian
sudo apt update
sudo apt install ansible

# pip
pip install ansible
```

## Setup

### 1. Configure Inventory

Edit `inventory.yml` with your server details:

```yaml
production:
  hosts:
    freehekim-rag-prod:
      ansible_host: YOUR_SERVER_IP
      ansible_user: freehekim
```

### 2. Test Connection

```bash
ansible all -i inventory.yml -m ping
```

### 3. Run Playbook

```bash
# Dry run (check mode)
ansible-playbook -i inventory.yml playbook.yml --check

# Execute
ansible-playbook -i inventory.yml playbook.yml

# Execute on specific host
ansible-playbook -i inventory.yml playbook.yml --limit production

# With verbose output
ansible-playbook -i inventory.yml playbook.yml -vvv
```

## What It Does

The playbook configures:

- ✅ System updates & security patches
- ✅ Docker & Docker Compose installation
- ✅ UFW firewall configuration
- ✅ fail2ban for SSH protection
- ✅ Application directories
- ✅ Environment files
- ✅ Monitoring setup (Prometheus/Grafana)
- ✅ Automated backups
- ✅ Cloudflare Tunnel
- ✅ System tuning (limits, sysctl)

## Directory Structure

```
ansible/
├── playbook.yml           # Main playbook
├── inventory.yml          # Server inventory
├── templates/             # Template files
│   ├── env.j2            # Environment variables
│   └── backup.sh.j2      # Backup script
├── roles/                # Ansible roles (optional)
└── README.md             # This file
```

## Common Tasks

### Update Application

```bash
ansible-playbook -i inventory.yml playbook.yml --tags update
```

### Restart Services

```bash
ansible production -i inventory.yml -a "systemctl restart docker"
```

### Check Server Status

```bash
ansible production -i inventory.yml -m setup
```

### Run Backup

```bash
ansible production -i inventory.yml -a "/usr/local/bin/backup-freehekim-rag"
```

## Tags

Run specific parts of the playbook:

```bash
# Only security tasks
ansible-playbook -i inventory.yml playbook.yml --tags security

# Only Docker installation
ansible-playbook -i inventory.yml playbook.yml --tags docker

# Skip backup setup
ansible-playbook -i inventory.yml playbook.yml --skip-tags backup
```

## Variables

Key variables (can be overridden):

```yaml
app_user: freehekim
app_dir: /home/freehekim/apps/freehekim-rag-api
docker_compose_version: "2.24.0"
```

## Security Best Practices

- ✅ Use SSH keys, not passwords
- ✅ Restrict SSH to specific IPs
- ✅ Enable UFW firewall
- ✅ Setup fail2ban
- ✅ Regular security updates
- ✅ Use secrets management (Ansible Vault)

## Ansible Vault

For sensitive data:

```bash
# Create encrypted file
ansible-vault create secrets.yml

# Edit encrypted file
ansible-vault edit secrets.yml

# Run playbook with vault
ansible-playbook -i inventory.yml playbook.yml --ask-vault-pass
```

## Troubleshooting

### Connection Issues

```bash
# Test SSH connection
ssh freehekim@YOUR_SERVER_IP

# Test with ansible
ansible all -i inventory.yml -m ping -vvv
```

### Permission Denied

```bash
# Check SSH key
ssh-add -l

# Add key if needed
ssh-add ~/.ssh/id_rsa
```

### Python Not Found

```bash
# Install Python on target
ssh freehekim@YOUR_SERVER_IP
sudo apt install python3
```

## Next Steps

1. Setup templates (env.j2, backup.sh.j2)
2. Configure Ansible Vault for secrets
3. Create custom roles for complex tasks
4. Integrate with CI/CD pipeline
