# Cloudflare Tunnel Setup

Cloudflare Tunnel (formerly Argo Tunnel) configuration for FreeHekim RAG API.

## What is Cloudflare Tunnel?

Cloudflare Tunnel creates a secure, outbound-only connection between your origin server and Cloudflare, without opening inbound firewall ports.

**Benefits:**
- ✅ No public IP exposure
- ✅ DDoS protection
- ✅ Automatic HTTPS
- ✅ Zero Trust access control
- ✅ No VPN needed

## Prerequisites

- Cloudflare account
- Domain managed by Cloudflare (hakancloud.com)
- cloudflared installed on server
- Server with API running

## Installation

### 1. Install cloudflared

```bash
# Ubuntu/Debian
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# macOS
brew install cloudflared

# Docker
docker pull cloudflare/cloudflared:latest
```

### 2. Authenticate

```bash
cloudflared tunnel login
```

This opens a browser to authenticate with Cloudflare.

### 3. Create Tunnel

```bash
cloudflared tunnel create freehekim-rag
```

This creates:
- Tunnel ID
- Credentials file: `~/.cloudflared/<TUNNEL_ID>.json`

**Save the Tunnel ID!** Update `tunnel-config.yml` with it.

### 4. Configure DNS

```bash
# Route domain to tunnel
cloudflared tunnel route dns freehekim-rag rag.hakancloud.com
cloudflared tunnel route dns freehekim-rag metrics.hakancloud.com
cloudflared tunnel route dns freehekim-rag grafana.hakancloud.com
```

Or manually in Cloudflare Dashboard:
- Type: CNAME
- Name: rag
- Target: `<TUNNEL_ID>.cfargotunnel.com`
- Proxy: Yes (orange cloud)

### 5. Copy Configuration

```bash
sudo mkdir -p /etc/cloudflared
sudo cp tunnel-config.yml /etc/cloudflared/config.yml
```

Update the file with your tunnel ID and credentials path.

### 6. Install as Service

```bash
sudo cloudflared service install
sudo systemctl start cloudflared
sudo systemctl enable cloudflared
```

### 7. Verify

```bash
# Check status
sudo systemctl status cloudflared

# Check logs
sudo journalctl -u cloudflared -f

# Test endpoint
curl https://rag.hakancloud.com/health
```

## Configuration

### Basic Setup

```yaml
tunnel: YOUR_TUNNEL_ID
credentials-file: /path/to/credentials.json

ingress:
  - hostname: rag.hakancloud.com
    service: http://localhost:8080
  - service: http_status:404
```

### Multiple Services

```yaml
ingress:
  # API
  - hostname: rag.hakancloud.com
    service: http://localhost:8080

  # Metrics (restrict with Cloudflare Access)
  - hostname: metrics.hakancloud.com
    service: http://localhost:9090

  # Grafana (restrict with Cloudflare Access)
  - hostname: grafana.hakancloud.com
    service: http://localhost:3000

  # Catch-all
  - service: http_status:404
```

### Advanced Options

```yaml
originRequest:
  connectTimeout: 30s        # Connection timeout
  tcpKeepAlive: 30s         # TCP keepalive
  noTLSVerify: false        # Verify TLS certificates
  disableChunkedEncoding: false
  bastionMode: false
  proxyAddress: 127.0.0.1
  proxyPort: 0
  proxyType: ""
  httpHostHeader: ""
```

## Security with Cloudflare Access

Restrict internal endpoints (metrics, grafana):

### 1. Enable Cloudflare Access

Cloudflare Dashboard → Zero Trust → Access

### 2. Create Application

```
Name: FreeHekim Metrics
Domain: metrics.hakancloud.com, grafana.hakancloud.com
Session Duration: 24 hours
```

### 3. Create Policy

```
Rule Name: Team Access
Action: Allow
Include: Emails → your-team@example.com
```

Now metrics/grafana require authentication!

## Commands

```bash
# Start tunnel
cloudflared tunnel run freehekim-rag

# Stop tunnel
sudo systemctl stop cloudflared

# Restart tunnel
sudo systemctl restart cloudflared

# View logs
sudo journalctl -u cloudflared -f

# List tunnels
cloudflared tunnel list

# Delete tunnel
cloudflared tunnel delete freehekim-rag

# Test configuration
cloudflared tunnel --config /etc/cloudflared/config.yml run
```

## Troubleshooting

### Connection Issues

```bash
# Check if API is running
curl http://localhost:8080/health

# Check cloudflared status
sudo systemctl status cloudflared

# Check logs
sudo journalctl -u cloudflared -n 100
```

### DNS Not Resolving

```bash
# Check DNS record
dig rag.hakancloud.com

# Should show CNAME to *.cfargotunnel.com
```

### Certificate Errors

```bash
# Re-authenticate
cloudflared tunnel login

# Check credentials
ls -la ~/.cloudflared/
```

## Monitoring

### Health Check

```bash
# Local
curl http://localhost:8080/health

# Through tunnel
curl https://rag.hakancloud.com/health
```

### Metrics

Cloudflare Dashboard → Analytics → Traffic

- Requests per second
- Bandwidth
- Status codes
- Countries
- Threats blocked

## High Availability

### Multiple Replicas

Run cloudflared on multiple servers:

```bash
# Server 1
cloudflared tunnel run freehekim-rag

# Server 2
cloudflared tunnel run freehekim-rag
```

Cloudflare automatically load balances!

### Automatic Restart

```bash
# Systemd will auto-restart on failure
sudo systemctl enable cloudflared
```

## Best Practices

- ✅ Use systemd for auto-start
- ✅ Enable auto-updates
- ✅ Use Cloudflare Access for internal endpoints
- ✅ Monitor logs regularly
- ✅ Set up health checks
- ✅ Use separate tunnels for prod/staging
- ✅ Keep credentials secure (chmod 600)

## Cost

Cloudflare Tunnel is **FREE** on all Cloudflare plans!

## Documentation

- [Official Docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
- [Configuration Reference](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/configure-tunnels/local-management/configuration-file/)
