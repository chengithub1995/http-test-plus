#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP客户端工具
用于执行HTTP请求、生成完整测试报告并返回中文结论
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode, urlparse

import requests


def parse_json_param(param, default=None):
    """解析JSON参数"""
    if not param or param == "null":
        return default or {}
    try:
        return json.loads(param)
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}", file=sys.stderr)
        return default or {}


def merge_headers(base_headers, auth_header, custom_headers):
    """合并请求头，优先级：custom > auth > base"""
    headers = base_headers.copy()
    headers.update(auth_header)
    headers.update(custom_headers)
    return headers


def build_url(base_url, query_params):
    """构建完整URL"""
    if not query_params:
        return base_url

    parsed = urlparse(base_url)
    if parsed.query:
        return f"{base_url}&{urlencode(query_params)}"
    return f"{base_url}?{urlencode(query_params)}"


def format_body(body, content_type=""):
    """格式化请求/响应体"""
    if body is None or body == "":
        return ""

    if "json" in content_type.lower() or (isinstance(body, str) and body.strip().startswith(("{", "["))):
        try:
            if isinstance(body, str):
                data = json.loads(body)
            else:
                data = body
            return json.dumps(data, ensure_ascii=False, indent=4)
        except Exception:
            pass

    return str(body)


def normalize_expected_status(expected_status):
    """标准化 expected_status 配置"""
    if expected_status is None:
        return None

    items = expected_status if isinstance(expected_status, list) else [expected_status]
    normalized = []

    for item in items:
        if isinstance(item, bool):
            raise ValueError("expected_status 不能是布尔值")
        if isinstance(item, int):
            normalized.append(item)
            continue
        if isinstance(item, str) and item.isdigit():
            normalized.append(int(item))
            continue
        raise ValueError(f"expected_status 包含无效值: {item}")

    return sorted(set(normalized))


def is_expected_response(response_info, expected_statuses=None):
    """判断响应是否符合期望"""
    if not response_info.get("success", False):
        return False

    status_code = response_info.get("status_code", 500)
    if expected_statuses:
        return status_code in expected_statuses
    return 200 <= status_code < 300


def execute_request(url, method, headers, body=None, timeout=30):
    """执行HTTP请求"""
    start_time = time.time()

    try:
        response = requests.request(
            method=method.upper(),
            url=url,
            headers=headers,
            json=body if body else None,
            timeout=timeout,
        )

        elapsed_time = int((time.time() - start_time) * 1000)

        return {
            "success": True,
            "status_code": response.status_code,
            "status_text": response.reason,
            "headers": dict(response.headers),
            "body": response.text,
            "elapsed_time": elapsed_time,
            "url": response.url,
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "请求超时",
            "message": f"请求超过{timeout}秒未响应",
        }

    except requests.exceptions.ConnectionError as e:
        return {
            "success": False,
            "error": "连接错误",
            "message": str(e),
        }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": "请求异常",
            "message": str(e),
        }


def substitute_variables(data, context, jmespath_module):
    """递归替换 ${...} 变量"""
    if isinstance(data, dict):
        return {k: substitute_variables(v, context, jmespath_module) for k, v in data.items()}
    if isinstance(data, list):
        return [substitute_variables(i, context, jmespath_module) for i in data]
    if isinstance(data, str):
        for match in re.finditer(r"\$\{(.+?)\}", data):
            placeholder = match.group(0)
            path = match.group(1)
            try:
                value = jmespath_module.search(path, context)
                if value is not None:
                    if data == placeholder:
                        return value
                    data = data.replace(placeholder, str(value))
            except jmespath_module.exceptions.JMESPathError as e:
                raise ValueError(f"数据提取表达式 '{path}' 无效: {e}") from e
            except Exception as e:
                raise ValueError(f"替换变量 '{path}' 时出错: {e}") from e
        return data
    return data


def build_request_info(method, url, headers, query=None, body=None):
    """构建请求信息"""
    return {
        "method": method,
        "url": url,
        "headers": headers,
        "query": query or {},
        "body": body,
    }


def build_result_entry(
    step_id,
    description,
    request_info,
    response_info,
    success,
    expected_statuses=None,
    extracted_data=None,
    notes=None,
):
    """构建统一结果"""
    return {
        "id": step_id,
        "description": description,
        "success": success,
        "expected_statuses": expected_statuses,
        "request": request_info,
        "response": response_info,
        "extracted_data": extracted_data or {},
        "notes": notes or [],
    }


def create_run_result(mode, source, results, terminated_early=False, stop_on_error=None, unexecuted_tests=None, run_error=None):
    """构建统一运行结果"""
    passed = sum(1 for result in results if result["success"])
    failed = len(results) - passed
    overall_success = failed == 0 and run_error is None

    return {
        "mode": mode,
        "source": source,
        "results": results,
        "terminated_early": terminated_early,
        "stop_on_error": stop_on_error,
        "unexecuted_tests": unexecuted_tests or [],
        "run_error": run_error,
        "passed": passed,
        "failed": failed,
        "total": len(results),
        "overall_success": overall_success,
    }


