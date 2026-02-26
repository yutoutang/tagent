"""Bash command execution for pi-coding.

Converted from TypeScript core/bash-executor.ts
"""
import asyncio
import shlex
from typing import Any, Optional
from pathlib import Path


class BashExecutor:
    """Executes bash commands and returns output."""

    def __init__(self, cwd: Optional[str | Path] = None):
        """
        Initialize the bash executor.

        Args:
            cwd: Working directory for commands (default: current directory)
        """
        self.cwd = Path(cwd) if cwd else Path.cwd()

    async def execute(
        self,
        command: str,
        timeout: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Execute a bash command.

        Args:
            command: Command string to execute
            timeout: Optional timeout in seconds

        Returns:
            Dict with keys:
            - exitCode: int
            - stdout: str
            - stderr: str
        """
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.cwd,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )

            return {
                "exitCode": process.returncode or 0,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
            }
        except asyncio.TimeoutError:
            try:
                process.kill()
                await process.wait()
            except:
                pass
            return {
                "exitCode": -1,
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
            }
        except Exception as e:
            return {
                "exitCode": -1,
                "stdout": "",
                "stderr": str(e),
            }

    def execute_sync(self, command: str) -> dict[str, Any]:
        """
        Execute a bash command synchronously.

        Args:
            command: Command string to execute

        Returns:
            Dict with exitCode, stdout, stderr
        """
        import subprocess

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=self.cwd,
                timeout=300,  # 5 minute default
            )
            return {
                "exitCode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except subprocess.TimeoutExpired as e:
            return {
                "exitCode": -1,
                "stdout": e.stdout.decode("utf-8", errors="replace") if e.stdout else "",
                "stderr": e.stderr.decode("utf-8", errors="replace") if e.stderr else "Command timed out",
            }
        except Exception as e:
            return {
                "exitCode": -1,
                "stdout": "",
                "stderr": str(e),
            }


__all__ = ["BashExecutor"]
