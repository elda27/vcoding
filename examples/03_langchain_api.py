"""Example 03: LangChain API - Integration with LangChain agents.

Goal: Use vcoding as LangChain tools for AI agent workflows.

This example demonstrates:
- Using vcoding.langchain.get_langchain_tools() to get LangChain-compatible tools
- Creating a LangChain agent with create_agent (modern LangChain API)
- Running the agent to execute code in a virtual environment

Prerequisites:
- Docker Desktop must be running
- langchain and langchain-google-genai must be installed:
    pip install langchain langchain-google-genai
- GOOGLE_API_KEY environment variable must be set (for Google Gemini)
"""

import os
from pathlib import Path

import vcoding
from vcoding.langchain import get_langchain_tools

# Import LangChain components
try:
    from langchain.agents import create_agent
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError as e:
    print(f"\n[ERROR] Required packages not installed: {e}")
    print("Please install them with:")
    print("  pip install langchain langchain-google-genai")


def main():
    """Demonstrate LangChain integration with vcoding."""
    print("vcoding Example 03: LangChain API")
    print("=" * 50)

    # Setup: Create project directory
    target_path = Path("./my-project")
    target_path.mkdir(exist_ok=True)
    # Use context manager to manage workspace lifecycle
    print("\n[Starting workspace context...]")

    with vcoding.workspace_context("./my-project", language="python") as ws:
        # Step 1: Get LangChain tools from workspace
        print("\n[Step 1] Getting LangChain tools...")
        tools = get_langchain_tools(ws)

        print(f"Available tools ({len(tools)}):")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description[:60]}...")

        # Step 2: Create LangChain agent using create_agent (modern API)
        print("\n[Step 2] Creating LangChain agent...")

        # Create Google Gemini model
        model = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)

        # Create agent with create_agent (built on LangGraph)
        agent = create_agent(
            model=model,
            tools=tools,
            system_prompt=(
                "You are a helpful coding assistant with access to a virtual environment. "
                "You can execute shell commands to create files, run Python code, and manage git. "
                "Always use the vcoding_execute tool to run commands."
            ),
        )

        print("Agent created successfully!")

        # Step 3: Run agent to create and execute a Python file
        print("\n[Step 3] Running agent to create and run a Python file...")
        print("-" * 40)

        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Create a Python file called 'hello.py' that prints "
                            "'Hello from LangChain Agent!', then run it to verify it works."
                        ),
                    }
                ]
            }
        )

        # Get the last message from the agent
        last_message = result["messages"][-1].content
        print("-" * 40)
        print(f"\nAgent output: {last_message}")

        # Step 4: Run agent for a more complex task
        print("\n[Step 4] Running agent for a more complex task...")
        print("-" * 40)

        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Create a Python file called 'calculator.py' with a function "
                            "called 'add' that adds two numbers, then test it by running: "
                            'python -c "from calculator import add; print(add(3, 5))"'
                        ),
                    }
                ]
            }
        )

        last_message = result["messages"][-1].content
        print("-" * 40)
        print(f"\nAgent output: {last_message}")

        # Step 5: Commit changes with agent
        print("\n[Step 5] Committing changes with agent...")
        print("-" * 40)

        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": "Commit all changes with the message 'Add files created by LangChain agent'",
                    }
                ]
            }
        )

        last_message = result["messages"][-1].content
        print("-" * 40)
        print(f"\nAgent output: {last_message}")

    # Context manager automatically cleans up here
    print("\n[Workspace context closed]")

    print("\n" + "=" * 50)
    print("Example completed!")


if __name__ == "__main__":
    main()