def display_mode(mode):
    """显示执行模式"""
    if mode == "batch":
        return "批量"
    return "单请求"


def display_result(success):
    """显示执行结果"""
    return "通过" if success else "失败"


def default_case_title(index):
    """默认用例标题"""
    return f"第{index}个请求"


def serialize_for_block(value, content_type=""):
    """序列化为报告代码块内容"""
    if value is None or value == "" or value == {} or value == []:
        return "(无)"

    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=4)

    formatted = format_body(value, content_type)
    if formatted == "":
        return "(无)"

    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith(("{", "[")):
            try:
                parsed = json.loads(value)
                return json.dumps(parsed, ensure_ascii=False, indent=4)
            except json.JSONDecodeError:
                pass

    return formatted


def render_code_block(value, content_type=""):
    """渲染Markdown代码块"""
    text = serialize_for_block(value, content_type)
    return f"```\n{text}\n```"


def render_case_markdown(index, result):
    """渲染单条请求结果"""
    response = result["response"]
    request = result["request"]
    title = result.get("description") or default_case_title(index)
    expected_statuses = result.get("expected_statuses")
    expected_display = (
        "默认成功状态码（2xx）"
        if not expected_statuses
        else "、".join(str(code) for code in expected_statuses)
    )
    status_code = response.get("status_code")
    final_url = response.get("url", request.get("url", ""))
    content_type = response.get("headers", {}).get("Content-Type", "") if response.get("success") else ""
    status_display = status_code if status_code is not None else "无"

    lines = [
        f"## {index}. {title}",
        "",
        f"- 结果: {display_result(result['success'])}",
        f"- 期望状态码: {expected_display}",
        f"- 实际状态码: {status_display}",
        f"- 响应时间: {response.get('elapsed_time', '无')}毫秒",
        f"- 最终响应地址: {final_url or '(无)'}",
        "",
        "### 请求信息",
        "",
        f"- 请求方法: {request.get('method', '(无)')}",
        f"- 请求地址: {request.get('url', '(无)')}",
        "",
        "#### 请求头",
        "",
        render_code_block(request.get("headers", {}), "application/json"),
        "",
        "#### 查询参数",
        "",
        render_code_block(request.get("query", {}), "application/json"),
        "",
        "#### 请求体",
        "",
        render_code_block(request.get("body"), "application/json"),
        "",
        "### 响应信息",
        "",
    ]

    if response.get("success"):
        lines.extend(
            [
                f"- 状态码: {status_display}",
                f"- 内容类型: {content_type or '未知'}",
                "",
                "#### 响应头",
                "",
                render_code_block(response.get("headers", {}), "application/json"),
                "",
                "#### 响应体",
                "",
                render_code_block(response.get("body"), content_type),
            ]
        )
    else:
        lines.extend(
            [
                f"- 错误类型: {response.get('error', '未知错误')}",
                f"- 错误详情: {response.get('message', '(无)')}",
            ]
        )

    if result.get("extracted_data"):
        lines.extend(
            [
                "",
                "### 提取结果",
                "",
                render_code_block(result["extracted_data"], "application/json"),
            ]
        )

    if result.get("notes"):
        lines.extend(["", "### 备注", ""])
        lines.extend([f"- {note}" for note in result["notes"]])

    lines.append("")
    return "\n".join(lines)


