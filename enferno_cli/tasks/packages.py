"""Task for installing essential packages."""

from rich.console import Console

from enferno_cli.core.task import Task

console = Console()


class PackagesTask(Task):
    """Task for installing essential packages."""

    name = "packages"
    description = "Install essential packages"
    depends_on = []

    def run(self) -> bool:
        """Run the task."""
        console.print("[cyan]Updating apt cache and installing essential packages...[/]")
        
        # Update apt cache
        if not self.sudo_execute("apt update"):
            console.print("[bold red]Failed to update apt cache[/]")
            return False
        
        # Define essential packages
        essential_packages = [
            "build-essential",
            "python3-dev",
            "libjpeg8-dev",
            "libzip-dev",
            "libffi-dev",
            "libxslt1-dev",
            "python3-pip",
            "git",
            "redis-server",
            "python3-venv",
            "nginx",
        ]
        
        # Add PostgreSQL packages if enabled
        if self.config.postgres_enabled:
            console.print("[cyan]PostgreSQL setup is enabled, including PostgreSQL packages...[/]")
            postgresql_packages = [
                "libpq-dev",
                "postgresql",
                "postgresql-contrib",
            ]
            essential_packages.extend(postgresql_packages)
        else:
            console.print("[cyan]PostgreSQL setup is disabled, skipping PostgreSQL packages...[/]")
        
        # Install packages
        install_cmd = f"apt install -y {' '.join(essential_packages)}"
        if not self.sudo_execute(install_cmd):
            console.print("[bold red]Failed to install packages[/]")
            return False
        
        # Configure PostgreSQL if enabled
        if self.config.postgres_enabled:
            console.print("[cyan]Ensuring PostgreSQL is started and enabled...[/]")
            
            # Enable PostgreSQL service first
            if not self.sudo_execute("systemctl enable postgresql"):
                console.print("[yellow]Failed to enable PostgreSQL service[/]")
            
            # Start PostgreSQL service
            if not self.sudo_execute("systemctl start postgresql"):
                console.print("[yellow]Failed to start PostgreSQL service[/]")
                return False
            
            # Check PostgreSQL status using is-active (non-interactive)
            exit_code, stdout, stderr = self.ssh.execute("systemctl is-active postgresql", sudo=True)
            if exit_code == 0 and stdout.strip() == "active":
                console.print("[green]PostgreSQL is running correctly[/]")
            else:
                console.print("[yellow]PostgreSQL may not be running correctly, but continuing with setup[/]")
                console.print("[yellow]You may need to troubleshoot PostgreSQL after setup completes[/]")
        
        console.print("[green]Successfully installed essential packages[/]")
        return True