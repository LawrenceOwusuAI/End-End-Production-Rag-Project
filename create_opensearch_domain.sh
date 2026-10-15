# CREATE AMAZON OPENSEARCH DOMAIN
# 1. Validates AWS CLI
# 2. Reads the current AWS account and IAM identity
# 3. Creates an OpenSearch domain
# 4. Enables HTTPS,TLS 1.2+, encryption at rest, node-to-node encryption,fine-grained access control
# 6. Echo domain ARN, ID, endpoint, dashboard URL, engine version, account IDmaster IAM ARN, processing status
# 7. Prints everything

set -euo pipefail

DOMAIN_NAME="${DOMAIN_NAME:-rag-observability}"

AWS_REGION="${AWS_REGION:-us-east-1}"

ENGINE_VERSION="${ENGINE_VERSION:-OpenSearch_2.19}"

INSTANCE_TYPE="${INSTANCE_TYPE:-t3.small.search}"

INSTANCE_COUNT="${INSTANCE_COUNT:-1}"

EBS_VOLUME_SIZE="${EBS_VOLUME_SIZE:-20}"

EBS_VOLUME_TYPE="${EBS_VOLUME_TYPE:-gp3}"

GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
BLUE="\033[0;34m"
NC="\033[0m"

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

if ! command -v aws >/dev/null 2>&1
then
    error "AWS CLI was not found."
    echo "Install AWS CLI v2 and run:"
    echo
    echo "aws --version"

    exit 1
fi

AWS_CLI_VERSION="$(aws --version 2>&1)"
info "AWS CLI detected: ${AWS_CLI_VERSION}"

info "Checking AWS credentials..."

if ! aws sts get-caller-identity \
    --region "${AWS_REGION}" \
    >/dev/null 2>&1
then
    error "AWS credentials are not valid or not configured."

    echo "Verify with:"
    echo
    echo "aws sts get-caller-identity"

    exit 1
fi

success "AWS credentials are valid."

ACCOUNT_ID="$(aws sts get-caller-identity --query "Account" --output text)"

CALLER_ARN="$(aws sts get-caller-identity --query "Arn" --output text)"

CALLER_USER_ID="$(aws sts get-caller-identity --query "UserId" --output text)"

info "AWS Account ID: ${ACCOUNT_ID}"

info "Caller ARN: ${CALLER_ARN}"

MASTER_USER_ARN="${MASTER_USER_ARN:-${CALLER_ARN}}"

if [[ "${MASTER_USER_ARN}" == arn:aws:sts::* ]]
then
    error "The current identity is an STS assumed-role ARN."
    echo
    echo "Current identity:"
    echo
    echo "${MASTER_USER_ARN}"
    echo
    echo "Set MASTER_USER_ARN to the IAM role ARN instead."
    echo
    echo "Example:"
    echo
    echo "MASTER_USER_ARN=arn:aws:iam::${ACCOUNT_ID}:role/MyRole"
    exit 1
fi

EXPECTED_DOMAIN_ARN="arn:aws:es:${AWS_REGION}:${ACCOUNT_ID}:domain/${DOMAIN_NAME}"

ACCESS_POLICY=$(python - <<PY
import json

policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::${ACCOUNT_ID}:root"
            },
            "Action": "es:ESHttp*",
            "Resource": "${EXPECTED_DOMAIN_ARN}/*"
        }
    ]
}

print(json.dumps(policy, separators=(",", ":")))
PY
)

echo
echo "Access policy:"
echo "${ACCESS_POLICY}"
echo


# ACCESS_POLICY="$(
# cat <<EOF
# {
#   "Version": "2012-10-17",
#   "Statement": [
#     {
#       "Effect": "Allow",
#       "Principal": {
#         "AWS": "arn:aws:iam::${ACCOUNT_ID}:root"
#       },
#       "Action": "es:ESHttp*",
#       "Resource": "${EXPECTED_DOMAIN_ARN}/*"
#     }
#   ]
# }
# EOF
# )"

info "Checking whether OpenSearch domain '${DOMAIN_NAME}' exists..."

if aws opensearch describe-domain \
    --domain-name "${DOMAIN_NAME}" \
    --region "${AWS_REGION}" \
    >/dev/null 2>&1
then
    warning "Domain '${DOMAIN_NAME}' already exists."
    warning "Skipping domain creation."