def render_markdown_report(run_result):
    """渲染完整Markdown测试报告"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# 接口测试报告",
        "",
        f"- 生成时间: {timestamp}",
        f"- 执行模式: {display_mode(run_result['mode'])}",
        f"- 最终结论: {display_result(run_result['overall_success'])}",
        f"- 总请求数: {run_result['total']}",
        f"- 通过数: {run_result['passed']}",
        f"- 失败数: {run_result['failed']}",
    ]

    if run_result["mode"] == "batch":
        lines.extend(
            [
                f"- 失败即停止: {'是' if run_result['stop_on_error'] else '否'}",
                f"- 是否提前终止: {'是' if run_result['terminated_early'] else '否'}",
            ]
        )

    lines.extend(["", "## 最终结论", ""])

    if run_result["run_error"]:
        lines.append(f"- 运行错误: {run_result['run_error']}")
    else:
        lines.append(f"- 执行结果: {'全部通过' if run_result['overall_success'] else '存在失败'}")

    if run_result["mode"] == "batch" and run_result["unexecuted_tests"]:
        lines.extend(["", "## 未执行步骤", ""])
        lines.extend(
            [
                f"- {item.get('description') or default_case_title(index + 1)}"
                for index, item in enumerate(run_result["unexecuted_tests"])
            ]
        )

    lines.extend(["", "## 请求详情", ""])

    if not run_result["results"]:
        lines.extend(["- 本次运行未产生请求记录。", ""])
        return "\n".join(lines)

    for index, result in enumerate(run_result["results"], start=1):
        lines.append(render_case_markdown(index, result))

    return "\n".join(lines).rstrip() + "\n"


def write_report(run_result, report_dir=None):
    """写入Markdown测试报告"""
    target_dir = Path(report_dir).expanduser() if report_dir else Path.cwd()
    target_dir = target_dir.resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]
    mode_label = display_mode(run_result["mode"])
    result_label = display_result(run_result["overall_success"])
    report_path = target_dir / f"{mode_label}-{timestamp}-{result_label}.md"
    report_path.write_text(render_markdown_report(run_result), encoding="utf-8")
    return str(report_path)


def print_terminal_summary(run_result, report_path):
    """打印终端简短结论"""
    print("接口测试执行完成")
    print(f"执行模式: {display_mode(run_result['mode'])}")
    print(f"最终结论: {display_result(run_result['overall_success'])}")
    print(f"总请求数: {run_result['total']}")
    print(f"通过数: {run_result['passed']}")
    print(f"失败数: {run_result['failed']}")
    print(f"完整报告路径: {report_path}")


def collect_unexecuted_tests(tests, start_index):
    """收集未执行步骤"""
    pending = []
    for offset, item in enumerate(tests[start_index:], start=1):
        if not isinstance(item, dict):
            continue
        pending.append(
            {
                "description": item.get("description") or f"第{start_index + offset}个请求",
            }
        )
    return pending


def run_batch_tests(file_path, timeout=30):
    """批量执行测试用例"""
    try:
        import yaml
        import jmespath
    except ImportError as e:
        return create_run_result("batch", str(Path(file_path).resolve()), [], run_error=f"缺少依赖库 {e.name}")

    source = str(Path(file_path).resolve())

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            suite = yaml.safe_load(f)
    except FileNotFoundError:
        return create_run_result("batch", source, [], run_error=f"测试文件未找到: {file_path}")
    except yaml.YAMLError as e:
        return create_run_result("batch", source, [], run_error=f"YAML 格式错误: {e}")
    except Exception as e:
        return create_run_result("batch", source, [], run_error=f"读取文件失败: {e}")

    if not isinstance(suite, dict):
        return create_run_result("batch", source, [], run_error=f"YAML 配置必须是字典类型，当前为 {type(suite).__name__}")

    tests = suite.get("tests", [])
    if not isinstance(tests, list):
        return create_run_result("batch", source, [], run_error="tests 字段必须是数组类型")

    context = {"config": suite.get("config", {}), "tests": {}}
    results = []
    stop_on_error = context["config"].get("stop_on_error", True)
    base_url = context["config"].get("base_url", "")
    auth_header = context["config"].get("auth_header", {})
    terminated_early = False
    unexecuted_tests = []

    for index, test in enumerate(tests):
        if not isinstance(test, dict):
            continue

        test_id = test.get("id") or f"step_{index + 1}"
        description = test.get("description") or default_case_title(index + 1)
        notes = []

        if "request" not in test or not isinstance(test["request"], dict):
            response_info = {"success": False, "error": "配置错误", "message": "request 字段无效"}
            results.append(
                build_result_entry(
                    test_id,
                    description,
                    build_request_info("(无)", "(无)", {}, {}, None),
                    response_info,
                    False,
                    notes=["测试配置缺少有效的 request 字段"],
                )
            )
            if stop_on_error:
                terminated_early = True
                unexecuted_tests = collect_unexecuted_tests(tests, index + 1)
                break
            continue

        try:
            request_data = substitute_variables(test["request"], context, jmespath)
        except ValueError as e:
            response_info = {"success": False, "error": "变量替换错误", "message": str(e)}
            results.append(
                build_result_entry(
                    test_id,
                    description,
                    build_request_info("(无)", "(无)", {}, {}, None),
                    response_info,
                    False,
                )
            )
            if stop_on_error:
                terminated_early = True
                unexecuted_tests = collect_unexecuted_tests(tests, index + 1)
                break
            continue

        url = request_data.get("url", "")
        if base_url and not url.startswith("http"):
            url = base_url.rstrip("/") + "/" + url.lstrip("/")

        query_params = request_data.get("query", {})
        if query_params is None:
            query_params = {}
        if not isinstance(query_params, dict):
            response_info = {"success": False, "error": "配置错误", "message": "request.query 字段无效"}
            request_info = build_request_info(
                request_data.get("method", "GET").upper(),
                url,
                {},
                request_data.get("query"),
                request_data.get("body"),
            )
            results.append(build_result_entry(test_id, description, request_info, response_info, False))
            if stop_on_error:
                terminated_early = True
                unexecuted_tests = collect_unexecuted_tests(tests, index + 1)
                break
            continue

        final_url = build_url(url, query_params)
        method = request_data.get("method", "GET").upper()
        headers = {"Content-Type": "application/json"}
        if isinstance(auth_header, dict):
            headers.update(auth_header)
        custom_headers = request_data.get("headers", {})
        if isinstance(custom_headers, dict):
            headers.update(custom_headers)

        body = request_data.get("body")
        request_body = body if method in ["POST", "PUT", "PATCH"] else None

        try:
            expected_statuses = normalize_expected_status(test.get("expected_status"))
        except ValueError as e:
            response_info = {"success": False, "error": "配置错误", "message": str(e)}
            request_info = build_request_info(method, final_url, headers, query_params, request_body)
            results.append(build_result_entry(test_id, description, request_info, response_info, False))
            if stop_on_error:
                terminated_early = True
                unexecuted_tests = collect_unexecuted_tests(tests, index + 1)
                break
            continue

        request_info = build_request_info(method, final_url, headers, query_params, request_body)
        response_info = execute_request(final_url, method, headers, body=request_body, timeout=timeout)
        success = is_expected_response(response_info, expected_statuses)

        extracted = {}
        if success and "extract" in test:
            if not isinstance(test["extract"], dict):
                notes.append("extract 字段不是字典，已跳过提取")
            else:
                try:
                    response_body = json.loads(response_info.get("body", "{}"))
                    for key, path in test["extract"].items():
                        try:
                            extracted[key] = jmespath.search(path, response_body)
                        except jmespath.exceptions.JMESPathError as e:
                            notes.append(f"提取表达式 '{path}' 无效: {e}")
                            extracted[key] = None
                    context["tests"][test_id] = extracted
                except json.JSONDecodeError as e:
                    notes.append(f"响应体不是 JSON，无法提取数据: {e}")

        results.append(
            build_result_entry(
                test_id,
                description,
                request_info,
                response_info,
                success,
                expected_statuses=expected_statuses,
                extracted_data=extracted,
                notes=notes,
            )
        )

        if not success and stop_on_error:
            terminated_early = True
            unexecuted_tests = collect_unexecuted_tests(tests, index + 1)
            break

    return create_run_result(
        "batch",
        source,
        results,
        terminated_early=terminated_early,
        stop_on_error=stop_on_error,
        unexecuted_tests=unexecuted_tests,
    )


def run_single_request(url, method, headers, query_params, body, timeout):
    """执行单请求模式"""
    final_url = build_url(url, query_params)
    request_body = body if method in ["POST", "PUT", "PATCH"] else None
    request_info = build_request_info(method, final_url, headers, query_params, request_body)
    response_info = execute_request(final_url, method, headers, body=request_body, timeout=timeout)
    success = is_expected_response(response_info)
    result = build_result_entry("single_request", "单次请求", request_info, response_info, success)
    return create_run_result("single", final_url, [result])


def main():
    parser = argparse.ArgumentParser(description="HTTP客户端工具")
    parser.add_argument("--batch", help="批量测试配置文件 (YAML)")
    parser.add_argument("--url", help="目标URL (单请求模式)")
    parser.add_argument("--method", default="GET", help="HTTP方法")
    parser.add_argument("--headers", default="{}", help="自定义请求头(JSON)")
    parser.add_argument("--auth-header", default="{}", help="公共鉴权请求头(JSON)")
    parser.add_argument("--query", default="{}", help="查询参数(JSON)")
    parser.add_argument("--body", default="{}", help="请求体(JSON)")
    parser.add_argument("--timeout", type=int, default=30, help="超时时间(秒)")
    parser.add_argument("--report-dir", help="测试报告输出目录，默认使用当前目录")

    args = parser.parse_args()

    if args.batch:
        run_result = run_batch_tests(args.batch, timeout=args.timeout)
        report_path = write_report(run_result, report_dir=args.report_dir)
        print_terminal_summary(run_result, report_path)
        sys.exit(0 if run_result["overall_success"] else 1)

    if not args.url:
        parser.error("单请求模式需要 --url 参数，或使用 --batch 进行批量测试")

    base_headers = {"Content-Type": "application/json"}
    auth_header = parse_json_param(args.auth_header)
    custom_headers = parse_json_param(args.headers)
    query_params = parse_json_param(args.query)
    body = parse_json_param(args.body)

    headers = merge_headers(base_headers, auth_header, custom_headers)
    method = args.method.upper()
    run_result = run_single_request(args.url, method, headers, query_params, body, args.timeout)
    report_path = write_report(run_result, report_dir=args.report_dir)
    print_terminal_summary(run_result, report_path)
    sys.exit(0 if run_result["overall_success"] else 1)


if __name__ == "__main__":
    main()
