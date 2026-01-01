# Heimdall Setup Instructions

## System Info
- **Hostname**: heimdall (192.168.1.176)
- **CPU**: Intel Core i5-4278U @ 2.60GHz (4 cores)
- **RAM**: 7.6 GB
- **Disk**: 220 GB (99% free)
- **OS**: Debian 13 (Trixie)

## Issue
**`sudo` is not installed** - Cannot install packages without root access

## Missing Tools
- sudo
- curl  
- git
- gcc/make (build-essential)

## Fix Required
Need root access to install sudo. Choose one:

### Option A: SSH as root
```bash
ssh root@192.168.1.176
apt update && apt install -y sudo curl git build-essential
usermod -aG sudo rod
echo "rod ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/rod
chmod 0440 /etc/sudoers.d/rod
```

### Option B: Use su
```bash
ssh rod@192.168.1.176
su -
# Enter root password, then run same apt commands as Option A
```
