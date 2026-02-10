#!/bin/bash
# AWS Deployment Script for Cognito Backend
# Deploys to AWS Fargate with auto-scaling to 0 (cost-efficient)

set -e

# Configuration
AWS_REGION="us-east-1"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO_NAME="cognito-backend"
ECS_CLUSTER_NAME="cognito-cluster"
ECS_SERVICE_NAME="cognito-backend"
ECS_TASK_FAMILY="cognito-backend"
VPC_ID=""  # Set your VPC ID
SUBNET_1=""  # Set your subnet ID
SUBNET_2=""  # Set your subnet ID (different AZ)
SECURITY_GROUP=""  # Set your security group ID

echo "🚀 Deploying Syllabus.ai Backend to AWS"
echo "Region: $AWS_REGION"
echo "Account: $AWS_ACCOUNT_ID"

# Step 1: Create ECR Repository
echo ""
echo "📦 Step 1: Creating ECR repository..."
aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $AWS_REGION 2>/dev/null || \
  aws ecr create-repository \
    --repository-name $ECR_REPO_NAME \
    --region $AWS_REGION \
    --image-scanning-configuration scanOnPush=true

ECR_REPO_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME"
echo "✅ ECR Repository: $ECR_REPO_URI"

# Step 2: Build and Push Docker Image
echo ""
echo "🏗️  Step 2: Building Docker image with model caching..."
cd ../
docker build -f Dockerfile.prod -t $ECR_REPO_NAME:latest .

echo ""
echo "🔐 Authenticating Docker to ECR..."
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $ECR_REPO_URI

echo ""
echo "⬆️  Pushing image to ECR..."
docker tag $ECR_REPO_NAME:latest $ECR_REPO_URI:latest
docker push $ECR_REPO_URI:latest
echo "✅ Image pushed successfully"

# Step 3: Create Secrets in AWS Secrets Manager
echo ""
echo "🔑 Step 3: Setting up secrets (skip if already exist)..."
for secret in "syllabus-ai/openai-key" "syllabus-ai/supabase-url" "syllabus-ai/supabase-key" "syllabus-ai/sarvam-key"; do
  aws secretsmanager describe-secret --secret-id $secret --region $AWS_REGION 2>/dev/null || \
    echo "⚠️  Secret $secret not found. Create it manually with: aws secretsmanager create-secret --name $secret --secret-string 'your_value'"
done

# Step 4: Create CloudWatch Log Group
echo ""
echo "📊 Step 4: Creating CloudWatch log group..."
aws logs create-log-group \
  --log-group-name /ecs/$ECS_TASK_FAMILY \
  --region $AWS_REGION 2>/dev/null || \
  echo "✅ Log group already exists"

# Step 5: Create ECS Task Execution Role
echo ""
echo "👤 Step 5: Setting up IAM roles..."
EXECUTION_ROLE_ARN=$(aws iam get-role --role-name ecsTaskExecutionRole --query 'Role.Arn' --output text 2>/dev/null || echo "")
if [ -z "$EXECUTION_ROLE_ARN" ]; then
  echo "Creating ecsTaskExecutionRole..."
  aws iam create-role \
    --role-name ecsTaskExecutionRole \
    --assume-role-policy-document file://deploy/ecs-task-trust-policy.json \
    --region $AWS_REGION
  
  aws iam attach-role-policy \
    --role-name ecsTaskExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy \
    --region $AWS_REGION
  
  aws iam attach-role-policy \
    --role-name ecsTaskExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite \
    --region $AWS_REGION
  
  EXECUTION_ROLE_ARN=$(aws iam get-role --role-name ecsTaskExecutionRole --query 'Role.Arn' --output text)
fi
echo "✅ Execution Role: $EXECUTION_ROLE_ARN"

