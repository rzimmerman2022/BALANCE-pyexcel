# BALANCE-pyexcel Deployment Guide

**Last Updated**: 2025-08-10  
**Version**: 1.0.3  
**Status**: ✅ **Production Ready**

This guide provides step-by-step instructions for deploying BALANCE-pyexcel in production environments.

---

## 🎯 **Deployment Overview**

BALANCE-pyexcel is designed for easy deployment across different environments:
- **Local Development**: Full pipeline on developer machines
- **Server Deployment**: Automated processing on Windows/Linux servers
- **CI/CD Integration**: Automated testing and deployment pipelines

---

## 📋 **Prerequisites**

### **System Requirements**
- **Operating System**: Windows 10/11, macOS 10.15+, or Ubuntu 18.04+
- **Python**: 3.11 or higher (tested up to 3.13)
- **Memory**: Minimum 4GB RAM (8GB recommended for large datasets)
- **Storage**: 2GB free space (more for data processing)

### **Required Software**
- **Python 3.11+**: [python.org](https://python.org)
- **Poetry**: Package manager - `pip install poetry`
- **PowerShell**: For Windows users (pwsh for cross-platform)
- **Git**: For version control

### **Optional Tools**
- **Power BI Desktop**: For viewing generated reports
- **Excel**: For viewing Excel outputs

---

## 🚀 **Quick Deployment (5 Minutes)**

### **1. Clone and Setup**
```bash
# Clone the repository
git clone https://github.com/rzimmerman2022/BALANCE-pyexcel.git
cd BALANCE-pyexcel

# Install dependencies
poetry install --no-root

# Verify installation
poetry run balance-pipe --help
```

### **2. Test the Pipeline**
```powershell
# Windows
.\pipeline.ps1 status

# Linux/macOS
pwsh -c "./pipeline.ps1 status"
```

### **3. Process Sample Data**
```powershell
# Add CSV files to csv_inbox/ directory
# Then process them
.\pipeline.ps1 process
```

**✅ That's it! Your pipeline is deployed and ready.**

---

## 🏗️ **Production Deployment**

### **Environment Setup**

#### **1. Environment Variables (Optional)**
```bash
# Set custom paths if needed
export BALANCE_CSV_INBOX="/path/to/csv/files"
export BALANCE_OUTPUT_DIR="/path/to/outputs"
export BALANCE_SCHEMA_MODE="flexible"  # or "strict"
export BALANCE_LOG_LEVEL="INFO"  # DEBUG, INFO, WARNING, ERROR
```

#### **2. Directory Structure**
```
production-balance/
├── BALANCE-pyexcel/          # Cloned repository
├── data/
│   ├── csv_inbox/           # Input CSV files
│   └── outputs/             # Generated reports
├── config/                  # Custom configurations
└── logs/                    # Application logs
```

### **Configuration Customization**

#### **1. Schema Configuration**
```yaml
# config/custom_balance_analyzer.yaml
schema_mode: "flexible"
log_level: "INFO"
output_formats: ["excel", "powerbi", "csv"]
```

#### **2. Bank Schema Rules**
```yaml
# rules/custom_bank_schema.yaml
name: "CustomBank"
patterns:
  - "custom_bank_*.csv"
  - "*_custom_format.csv"
columns:
  date: ["Transaction Date", "Date"]
  amount: ["Amount", "Transaction Amount"]
```

### **Automated Deployment Script**

#### **Linux/macOS Deployment**
```bash
#!/bin/bash
# deploy_balance.sh

set -e

echo "🚀 Deploying BALANCE-pyexcel..."

# 1. Update repository
git pull origin main

# 2. Update dependencies
poetry install --no-root --only=main

# 3. Run tests
poetry run pytest --quiet

# 4. Verify pipeline
poetry run balance-pipe --help > /dev/null

# 5. Process pending data
if [ -d "csv_inbox" ] && [ "$(ls -A csv_inbox)" ]; then
    echo "📊 Processing pending CSV files..."
    pwsh -c "./pipeline.ps1 process"
fi

echo "✅ BALANCE-pyexcel deployment complete!"
```

#### **Windows Deployment**
```powershell
# deploy_balance.ps1
param([switch]$RunTests)

Write-Host "🚀 Deploying BALANCE-pyexcel..." -ForegroundColor Green

try {
    # 1. Update repository
    git pull origin main

    # 2. Update dependencies  
    poetry install --no-root --only=main

    # 3. Run tests (optional)
    if ($RunTests) {
        Write-Host "🧪 Running tests..." -ForegroundColor Yellow
        poetry run pytest --quiet
    }

    # 4. Verify pipeline
    poetry run balance-pipe --help | Out-Null

    # 5. Process pending data
    if ((Test-Path "csv_inbox") -and @(Get-ChildItem "csv_inbox" -Recurse -File).Count -gt 0) {
        Write-Host "📊 Processing pending CSV files..." -ForegroundColor Yellow
        .\pipeline.ps1 process
    }

    Write-Host "✅ BALANCE-pyexcel deployment complete!" -ForegroundColor Green
}
catch {
    Write-Host "❌ Deployment failed: $_" -ForegroundColor Red
    exit 1
}
```

---

## 🔧 **Server Configuration**

### **Systemd Service (Linux)**
```ini
# /etc/systemd/system/balance-processor.service
[Unit]
Description=BALANCE Financial Data Processor
After=network.target

[Service]
Type=oneshot
User=balance
Group=balance
WorkingDirectory=/opt/balance-pyexcel
Environment=PATH=/opt/balance-pyexcel/.venv/bin
ExecStart=/opt/balance-pyexcel/deploy_balance.sh
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### **Scheduled Processing (Windows)**
```xml
<!-- balance-processor.xml - Windows Task Scheduler -->
<?xml version="1.0"?>
<Task xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>BALANCE Financial Data Processing</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2025-01-01T02:00:00</StartBoundary>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Actions>
    <Exec>
      <Command>PowerShell.exe</Command>
      <Arguments>-ExecutionPolicy Bypass -File "C:\balance-pyexcel\deploy_balance.ps1"</Arguments>
    </Exec>
  </Actions>
</Task>
```

---

## 🔒 **Security Considerations**

### **File Permissions**
```bash
# Set appropriate permissions
chmod 755 pipeline.ps1
chmod 644 config/*.yaml
chmod 600 .env  # if using environment file
```

### **Data Security**
- **Input Data**: Store CSV files in secure directory with restricted access
- **Output Data**: Protect generated reports with appropriate file permissions
- **Logs**: Configure log rotation to prevent disk space issues
- **Credentials**: Never commit sensitive data to version control

### **Network Security**
- **Firewall**: Only open required ports for monitoring/management
- **Access**: Use VPN or secure tunnels for remote access
- **Updates**: Keep Python and dependencies updated regularly

---

## 📊 **Monitoring and Maintenance**

### **Health Checks**
```bash
# Basic health check script
#!/bin/bash
# health_check.sh

# Check if pipeline responds
if poetry run balance-pipe --help > /dev/null 2>&1; then
    echo "✅ Pipeline: Healthy"
else
    echo "❌ Pipeline: Failed"
    exit 1
fi

# Check disk space
USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $USAGE -gt 90 ]; then
    echo "⚠️ Disk: $USAGE% full"
else
    echo "✅ Disk: $USAGE% used"
fi
```

### **Log Management**
```bash
# Log rotation configuration
# /etc/logrotate.d/balance-pyexcel
/var/log/balance-pyexcel/*.log {
    daily
    missingok
    rotate 30
    compress
    notifempty
    copytruncate
}
```

### **Backup Strategy**
```bash
# Backup script
#!/bin/bash
BACKUP_DIR="/backup/balance-$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Backup configuration
cp -r config/ $BACKUP_DIR/
cp -r rules/ $BACKUP_DIR/

# Backup recent outputs (last 30 days)  
find output/ -mtime -30 -type f -exec cp {} $BACKUP_DIR/outputs/ \;

echo "✅ Backup completed: $BACKUP_DIR"
```

---

## 🚨 **Troubleshooting**

### **Common Issues**

#### **"Command not found" errors**
```bash
# Solution: Activate poetry environment
poetry shell
# or use: poetry run <command>
```

#### **Permission denied errors**
```bash
# Solution: Fix file permissions
chmod +x pipeline.ps1
# or run as administrator on Windows
```

#### **Module import errors**
```bash
# Solution: Reinstall dependencies
poetry install --no-root
```

#### **PowerShell execution policy errors**
```powershell
# Solution: Set execution policy
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### **Debug Mode**
```powershell
# Run with maximum debugging
.\pipeline.ps1 process -Debug

# Check detailed logs
poetry run balance-pipe process *.csv --debug
```

### **Performance Issues**
- **Large datasets**: Use `--batch-size` parameter to process in chunks
- **Memory**: Increase available memory or use streaming processing
- **Storage**: Ensure sufficient disk space for temporary files

---

## 📞 **Support and Updates**

### **Getting Help**
- **Documentation**: Check `docs/` directory for detailed guides
- **GitHub Issues**: Report bugs or request features
- **Status Check**: Run `.\pipeline.ps1 status` for health information

### **Updates**
```bash
# Update to latest version
git pull origin main
poetry update
poetry run pytest  # Verify tests pass
```

### **Version Management**
- **Current Version**: 1.0.3
- **Compatibility**: Python 3.11-3.13
- **Update Policy**: Follow semantic versioning

---

## ✅ **Deployment Checklist**

- [ ] **Prerequisites installed**: Python 3.11+, Poetry, PowerShell/pwsh
- [ ] **Repository cloned** and dependencies installed
- [ ] **Configuration customized** for production environment
- [ ] **Test run completed** with sample data
- [ ] **Security measures applied**: permissions, access controls
- [ ] **Monitoring configured**: health checks, logging, backups
- [ ] **Documentation reviewed** and team trained
- [ ] **Production testing** with real data completed
- [ ] **Rollback plan** prepared in case of issues

---

**🎉 Congratulations! BALANCE-pyexcel is successfully deployed and ready for production use.**

For additional help, consult the other documentation files in the `docs/` directory or check the project's GitHub repository.