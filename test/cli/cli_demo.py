import asyncio
from pathlib import Path

from pi.coding.main import main_async
from pi.coding.modes import InteractiveModeConfig


def main():

    config = InteractiveModeConfig(
        cwd=Path.cwd(),
        provider="opecode",
        model="glm5",
        thinking_level="",
        messages=parsed.messages,
    )
    interactive_mode = InteractiveMode(config)
    return await interactive_mode.run()


if __name__ == '__main__':
    asyncio.run(main_async(args))