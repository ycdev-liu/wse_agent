import os
import sys
import json
import re
import subprocess
import urllib.request
import urllib.error
import urllib.parse

from pathlib import Path


# ============================================================
# Paths
# ============================================================

ROOT_DIR = Path(__file__).resolve().parent

WORKSPACE = ROOT_DIR / "workspace"

PORTABLE_PYTHON = (
    ROOT_DIR
    / "runtime"
    / "python"
    / "bin"
    / "python3"
)

WORKSPACE.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# Config
# ============================================================

BASE_URL = os.environ.get(
    "ANTHROPIC_BASE_URL"
)

AUTH_TOKEN = os.environ.get(
    "ANTHROPIC_AUTH_TOKEN"
)

MODEL = os.environ.get(
    "ANTHROPIC_MODEL"
)

if not BASE_URL:
    raise RuntimeError(
        "ANTHROPIC_BASE_URL is not set"
    )

if not AUTH_TOKEN:
    raise RuntimeError(
        "ANTHROPIC_AUTH_TOKEN is not set"
    )

if not MODEL:
    raise RuntimeError(
        "ANTHROPIC_MODEL is not set"
    )

BASE_URL = BASE_URL.rstrip("/")

API_URL = (
    BASE_URL
    + "/v1/messages"
)

# 最多执行轮次
MAX_STEPS = 20


# ============================================================
# Verify portable python
# ============================================================

if not PORTABLE_PYTHON.exists():

    raise RuntimeError(
        f"Portable Python not found:\n"
        f"{PORTABLE_PYTHON}\n\n"
        f"Please run ./setup_runtime.sh"
    )


# ============================================================
# Path security
# ============================================================

def safe_path(
    relative_path: str
) -> Path:

    target = (
        WORKSPACE
        / relative_path
    ).resolve()

    workspace_resolved = (
        WORKSPACE.resolve()
    )

    if (
        target != workspace_resolved
        and workspace_resolved
        not in target.parents
    ):

        raise ValueError(
            f"Access outside workspace "
            f"is forbidden: {relative_path}"
        )

    return target


# ============================================================
# Tool: list files
# ============================================================

def list_files(
    path: str = "."
) -> str:

    target = safe_path(path)

    if not target.exists():

        return (
            f"Path does not exist: {path}"
        )

    if target.is_file():

        return str(
            target.relative_to(
                WORKSPACE
            )
        )

    result = []

    for item in target.rglob("*"):

        if not item.is_file():
            continue

        rel = item.relative_to(
            WORKSPACE
        )

        if any(
            part in {
                "__pycache__",
                ".git",
                ".pytest_cache",
                ".agent_packages",
            }
            for part in rel.parts
        ):
            continue

        result.append(
            str(rel)
        )

    if not result:

        return "(workspace empty)"

    return "\n".join(
        result[:500]
    )


# ============================================================
# Tool: read file
# ============================================================

def read_file(
    path: str
) -> str:

    target = safe_path(path)

    if not target.exists():

        return (
            f"File not found: {path}"
        )

    if not target.is_file():

        return (
            f"Not a file: {path}"
        )

    content = target.read_text(
        encoding="utf-8",
        errors="replace",
    )

    max_chars = 30000

    if len(content) > max_chars:

        content = (
            content[:max_chars]
            + "\n...[TRUNCATED]"
        )

    return content

# ============================================================
# Tool: write file
# ============================================================

def write_file(
    path: str,
    content: str,
) -> str:

    target = safe_path(path)

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    target.write_text(
        content,
        encoding="utf-8",
    )

    return (
        f"Successfully wrote {path}"
    )

# ============================================================
# Tool: run Python
# ============================================================

def python_env() -> dict:

    env = os.environ.copy()
    paths = [str(safe_path(".agent_packages"))]

    if env.get("PYTHONPATH"):
        paths.append(env["PYTHONPATH"])

    env["PYTHONPATH"] = os.pathsep.join(paths)
    return env


def run_python(
    path: str,
    args: list | None = None,
) -> str:

    target = safe_path(path)

    if not target.exists():

        return (
            f"Python file not found: {path}"
        )

    if args is None:

        args = []

    command = [
        str(PORTABLE_PYTHON),
        str(target),
        *args,
    ]

    try:

        result = subprocess.run(
            command,
            cwd=WORKSPACE,
            env=python_env(),
            capture_output=True,
            text=True,
            timeout=60,
        )

    except subprocess.TimeoutExpired:

        return (
            "Execution timed out "
            "after 60 seconds"
        )

    return f"""
COMMAND:
{" ".join(command)}

RETURN CODE:
{result.returncode}

STDOUT:
{result.stdout}

STDERR:
{result.stderr}
""".strip()


