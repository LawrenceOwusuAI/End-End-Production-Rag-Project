#!/usr/bin/env bash
set -euo pipefail


# AWS Load Balancer Controller IAM bootstrap
# This script:
#   1. Downloads the official AWS Load Balancer Controller IAM policy
#   2. Creates the IAM policy
#   3. Creates an EC2 trust policy
#   4. Creates a worker-node IAM role
#   5. Attaches the controller IAM policy to the role
#   6. Creates an EC2 instance profile
#   7. Adds the IAM role to the instance profile
#   8. Attaches the instance profile to both worker nodes
#   9. Verifies the result


# Configuration
AWS_ACCOUNT_ID="062416134769"
AWS_REGION="us-east-1"
WORKER_1_INSTANCE_ID="i-0e6a7dead73bfe2f7"
WORKER_2_INSTANCE_ID="i-03215955b3c76568e"
IAM_POLICY_NAME="AWSLoadBalancerControllerIAMPolicy"
IAM_ROLE_NAME="ProductionRAGWorkerRole"
INSTANCE_PROFILE_NAME="ProductionRAGWorkerInstanceProfile"
IAM_POLICY_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${IAM_POLICY_NAME}"

# ------------------------------------------------------------
# Resolve the directory containing this script.
# Git Bash represents Windows paths as /c/Users/...
# but the Windows AWS CLI expects C:/Users/...
# ------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

IAM_POLICY_FILE="${SCRIPT_DIR}/iam-policy.json"
TRUST_POLICY_FILE="${SCRIPT_DIR}/ec2-trust-policy.json"

# Convert Git Bash paths to Windows-compatible paths
# specifically for commands executed by the Windows AWS CLI.
IAM_POLICY_FILE_AWS="$(cygpath -m "${IAM_POLICY_FILE}")"
TRUST_POLICY_FILE_AWS="$(cygpath -m "${TRUST_POLICY_FILE}")"



# Step 1 Download the official AWS Load Balancer Controller IAM policy.
# This policy gives the controller permissions to create and
# manage AWS load balancers, target groups, listeners, etc.

echo "STEP 1: Download AWS Load Balancer Controller IAM policy"

curl -fsSL https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v3.6.0/docs/install/iam_policy.json -o "${IAM_POLICY_FILE}"
echo "Downloaded:"
echo "${IAM_POLICY_FILE}"

# Step 2
# Creating IAM policy in your AWS account. If the policy already exists, skip creation instead of failing.
echo "STEP 2: Create IAM policy"

if aws iam get-policy --policy-arn "${IAM_POLICY_ARN}" >/dev/null 2>&1; then
    echo "IAM policy already exists:"
    echo "${IAM_POLICY_ARN}"
else
    aws iam create-policy \
  --policy-name "${IAM_POLICY_NAME}" \
  --policy-document "file://${IAM_POLICY_FILE_AWS}"
    echo "IAM policy created successfully."
fi

# Step 3 Create the EC2 trust policy. This allows EC2 instances to assume the worker-node IAM role.
echo "STEP 3: Create EC2 trust policy"

cat > "${TRUST_POLICY_FILE}" <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

echo "Created trust policy:"
echo "${TRUST_POLICY_FILE}"

# Step 4 Create the IAM role that will be used by the worker nodes. If the role already exists, skip creation.
echo "STEP 4: Create worker IAM role"
if aws iam get-role --role-name "${IAM_ROLE_NAME}" >/dev/null 2>&1; then
    echo "IAM role already exists:"
    echo "${IAM_ROLE_NAME}"
else
    aws iam create-role \
  --role-name "${IAM_ROLE_NAME}" \
  --assume-role-policy-document "file://${TRUST_POLICY_FILE_AWS}"
    echo "IAM role created successfully."
fi

# Step 5 Attach the AWS Load Balancer Controller IAM policy to the worker-node role.
echo "STEP 5: Attach IAM policy to worker role"
aws iam attach-role-policy --role-name "${IAM_ROLE_NAME}" --policy-arn "${IAM_POLICY_ARN}"
echo "Policy attached successfully."

# Step 6 Create the EC2 instance profile. EC2 instances receive IAM roles through instance profiles.
# If the profile already exists, skip creation.
echo "STEP 6: Creating EC2 instance profile"

