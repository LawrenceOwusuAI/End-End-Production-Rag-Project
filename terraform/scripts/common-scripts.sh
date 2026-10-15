#!/usr/bin/env bash

set -euo pipefail

# VARIABLES
KUBERNETES_MINOR="v1.36"
KUBERNETES_PACKAGE_VERSION="1.36.5-1.1"

CRIO_VERSION="v1.36"
CRICTL_VERSION="v1.36.0"

# AWS network created by Terraform
AWS_VPC_CIDR="10.0.0.0/16"
AWS_SUBNET_CIDR="10.0.1.0/24"

NODE_NAME="${1:-}"

if [[ -z "$NODE_NAME" ]]; then
    echo "ERROR: Node name is required."
    echo ""
    echo "Examples:"
    echo "  sudo bash common.sh control-plane-node"
    echo "  sudo bash common.sh worker-node-1"
    echo "  sudo bash common.sh worker-node-2"
    exit 1
fi

echo " Configuring Kubernetes node: $NODE_NAME"
echo " Kubernetes version: $KUBERNETES_MINOR"
echo " AWS VPC CIDR: $AWS_VPC_CIDR"
echo " AWS subnet CIDR: $AWS_SUBNET_CIDR"

# SET HOSTNAME
hostnamectl set-hostname "$NODE_NAME"

echo "Hostname configured:"
hostname

# DISABLE SWAP
# Kubernetes requires swap to be disabled.

swapoff -a

# Permanently disable swap in /etc/fstab
sed -ri '/\sswap\s/s/^#?/#/' /etc/fstab

# LOAD REQUIRED KERNEL MODULES


cat <<EOF >/etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

modprobe overlay
modprobe br_netfilter


# KUBERNETES NETWORK SYSCTL SETTINGS


cat <<EOF >/etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF

sysctl --system


# INSTALL BASIC PACKAGES
export DEBIAN_FRONTEND=noninteractive

apt-get update

apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gpg \
    gnupg \
    software-properties-common \
    jq



# CREATE APT KEYRING DIRECTORY
install -m 0755 -d /etc/apt/keyrings

# INSTALL CRI-O

curl -fsSL \
    "https://download.opensuse.org/repositories/isv:/cri-o:/stable:/${CRIO_VERSION}/deb/Release.key" \
    | gpg --dearmor --yes \
    -o /etc/apt/keyrings/cri-o-apt-keyring.gpg


echo \
"deb [signed-by=/etc/apt/keyrings/cri-o-apt-keyring.gpg] https://download.opensuse.org/repositories/isv:/cri-o:/stable:/${CRIO_VERSION}/deb/ /" \
    > /etc/apt/sources.list.d/cri-o.list


apt-get update

apt-get install -y cri-o

systemctl daemon-reload
systemctl enable --now crio


# Verify CRI-O
systemctl is-active --quiet crio || {
    echo "ERROR: CRI-O failed to start."
    exit 1
}

echo "CRI-O installed successfully."


# INSTALL CRICTL


ARCH="$(dpkg --print-architecture)"

case "$ARCH" in
    amd64)
        CRICTL_ARCH="amd64"
        ;;
    arm64)
        CRICTL_ARCH="arm64"
        ;;
    *)
        echo "Unsupported architecture: $ARCH"
        exit 1
        ;;
esac


curl -fL \
    -o /tmp/crictl.tar.gz \
    "https://github.com/kubernetes-sigs/cri-tools/releases/download/${CRICTL_VERSION}/crictl-${CRICTL_VERSION}-linux-${CRICTL_ARCH}.tar.gz"


tar -xzf /tmp/crictl.tar.gz -C /usr/local/bin

rm -f /tmp/crictl.tar.gz


# Configure crictl for CRI-O
cat <<EOF >/etc/crictl.yaml
runtime-endpoint: unix:///var/run/crio/crio.sock
image-endpoint: unix:///var/run/crio/crio.sock
timeout: 10
debug: false
EOF

echo "crictl installed successfully."

# ADD KUBERNETES APT REPOSITORY

curl -fsSL \
    "https://pkgs.k8s.io/core:/stable:/${KUBERNETES_MINOR}/deb/Release.key" \
    | gpg --dearmor --yes \
    -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg


echo \
"deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/${KUBERNETES_MINOR}/deb/ /" \
    > /etc/apt/sources.list.d/kubernetes.list


apt-get update


# INSTALL KUBERNETES

apt-get install -y \
    kubelet="${KUBERNETES_PACKAGE_VERSION}" \
    kubeadm="${KUBERNETES_PACKAGE_VERSION}" \
    kubectl="${KUBERNETES_PACKAGE_VERSION}"


# Prevent unintended Kubernetes upgrades
apt-mark hold kubelet kubeadm kubectl

# GET EC2 PRIVATE IP USING AWS IMDSv2

IMDS_TOKEN="$(curl -fsS \
    -X PUT \
    -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" \
    http://169.254.169.254/latest/api/token)"


NODE_PRIVATE_IP="$(curl -fsS \
    -H "X-aws-ec2-metadata-token: ${IMDS_TOKEN}" \
    http://169.254.169.254/latest/meta-data/local-ipv4)"


if [[ -z "$NODE_PRIVATE_IP" ]]; then
    echo "ERROR: Could not determine EC2 private IP address."
    exit 1
fi


echo "EC2 private IP: $NODE_PRIVATE_IP"

# CONFIGURE KUBELET TO USE EC2 PRIVATE IP


cat <<EOF >/etc/default/kubelet
KUBELET_EXTRA_ARGS=--node-ip=${NODE_PRIVATE_IP}
EOF

systemctl daemon-reload
systemctl enable kubelet


# kubelet will restart repeatedly until kubeadm initializes
# or joins the node. This is expected.
systemctl restart kubelet || true

# VERIFY INSTALLATION
echo " COMMON NODE SETUP COMPLETE"
echo "Node name:"
hostname
echo ""
echo "Private IP:"
echo "$NODE_PRIVATE_IP"
echo "Kubernetes:"
kubeadm version -o short

echo ""
echo "CRI-O:"
crio --version | head -n 1

echo ""
echo "crictl:"
crictl --version

echo ""
echo "Swap:"
swapon --show || true

echo ""