else
    info "Creating Amazon OpenSearch domain..."
    info "Domain name: ${DOMAIN_NAME}"
    info "Region: ${AWS_REGION}"
    info "Engine: ${ENGINE_VERSION}"
    info "Instance: ${INSTANCE_TYPE}"
    info "Master user ARN: ${MASTER_USER_ARN}"


    CREATE_OUTPUT="$(
        aws opensearch create-domain \
            --domain-name "${DOMAIN_NAME}" \
            --region "${AWS_REGION}" \
            --engine-version "${ENGINE_VERSION}" \
            --cluster-config \
                "InstanceType=${INSTANCE_TYPE},InstanceCount=${INSTANCE_COUNT},DedicatedMasterEnabled=false,ZoneAwarenessEnabled=false" \
            --ebs-options \
                "EBSEnabled=true,VolumeType=${EBS_VOLUME_TYPE},VolumeSize=${EBS_VOLUME_SIZE}" \
            --node-to-node-encryption-options \
                "Enabled=true" \
            --encryption-at-rest-options \
                "Enabled=true" \
            --domain-endpoint-options \
                "EnforceHTTPS=true,TLSSecurityPolicy=Policy-Min-TLS-1-2-PFS-2023-10" \
            --advanced-security-options \
                "Enabled=true,InternalUserDatabaseEnabled=false,MasterUserOptions={MasterUserARN=${MASTER_USER_ARN}}" \
            --access-policies "${ACCESS_POLICY}" \
            --tag-list \
                "Key=Project,Value=RAG-Observability" \
                "Key=Environment,Value=development" \
            --no-cli-pager \
            --output json
    )"

    CREATED_DOMAIN_ARN="$(
        echo "${CREATE_OUTPUT}" \
        | python -c \
        "import json,sys; print(json.load(sys.stdin)['DomainStatus']['ARN'])"
    )"

    CREATED_DOMAIN_ID="$(
        echo "${CREATE_OUTPUT}" \
        | python -c \
        "import json,sys; print(json.load(sys.stdin)['DomainStatus']['DomainId'])"
    )"

    success "OpenSearch domain creation request submitted."
    echo
    echo "Initial ARN:"
    echo "${CREATED_DOMAIN_ARN}"
    echo
    echo "Initial Domain ID:"
    echo "${CREATED_DOMAIN_ID}"
fi

echo
info "Waiting for OpenSearch domain to become active..."

while true
do
    CREATED="$(
        aws opensearch describe-domain \
            --domain-name "${DOMAIN_NAME}" \
            --region "${AWS_REGION}" \
            --query "DomainStatus.Created" \
            --output text
    )"

    PROCESSING="$(
        aws opensearch describe-domain \
            --domain-name "${DOMAIN_NAME}" \
            --region "${AWS_REGION}" \
            --query "DomainStatus.Processing" \
            --output text
    )"

    ENDPOINT="$(
        aws opensearch describe-domain \
            --domain-name "${DOMAIN_NAME}" \
            --region "${AWS_REGION}" \
            --query "DomainStatus.Endpoint" \
            --output text
    )"

    echo
    echo "Created:    ${CREATED}"
    echo "Processing: ${PROCESSING}"
    echo "Endpoint:   ${ENDPOINT}"

    if [[ "${CREATED}" == "True" ]] \
       && [[ "${PROCESSING}" == "False" ]] \
       && [[ "${ENDPOINT}" != "None" ]]
    then

        break
    fi

    info "Domain is still provisioning. Checking again in 30 seconds..."
    sleep 30
done

info "Retrieving final domain information..."

DOMAIN_ARN="$(
    aws opensearch describe-domain \
        --domain-name "${DOMAIN_NAME}" \
        --region "${AWS_REGION}" \
        --query "DomainStatus.ARN" \
        --output text
)"

DOMAIN_ID="$(
    aws opensearch describe-domain \
        --domain-name "${DOMAIN_NAME}" \
        --region "${AWS_REGION}" \
        --query "DomainStatus.DomainId" \
        --output text
)"

DOMAIN_ENDPOINT="$(
    aws opensearch describe-domain \
        --domain-name "${DOMAIN_NAME}" \
        --region "${AWS_REGION}" \
        --query "DomainStatus.Endpoint" \
        --output text
)"

FINAL_ENGINE_VERSION="$(
    aws opensearch describe-domain \
        --domain-name "${DOMAIN_NAME}" \
        --region "${AWS_REGION}" \
        --query "DomainStatus.EngineVersion" \
        --output text
)"

FINAL_INSTANCE_TYPE="$(
    aws opensearch describe-domain \
        --domain-name "${DOMAIN_NAME}" \
        --region "${AWS_REGION}" \
        --query "DomainStatus.ClusterConfig.InstanceType" \
        --output text
)"

FINAL_INSTANCE_COUNT="$(
    aws opensearch describe-domain \
        --domain-name "${DOMAIN_NAME}" \
        --region "${AWS_REGION}" \
        --query "DomainStatus.ClusterConfig.InstanceCount" \
        --output text
)"

PROCESSING="$(
    aws opensearch describe-domain \
        --domain-name "${DOMAIN_NAME}" \
        --region "${AWS_REGION}" \
        --query "DomainStatus.Processing" \
        --output text
)"

CREATED="$(
    aws opensearch describe-domain \
        --domain-name "${DOMAIN_NAME}" \
        --region "${AWS_REGION}" \
        --query "DomainStatus.Created" \
        --output text
)"