# ============================================================
# Tool: install and create tools
# ============================================================

def download_file(url: str, path: str) -> str:

    parsed = urllib.parse.urlparse(url)

    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Download URL must be HTTPS")

    target = safe_path(path)

    with urllib.request.urlopen(url, timeout=30) as response:
        if urllib.parse.urlparse(response.geturl()).scheme != "https":
            raise ValueError("Download redirected away from HTTPS")

        data = response.read(10 * 1024 * 1024 + 1)

    if len(data) > 10 * 1024 * 1024:
        raise ValueError("Download exceeds 10 MB")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return f"Downloaded {len(data)} bytes to {path}"


def install_package(
    package: str,
    version: str = "",
) -> str:

    if not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._-]*(\[[A-Za-z0-9,_-]+\])?",
        package,
    ):
        raise ValueError("Invalid Python package name")

    if version and not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._+!-]*",
        version,
    ):
        raise ValueError("Invalid package version")

    requirement = package + (f"=={version}" if version else "")
    packages_dir = safe_path(".agent_packages")
    packages_dir.mkdir(parents=True, exist_ok=True)

    try:
        result = subprocess.run(
            [
                str(PORTABLE_PYTHON),
                "-m", "pip", "install",
                "--disable-pip-version-check",
                "--no-input",
                "--upgrade",
                "--target", str(packages_dir),
                requirement,
            ],
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        return "Package installation timed out after 180 seconds"

    return (
        f"RETURN CODE: {result.returncode}\n"
        f"STDOUT:\n{result.stdout[-4000:]}\n"
        f"STDERR:\n{result.stderr[-4000:]}"
    )


def tool_name_path(name: str) -> Path:

    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", name):
        raise ValueError("Invalid tool name")

    return safe_path(f".agent_tools/{name}.py")


def create_tool(
    name: str,
    description: str,
    code: str,
) -> str:

    script = tool_name_path(name)

    if not description.strip():
        raise ValueError("Tool description cannot be empty")

    compile(code, str(script), "exec")
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(code, encoding="utf-8")
    script.with_suffix(".json").write_text(
        json.dumps(
            {"name": name, "description": description},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return f"Created tool {name}. Test it with run_tool."


def list_tools() -> str:

    tools_dir = safe_path(".agent_tools")

    if not tools_dir.exists():
        return "(no custom tools)"

    tools = []

    for manifest in sorted(tools_dir.glob("*.json")):
        if manifest.with_suffix(".py").is_file():
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            tools.append(
                f"{metadata['name']}: {metadata['description']}"
            )

    return "\n".join(tools) if tools else "(no custom tools)"

# 传入要调用的工具名字与参数
def run_tool(
    name: str,
    arguments: dict,
) -> str:

    script = tool_name_path(name)

    if not script.is_file() or not script.with_suffix(".json").is_file():
        return f"Custom tool not found: {name}"

    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments must be a JSON object")

    try:
        result = subprocess.run(
            [str(PORTABLE_PYTHON), str(script)],
            input=json.dumps(arguments, ensure_ascii=False),
            cwd=WORKSPACE,
            env=python_env(),
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        return "Tool execution timed out after 60 seconds"

    return (
        f"RETURN CODE: {result.returncode}\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )


# ============================================================
# Tool: run unittest
# ============================================================

def run_tests() -> str:

    command = [
        str(PORTABLE_PYTHON),
        "-m",
        "unittest",
        "discover",
        "-v",
    ]

    try:

        result = subprocess.run(
            command,
            cwd=WORKSPACE,
            env=python_env(),
            capture_output=True,
            text=True,
            timeout=60,
        )

    except subprocess.TimeoutExpired:

        return (
            "Tests timed out"
        )

    return f"""
COMMAND:
{" ".join(command)}

RETURN CODE:
{result.returncode}

STDOUT:
{result.stdout}

STDERR:
{result.stderr}
""".strip()


# ============================================================
# Tool executor
# ============================================================

def execute_tool(
    name: str,
    arguments: dict,
) -> str:

    try:

        if name == "list_files":

            return list_files(
                **arguments
            )

        if name == "read_file":

            return read_file(
                **arguments
            )

        if name == "write_file":

            return write_file(
                **arguments
            )

        if name == "run_python":

            return run_python(
                **arguments
            )

        if name == "run_tests":

            return run_tests()

        if name == "install_package":

            return install_package(**arguments)

        if name == "download_file":

            return download_file(**arguments)

        if name == "create_tool":

            return create_tool(**arguments)

        if name == "list_tools":

            return list_tools()

        if name == "run_tool":

            return run_tool(**arguments)

        return (
            f"Unknown tool: {name}"
        )

    except Exception as exc:

        return (
            f"{type(exc).__name__}: "
            f"{exc}"
        )


# ============================================================
# Tool schemas
# ============================================================

# 定义工具tool
TOOLS = [

    {
        "type": "function",

        "name": "list_files",

        "description":
            "List files recursively "
            "inside the coding workspace.",

        "parameters": {

            "type": "object",

            "properties": {

                "path": {
                    "type": "string",
                    "description":
                        "Directory path relative "
                        "to workspace."
                }

            },

            "required": ["path"],

            "additionalProperties":
                False,
        },

        "strict": True,
    },

    {
        "type": "function",

        "name": "read_file",

        "description":
            "Read a text file "
            "inside the workspace.",

        "parameters": {

            "type": "object",

            "properties": {

                "path": {
                    "type": "string"
                }

            },

            "required": ["path"],

            "additionalProperties":
                False,
        },

        "strict": True,
    },

    {
        "type": "function",

        "name": "write_file",

        "description":
            "Create or overwrite "
            "a file inside workspace.",

        "parameters": {

            "type": "object",

            "properties": {

                "path": {
                    "type": "string"
                },

                "content": {
                    "type": "string"
                }

            },

            "required": [
                "path",
                "content",
            ],

            "additionalProperties":
                False,
        },

        "strict": True,
    },

    {
        "type": "function",

        "name": "run_python",

        "description":
            "Execute a Python file "
            "using the bundled "
            "portable Python runtime.",

        "parameters": {

            "type": "object",

            "properties": {

                "path": {
                    "type": "string"
                },

                "args": {

                    "type": "array",

                    "items": {
                        "type": "string"
                    }
                }

            },

            "required": [
                "path",
                "args",
            ],

            "additionalProperties":
                False,
        },

        "strict": True,
    },

    {
        "type": "function",

        "name": "run_tests",

        "description":
            "Run unittest discovery "
            "using the bundled "
            "portable Python.",

        "parameters": {

            "type": "object",

            "properties": {},

            "additionalProperties":
                False,
        },

        "strict": True,
    },

    {
        "name": "download_file",
        "description": "Download an HTTPS file of up to 10 MB into the workspace. Inspect code before running it.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "path": {"type": "string", "description": "Destination relative to the workspace."},
            },
            "required": ["url", "path"],
            "additionalProperties": False,
        },
    },

    {
        "name": "install_package",
        "description": "Download and install a Python package into the workspace using the bundled pip. Use only when the task needs it.",
        "parameters": {
            "type": "object",
            "properties": {
                "package": {"type": "string", "description": "PyPI package name, optionally with extras."},
                "version": {"type": "string", "description": "Exact version, or empty string for latest."},
            },
            "required": ["package", "version"],
            "additionalProperties": False,
        },
    },

    {
        "name": "create_tool",
        "description": "Create or update a reusable Python tool in the workspace. The script reads one JSON object from stdin and prints its result to stdout.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Tool name using letters, numbers, and underscores."},
                "description": {"type": "string", "description": "What the tool does and the JSON keys it accepts."},
                "code": {"type": "string", "description": "Complete Python script. Read JSON from sys.stdin and print the result."},
            },
            "required": ["name", "description", "code"],
            "additionalProperties": False,
        },
    },

    {
        "name": "list_tools",
        "description": "List reusable tools created in this workspace.",
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },

    {
        "name": "run_tool",
        "description": "Run a reusable tool created with create_tool, passing JSON arguments on stdin.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "arguments": {"type": "object", "additionalProperties": True},
            },
            "required": ["name", "arguments"],
            "additionalProperties": False,
        },
    },
]


