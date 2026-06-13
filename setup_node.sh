#!/usr/bin/env bash
# ============================================================
#  setup_laptop.sh  —  Run ONCE on each hospital laptop
#  Usage:  sudo bash setup_laptop.sh A   (A=Colombo B=Kandy C=Galle D=Jaffna)
# ============================================================
set -e

NODE_KEY=${1:?"Usage: sudo bash setup_laptop.sh <A|B|C|D>"}

declare -A HOSPITALS
HOSPITALS["A"]="Colombo General Hospital"
HOSPITALS["B"]="Kandy Teaching Hospital"
HOSPITALS["C"]="Galle District Hospital"
HOSPITALS["D"]="Jaffna Teaching Hospital"

echo "========================================================"
echo "  PoCL Laptop Setup — Node ${NODE_KEY}: ${HOSPITALS[$NODE_KEY]}"
echo "========================================================"

# 1. Java
echo "[1/5] Installing Java 17..."
apt-get update -qq
apt-get install -y -qq openjdk-17-jdk curl gnupg

# 2. Jenkins
echo "[2/5] Installing Jenkins..."
curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io-2023.key \
    | tee /usr/share/keyrings/jenkins-keyring.asc > /dev/null
echo "deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] \
    https://pkg.jenkins.io/debian-stable binary/" \
    | tee /etc/apt/sources.list.d/jenkins.list > /dev/null
apt-get update -qq && apt-get install -y -qq jenkins
systemctl enable jenkins && systemctl start jenkins

# 3. Docker
echo "[3/5] Installing Docker..."
apt-get install -y -qq docker.io
systemctl enable docker && systemctl start docker
usermod -aG docker jenkins

# 4. NODE_KEY global env for Jenkins
echo "[4/5] Setting NODE_KEY=${NODE_KEY} for Jenkins..."
JENKINS_INIT_DIR="/var/lib/jenkins/init.groovy.d"
mkdir -p "$JENKINS_INIT_DIR"
cat > "$JENKINS_INIT_DIR/set_node_key.groovy" << GROOVY
import jenkins.model.*
def instance = Jenkins.getInstance()
def globalNodeProperties = instance.getGlobalNodeProperties()
def envClass = hudson.slaves.EnvironmentVariablesNodeProperty
def props = globalNodeProperties.getAll(envClass)
def envProp = props.isEmpty() ? new envClass() : props.get(0)
if (props.isEmpty()) globalNodeProperties.add(envProp)
envProp.getEnvVars().put("NODE_KEY", "${NODE_KEY}")
instance.save()
println "NODE_KEY=${NODE_KEY} configured"
GROOVY

# 5. ngrok
echo "[5/5] Installing ngrok..."
curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc \
    | tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" \
    | tee /etc/apt/sources.list.d/ngrok.list >/dev/null
apt-get update -qq && apt-get install -y -qq ngrok

systemctl restart jenkins

echo ""
echo "========================================================"
echo "  DONE! Node ${NODE_KEY} — ${HOSPITALS[$NODE_KEY]}"
echo ""
echo "  Jenkins:  http://localhost:8080"
echo "  Password: sudo cat /var/lib/jenkins/secrets/initialAdminPassword"
echo ""
echo "  Expose webhook:  ngrok http 8080"
echo "  Docker image:    docker pull ghcr.io/YOUR_GITHUB_USER/pocl-node:latest"
echo "========================================================"