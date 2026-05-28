# AI 智能体平台示例

内置 demo 服务位于 `demo/agent_platform/`。

## 启动方式

```bash
pip install -r demo/agent_platform/requirements.txt
python -m uvicorn demo.agent_platform.app:app --host 127.0.0.1 --port 8000
```

## 示例账号

- `creator / demo123`
- `reviewer / demo123`
- `admin / demo123`

## 必需请求头

每个 demo 请求都需要：

```json
{"X-Client-Key":"demo-client-key"}
```

静态客户端标识放在 `config.auth_header`。
动态 Bearer token 放在每个步骤的 `headers` 中。

## 主流程

1. 使用 `creator` 登录
2. 创建知识库
3. 使用 `request.query` 查询知识库
4. 创建智能体
5. 更新智能体字段和运行配置
6. 绑定知识库
7. 提交审核
8. 使用 `reviewer` 登录并审批
9. 使用 `admin` 登录并发布
10. 使用 `request.query` 查询已发布智能体
11. 下架并删除

## 用例路径

- 成功路径：`demo/agent_platform/suites/agent_happy_path.yml`
- 负例路径：`demo/agent_platform/suites/agent_negative_cases.yml`

## 报告输出

- 每次执行都会生成完整 Markdown 报告。
- 默认输出到当前目录；如需其他目录，显式传 `--report-dir`。
- 终端输出保持精简，只返回中文结论和报告路径。