# ============================================================
# System prompt
# ============================================================

SYSTEM_PROMPT = """
You are a minimal autonomous software engineering agent.

You operate only inside a restricted workspace.

You have these tools:

- list_files
- read_file
- write_file
- run_python
- run_tests
- download_file
- install_package
- create_tool
- list_tools
- run_tool

If the task needs a third-party Python library, call install_package. Installed packages are available to run_python, run_tests, and custom tools. Use download_file for other HTTPS resources. Inspect downloaded code before running it. Prefer the standard library when it is enough.

For reusable capabilities, create a tool with create_tool. Its Python code must read a JSON object from stdin (json.load(sys.stdin)) and print a result. Give its description the expected input keys. Use run_tool to test and invoke it. Use list_tools to discover tools saved from previous tasks. Custom tools persist in the workspace.

Important rules:

1. Inspect the repository before changing code.
2. Never invent file contents.
3. Use write_file to make real changes.
4. Run code after editing.
5. If execution fails, inspect the error.
6. Fix the error and run again.
7. Prefer Python standard library.
8. Do not assume Conda exists.
9. Do not assume system Python exists.
10. Python execution must use the bundled runtime.
11. Do not claim success unless you verified it.
12. Keep changes minimal.

Typical loop:

inspect
-> reason
-> edit
-> execute
-> observe
-> fix
-> execute again
-> finish
"""


