"""Base task class for server setup tasks."""

from abc import ABC, abstractmethod
from typing import List, Optional

from rich.console import Console

from enferno_cli.core.config import ServerConfig
from enferno_cli.core.ssh import SSHClient
from enferno_cli.core.templates import TemplateRenderer

console = Console()


class Task(ABC):
    """Base class for server setup tasks."""

    name: str = "base_task"
    description: str = "Base task class"
    depends_on: List[str] = []

    def __init__(self, config: ServerConfig, ssh: SSHClient):
        """Initialize task with server configuration and SSH client."""
        self.config = config
        self.ssh = ssh
        self.renderer = TemplateRenderer(config)
        self.success = False

    @abstractmethod
    def run(self) -> bool:
        """Run the task.
        
        Returns:
            True if the task was successful, False otherwise
        """
        pass

    def pre_run(self) -> bool:
        """Run before the main task.
        
        Returns:
            True if pre-run was successful, False otherwise
        """
        return True

    def post_run(self) -> bool:
        """Run after the main task.
        
        Returns:
            True if post-run was successful, False otherwise
        """
        return True

    def execute(self) -> bool:
        """Execute the task with pre and post hooks.
        
        Returns:
            True if the task was successful, False otherwise
        """
        console.print(f"[bold cyan]Running task: {self.name}[/]")
        console.print(f"[dim]{self.description}[/]")

        # Run pre-task
        if not self.pre_run():
            console.print(f"[bold red]Pre-run failed for task: {self.name}[/]")
            return False

        # Run main task
        self.success = self.run()
        if not self.success:
            console.print(f"[bold red]Task failed: {self.name}[/]")
            return False

        # Run post-task
        if not self.post_run():
            console.print(f"[bold red]Post-run failed for task: {self.name}[/]")
            return False

        console.print(f"[bold green]Task completed successfully: {self.name}[/]")
        return True

    def sudo_execute(self, command: str) -> bool:
        """Execute a command with sudo.
        
        Args:
            command: Command to execute
            
        Returns:
            True if the command was successful, False otherwise
        """
        exit_code, stdout, stderr = self.ssh.execute(command, sudo=True)
        return exit_code == 0

    def execute_command(self, command: str) -> bool:
        """Execute a command without sudo.
        
        Args:
            command: Command to execute
            
        Returns:
            True if the command was successful, False otherwise
        """
        exit_code, stdout, stderr = self.ssh.execute(command)
        return exit_code == 0 