ENFORCE_HTTPS="$(
    aws opensearch describe-domain \
        --domain-name "${DOMAIN_NAME}" \
        --region "${AWS_REGION}" \
        --query "DomainStatus.DomainEndpointOptions.EnforceHTTPS" \
        --output text
)"

ENCRYPTION_AT_REST="$(
    aws opensearch describe-domain \
        --domain-name "${DOMAIN_NAME}" \
        --region "${AWS_REGION}" \
        --query "DomainStatus.EncryptionAtRestOptions.Enabled" \
        --output text
)"

NODE_TO_NODE_ENCRYPTION="$(
    aws opensearch describe-domain \
        --domain-name "${DOMAIN_NAME}" \
        --region "${AWS_REGION}" \
        --query "DomainStatus.NodeToNodeEncryptionOptions.Enabled" \
        --output text
)"

FINE_GRAINED_ACCESS_CONTROL="$(
    aws opensearch describe-domain \
        --domain-name "${DOMAIN_NAME}" \
        --region "${AWS_REGION}" \
        --query "DomainStatus.AdvancedSecurityOptions.Enabled" \
        --output text
)"

OPENSEARCH_URL="https://${DOMAIN_ENDPOINT}"

OPENSEARCH_DASHBOARDS_URL="https://${DOMAIN_ENDPOINT}/_dashboards/"

DOMAIN_STATE="$(
    aws opensearch describe-domain-health \
        --domain-name "${DOMAIN_NAME}" \
        --region "${AWS_REGION}" \
        --query "DomainState" \
        --output text \
        2>/dev/null \
        || echo "NotAvailable"
)"

CLUSTER_HEALTH="$(
    aws opensearch describe-domain-health \
        --domain-name "${DOMAIN_NAME}" \
        --region "${AWS_REGION}" \
        --query "ClusterHealth" \
        --output text \
        2>/dev/null \
        || echo "NotAvailable"
)"

echo "       AMAZON OPENSEARCH DOMAIN CREATED SUCCESSFULLY"
echo

printf "%-30s %s\n" \
    "Domain Name:" \
    "${DOMAIN_NAME}"

printf "%-30s %s\n" \
    "Domain ARN:" \
    "${DOMAIN_ARN}"

printf "%-30s %s\n" \
    "Domain ID:" \
    "${DOMAIN_ID}"

printf "%-30s %s\n" \
    "AWS Account ID:" \
    "${ACCOUNT_ID}"

printf "%-30s %s\n" \
    "AWS Region:" \
    "${AWS_REGION}"

printf "%-30s %s\n" \
    "AWS Caller ARN:" \
    "${CALLER_ARN}"

printf "%-30s %s\n" \
    "Master User ARN:" \
    "${MASTER_USER_ARN}"

printf "%-30s %s\n" \
    "Engine Version:" \
    "${FINAL_ENGINE_VERSION}"

printf "%-30s %s\n" \
    "Instance Type:" \
    "${FINAL_INSTANCE_TYPE}"

printf "%-30s %s\n" \
    "Instance Count:" \
    "${FINAL_INSTANCE_COUNT}"

printf "%-30s %s\n" \
    "Created:" \
    "${CREATED}"

printf "%-30s %s\n" \
    "Processing:" \
    "${PROCESSING}"

printf "%-30s %s\n" \
    "Domain State:" \
    "${DOMAIN_STATE}"

printf "%-30s %s\n" \
    "Cluster Health:" \
    "${CLUSTER_HEALTH}"

echo

printf "%-30s %s\n" \
    "HTTPS Enabled:" \
    "${ENFORCE_HTTPS}"

printf "%-30s %s\n" \
    "Encryption At Rest:" \
    "${ENCRYPTION_AT_REST}"

printf "%-30s %s\n" \
    "Node Encryption:" \
    "${NODE_TO_NODE_ENCRYPTION}"

printf "%-30s %s\n" \
    "Fine-Grained Security:" \
    "${FINE_GRAINED_ACCESS_CONTROL}"

echo

printf "%-30s %s\n" \
    "Endpoint:" \
    "${DOMAIN_ENDPOINT}"

printf "%-30s %s\n" \
    "OpenSearch URL:" \
    "${OPENSEARCH_URL}"

printf "%-30s %s\n" \
    "Dashboards URL:" \
    "${OPENSEARCH_DASHBOARDS_URL}"

echo
echo "Add the following values to your .env file:"

echo "AWS_REGION=${AWS_REGION}"

echo "OPENSEARCH_HOST=${OPENSEARCH_URL}"

echo "OPENSEARCH_DOMAIN_ARN=${DOMAIN_ARN}"

echo "OPENSEARCH_DOMAIN_NAME=${DOMAIN_NAME}"

echo "OPENSEARCH_LOG_INDEX=logs-otel-v1-*"

echo "OPENSEARCH_TRACE_INDEX=otel-v1-apm-span-*"

echo
success "OpenSearch setup complete."