if aws iam get-instance-profile --instance-profile-name "${INSTANCE_PROFILE_NAME}" >/dev/null 2>&1; then
    echo "Instance profile already exists:"
    echo "${INSTANCE_PROFILE_NAME}"
else

    aws iam create-instance-profile --instance-profile-name "${INSTANCE_PROFILE_NAME}"
    echo "Instance profile created successfully."
    echo "Waiting briefly for IAM propagation..."
    sleep 10
fi

# Step 7 Add the worker IAM role to the EC2 instance profile. If it is already attached, skip the operation.
echo "STEP 7: Add IAM role to instance profile"
ROLE_ALREADY_ATTACHED="$(
  aws iam get-instance-profile \
    --instance-profile-name "${INSTANCE_PROFILE_NAME}" \
    --query "InstanceProfile.Roles[?RoleName=='${IAM_ROLE_NAME}'].RoleName" \
    --output text
)"

if [[ "${ROLE_ALREADY_ATTACHED}" == "${IAM_ROLE_NAME}" ]]; then
    echo "Role is already attached to the instance profile."
else
    aws iam add-role-to-instance-profile --instance-profile-name "${INSTANCE_PROFILE_NAME}" --role-name "${IAM_ROLE_NAME}"
    echo "Role added to instance profile successfully."
    echo "Waiting briefly for IAM propagation..."
    sleep 10
fi

# Step 8 Attach the instance profile to worker-node-1. Because the worker currently has no instance profile,

echo "STEP 8A: Attach instance profile to worker-node-1"

WORKER_1_PROFILE="$(
  aws ec2 describe-instances \
    --region "${AWS_REGION}" \
    --instance-ids "${WORKER_1_INSTANCE_ID}" \
    --query "Reservations[0].Instances[0].IamInstanceProfile.Arn" \
    --output text
)"

if [[ "${WORKER_1_PROFILE}" == "None" || -z "${WORKER_1_PROFILE}" ]]; then

    aws ec2 associate-iam-instance-profile \
      --region "${AWS_REGION}" \
      --instance-id "${WORKER_1_INSTANCE_ID}" \
      --iam-instance-profile Name="${INSTANCE_PROFILE_NAME}"
    echo "Instance profile attached to worker-node-1."
else
    echo "worker-node-1 already has an instance profile:"
    echo "${WORKER_1_PROFILE}"

fi

# Step 8B Attach the same instance profile to worker-node-2.
echo "STEP 8B: Attach instance profile to worker-node-2"

WORKER_2_PROFILE="$(
  aws ec2 describe-instances \
    --region "${AWS_REGION}" \
    --instance-ids "${WORKER_2_INSTANCE_ID}" \
    --query "Reservations[0].Instances[0].IamInstanceProfile.Arn" \
    --output text
)"

if [[ "${WORKER_2_PROFILE}" == "None" || -z "${WORKER_2_PROFILE}" ]]; then

    aws ec2 associate-iam-instance-profile \
      --region "${AWS_REGION}" \
      --instance-id "${WORKER_2_INSTANCE_ID}" \
      --iam-instance-profile Name="${INSTANCE_PROFILE_NAME}"

    echo "Instance profile attached to worker-node-2."

else

    echo "worker-node-2 already has an instance profile:"
    echo "${WORKER_2_PROFILE}"

fi

# Final verification Show the IAM instance profile associated with both workers.
echo "FINAL VERIFICATION"

aws ec2 describe-instances \
  --region "${AWS_REGION}" \
  --instance-ids \
    "${WORKER_1_INSTANCE_ID}" \
    "${WORKER_2_INSTANCE_ID}" \
  --query "Reservations[].Instances[].{Name:Tags[?Key=='Name']|[0].Value,InstanceId:InstanceId,Profile:IamInstanceProfile.Arn}" \
  --output table

# Verify the IAM policy is attached to the worker role.

echo "VERIFY ATTACHED IAM POLICIES"

aws iam list-attached-role-policies \
  --role-name "${IAM_ROLE_NAME}" \
  --output table

echo "AWS Load Balancer Controller IAM bootstrap completed."
