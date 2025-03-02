"""Task manager for server setup."""

import importlib
import pkgutil
from typing import Dict, List, Optional, Type

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from enferno_cli.core.config import ServerConfig
from enferno_cli.core.ssh import SSHClient
from enferno_cli.core.task import Task

console = Console()


class TaskManager:
    """Task manager for server setup."""

    def __init__(self, config: ServerConfig):
        """Initialize the task manager.

        Args:
            config: Server configuration.
        """
        self.config = config
        self.ssh = SSHClient(config)
        self.tasks: Dict[str, Type[Task]] = {}
        self.executed_tasks: List[str] = []
        self._discover_tasks()

    def _discover_tasks(self) -> None:
        """Discover available tasks."""
        import enferno_cli.tasks

        # Find all modules in the tasks package
        for _, name, _ in pkgutil.iter_modules(enferno_cli.tasks.__path__):
            # Import the module
            module = importlib.import_module(f"enferno_cli.tasks.{name}")
            
            # Find all classes in the module that are subclasses of Task
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, Task)
                    and attr is not Task
                    and hasattr(attr, "name")
                ):
                    self.tasks[attr.name] = attr
        
        console.print(f"[green]Discovered {len(self.tasks)} tasks[/]")

    def get_task_names(self) -> List[str]:
        """Get names of all available tasks.
        
        Returns:
            List of task names
        """
        return list(self.tasks.keys())

    def get_task_dependencies(self, task_name: str) -> List[str]:
        """Get dependencies for a task.
        
        Args:
            task_name: Name of the task
            
        Returns:
            List of task names that this task depends on
        """
        if task_name not in self.tasks:
            return []
        
        # Get the dependencies
        dependencies = self.tasks[task_name].depends_on
        
        # Filter out the database task if PostgreSQL is not enabled
        if not self.config.postgres_enabled and "database" in dependencies:
            console.print(f"[yellow]Skipping database dependency for {task_name} as PostgreSQL is not enabled[/]")
            dependencies = [dep for dep in dependencies if dep != "database"]
        
        return dependencies

    def run_task(self, task_name: str) -> bool:
        """Run a single task.
        
        Args:
            task_name: Name of the task to run
            
        Returns:
            True if the task was successful, False otherwise
        """
        # Skip the database task if PostgreSQL is not enabled
        if task_name == "database" and not self.config.postgres_enabled:
            console.print("[yellow]Skipping database task as PostgreSQL is not enabled[/]")
            return True
            
        if task_name not in self.tasks:
            console.print(f"[bold red]Task not found: {task_name}[/]")
            return False
        
        # Check if task has already been executed
        if task_name in self.executed_tasks:
            console.print(f"[yellow]Task already executed: {task_name}[/]")
            return True
        
        # Run dependencies first
        for dep in self.get_task_dependencies(task_name):
            if not self.run_task(dep):
                console.print(f"[bold red]Dependency failed: {dep} for task {task_name}[/]")
                return False
        
        # Create and run the task
        task_class = self.tasks[task_name]
        task = task_class(self.config, self.ssh)
        
        success = task.execute()
        if success:
            self.executed_tasks.append(task_name)
        
        return success

    def run_all_tasks(self) -> bool:
        """Run all tasks.
        
        Returns:
            True if all tasks were successful, False otherwise
        """
        # If specific tasks are selected, run only those
        if self.config.selected_tasks:
            # Check if any selected tasks don't exist
            unknown_tasks = [task for task in self.config.selected_tasks if task not in self.tasks]
            if unknown_tasks:
                console.print(f"[bold red]Task not found: {unknown_tasks}[/]")
                return False
            
            # Run the selected tasks
            for task_name in self.config.selected_tasks:
                if not self.run_task(task_name):
                    return False
            return True
        
        # Otherwise run all tasks except database (which is optional) unless postgres_enabled is True
        all_success = True
        for task_name in self.get_task_names():
            if task_name != "database" or self.config.postgres_enabled:  # Skip database task by default unless postgres_enabled
                if not self.run_task(task_name):
                    all_success = False
        
        return all_success

    def run_setup(self) -> bool:
        """Run the server setup.
        
        Returns:
            True if setup was successful, False otherwise
        """
        console.print("[bold]Starting server setup[/]")
        console.print(f"Server: {self.config.host}")
        console.print(f"Hostname: {self.config.server_hostname}")
        
        # Connect to the server
        if not self.ssh.connect():
            return False
        
        try:
            # Run all tasks
            success = self.run_all_tasks()
            
            if success:
                console.print("[bold green]Server setup completed successfully![/]")
            else:
                console.print("[bold red]Server setup failed![/]")
            
            return success
        finally:
            # Disconnect from the server
            self.ssh.disconnect() 