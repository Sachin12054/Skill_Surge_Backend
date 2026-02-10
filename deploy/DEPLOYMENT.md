# Syllabus.ai Backend - Production Deployment Guide

## Overview
Deploy Syllabus.ai backend with serverless architecture to AWS Fargate or Google Cloud Run.
- **Pay-per-request pricing**: No charges when idle
- **Auto-scaling**: Scales to 0 instances when not in use
- **Model caching**: Pre-downloads ML models in Docker image (no repeated downloads)

---

## Prerequisites

### 1. Build Production Docker Image
```bash
cd backend

# Build with model pre-loaded
docker build -f Dockerfile.prod -t syllabus-ai-backend:latest .

# Test locally
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=your_key \
  -e SUPABASE_URL=your_url \
  -e SUPABASE_SERVICE_KEY=your_key \
  -e SARVAM_API_KEY=your_key \
  syllabus-ai-backend:latest
```

### 2. Set Up Environment Variables
Create secrets in your cloud provider for:
- `OPENAI_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `SARVAM_API_KEY`

---

## Option A: AWS Fargate (Recommended for AWS-native)

### Step 1: Push Image to ECR
```bash
# Authenticate Docker to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Create ECR repository
aws ecr create-repository --repository-name syllabus-ai-backend --region us-east-1

# Tag and push
docker tag syllabus-ai-backend:latest \
  YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/syllabus-ai-backend:latest

docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/syllabus-ai-backend:latest
```

### Step 2: Store Secrets in AWS Secrets Manager
```bash
aws secretsmanager create-secret \
  --name syllabus-ai/openai-key \
  --secret-string "your_openai_key" \
  --region us-east-1

aws secretsmanager create-secret \
  --name syllabus-ai/supabase-url \
  --secret-string "your_supabase_url" \
  --region us-east-1

aws secretsmanager create-secret \
  --name syllabus-ai/supabase-key \
  --secret-string "your_supabase_service_key" \
  --region us-east-1

aws secretsmanager create-secret \
  --name syllabus-ai/sarvam-key \
  --secret-string "your_sarvam_key" \
  --region us-east-1
```

### Step 3: Create ECS Task Definition
```bash
# Update deploy/aws-fargate.yaml with your account details
# Then register the task definition
aws ecs register-task-definition \
  --cli-input-json file://deploy/aws-fargate.yaml \
  --region us-east-1
```

### Step 4: Create ECS Service with Auto-Scaling
```bash
# Create ECS cluster
aws ecs create-cluster --cluster-name syllabus-ai-cluster --region us-east-1

# Create service (requires VPC, subnets, security groups)
aws ecs create-service \
  --cluster syllabus-ai-cluster \
  --service-name syllabus-ai-backend \
  --task-definition syllabus-ai-backend \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-xxx],assignPublicIp=ENABLED}" \
  --region us-east-1

# Set up auto-scaling to scale to 0 when idle
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/syllabus-ai-cluster/syllabus-ai-backend \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 0 \
  --max-capacity 10 \
  --region us-east-1

# Scale down to 0 after 5 minutes of no requests
aws application-autoscaling put-scaling-policy \
  --policy-name scale-down-policy \
  --service-namespace ecs \
  --resource-id service/syllabus-ai-cluster/syllabus-ai-backend \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration file://scale-down-policy.json \
  --region us-east-1
```

### Step 5: Configure Application Load Balancer (Optional)
```bash
# Create ALB to expose service
aws elbv2 create-load-balancer \
  --name syllabus-ai-alb \
  --subnets subnet-xxx subnet-yyy \
  --security-groups sg-xxx \
  --region us-east-1

# Create target group and listener
# Update ECS service to use ALB
```

### Cost Estimation (AWS Fargate)
- **Idle (0 tasks)**: $0/month
- **Active (1 task @ 0.5 vCPU, 1GB RAM)**: ~$15/month if running 24/7
- **With auto-scaling to 0**: ~$5-10/month for typical usage
- **Data transfer**: $0.09/GB outbound

---

## Option B: Google Cloud Run (Simpler, recommended for beginners)

### Step 1: Push Image to Google Container Registry
```bash
# Authenticate Docker to GCR
gcloud auth configure-docker

