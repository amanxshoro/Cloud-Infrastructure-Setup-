# Cloud Infrastructure Setup for Web Application: Manual

**Student:** ____________  **Course:** ____________  **Date:** ____________

## 1. System overview

Cloud Notes is a small web application where visitors post short notes. Notes are saved in a MySQL database. The page shows which cloud the server runs on (detected from the instance metadata service).

| Layer | Technology |
|---|---|
| Web server | nginx (reverse proxy, port 80) |
| Application | Python 3 / Flask served by gunicorn (port 5000, localhost only) |
| Database | MySQL 8 (port 3306, localhost only) |
| OS | Ubuntu Server 24.04 LTS on a Linux VM |

**Request flow:** Browser -> nginx :80 -> gunicorn/Flask :5000 -> MySQL :3306 -> response.

The database is not exposed to the internet; only the application on the same VM connects to it.

## 2. Cloud accounts

| Platform | Account email | Console URL | Region used |
|---|---|---|---|
| AWS | | https://console.aws.amazon.com | |
| GCP | | https://console.cloud.google.com | |
| Azure | | https://portal.azure.com | |

## 3. Deployment (platform used for the live website: ____________)

### 3.1 AWS (EC2)
1. EC2 -> Launch instance -> Ubuntu Server 24.04 LTS, `t3.micro`/`t2.micro` (free tier).
2. Create a key pair (.pem). Allow SSH (22) and HTTP (80).
3. Launch and note the **Public IPv4 address**.

### 3.2 GCP (Compute Engine)
1. Compute Engine -> Create instance -> `e2-micro`, Ubuntu 24.04 LTS.
2. Tick **Allow HTTP traffic**. Note the **External IP**.

### 3.3 Azure (Virtual Machine)
1. Virtual machines -> Create -> Ubuntu Server 24.04 LTS, size `B1s`.
2. Inbound ports: SSH (22) and HTTP (80). Note the **Public IP address**.

## 4. Installing the application

```bash
ssh <user>@<public-ip>
sudo apt-get update && sudo apt-get install -y git
git clone <YOUR_REPO_URL> cloudnotes
cd cloudnotes
sudo DB_PASS='ChooseAStrongPassword' bash setup.sh
curl http://localhost/health      # expect {"status":"ok","database":"connected",...}
```

`setup.sh` installs nginx and MySQL, creates database `cloudnotes` and user `cloudnotes`, installs the app in `/opt/cloudnotes` with a Python virtualenv, registers a systemd service `cloudnotes`, and configures nginx as a reverse proxy.

## 5. Database

- Engine: MySQL, database `cloudnotes`, user `cloudnotes` (access from localhost only).
- Table `notes`: `id` (INT auto-increment PK), `author` (VARCHAR 80), `message` (TEXT), `created_at` (TIMESTAMP).
- Integration: the Flask app connects using PyMySQL with credentials passed as environment variables in `/etc/systemd/system/cloudnotes.service`.
- Inspect data: `sudo mysql -e "SELECT * FROM cloudnotes.notes;"`

## 6. Access details

| Item | Value |
|---|---|
| Website URL | http://<public-ip> |
| Health check | http://<public-ip>/health |
| SSH user | |
| SSH key / password | |
| DB name / user / password | cloudnotes / cloudnotes / ______ |

## 7. Operations

- Status: `sudo systemctl status cloudnotes nginx mysql`
- App logs: `sudo journalctl -u cloudnotes -f`
- Restart app: `sudo systemctl restart cloudnotes`

## 8. Testing evidence

Add screenshots: (1) cloud console showing the running VM, (2) the website in a browser, (3) a posted note, (4) MySQL output showing the stored row.

## 9. Cleanup / cost control

Stop or delete the VMs after grading and set a billing budget alert on every account.
