# VoiceVault AWS Deployment Assets

These files support the AWS deployment plan in `docs/AWS_DEPLOYMENT_PLAN.md`.

| File | Purpose |
| --- | --- |
| `ecs-task-definition.example.json` | Starting point for the ECS Fargate task running API, MCP, and worker containers |
| `amplify.yml.example` | Amplify Hosting build spec for the `frontend/` Vite app |
| `frontend.env.example` | Frontend environment variables for Amplify |

Replace all `REPLACE_*` placeholders before using these files in AWS.
