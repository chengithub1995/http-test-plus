# 批量 YAML

当用户需要多步骤 HTTP 验证时使用批量模式，例如登录、提取 token、传递 ID、串联 CRUD 操作或执行负例验证。

## 基本结构

```yaml
config:
  base_url: "http://127.0.0.1:8000"
  stop_on_error: true
  auth_header:
    X-Client-Key: "demo-client-key"

tests:
  - id: login
    description: "登录并提取 token"
    request:
      method: POST
      url: "/auth/login"
      body:
        username: "creator"
        password: "demo123"
    extract:
      token: "data.token"

  - id: list_agents
    description: "查询已发布智能体"
    request:
      method: GET
      url: "/agents"
      headers:
        Authorization: "Bearer ${tests.login.token}"
      query:
        keyword: "平台"
        publish_status: "online"
        page: 1
        page_size: 10
```

## 规则

- 执行顺序严格按 YAML 顺序。
- 使用 `${config.xxx}` 读取 `config` 配置。
- 使用 `${tests.step_id.key}` 读取前序步骤提取的数据。
- `request.query` 必须是 JSON 对象。
- `expected_status` 可以是单个整数，也可以是整数数组。
- 运行结束后，脚本默认在当前目录生成一份完整 Markdown 报告；如需其他目录，显式传 `--report-dir`。
- 终端只输出最终结论、统计信息和报告路径。
- 批量步骤满足以下任一条件时视为通过：
  - 请求成功并返回 `2xx`
  - 响应状态码命中 `expected_status`
- 响应命中期望状态码且响应体是有效 JSON 时，才执行数据提取。
- 生成面向用户查看的 YAML 时，`description`、注释、示例说明默认使用中文。

## 负例示例

```yaml
- id: creator_publish_denied
  description: "创建者不能直接发布"
  expected_status: 403
  request:
    method: POST
    url: "/agents/${tests.create_agent.agent_id}/publish"
    headers:
      X-Client-Key: "demo-client-key"
      Authorization: "Bearer ${tests.creator_login.token}"
```
