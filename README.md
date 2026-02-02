# vcoding 🚀

**Secure, sandboxed environments for AI code agents.**

Run GitHub Copilot CLI, Claude Code, and other AI coding tools safely in isolated containers—with full Git version control.

## ✨ Features

- 🔒 **Sandboxed execution** — AI agents run in containers, not your host
- 🔄 **Git-based rollback** — Undo any AI-generated changes instantly
- 🤖 **MCP server included** — Works with Claude, GPT, and MCP-compatible clients
- 📦 **Zero config** — Auto-generates Dockerfiles for Python, Node.js, Go

## 📦 Install

```bash
pip install vcoding
# With MCP server support
pip install vcoding[mcp]
```

## 🚀 Quick Start

### Python API

```python
import vcoding

# One-liner: generate code safely
result = vcoding.generate("./project/fib.py", "Create a fibonacci function")

# Or manage the full lifecycle
with vcoding.workspace_context("./my-project") as ws:
    ws.execute("python -m pytest")
    ws.run_agent("copilot", "Add error handling to main.py")
```

### MCP Server

```bash
# Run the MCP server
vcoding-mcp
# Or with fastmcp
fastmcp run vcoding.mcp:mcp
```

Use with Claude Desktop, VS Code, or any MCP client.

## 🛠️ MCP Tools

| Tool | Description |
|------|-------------|
| `create_workspace` | Create isolated environment |
| `execute_command` | Run commands in container |
| `run_agent` | Execute Copilot/Claude Code |
| `commit_changes` | Git commit in workspace |
| `rollback` | Revert to any commit |
| `sync_to_workspace` | Copy files to container |
| `sync_from_workspace` | Copy results back |

## 📖 How It Works

```
Host                          Container
┌─────────────┐    SSH    ┌─────────────────┐
│ vcoding API │◄────────►│ AI Agent (safe) │
│ Git control │           │ Your code copy  │
└─────────────┘           └─────────────────┘
```

1. Creates isolated container from your Dockerfile
2. Copies code via secure temp directory (not direct mount)
3. AI agents edit inside container
4. You review & sync changes back

## 📄 License

Apache 2.0
