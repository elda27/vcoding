#!/usr/bin/env python3
"""LangChain integration example.

This example demonstrates how to use vcoding with LangChain.

Prerequisites:
- Install LangChain: pip install langchain
- Install an LLM provider (e.g., pip install langchain-openai)
"""

from pathlib import Path
from tempfile import mkdtemp

from vcoding import workspace_context

# Check if LangChain is available
try:
    from vcoding.langchain import get_langchain_tools

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("LangChain not installed. Install with: pip install vcoding[langchain]")


def basic_langchain_tools() -> None:
    """Get and inspect LangChain tools."""
    if not LANGCHAIN_AVAILABLE:
        print("Skipping: LangChain not available")
        return

    project_dir = Path(mkdtemp(prefix="vcoding_langchain_"))

    (project_dir / "Dockerfile").write_text("FROM python:3.11-slim\nWORKDIR /workspace\n")

    try:
        with workspace_context(project_dir, auto_destroy=True) as ws:
            # Get LangChain tools
            tools = get_langchain_tools(ws)

            print("=== Available LangChain Tools ===\n")
            for tool in tools:
                print(f"Name: {tool.name}")
                print(f"Description: {tool.description}")
                print()

    finally:
        import shutil

        shutil.rmtree(project_dir, ignore_errors=True)


def use_execute_tool() -> None:
    """Demonstrate using the execute tool."""
    if not LANGCHAIN_AVAILABLE:
        print("Skipping: LangChain not available")
        return

    project_dir = Path(mkdtemp(prefix="vcoding_exec_tool_"))

    (project_dir / "Dockerfile").write_text("FROM python:3.11-slim\nWORKDIR /workspace\n")

    try:
        with workspace_context(project_dir, auto_destroy=True) as ws:
            tools = get_langchain_tools(ws)

            # Find the execute tool
            execute_tool = next(t for t in tools if t.name == "vcoding_execute")

            # Use the tool directly
            result = execute_tool._run(command="python -c 'print(2 + 2)'")
            print(f"Execute result:\n{result}")

            result = execute_tool._run(command="ls -la")
            print(f"Directory listing:\n{result}")

    finally:
        import shutil

        shutil.rmtree(project_dir, ignore_errors=True)


def agent_example() -> None:
    """Example of using vcoding tools with a LangChain agent.

    Note: This requires an LLM provider to be configured.
    """
    if not LANGCHAIN_AVAILABLE:
        print("Skipping: LangChain not available")
        return

    print(
        """
=== LangChain Agent Example ===

This example shows how to use vcoding tools with a LangChain agent.
You need to configure an LLM provider first.

Example code:

```python
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

from vcoding import workspace_context
from vcoding.langchain import get_langchain_tools

with workspace_context("/path/to/project") as ws:
    # Get vcoding tools
    tools = get_langchain_tools(ws)
    
    # Create LLM
    llm = ChatOpenAI(model="gpt-4", temperature=0)
    
    # Create prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful coding assistant."),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    # Create agent
    agent = create_openai_tools_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    
    # Run agent
    result = executor.invoke({
        "input": "Check the Python version and list installed packages"
    })
    print(result["output"])
```
"""
    )


def custom_tool_example() -> None:
    """Example of creating custom LangChain tools with vcoding."""
    if not LANGCHAIN_AVAILABLE:
        print("Skipping: LangChain not available")
        return

    print(
        """
=== Custom Tool Example ===

You can create custom LangChain tools that use vcoding:

```python
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from vcoding import workspace_context

class RunPythonScriptInput(BaseModel):
    script_content: str = Field(description="Python code to execute")
    
class RunPythonScriptTool(BaseTool):
    name = "run_python_script"
    description = "Execute Python code in an isolated container"
    args_schema = RunPythonScriptInput
    _workspace = None
    
    def __init__(self, workspace, **kwargs):
        super().__init__(**kwargs)
        self._workspace = workspace
    
    def _run(self, script_content: str) -> str:
        # Write script to container
        self._workspace.execute(
            f'echo {repr(script_content)} > /tmp/script.py'
        )
        
        # Execute script
        exit_code, stdout, stderr = self._workspace.execute(
            "python /tmp/script.py"
        )
        
        if exit_code == 0:
            return f"Output:\\n{stdout}"
        return f"Error (exit {exit_code}):\\n{stderr}"

# Usage:
with workspace_context("/path/to/project") as ws:
    tool = RunPythonScriptTool(ws)
    result = tool._run("print('Hello from custom tool!')")
    print(result)
```
"""
    )


def integration_with_chain() -> None:
    """Example of using vcoding tools in a LangChain chain."""
    if not LANGCHAIN_AVAILABLE:
        print("Skipping: LangChain not available")
        return

    print(
        """
=== Integration with LangChain Chains ===

vcoding tools can be integrated into complex LangChain chains:

```python
from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

from vcoding import workspace_context
from vcoding.langchain import get_langchain_tools

def analyze_and_run(project_path: str, task: str):
    with workspace_context(project_path) as ws:
        tools = get_langchain_tools(ws)
        execute_tool = next(t for t in tools if t.name == "vcoding_execute")
        
        llm = ChatOpenAI(model="gpt-4")
        
        # Chain 1: Analyze project structure
        structure = execute_tool._run("find . -type f -name '*.py' | head -20")
        
        # Chain 2: Generate commands based on analysis
        prompt = PromptTemplate(
            input_variables=["structure", "task"],
            template="Given this project structure:\\n{structure}\\n\\nTask: {task}\\n\\nWhat command should I run?"
        )
        
        chain = LLMChain(llm=llm, prompt=prompt)
        suggested_command = chain.run(structure=structure, task=task)
        
        # Chain 3: Execute suggested command
        result = execute_tool._run(suggested_command)
        
        return result

# Usage:
result = analyze_and_run("/my/project", "Run all tests")
print(result)
```
"""
    )


if __name__ == "__main__":
    print("=== LangChain Tools Overview ===\n")
    basic_langchain_tools()

    print("\n\n=== Execute Tool Demo ===\n")
    use_execute_tool()

    print("\n")
    agent_example()

    print("\n")
    custom_tool_example()

    print("\n")
    integration_with_chain()
