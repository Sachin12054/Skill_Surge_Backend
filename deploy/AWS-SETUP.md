# AWS Deployment Setup for Syllabus.ai Backend

## Quick Start (Fully Automated)

```bash
cd backend/deploy
chmod +x aws-deploy.sh
./aws-deploy.sh
```

The script will:
1. ✅ Create ECR repository
2. ✅ Build Docker image with pre-cached model
3. ✅ Push to ECR
4. ✅ Setup IAM roles and CloudWatch logs
5. ✅ Register ECS task definition
6. ✅ Create ECS cluster
7. ✅ Deploy Fargate service
8. ✅ Configure auto-scaling (0-10 instances)

---

## Prerequisites

### 1. Install AWS CLI
```bash
# Windows (PowerShell)
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi

# Verify
aws --version
```

### 2. Configure AWS Credentials
```bash
aws configure
# AWS Access Key ID: YOUR_ACCESS_KEY
# AWS Secret Access Key: YOUR_SECRET_KEY
# Default region: us-east-1
# Default output format: json
```

### 3. Install Docker Desktop
Download from: https://www.docker.com/products/docker-desktop

---

## Step-by-Step Setup

### Step 1: Create Secrets in AWS Secrets Manager

```bash
# OpenAI API Key
aws secretsmanager create-secret \
  --name syllabus-ai/openai-key \
  --description "OpenAI API key for podcast generation" \
  --secret-string "sk-..." \
  --region us-east-1

# Supabase URL
aws secretsmanager create-secret \
  --name syllabus-ai/supabase-url \
  --description "Supabase project URL" \
  --secret-string "https://xxx.supabase.co" \
  --region us-east-1

# Supabase Service Key
aws secretsmanager create-secret \
  --name syllabus-ai/supabase-key \
  --description "Supabase service role key" \
  --secret-string "eyJ..." \
  --region us-east-1

# Sarvam AI API Key
aws secretsmanager create-secret \
  --name syllabus-ai/sarvam-key \
  --description "Sarvam AI TTS API key" \
  --secret-string "..." \
  --region us-east-1
```

### Step 2: Create VPC and Security Group (if needed)

```bash
# Create VPC
VPC_ID=$(aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=syllabus-ai-vpc}]' \
  --query 'Vpc.VpcId' --output text --region us-east-1)

# Create Internet Gateway
IGW_ID=$(aws ec2 create-internet-gateway \
  --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=syllabus-ai-igw}]' \
  --query 'InternetGateway.InternetGatewayId' --output text --region us-east-1)

aws ec2 attach-internet-gateway \
  --vpc-id $VPC_ID \
  --internet-gateway-id $IGW_ID \
  --region us-east-1

# Create public subnets in different AZs
SUBNET_1=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.1.0/24 \
  --availability-zone us-east-1a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=syllabus-ai-subnet-1}]' \
  --query 'Subnet.SubnetId' --output text --region us-east-1)

SUBNET_2=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.2.0/24 \
  --availability-zone us-east-1b \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=syllabus-ai-subnet-2}]' \
  --query 'Subnet.SubnetId' --output text --region us-east-1)

# Create route table and associate with subnets
ROUTE_TABLE=$(aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=syllabus-ai-rt}]' \
  --query 'RouteTable.RouteTableId' --output text --region us-east-1)

aws ec2 create-route \
  --route-table-id $ROUTE_TABLE \
  --destination-cidr-block 0.0.0.0/0 \
  --gateway-id $IGW_ID \
  --region us-east-1

aws ec2 associate-route-table \
  --route-table-id $ROUTE_TABLE \
  --subnet-id $SUBNET_1 \
  --region us-east-1

aws ec2 associate-route-table \
  --route-table-id $ROUTE_TABLE \
  --subnet-id $SUBNET_2 \
  --region us-east-1

# Create security group (allow port 8000)
SECURITY_GROUP=$(aws ec2 create-security-group \
  --group-name syllabus-ai-sg \
  --description "Security group for Syllabus.ai backend" \
  --vpc-id $VPC_ID \
  --query 'GroupId' --output text --region us-east-1)

aws ec2 authorize-security-group-ingress \
  --group-id $SECURITY_GROUP \
  --protocol tcp \
  --port 8000 \
  --cidr 0.0.0.0/0 \
  --region us-east-1

echo "VPC_ID=$VPC_ID"
echo "SUBNET_1=$SUBNET_1"
echo "SUBNET_2=$SUBNET_2"
echo "SECURITY_GROUP=$SECURITY_GROUP"
```

**Save these IDs!** You'll need them in the deployment script.

### Step 3: Update Deployment Script

Edit `aws-deploy.sh` and set:
```bash
VPC_ID="vpc-xxxxx"
SUBNET_1="subnet-xxxxx"
SUBNET_2="subnet-yyyyy"
SECURITY_GROUP="sg-xxxxx"
```

### Step 4: Run Deployment

```bash
cd backend/deploy
chmod +x aws-deploy.sh
./aws-deploy.sh
```

---

## Getting the Backend URL

### Option A: Use Task Public IP (Simple)
```bash
# Get task ARN
TASK_ARN=$(aws ecs list-tasks \
  --cluster syllabus-ai-cluster \
  --service-name syllabus-ai-backend \
  --query 'taskArns[0]' --output text --region us-east-1)

# Get task details
aws ecs describe-tasks \
  --cluster syllabus-ai-cluster \
  --tasks $TASK_ARN \
  --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' \
  --output text --region us-east-1

# Get ENI public IP
ENI=$(aws ecs describe-tasks \
  --cluster syllabus-ai-cluster \
  --tasks $TASK_ARN \
  --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' \
  --output text --region us-east-1)

PUBLIC_IP=$(aws ec2 describe-network-interfaces \
  --network-interface-ids $ENI \
  --query 'NetworkInterfaces[0].Association.PublicIp' \
  --output text --region us-east-1)

echo "Backend URL: http://$PUBLIC_IP:8000"
```

