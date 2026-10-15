#!/usr/bin/env bash

set -euo pipefail


# VARIABLES
AWS_VPC_CIDR="10.0.0.0/16"
AWS_SUBNET_CIDR="10.0.1.0/24"

# Kubernetes networking:
# Must NOT overlap with AWS VPC 10.0.0.0/16.
POD_CIDR="192.168.0.0/16"

# Kubernetes default service CIDR
SERVICE_CIDR="10.96.0.0/12"

CALICO_VERSION="v3.33.0"

NODENAME="$(hostname -s)"


echo " INITIALIZING KUBERNETES CONTROL PLANE"

echo "Node name:        $NODENAME"
echo "AWS VPC CIDR:     $AWS_VPC_CIDR"
echo "AWS subnet CIDR:  $AWS_SUBNET_CIDR"
echo "Pod CIDR:         $POD_CIDR"
echo "Service CIDR:     $SERVICE_CIDR"


# ============================================================
# VALIDATE NODE
# ============================================================

if [[ "$NODENAME" != "control-plane-node" ]]; then
    echo ""
    echo "ERROR: This script must run on control-plane-node."
    echo "Current hostname: $NODENAME"
    exit 1
fi


# ============================================================
# GET EC2 PRIVATE + PUBLIC IPS USING IMDSv2
# ============================================================

IMDS_TOKEN="$(curl -fsS \
    -X PUT \
    -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" \
    http://169.254.169.254/latest/api/token)"


CONTROL_PLANE_PRIVATE_IP="$(curl -fsS \
    -H "X-aws-ec2-metadata-token: ${IMDS_TOKEN}" \
    http://169.254.169.254/latest/meta-data/local-ipv4)"


CONTROL_PLANE_PUBLIC_IP="$(curl -fsS \
    -H "X-aws-ec2-metadata-token: ${IMDS_TOKEN}" \
    http://169.254.169.254/latest/meta-data/public-ipv4 || true)"


if [[ -z "$CONTROL_PLANE_PRIVATE_IP" ]]; then
    echo "ERROR: Unable to determine control-plane private IP."
    exit 1
fi


echo ""
echo "Control-plane private IP: $CONTROL_PLANE_PRIVATE_IP"

if [[ -n "$CONTROL_PLANE_PUBLIC_IP" ]]; then
    echo "Control-plane Elastic/Public IP: $CONTROL_PLANE_PUBLIC_IP"
fi


# ============================================================
# MAKE SURE CRI-O IS RUNNING
# ============================================================

systemctl enable --now crio

if ! systemctl is-active --quiet crio; then
    echo "ERROR: CRI-O is not running."
    exit 1
fi


# ============================================================
# PRE-PULL KUBERNETES IMAGES
# ============================================================

echo ""
echo "Pulling Kubernetes control-plane images..."

kubeadm config images pull \
    --cri-socket unix:///var/run/crio/crio.sock


# ============================================================
# PREVENT ACCIDENTAL SECOND INITIALIZATION
# ============================================================

if [[ -f /etc/kubernetes/admin.conf ]]; then

    echo ""
    echo "Kubernetes control plane already appears initialized."
    echo "/etc/kubernetes/admin.conf already exists."
    echo ""
    echo "Skipping kubeadm init."

else

    echo ""
    echo "Initializing Kubernetes..."


    # If Elastic/Public IP exists, include it in TLS certificate SANs.
    if [[ -n "$CONTROL_PLANE_PUBLIC_IP" ]]; then

        kubeadm init \
            --apiserver-advertise-address="$CONTROL_PLANE_PRIVATE_IP" \
            --apiserver-cert-extra-sans="$CONTROL_PLANE_PRIVATE_IP,$CONTROL_PLANE_PUBLIC_IP" \
            --pod-network-cidr="$POD_CIDR" \
            --service-cidr="$SERVICE_CIDR" \
            --node-name="$NODENAME" \
            --cri-socket unix:///var/run/crio/crio.sock

    else

        kubeadm init \
            --apiserver-advertise-address="$CONTROL_PLANE_PRIVATE_IP" \
            --apiserver-cert-extra-sans="$CONTROL_PLANE_PRIVATE_IP" \
            --pod-network-cidr="$POD_CIDR" \
            --service-cidr="$SERVICE_CIDR" \
            --node-name="$NODENAME" \
            --cri-socket unix:///var/run/crio/crio.sock

    fi

