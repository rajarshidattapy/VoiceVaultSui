# VoiceVault AWS Deployment Plan

This is the active production deployment path. It keeps Sui, Walrus, LiveKit, Murf, and OpenAI as external services, and moves the VoiceVault application runtime to AWS.

## Recommended Architecture

| Layer | AWS service | Purpose |
| --- | --- | --- |
| Frontend | AWS Amplify Hosting | Build and host the React/Vite app from `frontend/` |
| Backend runtime | Amazon ECS on AWS Fargate | Run the FastAPI API, Agent Network MCP server, and LiveKit worker |
| Container registry | Amazon ECR | Store the backend Docker image built from the root `Dockerfile` |
| Public routing | Application Load Balancer | Terminate HTTPS and route public API traffic to the API container |
| Secrets | AWS Secrets Manager | Store API keys and provider secrets outside the container image |
| Persistent runtime state | Amazon EFS | Share `/var/lib/voicevault` between the API, MCP, and worker containers |
| Logs | Amazon CloudWatch Logs | Central logs for API, MCP, and worker containers |
| DNS/TLS | Route 53 and AWS Certificate Manager | Optional custom domains for frontend and backend |

Use one ECS service with one Fargate task at first. That task runs three containers from the same image:

- `voicevault-api`: `python -m uvicorn server:app --host 0.0.0.0 --port 8000`
- `voicevault-mcp`: `python swaraos_mcp_server.py`
- `voicevault-agent-worker`: `python agent_worker.py start`

The API is the only public container. MCP stays private on `127.0.0.1:8001`, and the worker calls MCP and the API over localhost inside the task.

## Why ECS Fargate

VoiceVault is not only a web API. Agent deployment depends on the API, the MCP server, and a long-running LiveKit worker. ECS Fargate maps cleanly to that shape without managing an EC2 host, nginx, certbot, or systemd services. App Runner is simpler for a single web process, but it is a weaker fit for this multi-process runtime and shared agent state.

## Target Repository Layout

AWS-specific files now live under:

```text
deploy/aws/
  README.md
  amplify.yml.example
  ecs-task-definition.example.json
  frontend.env.example
```

Legacy cloud-specific files and guides have been removed.

## Deployment Phases

### 1. Prepare AWS

Create or choose:

- AWS account and deployment region.
- VPC with at least two public subnets for the Application Load Balancer.
- Private subnets for ECS tasks if you have NAT egress. For lower-cost staging, public ECS subnets with a locked-down security group are acceptable.
- ACM certificate for the backend API domain, for example `api.voicevault.example.com`.
- CloudWatch log group, for example `/ecs/voicevault`.
- EFS file system and access point for `/var/lib/voicevault`.
- ECR repository, for example `voicevault-backend`.
- Secrets Manager secret, for example `voicevault/prod`, containing provider keys.

Minimum Secrets Manager keys:

```text
OPENAI_API_KEY
LIVEKIT_API_KEY
LIVEKIT_API_SECRET
MURF_API_KEY
API_SECRET_KEY
```

Optional:

```text
ANTHROPIC_API_KEY
```

### 2. Build and Push Backend Image

From the repo root:

```bash
aws ecr create-repository --repository-name voicevault-backend
aws ecr get-login-password --region REPLACE_REGION | docker login --username AWS --password-stdin REPLACE_ACCOUNT_ID.dkr.ecr.REPLACE_REGION.amazonaws.com
docker build -t voicevault-backend -f Dockerfile .
docker tag voicevault-backend:latest REPLACE_ACCOUNT_ID.dkr.ecr.REPLACE_REGION.amazonaws.com/voicevault-backend:latest
docker push REPLACE_ACCOUNT_ID.dkr.ecr.REPLACE_REGION.amazonaws.com/voicevault-backend:latest
```

Do not bake `.env` files into the image. Runtime configuration should come from ECS environment variables and Secrets Manager.

### 3. Create the Backend ECS Service

Use `deploy/aws/ecs-task-definition.example.json` as the starting point.

Replace placeholders for:

- AWS account ID and region.
- ECR image URI.
- ECS task execution role ARN.
- ECS task role ARN.
- EFS file system ID and access point ID.
- Full Secrets Manager secret ARN. If you store keys in one JSON secret named `voicevault/prod`, use the ARN AWS returns, including its generated suffix, before the `:JSON_KEY::` selector.
- Public backend URL.
- Frontend origin in `CORS_ORIGINS`.

Then create:

1. ECS cluster: `voicevault`.
2. Task definition: `voicevault-backend`.
3. Application Load Balancer target group:
   - Target type: `ip`
   - Protocol: HTTP
   - Port: `8000`
   - Health check path: `/healthz`
