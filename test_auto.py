"""Test barista with automated input."""

import asyncio
import sys
from io import StringIO

from examples.barista import main

async def test():
    # Mock input
    inputs = iter(["I want an espresso", "small", "/quit"])
    
    def mock_input(prompt):
        try:
            return next(inputs)
        except StopIteration:
            return "/quit"
    
    # Replace input
    original_input = __builtins__['input']
    __builtins__['input'] = mock_input
    
    try:
        await main()
    finally:
        __builtins__['input'] = original_input

if __name__ == "__main__":
    asyncio.run(test())