"""Test the MCP server via actual stdio transport using the MCP client SDK.

Run with: python tests/test_mcp_protocol.py
"""

import asyncio
import json
import os
import sys

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp import ClientSession


async def main():
    print("=== MCP Server Protocol Test (via MCP Client SDK) ===")
    print()

    env = {**os.environ, "LINKEDIN_USERNAME": "test", "LINKEDIN_PASSWORD": "test"}

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-c", "from linkedin_mcp.server import main; main()"],
        env=env,
    )

    passed = 0
    failed = 0

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # 1. Initialize
            result = await session.initialize()
            print(f"  1. initialize: OK")
            print(f"     protocol: {result.protocolVersion}")
            print(f"     capabilities: {list(vars(result.capabilities).keys())}")
            passed += 1

            # 2. List tools
            tools_result = await session.list_tools()
            tools = tools_result.tools
            print(f"  2. tools/list: OK ({len(tools)} tools)")
            for t in tools:
                params = list(t.inputSchema.get("properties", {}).keys()) if t.inputSchema else []
                print(f"     - {t.name}({', '.join(params)})")
            if len(tools) == 13:
                passed += 1
            else:
                print(f"     WARN: expected 13 tools, got {len(tools)}")
                failed += 1

            # 3. List prompts
            prompts_result = await session.list_prompts()
            prompts = prompts_result.prompts
            print(f"  3. prompts/list: OK ({len(prompts)} prompts)")
            for p in prompts:
                print(f"     - {p.name}: {(p.description or '')[:60]}")
            if len(prompts) == 3:
                passed += 1
            else:
                print(f"     WARN: expected 3 prompts, got {len(prompts)}")
                failed += 1

            # 4. List resources
            resources_result = await session.list_resources()
            resources = resources_result.resources
            print(f"  4. resources/list: OK ({len(resources)} resources)")
            for r in resources:
                print(f"     - {r.uri}: {r.name}")
            passed += 1

            # 5. List resource templates
            templates_result = await session.list_resource_templates()
            templates = templates_result.resourceTemplates
            print(f"  5. resource templates: OK ({len(templates)} templates)")
            for t in templates:
                print(f"     - {t.uriTemplate}: {t.name}")
            if len(templates) == 2:
                passed += 1
            else:
                print(f"     WARN: expected 2 templates, got {len(templates)}")
                failed += 1

            # 6. Call list_templates tool
            result = await session.call_tool("list_templates", {"template_type": "all"})
            text = result.content[0].text if result.content else ""
            if result.isError:
                print(f"  6. list_templates tool: ERROR - {text[:100]}")
                failed += 1
            else:
                data = json.loads(text)
                print(f"  6. list_templates tool: OK")
                for k, v in data.items():
                    print(f"     {k}: {len(v)} template(s)")
                passed += 1

            # 7. Call list_applications tool
            result = await session.call_tool("list_applications", {"status": ""})
            text = result.content[0].text if result.content else ""
            if result.isError:
                print(f"  7. list_applications tool: ERROR - {text[:100]}")
                failed += 1
            else:
                data = json.loads(text)
                print(f"  7. list_applications tool: OK ({len(data)} apps)")
                passed += 1

            # 8. Call track_application tool
            result = await session.call_tool("track_application", {
                "job_id": "proto-test-001",
                "job_title": "Protocol Test Engineer",
                "company": "MCP Corp",
                "status": "applied",
                "notes": "Tested via MCP client SDK",
            })
            text = result.content[0].text if result.content else ""
            if result.isError:
                print(f"  8. track_application tool: ERROR - {text[:100]}")
                failed += 1
            else:
                data = json.loads(text)
                assert data["job_id"] == "proto-test-001"
                assert data["status"] == "applied"
                print(f"  8. track_application tool: OK (tracked '{data['job_title']}')")
                passed += 1

            # 9. Verify tracked application shows up in list
            result = await session.call_tool("list_applications", {"status": "applied"})
            text = result.content[0].text if result.content else ""
            data = json.loads(text)
            found = any(a["job_id"] == "proto-test-001" for a in data)
            if found:
                print(f"  9. verify tracked app in list: OK")
                passed += 1
            else:
                print(f"  9. verify tracked app in list: FAILED - not found in {len(data)} apps")
                failed += 1

            # 10. Update application status
            result = await session.call_tool("update_application_status", {
                "job_id": "proto-test-001",
                "status": "interviewing",
                "notes": "Phone screen scheduled",
            })
            text = result.content[0].text if result.content else ""
            if result.isError:
                print(f"  10. update_application_status: ERROR - {text[:100]}")
                failed += 1
            else:
                data = json.loads(text)
                assert data["status"] == "interviewing"
                print(f"  10. update_application_status: OK (-> {data['status']})")
                passed += 1

            # 11. Invalid status -> isError
            result = await session.call_tool("track_application", {
                "job_id": "bad",
                "job_title": "Bad",
                "company": "Bad",
                "status": "NOT_VALID",
            })
            if result.isError:
                print(f"  11. invalid status -> isError: OK")
                passed += 1
            else:
                print(f"  11. invalid status: BUG - should be isError")
                failed += 1

            # 12. Invalid format -> isError
            result = await session.call_tool("generate_resume", {
                "profile_id": "test",
                "output_format": "docx",
            })
            if result.isError:
                print(f"  12. invalid format -> isError: OK")
                passed += 1
            else:
                print(f"  12. invalid format: BUG - should be isError")
                failed += 1

            # 13. Read applications resource
            result = await session.read_resource("linkedin://applications")
            text = result.contents[0].text if result.contents else ""
            data = json.loads(text)
            print(f"  13. read applications resource: OK (total={data.get('total', '?')})")
            passed += 1

            # 14. Get prompt (requires 'role' argument)
            result = await session.get_prompt("job_search_workflow", {"role": "Software Engineer", "location": "San Francisco"})
            if result.messages:
                msg_text = result.messages[0].content.text if hasattr(result.messages[0].content, "text") else str(result.messages[0].content)
                print(f"  14. get prompt: OK ({len(result.messages)} message)")
                print(f"     preview: {msg_text[:80]}...")
                passed += 1
            else:
                print(f"  14. get prompt: FAILED - no messages")
                failed += 1

            # 15. Get prompt without required arg -> error
            try:
                await session.get_prompt("job_search_workflow", {})
                print(f"  15. prompt missing arg: BUG - should have raised")
                failed += 1
            except Exception:
                print(f"  15. prompt missing required arg -> error: OK")
                passed += 1

            # 16. Get prompt with no args
            result = await session.get_prompt("profile_optimization", {})
            if result.messages:
                print(f"  16. profile_optimization prompt: OK")
                passed += 1
            else:
                print(f"  16. profile_optimization prompt: FAILED")
                failed += 1

    print()
    print(f"=== Results: {passed} passed, {failed} failed ===")
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    asyncio.run(main())