fi


# ============================================================
# CONFIGURE KUBECTL FOR THE UBUNTU USER
# ============================================================

# Script is normally executed with sudo.
# Configure kubeconfig for the original login user.

LOGIN_USER="${SUDO_USER:-ubuntu}"
LOGIN_HOME="$(getent passwd "$LOGIN_USER" | cut -d: -f6)"


mkdir -p "${LOGIN_HOME}/.kube"

cp /etc/kubernetes/admin.conf \
    "${LOGIN_HOME}/.kube/config"

chown -R "${LOGIN_USER}:${LOGIN_USER}" \
    "${LOGIN_HOME}/.kube"


export KUBECONFIG=/etc/kubernetes/admin.conf


# ============================================================
# INSTALL CALICO
# ============================================================

echo ""
echo "Installing Calico ${CALICO_VERSION}..."


# Kubernetes 1.36+ CRDs
kubectl apply -f \
"https://raw.githubusercontent.com/projectcalico/calico/${CALICO_VERSION}/manifests/v3_projectcalico_org.yaml"


# Tigera Operator
kubectl apply -f \
"https://raw.githubusercontent.com/projectcalico/calico/${CALICO_VERSION}/manifests/tigera-operator.yaml"


echo ""
echo "Waiting for Tigera operator..."

kubectl rollout status \
    deployment/tigera-operator \
    -n tigera-operator \
    --timeout=300s


# ============================================================
# DOWNLOAD CALICO CUSTOM RESOURCES
# ============================================================

curl -fsSL \
"https://raw.githubusercontent.com/projectcalico/calico/${CALICO_VERSION}/manifests/custom-resources.yaml" \
-o /tmp/calico-custom-resources.yaml


# Ensure Calico uses the same Pod CIDR as kubeadm.
sed -i \
    "s|cidr: 192.168.0.0/16|cidr: ${POD_CIDR}|g" \
    /tmp/calico-custom-resources.yaml


# ============================================================
# APPLY CALICO CONFIGURATION
# ============================================================

kubectl apply -f /tmp/calico-custom-resources.yaml


echo ""
echo "Waiting for Calico components..."


# Give the operator time to create resources.
sleep 15


# ============================================================
# WAIT FOR CONTROL PLANE TO BECOME READY
# ============================================================

echo ""
echo "Waiting for Kubernetes node to become Ready..."

kubectl wait \
    --for=condition=Ready \
    node/"$NODENAME" \
    --timeout=300s || true


# ============================================================
# GENERATE WORKER JOIN COMMAND
# ============================================================

echo ""
echo "Generating worker-node join command..."

JOIN_COMMAND="$(kubeadm token create --print-join-command)"


echo "$JOIN_COMMAND" > "${LOGIN_HOME}/worker-join-command.sh"

chmod 700 "${LOGIN_HOME}/worker-join-command.sh"

chown "${LOGIN_USER}:${LOGIN_USER}" \
    "${LOGIN_HOME}/worker-join-command.sh"


# ============================================================
# CLUSTER STATUS
# ============================================================

echo ""
echo "============================================================"
echo " KUBERNETES CONTROL PLANE CREATED"
echo "============================================================"

echo ""
kubectl get nodes -o wide

echo ""
kubectl get pods -A

echo ""
echo "Control Plane Private IP:"
echo "$CONTROL_PLANE_PRIVATE_IP"

echo ""
echo "Control Plane Elastic/Public IP:"
echo "${CONTROL_PLANE_PUBLIC_IP:-Not detected}"

echo ""
echo "Worker join command:"
echo ""
echo "$JOIN_COMMAND"

echo ""
echo "The join command was also saved to:"
echo "${LOGIN_HOME}/worker-join-command.sh"

echo ""
echo "============================================================"
echo " NEXT STEP"
echo "============================================================"
echo ""
echo "Run the generated kubeadm join command on:"
echo "  worker-node-1"
echo "  worker-node-2"
echo ""