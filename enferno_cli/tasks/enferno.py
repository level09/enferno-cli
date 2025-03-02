"""Task for setting up Enferno application."""

import os
from pathlib import Path

from rich.console import Console

from enferno_cli.core.task import Task

console = Console()


class EnfernoTask(Task):
    """Task for setting up Enferno application."""

    name = "enferno"
    description = "Download and set up Enferno application"
    depends_on = ["user", "packages", "python"]  # Added python dependency to ensure modern Python is installed

    def run(self) -> bool:
        """Run the task."""
        console.print("[cyan]Setting up Enferno application...[/]")
        
        # Create app directory
        app_dir = f"/home/{self.config.user_name}/{self.config.server_hostname}"
        if not self.sudo_execute(f"mkdir -p {app_dir}"):
            console.print("[bold red]Failed to create app directory[/]")
            return False
        
        # Set ownership
        if not self.sudo_execute(f"chown -R {self.config.user_name}:{self.config.user_name} {app_dir}"):
            console.print("[bold red]Failed to set ownership of app directory[/]")
            return False
        
        # Check if directory is empty before cloning
        check_dir_cmd = f"sudo -u {self.config.user_name} bash -c 'ls -A {app_dir} | wc -l'"
        exit_code, stdout, stderr = self.ssh.execute(check_dir_cmd, sudo=True)
        
        if exit_code == 0 and stdout.strip() != "0":
            console.print(f"[yellow]Warning: Directory {app_dir} is not empty. Cleaning directory before cloning...[/]")
            clean_dir_cmd = f"sudo -u {self.config.user_name} bash -c 'rm -rf {app_dir}/*'"
            self.sudo_execute(clean_dir_cmd)
            
            # Also check for hidden files
            clean_hidden_cmd = f"sudo -u {self.config.user_name} bash -c 'rm -rf {app_dir}/.[!.]*'"
            self.sudo_execute(clean_hidden_cmd)
        
        # Clone Enferno repository - using a proper shell command with cd
        console.print("[cyan]Cloning Enferno repository...[/]")
        clone_cmd = f"sudo -u {self.config.user_name} bash -c 'cd {app_dir} && git clone https://github.com/level09/enferno.git .'"
        exit_code, stdout, stderr = self.ssh.execute(clone_cmd, sudo=True)
        
        if exit_code != 0:
            console.print("[bold red]Failed to clone Enferno repository[/]")
            if stderr:
                console.print(f"[red]Git error: {stderr}[/]")
            
            # Try alternative approach if it looks like a network issue
            if "Could not resolve host" in stderr or "Connection timed out" in stderr:
                console.print("[yellow]Network issue detected. Trying with git protocol...[/]")
                alt_clone_cmd = f"sudo -u {self.config.user_name} bash -c 'cd {app_dir} && git clone git://github.com/level09/enferno.git .'"
                alt_exit_code, alt_stdout, alt_stderr = self.ssh.execute(alt_clone_cmd, sudo=True)
                
                if alt_exit_code != 0:
                    console.print("[bold red]Alternative clone method also failed[/]")
                    if alt_stderr:
                        console.print(f"[red]Git error: {alt_stderr}[/]")
                    return False
                else:
                    console.print("[green]Successfully cloned repository with alternative method[/]")
            else:
                return False
        else:
            console.print("[green]Successfully cloned Enferno repository[/]")
            if stdout:
                console.print(stdout)
        
        # Run setup script - using a proper shell command with cd and capturing output
        console.print("[cyan]Running Enferno setup script...[/]")
        setup_cmd = f"sudo -u {self.config.user_name} bash -c 'cd {app_dir} && ./setup.sh'"
        exit_code, stdout, stderr = self.ssh.execute(setup_cmd, sudo=True)
        
        # Display the output
        if stdout:
            console.print("[dim]Setup script output:[/]")
            console.print(stdout)
        
        if stderr:
            console.print("[yellow]Setup script errors:[/]")
            console.print(stderr)
        
        if exit_code != 0:
            console.print("[bold red]Failed to run Enferno setup script[/]")
            return False
        else:
            console.print("[green]Successfully ran Enferno setup script[/]")
        
        # Note about database usage
        if self.config.postgres_enabled:
            console.print("[cyan]PostgreSQL is enabled. Make sure to update the .env file to use PostgreSQL.[/]")
            console.print("[cyan]The database task will create a PostgreSQL database with superuser privileges.[/]")
        else:
            console.print("[cyan]PostgreSQL is not enabled. Enferno will use SQLite by default.[/]")
        
        # Run flask create-db command to initialize the database
        console.print("[cyan]Initializing database with flask create-db...[/]")
        
        create_db_cmd = f"sudo -u {self.config.user_name} bash -c 'cd {app_dir} && source env/bin/activate && flask create-db'"
        exit_code, stdout, stderr = self.ssh.execute(create_db_cmd, sudo=True)
        if exit_code != 0:
            console.print(f"[yellow]Warning: Failed to run flask create-db command. Error: {stderr}[/]")
            console.print("[yellow]Attempting alternative method to initialize the database...[/]")
            
            # Try an alternative approach - sometimes the command needs to be run from a specific directory
            alt_cmd = f"sudo -u {self.config.user_name} bash -c 'cd {app_dir} && source env/bin/activate && FLASK_APP=run.py flask create-db'"
            alt_exit_code, alt_stdout, alt_stderr = self.ssh.execute(alt_cmd, sudo=True)
            if alt_exit_code != 0:
                console.print(f"[yellow]Alternative method also failed. Error: {alt_stderr}[/]")
                console.print("[yellow]You may need to initialize the database manually after setup:[/]")
                console.print(f"[bold]cd {app_dir} && source env/bin/activate && flask create-db[/]")
                # Continue anyway, as this might not be critical
            else:
                console.print("[green]Successfully initialized database with alternative method[/]")
                if alt_stdout:
                    console.print(alt_stdout)
        else:
            console.print("[green]Successfully initialized database[/]")
            if stdout:
                console.print(stdout)
        
        console.print("[green]Successfully set up Enferno application[/]")
        return True