# ============================================================
# Anthropic Messages API
# ============================================================

def call_model(
    messages: list
) -> dict:

    body = {

        "model": MODEL,

        "system":
            SYSTEM_PROMPT,

        "max_tokens": 4096,

        "messages":
            messages,

        "tools":
            [
                {
                    "name": tool["name"],
                    "description": tool["description"],
                    "input_schema": tool["parameters"],
                }
                for tool in TOOLS
            ],
    }

    raw_data = json.dumps(
        body
    ).encode("utf-8")

    request = urllib.request.Request(
        API_URL,
        data=raw_data,
        method="POST",
        headers={
            "Authorization":
                f"Bearer {AUTH_TOKEN}",

            "Content-Type":
                "application/json",

            "anthropic-version":
                "2023-06-01",
        },
    )

    try:

        # 发送一个网络请求
        with urllib.request.urlopen(
            request,
            timeout=120,
        ) as response:

            # 生成python 对象
            return json.loads(
                response
                .read()
                .decode("utf-8")
            )

    # 如果失败
    except urllib.error.HTTPError as exc:

        body = exc.read().decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError(
            f"API error {exc.code}\n"
            f"{body}"
        )


# ============================================================
# Extract final text
# ============================================================

def extract_text(
    response: dict
) -> str:

    text_parts = []
    # 获得content 里面的内容
    for block in response.get(
        "content",
        []
    ):

        if block.get("type") == "text":
            text_parts.append(
                block.get("text", "")
            )
            # 拼接文本
    return "\n".join(
        text_parts
    )


# ============================================================
# Main Agent Loop
# ============================================================

def run_agent(
    task: str,
    history:list
):
    # 这里相当于短期记忆
    # 其实是没有长期记忆得
    # 构建我们的对话

    history.append(
       {"role":"user",
        "content":task,
        }
    )

    # 输出步数
    for step in range(
        1,
        MAX_STEPS + 1,
    ):

        print()
        print(
            "=" * 70
        )

        print(
            f"Agent Step {step}"
        )

        print(
            "=" * 70
        )

        response = call_model(
            history
        )

        #生成回答
        content = response.get(
            "content",
            []
        )

        if response.get("stop_reason") == "max_tokens":
            raise RuntimeError(
                "Model response was truncated; increase max_tokens"
            )

        # 将回答加入到历史
        history.append({
            "role": "assistant",
            "content": content,
        })

        tool_calls = [

            item
            # 判断是否需要调用工具
            for item in content

            if (
                item.get("type")
                == "tool_use"
            )
        ]

        # 如果不需要调用工具则输出答案
        if not tool_calls:

            answer = extract_text(
                response
            )

            print()
            print(
                "Agent Final Answer:"
            )

            print(answer)

            return

        # 如果需要调用工具
        tool_results = []

        for call in tool_calls:

            name = call["name"]

            arguments = call.get("input", {})

            print()
            print(
                f"[Tool Call] {name}"
            )

            print(
                json.dumps(
                    arguments,
                    indent=2,
                    ensure_ascii=False,
                )
            )

            # 输入调用工具的名称和参数
            result = execute_tool(
                name,
                arguments,
            )

            print()
            print(
                "[Tool Result]"
            )

            print(
                result[:5000]
            )
            # 将调用工具结果加入到历史
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": call["id"],
                "content": result,
            })

        # 将调用结果放在content 中
        history.append({
            "role": "user",
            "content": tool_results,
        })

    print(
        f"Stopped after "
        f"{MAX_STEPS} steps."
    )


# ============================================================
# CLI
# ============================================================

def main():

    print(
        "Portable SWE Agent"
    )

    print()

    print(
        "Agent Python:"
    )

    print(
        PORTABLE_PYTHON
    )

    print()

    print(
        "Workspace:"
    )

    print(
        WORKSPACE
    )

    print()

    # task = input(
    #     "Task > "
    # ).strip()

    # if not task:

    #     raise SystemExit(
    #         "Task cannot be empty"
    #     )

    # run_agent(
    #     task
    # )

    history=[]

    #  持续对话
    while True:
        try:
            task = input("task->").strip()
        except(EOFError,KeyboardInterrupt):
            print("\n已退出")
            break
        if task.casefold() in {"exit","quit","退出"}:
            print("\n已退出")
            break
        if not task:
            continue

        try:
            run_agent(task=task,history=history)
        except Exception as exc:
            print(f"本轮出错：{exc}")



if __name__ == "__main__":

    main()
