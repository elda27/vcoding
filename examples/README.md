# vcoding Examples

This directory contains example scripts demonstrating vcoding usage.

## Running Examples

```bash
# Install vcoding first
pip install -e .

# Run an example
python examples/01_simple_oneshot_api.py
```

## Examples

| Example                                                | Goal                   | Description                                                                    |
| ------------------------------------------------------ | ---------------------- | ------------------------------------------------------------------------------ |
| [01_simple_oneshot_api.py](01_simple_oneshot_api.py)   | Simple code generation | Generate code with a single function call without lifecycle management         |
| [02_context_manager_api.py](02_context_manager_api.py) | Multiple operations    | Use context manager for automatic resource management with multiple operations |
| [03_langchain_api.py](03_langchain_api.py)             | LangChain integration  | Use vcoding as LangChain tools for AI agent workflows                          |
