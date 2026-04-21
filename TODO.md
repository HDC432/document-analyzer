# Step 2 开工前必须处理

## VITE_API_URL 注入问题

**症状**：Vite 默认只读 `.env` 文件，不读进程环境变量。
`docker-compose.yml` 的 `environment: VITE_API_URL=...` 在容器内不会被 Vite 自动感知。

Step 1 能工作是因为 `api.ts` 有 fallback `'http://localhost:8000'`，且 Step 1 前端没发任何真实请求。

**Step 2 修法**：在 `frontend/Dockerfile` 的 CMD 里先把环境变量写入 `.env`：

```dockerfile
CMD sh -c "echo VITE_API_URL=$VITE_API_URL > .env && npm run dev -- --host"
```

这样容器启动时 Vite 能读到正确的 API URL。