# Tag and push
docker tag syllabus-ai-backend:latest gcr.io/YOUR_PROJECT_ID/syllabus-ai-backend:latest
docker push gcr.io/YOUR_PROJECT_ID/syllabus-ai-backend:latest
```

### Step 2: Store Secrets in Secret Manager
```bash
echo -n "your_openai_key" | gcloud secrets create openai-api-key --data-file=-
echo -n "your_supabase_url" | gcloud secrets create supabase-url --data-file=-
echo -n "your_supabase_service_key" | gcloud secrets create supabase-service-key --data-file=-
echo -n "your_sarvam_key" | gcloud secrets create sarvam-api-key --data-file=-
```

### Step 3: Deploy to Cloud Run
```bash
# Update deploy/cloud-run.yaml with your project ID
gcloud run services replace deploy/cloud-run.yaml \
  --region us-central1 \
  --platform managed

# Or deploy directly via CLI
gcloud run deploy syllabus-ai-backend \
  --image gcr.io/YOUR_PROJECT_ID/syllabus-ai-backend:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 2 \
  --timeout 300 \
  --min-instances 0 \
  --max-instances 10 \
  --set-env-vars "APP_VERSION=1.0.0,DEBUG=false,TRANSFORMERS_CACHE=/app/models" \
  --set-secrets "OPENAI_API_KEY=openai-api-key:latest,SUPABASE_URL=supabase-url:latest,SUPABASE_SERVICE_KEY=supabase-service-key:latest,SARVAM_API_KEY=sarvam-api-key:latest"
```

### Cost Estimation (Google Cloud Run)
- **Idle (0 instances)**: $0/month
- **Active requests**: $0.00002400 per vCPU-second, $0.00000250 per GiB-second
- **Typical usage (1000 requests/day, 10s avg)**: ~$5-8/month
- **1M free requests per month**

---

## Model Caching Details

### How It Works
1. **Build Time**: Dockerfile pre-downloads the `all-MiniLM-L6-v2` model (138MB) into `/app/models`
2. **Startup**: FastAPI lifespan event warms up the model on container start
3. **Runtime**: Model stays in memory, reused across requests (singleton pattern)
4. **Cost Savings**: No repeated downloads, faster responses (no 2-3s model load per request)

### Model Storage
- **Location**: `/app/models` inside container
- **Size**: ~150MB for sentence-transformers model
- **Cache reuse**: Shared across all requests to the same container instance

---

## Testing

### Local Test
```bash
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=test \
  -e SUPABASE_URL=test \
  -e SUPABASE_SERVICE_KEY=test \
  -e SARVAM_API_KEY=test \
  syllabus-ai-backend:latest

curl http://localhost:8000/health
```

### Production Test
```bash
# AWS Fargate
curl https://your-alb-url.amazonaws.com/health

# Google Cloud Run
curl https://syllabus-ai-backend-xxx-uc.a.run.app/health
```

---

## Monitoring

### AWS CloudWatch
```bash
# View logs
aws logs tail /ecs/syllabus-ai-backend --follow --region us-east-1

# View metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=syllabus-ai-backend \
  --start-time 2025-01-01T00:00:00Z \
  --end-time 2025-01-02T00:00:00Z \
  --period 3600 \
  --statistics Average
```

### Google Cloud Logs
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=syllabus-ai-backend" --limit 50

gcloud monitoring dashboards list
```

---

## Update Mobile App Backend URL

After deployment, update the backend URL in your mobile app:

```typescript
// mobile-app/constants/api.ts
export const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 
  'https://your-cloud-run-url.run.app';  // Update this
```

---

## Next Steps

1. ✅ Model caching implemented
2. ✅ Production Dockerfile created
3. ✅ Startup model warming added
4. ✅ Deployment configs created
5. 🔄 Choose cloud provider (AWS Fargate or Google Cloud Run)
6. 🔄 Build and push Docker image
7. 🔄 Configure secrets
8. 🔄 Deploy service
9. 🔄 Update mobile app with production URL
10. 🔄 Test end-to-end

---

## Troubleshooting

### Cold Start Delays
- **Issue**: First request takes 10-15 seconds
- **Solution**: Model is warmed up on container start, subsequent requests are fast
- **Alternative**: Set `min-instances=1` to keep one instance always warm (costs ~$15/month)

### Out of Memory
- **Issue**: Container OOM during model loading
- **Solution**: Increase memory to 2GB in task definition/Cloud Run config

### Model Download Failures
- **Issue**: Model not found in cache
- **Solution**: Verify Dockerfile multi-stage build copied model correctly
- **Debug**: Add `ls -la /app/models` to startup logs
