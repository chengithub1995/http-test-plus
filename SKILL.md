---
name: http-test-plus
description: 测试和调试 JSON HTTP 接口，支持单请求和批量 YAML 执行，包括鉴权请求头、查询参数、变量提取、串联请求和期望状态码负例校验。适用于登录鉴权、多步骤 CRUD 流程、复杂模块联调，以及需要默认生成完整中文测试报告的 HTTP 调试任务。
---

# HTTP Test Plus

## Overview

使用这个 skill 测试 JSON HTTP 接口，既支持单请求，也支持批量 YAML 用例。
当用户需要登录取 token、变量传递、串联请求、正负例混合验证或完整中文测试报告时，优先使用批量模式。

## Workflow

1. 单个接口调试时使用单请求模式。
2. 登录鉴权、依赖串联、完整流程验证时使用批量模式。
3. 直接执行 Python 脚本：

```bash
python .codex/skills/http-test-plus/scripts/http_client.py --url "https://api.example.com/items" --method "GET" --headers '{}' --auth-header '{}' --query '{}' --body '{}' --timeout 30
python .codex/skills/http-test-plus/scripts/http_client.py --batch "demo/agent_platform/suites/agent_happy_path.yml" --timeout 30
```

4. 脚本默认在当前目录生成完整 Markdown 测试报告；只有用户明确要求时才改到其他目录。
5. 无论用户是否要求，都返回中文结论和报告路径。
6. 不主动把完整报告内容贴回对话，除非用户明确要求查看报告。

## Parameters

- `URL`: 单请求模式的目标地址
- `METHOD`: HTTP 方法，默认 `GET`
- `HEADERS`: 单次请求自定义请求头，JSON 格式
- `AUTH_HEADER`: 单请求公共鉴权头，JSON 格式
- `QUERY`: 单请求查询参数，JSON 格式
- `BODY`: `POST`/`PUT`/`PATCH` 请求体，JSON 格式
- `BATCH`: 批量 YAML 用例路径
- `TIMEOUT`: 超时时间，默认 `30`
- `REPORT_DIR`: 可选，报告输出目录；未指定时默认当前目录

## Batch Rules

- 共享静态请求头放在 `config.auth_header`。
- 动态 token 放在 `request.headers`，通过 `${tests.step_name.extracted_key}` 引用。
- 批量查询参数使用 `request.query`。
- 使用 `extract` 和 JMESPath 提取 ID、token 等供后续步骤复用。
- 负例用 `expected_status` 声明命中的期望状态码。
- 单请求和批量模式都会写出完整 Markdown 中文测试报告。
- 报告默认不展示技术 `id`，而是展示中文标题。
- 报告包含原始请求 URL、明文请求头、查询参数、请求体、响应头、响应体和最终结论。

## 中文要求

- 生成给用户看的报告、终端结论和说明时，默认全部使用中文。
- 后续由 skill 生成的 YAML，用例标题、描述、注释和示例文案默认使用中文。
- YAML 内部技术 `id` 保持可引用即可，但不要在报告中展示给用户。

## References

- 编写或修改批量用例前，先读 [references/batch-yaml.md](references/batch-yaml.md)。
- 验证内置 AI 智能体平台 demo 时，先读 [references/agent-platform-demo.md](references/agent-platform-demo.md)。
- 向用户解释报告输出行为前，先读 [references/report-artifacts.md](references/report-artifacts.md)。
- 如果当前终端或 会话没有识别新建 skill，提示用户重启终端或会话后再试 `/http-test-plus`。