# Step 6: Register Task Definition
echo ""
echo "📋 Step 6: Registering ECS task definition..."
cat > deploy/task-definition.json <<EOF
{
  "family": "$ECS_TASK_FAMILY",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "$EXECUTION_ROLE_ARN",
  "containerDefinitions": [
    {
      "name": "syllabus-ai-api",
      "image": "$ECR_REPO_URI:latest",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "APP_VERSION", "value": "1.0.0"},
        {"name": "DEBUG", "value": "false"},
        {"name": "TRANSFORMERS_CACHE", "value": "/app/models"},
        {"name": "HF_HOME", "value": "/app/models"}
      ],
      "secrets": [
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:$AWS_REGION:$AWS_ACCOUNT_ID:secret:syllabus-ai/openai-key"
        },
        {
          "name": "SUPABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:$AWS_REGION:$AWS_ACCOUNT_ID:secret:syllabus-ai/supabase-url"
        },
        {
          "name": "SUPABASE_SERVICE_KEY",
          "valueFrom": "arn:aws:secretsmanager:$AWS_REGION:$AWS_ACCOUNT_ID:secret:syllabus-ai/supabase-key"
        },
        {
          "name": "SARVAM_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:$AWS_REGION:$AWS_ACCOUNT_ID:secret:syllabus-ai/sarvam-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/$ECS_TASK_FAMILY",
          "awslogs-region": "$AWS_REGION",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
EOF

aws ecs register-task-definition \
  --cli-input-json file://deploy/task-definition.json \
  --region $AWS_REGION
echo "✅ Task definition registered"

# Step 7: Create ECS Cluster
echo ""
echo "🏢 Step 7: Creating ECS cluster..."
aws ecs describe-clusters --clusters $ECS_CLUSTER_NAME --region $AWS_REGION 2>/dev/null | \
  grep -q "ACTIVE" || \
  aws ecs create-cluster \
    --cluster-name $ECS_CLUSTER_NAME \
    --region $AWS_REGION
echo "✅ Cluster ready"

# Step 8: Create or Update ECS Service
echo ""
echo "🎯 Step 8: Deploying ECS service..."
if aws ecs describe-services --cluster $ECS_CLUSTER_NAME --services $ECS_SERVICE_NAME --region $AWS_REGION 2>/dev/null | grep -q "ACTIVE"; then
  echo "Updating existing service..."
  aws ecs update-service \
    --cluster $ECS_CLUSTER_NAME \
    --service $ECS_SERVICE_NAME \
    --task-definition $ECS_TASK_FAMILY \
    --force-new-deployment \
    --region $AWS_REGION
else
  echo "Creating new service..."
  if [ -z "$VPC_ID" ] || [ -z "$SUBNET_1" ] || [ -z "$SECURITY_GROUP" ]; then
    echo "⚠️  Please set VPC_ID, SUBNET_1, SUBNET_2, and SECURITY_GROUP at the top of this script"
    echo "Then create the service manually with:"
    echo ""
    echo "aws ecs create-service \\"
    echo "  --cluster $ECS_CLUSTER_NAME \\"
    echo "  --service-name $ECS_SERVICE_NAME \\"
    echo "  --task-definition $ECS_TASK_FAMILY \\"
    echo "  --desired-count 1 \\"
    echo "  --launch-type FARGATE \\"
    echo "  --network-configuration \"awsvpcConfiguration={subnets=[\$SUBNET_1,\$SUBNET_2],securityGroups=[\$SECURITY_GROUP],assignPublicIp=ENABLED}\" \\"
    echo "  --region $AWS_REGION"
    exit 1
  fi
  
  aws ecs create-service \
    --cluster $ECS_CLUSTER_NAME \
    --service-name $ECS_SERVICE_NAME \
    --task-definition $ECS_TASK_FAMILY \
    --desired-count 1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_1,$SUBNET_2],securityGroups=[$SECURITY_GROUP],assignPublicIp=ENABLED}" \
    --region $AWS_REGION
fi
echo "✅ Service deployed"

# Step 9: Configure Auto-Scaling to 0
echo ""
echo "⚖️  Step 9: Configuring auto-scaling..."
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/$ECS_CLUSTER_NAME/$ECS_SERVICE_NAME \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 0 \
  --max-capacity 10 \
  --region $AWS_REGION 2>/dev/null || echo "✅ Scalable target already registered"

# Create scaling policy for scale down
cat > deploy/scale-policy.json <<EOF
{
  "TargetValue": 70.0,
  "PredefinedMetricSpecification": {
    "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
  },
  "ScaleInCooldown": 300,
  "ScaleOutCooldown": 60
}
EOF

aws application-autoscaling put-scaling-policy \
  --policy-name cpu-scaling-policy \
  --service-namespace ecs \
  --resource-id service/$ECS_CLUSTER_NAME/$ECS_SERVICE_NAME \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration file://deploy/scale-policy.json \
  --region $AWS_REGION 2>/dev/null || echo "✅ Scaling policy already exists"

echo ""
echo "✨ Deployment Complete!"
echo ""
echo "📍 Service Details:"
echo "   Cluster: $ECS_CLUSTER_NAME"
echo "   Service: $ECS_SERVICE_NAME"
echo "   Region: $AWS_REGION"
echo ""
echo "📊 View logs:"
echo "   aws logs tail /ecs/$ECS_TASK_FAMILY --follow --region $AWS_REGION"
echo ""
echo "🔍 Get service status:"
echo "   aws ecs describe-services --cluster $ECS_CLUSTER_NAME --services $ECS_SERVICE_NAME --region $AWS_REGION"
echo ""
echo "🌐 Get task public IP:"
echo "   aws ecs list-tasks --cluster $ECS_CLUSTER_NAME --service-name $ECS_SERVICE_NAME --region $AWS_REGION"
echo ""
echo "💰 Cost: ~\$0/month when idle (scales to 0), ~\$15/month if running 24/7"
