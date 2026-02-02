# vcoding CLI Reference

The vcoding CLI provides commands to access and manage existing vcoding development environments.

## Installation

```bash
pip install vcoding
```

## Commands

### `vcoding list`

List all vcoding environments (Docker containers).

```bash
vcoding list           # List all environments
vcoding list --running # List only running environments
vcoding ls -r          # Shorthand
```

**Output example:**
```
Found 2 vcoding environment(s):

  🟢 my-project
     Container: vcoding-my-project
     Status: running
     SSH port: 2222
     Workspace: /home/user/.vcoding/workspaces/ab/abc123...

  🔴 another-project
     Container: vcoding-another-project
     Status: exited
     SSH: N/A
```

### `vcoding exec`

Execute a command or open an interactive SSH shell in a vcoding environment.

```bash
vcoding exec                    # Interactive selection, then SSH shell
vcoding exec -n myenv           # SSH into 'myenv'
vcoding exec -n myenv ls -la    # Run 'ls -la' in 'myenv'
vcoding ssh -n myenv            # Alias for exec
```

**Options:**
- `-n, --name NAME` - Specify environment name (prompts for selection if omitted)

**Interactive selection:**

When multiple environments are running and no name is specified, you'll see a selection prompt:

```
Available vcoding environments:

  1. 🟢 my-project [SSH:2222]
  2. 🟢 another-project [SSH:2223]

Select environment (number or name, q to quit): 
```

### `vcoding cp`

Copy files to or from a vcoding environment using SCP.

```bash
# Copy local file to remote
vcoding cp local.txt myenv:/workspace/

# Copy remote file to local
vcoding cp myenv:/workspace/result.txt ./

# Copy directory recursively
vcoding cp -r ./src myenv:/workspace/
vcoding cp -r myenv:/workspace/output ./
```

**Syntax:**
- Local path: regular file path (e.g., `./file.txt`, `/home/user/data`)
- Remote path: `<env>:<path>` (e.g., `myenv:/workspace/file.txt`)

**Options:**
- `-r, --recursive` - Copy directories recursively

## Environment Identification

Environments can be identified by:
- **Workspace name** - The name given when creating the workspace
- **Container name** - The Docker container name (e.g., `vcoding-my-project`)

## SSH Configuration

The CLI uses native SSH/SCP clients with the following options:
- SSH keys are automatically managed per workspace
- Strict host key checking is disabled for convenience
- Keys are stored in `~/.vcoding/workspaces/<hash>/keys/`

## Examples

### Workflow: Edit and Test

```bash
# List available environments
vcoding list

# Copy source code to container
vcoding cp -r ./src myproject:/workspace/

# Run tests in container
vcoding exec -n myproject pytest

# Copy results back
vcoding cp myproject:/workspace/coverage.xml ./
```

### Workflow: Interactive Development

```bash
# Open SSH shell
vcoding exec -n myproject

# Inside container:
cd /workspace
python main.py
exit
```

### Workflow: Quick Command

```bash
# Run a single command
vcoding exec -n myproject python -c "print('Hello from container')"

# Check container status
vcoding exec -n myproject cat /etc/os-release
```

## Troubleshooting

### "No vcoding environments found"

- Ensure Docker is running
- Check that containers exist: `docker ps -a --filter label=vcoding.managed=true`

### "SSH key not found"

- The workspace may have been partially cleaned up
- Try restarting the workspace using the Python API

### "SSH port not available"

- The container may not be running
- Start the container: `vcoding list` then use Python API to start

## See Also

- [Python API Documentation](./api.md)
- [SPEC.md](../SPEC.md) - Full specification