### Option B: Add Application Load Balancer (Production)

```bash
# Create ALB
ALB_ARN=$(aws elbv2 create-load-balancer \
  --name syllabus-ai-alb \
  --subnets $SUBNET_1 $SUBNET_2 \
  --security-groups $SECURITY_GROUP \
  --scheme internet-facing \
  --query 'LoadBalancers[0].LoadBalancerArn' --output text --region us-east-1)

# Get ALB DNS
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --load-balancer-arns $ALB_ARN \
  --query 'LoadBalancers[0].DNSName' --output text --region us-east-1)

# Create target group
TG_ARN=$(aws elbv2 create-target-group \
  --name syllabus-ai-tg \
  --protocol HTTP \
  --port 8000 \
  --vpc-id $VPC_ID \
  --target-type ip \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --query 'TargetGroups[0].TargetGroupArn' --output text --region us-east-1)

# Create listener
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=$TG_ARN \
  --region us-east-1

# Update ECS service to use ALB
aws ecs update-service \
  --cluster syllabus-ai-cluster \
  --service syllabus-ai-backend \
  --load-balancers targetGroupArn=$TG_ARN,containerName=syllabus-ai-api,containerPort=8000 \
  --region us-east-1

echo "Backend URL: http://$ALB_DNS"
```

---

## Update Mobile App

Edit `mobile-app/constants/api.ts`:
```typescript
export const API_BASE_URL = 'http://YOUR_ALB_DNS_OR_PUBLIC_IP:8000';
```

Or for Windows local development (PowerShell):
```typescript
export const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 
  'http://YOUR_PUBLIC_IP:8000';
```

---

## Monitoring & Management

### View Logs
```bash
aws logs tail /ecs/syllabus-ai-backend --follow --region us-east-1
```

### Check Service Status
```bash
aws ecs describe-services \
  --cluster syllabus-ai-cluster \
  --services syllabus-ai-backend \
  --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount}' \
  --region us-east-1
```

### Scale Service Manually
```bash
# Scale up
aws ecs update-service \
  --cluster syllabus-ai-cluster \
  --service syllabus-ai-backend \
  --desired-count 2 \
  --region us-east-1

# Scale down to 0 (stop all tasks)
aws ecs update-service \
  --cluster syllabus-ai-cluster \
  --service syllabus-ai-backend \
  --desired-count 0 \
  --region us-east-1
```

### Update Application
```bash
# Rebuild and push new image
cd backend
docker build -f Dockerfile.prod -t syllabus-ai-backend:latest .
docker tag syllabus-ai-backend:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/syllabus-ai-backend:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/syllabus-ai-backend:latest

# Force new deployment
aws ecs update-service \
  --cluster syllabus-ai-cluster \
  --service syllabus-ai-backend \
  --force-new-deployment \
  --region us-east-1
```

---

## Cost Optimization

### Auto-Scaling Configuration
- **Min instances**: 0 (scales down when idle)
- **Max instances**: 10 (scales up under load)
- **Scale-in cooldown**: 300s (waits 5min before scaling down)
- **Scale-out cooldown**: 60s (scales up quickly)

### Cost Breakdown
- **Idle (0 tasks)**: $0/month
- **1 task running 24/7**: ~$15/month
  - CPU: 0.5 vCPU × $0.04048/hour = ~$14.57/month
  - Memory: 1GB × $0.004445/GB/hour = ~$3.20/month
- **With auto-scaling**: $5-10/month typical usage

### Additional Costs
- **ECR storage**: $0.10/GB/month (~$0.02 for 150MB image)
- **Data transfer**: $0.09/GB outbound after first 100GB/month
- **CloudWatch logs**: $0.50/GB ingested, $0.03/GB stored

---

## Troubleshooting

### Task fails to start
```bash
# Check task stopped reason
aws ecs describe-tasks \
  --cluster syllabus-ai-cluster \
  --tasks TASK_ARN \
  --query 'tasks[0].stoppedReason' \
  --region us-east-1

# Check logs
aws logs tail /ecs/syllabus-ai-backend --since 1h --region us-east-1
```

### Health check failing
```bash
# SSH into task (requires AWS Systems Manager Session Manager)
# Or check logs for health check errors
aws logs filter-pattern "health" --log-group-name /ecs/syllabus-ai-backend --region us-east-1
```

### Secrets not accessible
```bash
# Verify IAM role has SecretsManager permissions
aws iam list-attached-role-policies --role-name ecsTaskExecutionRole

# Test secret access
aws secretsmanager get-secret-value --secret-id syllabus-ai/openai-key --region us-east-1
```

### Model not loading
```bash
# Increase memory in task definition
# Edit task-definition.json: "memory": "2048"
# Re-register: aws ecs register-task-definition --cli-input-json file://task-definition.json
```

---

## Next Steps

1. ✅ Deploy to AWS Fargate
2. ⏭️ Add custom domain with Route 53
3. ⏭️ Setup SSL with ACM (AWS Certificate Manager)
4. ⏭️ Configure WAF for security
5. ⏭️ Setup CloudFront CDN for audio files
6. ⏭️ Migrate to AWS Bedrock (Claude 3.5)
7. ⏭️ Migrate to Amazon Polly or ElevenLabs TTS
