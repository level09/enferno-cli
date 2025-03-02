"""Command-line interface for Enferno server setup."""

import sys
from typing import List, Optional

import click
from rich.console import Console

from enferno_cli.core.config import ServerConfig
from enferno_cli.core.manager import TaskManager

console = Console()


@click.group()
@click.version_option()
def cli():
    """Enferno CLI - A Python tool for setting up Ubuntu servers with the Enferno framework."""
    pass


@cli.command()
@click.option(
    "--host",
    help="Server IP or hostname",
    required=False,
)
@click.option(
    "--env-file",
    help="Path to .env file with configuration",
    default=".env",
    show_default=True,
)
@click.option(
    "--interactive/--no-interactive",
    help="Run in interactive mode",
    default=None,
)
@click.option(
    "--ssh-key",
    help="Path to SSH key",
    default=None,
)
@click.option(
    "--ssh-port",
    help="SSH port",
    type=int,
    default=None,
)
@click.option(
    "--tasks",
    help="Comma-separated list of tasks to run (add 'database' explicitly if you want to set up PostgreSQL outside of interactive mode)",
    default=None,
)
@click.option(
    "--user",
    help="Initial SSH user (usually root or ubuntu)",
    default=None,
)
@click.option(
    "--skip-ssl",
    is_flag=True,
    help="Skip SSL setup (useful when DNS is not yet configured)",
    default=False,
)
@click.option(
    "--use-www",
    is_flag=True,
    help="Redirect to www subdomain (e.g., example.com → www.example.com)",
    default=False,
)
@click.option(
    "--postgres",
    is_flag=True,
    help="Set up PostgreSQL database",
    default=False,
)
def setup(
    host: Optional[str],
    env_file: str,
    interactive: Optional[bool],
    ssh_key: Optional[str],
    ssh_port: Optional[int],
    tasks: Optional[str],
    user: Optional[str],
    skip_ssl: bool,
    use_www: bool,
    postgres: bool,
):
    """Set up a server with Enferno framework."""
    # Try to load configuration from .env file
    config = ServerConfig.from_env(env_file)
    
    # If no config or interactive mode is requested, run interactive setup
    if config is None or interactive:
        console.print("[yellow]No configuration found or interactive mode requested.[/]")
        config = ServerConfig.interactive(host, env_file, skip_ssl)
    else:
        # Update config with command-line options
        if host:
            config.host = host
        if ssh_key:
            config.ssh_key_path = ssh_key
        if ssh_port:
            config.ssh_port = ssh_port
        if user:
            config.ansible_user = user
        if postgres:
            config.postgres_enabled = True
            if "database" not in config.selected_tasks and not tasks:
                config.selected_tasks.append("database")
        if use_www:
            config.use_www = True
    
    # Validate configuration
    if not config.host:
        console.print("[bold red]Error: No host specified[/]")
        sys.exit(1)
    
    # Simple fix for tasks parsing - ensure we don't have empty strings or '[]'
    if tasks == "[]" or tasks == "":
        config.selected_tasks = []
    elif tasks:
        # Fix: properly parse the comma-separated list without adding quotes
        config.selected_tasks = [t.strip() for t in tasks.split(",") if t.strip() and t != "[]"]
    
    # Handle SSL skip option
    if skip_ssl and not tasks:
        # If tasks are not explicitly specified, replace 'nginx' or 'nginx_ssl' or 'nginx_www' with 'nginx_basic'
        if not config.selected_tasks:
            # Get all available tasks
            manager = TaskManager(config)
            all_tasks = manager.get_task_names()
            # Filter out nginx tasks
            config.selected_tasks = [t for t in all_tasks if t not in ["nginx", "nginx_ssl", "nginx_www"]]
            # Add nginx_basic
            config.selected_tasks.append("nginx_basic")
        else:
            # Replace nginx tasks with nginx_basic in the selected tasks
            config.selected_tasks = [
                "nginx_basic" if t in ["nginx", "nginx_ssl", "nginx_www"] else t 
                for t in config.selected_tasks
            ]
        console.print("[yellow]Skipping SSL setup as requested[/]")
    elif not skip_ssl and not tasks and config.ssl_enabled:
        # If SSL is enabled and tasks are not explicitly specified, ensure the correct nginx task is used
        if config.use_www and "nginx_www" not in config.selected_tasks:
            # Replace nginx and nginx_ssl with nginx_www
            config.selected_tasks = [
                "nginx_www" if t in ["nginx", "nginx_ssl"] else t 
                for t in config.selected_tasks
            ]
            console.print("[yellow]Using www redirection as requested[/]")
    
    # Validate selected tasks
    config.validate_selected_tasks()
    
    # Run setup
    manager = TaskManager(config)
    success = manager.run_setup()
    
    if not success:
        sys.exit(1)
    
    # Print success message
    console.print("\n[bold green]✓ Setup completed successfully![/]")
    console.print("[bold green]✓ Enferno application is now running![/]")
    
    # Print URL based on SSL and www settings
    if config.ssl_enabled:
        if config.use_www:
            console.print(f"[bold green]✓ Your application is available at: https://www.{config.server_hostname}[/]")
        else:
            console.print(f"[bold green]✓ Your application is available at: https://{config.server_hostname}[/]")
    else:
        console.print(f"[bold green]✓ Your application is available at: http://{config.server_hostname}[/]")
    
    # Print next steps if SSL was skipped
    if skip_ssl:
        console.print("\n[bold]Next Steps:[/]")
        console.print("1. Configure DNS to point your domain to this server")
        console.print("2. Once DNS has propagated, run the SSL setup:")
        if config.use_www:
            console.print(f"   [cyan]python -m enferno_cli setup --tasks=nginx_www --host={config.host}[/]")
        else:
            console.print(f"   [cyan]python -m enferno_cli setup --tasks=nginx_ssl --host={config.host}[/]")
        console.print("3. Your application will then be available at:")
        if config.use_www:
            console.print(f"   [cyan]https://www.{config.server_hostname}[/]")
        else:
            console.print(f"   [cyan]https://{config.server_hostname}[/]")


@cli.command()
def list_tasks():
    """List available tasks for Enferno server setup."""
    # Create a dummy config for task discovery
    config = ServerConfig(
        host="localhost",
        server_hostname="example.com",
        user_name="user",
        password="password",
    )
    
    manager = TaskManager(config)
    tasks = manager.get_task_names()
    
    console.print("[bold]Available tasks for Enferno server setup:[/]")
    for task in sorted(tasks):
        console.print(f"- {task}")


def main():
    """Main entry point for the Enferno CLI."""
    cli()


if __name__ == "__main__":
    main() 