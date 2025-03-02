"""Task for setting up PostgreSQL database."""

import time
from typing import Optional

from rich.console import Console

from enferno_cli.core.task import Task

console = Console()


class DatabaseTask(Task):
    """Task for setting up PostgreSQL database for Enferno."""

    name = "database"
    description = "Set up PostgreSQL database for Enferno"
    depends_on = ["packages", "user"]

    def run(self) -> bool:
        """Run the task."""
        # Check if PostgreSQL is enabled in the config
        if not self.config.postgres_enabled:
            console.print("[yellow]PostgreSQL setup is disabled in configuration. Skipping...[/]")
            return True
            
        console.print("[cyan]Setting up PostgreSQL database for Enferno...[/]")
        
        # Check if PostgreSQL is installed
        console.print("[cyan]Checking if PostgreSQL is installed...[/]")
        exit_code, stdout, stderr = self.ssh.execute("command -v psql", sudo=True)
        
        # Install PostgreSQL if not installed
        if exit_code != 0:
            console.print("[yellow]PostgreSQL is not installed. Installing PostgreSQL...[/]")
            install_cmd = "apt update && apt install -y postgresql postgresql-contrib"
            install_exit_code, install_stdout, install_stderr = self.ssh.execute(install_cmd, sudo=True)
            
            if install_exit_code != 0:
                console.print(f"[bold red]Failed to install PostgreSQL. Error: {install_stderr}[/]")
                return False
            else:
                console.print("[green]PostgreSQL installed successfully[/]")
        else:
            console.print("[green]PostgreSQL is already installed[/]")
            
        # Check PostgreSQL service status without using status (which uses a pager)
        console.print("[cyan]Checking PostgreSQL service status...[/]")
        exit_code, stdout, stderr = self.ssh.execute("systemctl is-active postgresql", sudo=True)
        console.print(f"[cyan]PostgreSQL status: {stdout.strip()}[/]")
        
        if exit_code != 0 or stdout.strip() != "active":
            console.print("[bold red]PostgreSQL service is not running. Attempting to start it...[/]")
            
            # Try to start PostgreSQL service
            start_exit_code, start_stdout, start_stderr = self.ssh.execute("systemctl start postgresql", sudo=True)
            if start_exit_code != 0:
                console.print(f"[bold red]Failed to start PostgreSQL service. Error: {start_stderr}[/]")
                console.print("[yellow]You may need to fix PostgreSQL manually:[/]")
                console.print("[bold]sudo systemctl start postgresql[/]")
                return False
            
            # Check again if it's running
            check_exit_code, check_stdout, check_stderr = self.ssh.execute("systemctl is-active postgresql", sudo=True)
            if check_exit_code != 0 or check_stdout.strip() != "active":
                console.print("[bold red]PostgreSQL service failed to start properly.[/]")
                return False
            else:
                console.print("[green]PostgreSQL service started successfully[/]")
        
        # Test PostgreSQL connection with a simple query that won't produce much output
        console.print("[cyan]Testing PostgreSQL connection...[/]")
        test_cmd = "sudo -u postgres psql -c \"SELECT 1;\" -t"
        test_exit_code, test_stdout, test_stderr = self.ssh.execute(test_cmd, sudo=True)
        if test_exit_code != 0:
            console.print(f"[bold red]Failed to connect to PostgreSQL. Error: {test_stderr}[/]")
            console.print("[yellow]PostgreSQL may be installed but not functioning correctly.[/]")
            console.print("[yellow]You may need to reinstall PostgreSQL:[/]")
            console.print("[bold]sudo apt purge postgresql postgresql-contrib[/]")
            console.print("[bold]sudo apt install postgresql postgresql-contrib[/]")
            return False
        else:
            console.print("[green]PostgreSQL connection successful[/]")
        
        # Create database user with superuser privileges
        console.print("[cyan]Creating database user with superuser privileges...[/]")
        create_user_cmd = (
            f"sudo -u postgres psql -c \"CREATE USER {self.config.user_name} WITH SUPERUSER PASSWORD '{self.config.password}';\""
        )
        exit_code, stdout, stderr = self.ssh.execute(create_user_cmd, sudo=True)
        
        if exit_code != 0:
            console.print(f"[yellow]Could not create user. Error: {stderr}[/]")
            console.print("[yellow]Checking if user already exists...[/]")
            
            # Check if user already exists
            check_user_cmd = (
                f"sudo -u postgres psql -c \"SELECT 1 FROM pg_roles WHERE rolname='{self.config.user_name}';\""
            )
            exit_code, stdout, stderr = self.ssh.execute(check_user_cmd, sudo=True)
            
            if exit_code == 0 and "1 row" in stdout:
                console.print(f"[yellow]User {self.config.user_name} already exists, updating privileges and password...[/]")
                # Update user to have superuser privileges
                alter_user_cmd = (
                    f"sudo -u postgres psql -c \"ALTER USER {self.config.user_name} WITH SUPERUSER PASSWORD '{self.config.password}';\""
                )
                exit_code, stdout, stderr = self.ssh.execute(alter_user_cmd, sudo=True)
                if exit_code != 0:
                    console.print(f"[bold red]Failed to update user privileges and password. Error: {stderr}[/]")
                    return False
            else:
                console.print(f"[bold red]Failed to create database user. Error: {stderr}[/]")
                return False
        
        # Check if database already exists
        console.print("[cyan]Checking if database already exists...[/]")
        check_db_cmd = (
            f"sudo -u postgres psql -c \"SELECT 1 FROM pg_database WHERE datname='{self.config.user_name}';\""
        )
        exit_code, stdout, stderr = self.ssh.execute(check_db_cmd, sudo=True)
        
        if exit_code == 0 and "1 row" in stdout:
            console.print(f"[yellow]Database {self.config.user_name} already exists[/]")
        else:
            # Create database
            console.print(f"[cyan]Creating database {self.config.user_name}...[/]")
            create_db_cmd = (
                f"sudo -u postgres psql -c \"CREATE DATABASE {self.config.user_name} OWNER {self.config.user_name};\""
            )
            exit_code, stdout, stderr = self.ssh.execute(create_db_cmd, sudo=True)
            if exit_code != 0:
                console.print(f"[bold red]Failed to create database. Error: {stderr}[/]")
                return False
        
        # Grant privileges
        console.print("[cyan]Granting privileges on database...[/]")
        grant_cmd = (
            f"sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE {self.config.user_name} TO {self.config.user_name};\""
        )
        exit_code, stdout, stderr = self.ssh.execute(grant_cmd, sudo=True)
        if exit_code != 0:
            console.print(f"[bold red]Failed to grant privileges. Error: {stderr}[/]")
            return False
        
        # Configure PostgreSQL to allow password authentication for the user
        console.print("[cyan]Configuring PostgreSQL authentication...[/]")
        pg_hba_cmd = (
            f"sudo -u postgres psql -c \"ALTER USER {self.config.user_name} WITH PASSWORD '{self.config.password}';\""
        )
        exit_code, stdout, stderr = self.ssh.execute(pg_hba_cmd, sudo=True)
        if exit_code != 0:
            console.print(f"[yellow]Failed to update authentication method, but continuing... Error: {stderr}[/]")
        
        console.print(f"[green]Successfully set up PostgreSQL database for {self.config.user_name} with superuser privileges[/]")
        return True 