4. ECS Fargate service:
   - Desired count: `1`
   - Launch type: Fargate
   - Attach the ALB target group to container `voicevault-api`, port `8000`
   - Use the EFS volume from the task definition

Start with desired count `1`. Scale only after replacing the JSON file stores in `/var/lib/voicevault` with a shared database or a concurrency-safe storage layer.

### 4. Configure Networking

Security groups:

- ALB inbound: `80` and `443` from the internet.
- ALB outbound: to the ECS service security group on `8000`.
- ECS inbound: `8000` only from the ALB security group.
- ECS outbound: HTTPS `443` for Sui RPC, Walrus, LiveKit, OpenAI, Murf, and AWS APIs.
- EFS inbound: `2049` only from the ECS service security group.

Do not expose MCP port `8001` publicly.

### 5. Deploy the Frontend on Amplify

Create an Amplify Hosting app connected to the Git repository.

Use:

- App root: `frontend`
- Build command: `npm run build`
- Output directory: `dist`
- Example build spec: `deploy/aws/amplify.yml.example`

Set frontend environment variables from `deploy/aws/frontend.env.example`, replacing `REPLACE_WITH_BACKEND_HOST` with the backend ALB or API custom domain.

After Amplify gives you a frontend URL, update backend `CORS_ORIGINS` to include that exact origin and redeploy the ECS service.

### 6. Production Environment Values

Backend API container:

```text
PORT=8000
BACKEND_URL=https://REPLACE_WITH_BACKEND_HOST
VOICEVAULT_STORAGE_DIR=/var/lib/voicevault
CORS_ORIGINS=["https://REPLACE_WITH_FRONTEND_HOST","http://localhost:5173"]
CORS_ALLOW_CREDENTIALS=true
LIVEKIT_AGENT_EXTERNAL=true
LIVEKIT_AGENT_MANAGED=false
AGENT_NETWORK_MCP_URL=http://127.0.0.1:8001/sse
MCP_HOST=127.0.0.1
MCP_PORT=8001
```

MCP and worker containers should use:

```text
BACKEND_URL=http://127.0.0.1:8000
VOICEVAULT_STORAGE_DIR=/var/lib/voicevault
```

Frontend:

```text
VITE_API_URL=https://REPLACE_WITH_BACKEND_HOST
VITE_PROXY_URL=https://REPLACE_WITH_BACKEND_HOST
VITE_BACKEND_URL=https://REPLACE_WITH_BACKEND_HOST
VITE_WALRUS_AGGREGATOR_URL=https://REPLACE_WITH_BACKEND_HOST/api/walrus
```

### 7. Verification

Backend checks:

```bash
curl https://REPLACE_WITH_BACKEND_HOST/healthz
curl https://REPLACE_WITH_BACKEND_HOST/docs
```

Frontend checks:

- Open the Amplify URL.
- Connect wallet.
- Load `/marketplace`.
- Upload or register a test voice.
- Deploy an agent.
- Join a LiveKit room and confirm the worker responds.

Operational checks:

- CloudWatch logs contain one stream each for API, MCP, and worker.
- EFS contains `agents.json` and runtime storage under `/var/lib/voicevault`.
- ALB target group shows the ECS task as healthy.
- No inbound rule exposes port `8001`.

## CI/CD Plan

Use this order:

1. Amplify builds frontend automatically from Git pushes to `main`.
2. Backend image is built by GitHub Actions and pushed to ECR.
3. GitHub Actions updates the ECS service with the new task definition image tag.

Use GitHub OIDC for AWS access instead of long-lived AWS keys.

## Migration Checklist

- [ ] Confirm legacy cloud deployment files are removed from the repo.
- [ ] Build backend image without `.env` files.
- [ ] Create ECR repository.
- [ ] Create Secrets Manager secret.
- [ ] Create EFS file system and access point.
- [ ] Register ECS task definition.
- [ ] Create ALB, target group, listener, and ACM certificate.
- [ ] Create ECS service with desired count `1`.
- [ ] Deploy frontend on Amplify.
- [ ] Update backend CORS with Amplify domain.
- [ ] Verify `/healthz`, `/docs`, wallet flows, Walrus upload/download, TTS, and LiveKit agent calls.

## AWS References

- ECS on Fargate: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html
- ECS task definitions: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definitions.html
- ECS with Application Load Balancers: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/alb.html
- ECS Secrets Manager integration: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/secrets-envvar-secrets-manager.html
- ECS EFS volumes: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/efs-volumes.html
- ECR image push flow: https://docs.aws.amazon.com/AmazonECR/latest/userguide/docker-push-ecr-image.html
- Amplify build settings: https://docs.aws.amazon.com/amplify/latest/userguide/build-settings.html
- Amplify environment variables: https://docs.aws.amazon.com/amplify/latest/userguide/environment-variables.html
