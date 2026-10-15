#!/usr/bin/env bash

# Kubernetes Control Plane Post-Setup
#
# Run ONLY on control-plane-node
#
# What this script does:
#   1. Verifies kubectl works
#   2. Installs Calico
#   3. Applies Calico custom resources
#   4. Waits for networking to become healthy
#   5. Verifies control-plane readiness
#   6. Generates worker-node join command
#   7. Saves join command to a file
#   8. Prints useful cluster verification commands

set -euo pipefail

# VARIABLES

CALICO_VERSION="v3.33.0"

# This must match the CIDR used during kubeadm init.
POD_CIDR="192.168.0.0/16"

NODE_NAME="$(hostname -s)"

LOGIN_USER="${SUDO_USER:-ubuntu}"
LOGIN_HOME="$(getent passwd "$LOGIN_USER" | cut -d: -f6)"

export KUBECONFIG=/etc/kubernetes/admin.conf

# VERIFY CONTROL PLANE

if [[ "$NODE_NAME" != "control-plane-node" ]]; then
    echo "ERROR: Run this script only on control-plane-node."
    echo "Current hostname: $NODE_NAME"
    exit 1
fi


if [[ ! -f /etc/kubernetes/admin.conf ]]; then
    echo "ERROR: Kubernetes control plane is not initialized."
    echo "Run kubeadm init first."
    exit 1
fi

echo " KUBERNETES POST-INITIALIZATION"


echo "Control-plane node:"
echo "$NODE_NAME"

echo ""
echo "Pod CIDR:"
echo "$POD_CIDR"

echo ""
echo "Calico version:"
echo "$CALICO_VERSION"


# VERIFY KUBERNETES API


echo ""
echo "Checking Kubernetes API..."

kubectl cluster-info

# INSTALL CALICO CRDs

echo "Installing Calico CRDs..."

kubectl apply -f \
"https://raw.githubusercontent.com/projectcalico/calico/${CALICO_VERSION}/manifests/v3_projectcalico_org.yaml"

# INSTALL TIGERA OPERATOR

echo "Installing Tigera operator..."

kubectl apply -f \
"https://raw.githubusercontent.com/projectcalico/calico/${CALICO_VERSION}/manifests/tigera-operator.yaml"

echo "Waiting for Tigera operator..."

kubectl rollout status \
    deployment/tigera-operator \
    -n tigera-operator \
    --timeout=300s

# DOWNLOAD CALICO CUSTOM RESOURCES

echo "Downloading Calico custom resources..."

curl -fsSL \
"https://raw.githubusercontent.com/projectcalico/calico/${CALICO_VERSION}/manifests/custom-resources.yaml" \
-o /tmp/calico-custom-resources.yaml

echo ""
echo "Configuring Calico Pod CIDR..."

sed -i \
    "s|cidr: 192.168.0.0/16|cidr: ${POD_CIDR}|g" \
    /tmp/calico-custom-resources.yaml


echo ""
echo "Configured Calico CIDR:"

grep -n "cidr:" /tmp/calico-custom-resources.yaml

# APPLY CALICO CUSTOM RESOURCES

echo "Applying Calico custom resources..."

kubectl apply -f /tmp/calico-custom-resources.yaml

# VERIFY INSTALLATION RESOURCE

echo ""
echo "Checking Calico Installation resource..."

kubectl get installation default

echo ""
echo "Waiting for Calico components to start..."

sleep 20


echo ""
echo "Calico/Tigera status:"

kubectl get tigerastatus || true


# WAIT FOR CONTROL PLANE TO BECOME READY

echo "Waiting for control-plane-node to become Ready..."

kubectl wait \
    --for=condition=Ready \
    node/control-plane-node \
    --timeout=300s

echo "Current Kubernetes pods:"

kubectl get pods -A -o wide

# CHECK CONTROL PLANE

echo "Current Kubernetes nodes:"

kubectl get nodes -o wide


# GENERATE WORKER JOIN COMMAND

echo "Generating worker join command..."

JOIN_COMMAND="$(kubeadm token create --print-join-command)"

# SAVE JOIN COMMAND
JOIN_FILE="${LOGIN_HOME}/worker-join-command.sh"

cat <<EOF > "$JOIN_FILE"
#!/usr/bin/env bash

sudo ${JOIN_COMMAND}
EOF


chmod 700 "$JOIN_FILE"

chown "${LOGIN_USER}:${LOGIN_USER}" "$JOIN_FILE"

# PRINT JOIN COMMAND
echo " WORKER JOIN COMMAND"
echo ""

echo "Run this command on BOTH worker-node-1 and worker-node-2:"
echo ""

echo "sudo ${JOIN_COMMAND}"

echo ""

echo "The command has also been saved to:"
echo "$JOIN_FILE"

# USEFUL COMMANDS
echo " USEFUL KUBERNETES COMMANDS"

echo "# Check cluster nodes"
echo "kubectl get nodes -o wide"
echo ""
echo "# Watch nodes become Ready"
echo "watch kubectl get nodes -o wide"

echo ""
echo "# Check all pods"
echo "kubectl get pods -A -o wide"

echo ""
echo "# Check Calico pods"
echo "kubectl get pods -n calico-system -o wide"

echo ""
echo "# Check Tigera operator"
echo "kubectl get pods -n tigera-operator"

echo ""
echo "# Check Calico status"
echo "kubectl get tigerastatus"

echo ""
echo "# Generate a new worker join command"
echo "kubeadm token create --print-join-command"

echo ""
echo "# Check kubelet"
echo "sudo systemctl status kubelet --no-pager"

echo ""
echo "# Check CRI-O"
echo "sudo systemctl status crio --no-pager"

echo ""
echo "# Check kubelet logs"
echo "sudo journalctl -u kubelet -n 100 --no-pager"

echo ""
echo "# Check cluster information"
echo "kubectl cluster-info"

echo ""
echo "# Check Kubernetes version"
echo "kubectl version"

echo " POST-SETUP COMPLETE"
