"""Task for configuring systemd services for Enferno."""

from rich.console import Console

from enferno_cli.core.task import Task

console = Console()


class ServiceTask(Task):
    """Task for setting up systemd services."""

    name = "service"
    description = "Configure systemd services for Enferno"
    depends_on = ["enferno"]

    def run(self) -> bool:
        """Run the task."""
        console.print("[cyan]Configuring systemd services for Enferno...[/]")
        
        # Create service file for Enferno
        service_file = self.renderer.render_to_file("enferno.service")
        
        if not self.ssh.upload_file(service_file, "/tmp/enferno.service"):
            console.print("[bold red]Failed to upload enferno.service[/]")
            return False
        
        if not self.sudo_execute("mv /tmp/enferno.service /etc/systemd/system/enferno.service"):
            console.print("[bold red]Failed to move enferno.service[/]")
            return False
        
        # Set permissions
        if not self.sudo_execute("chmod 644 /etc/systemd/system/enferno.service"):
            console.print("[bold red]Failed to set permissions on enferno.service[/]")
            return False
        
        # Enable service
        if not self.sudo_execute("systemctl enable enferno"):
            console.print("[bold red]Failed to enable enferno service[/]")
            return False
        
        # Setup celery service
        if not self._setup_celery_service():
            return False
        
        # Reload systemd
        if not self.sudo_execute("systemctl daemon-reload"):
            console.print("[bold red]Failed to reload systemd[/]")
            return False
        
        # Start services
        if not self.start_services():
            return False
        
        console.print("[green]Successfully configured systemd services for Enferno[/]")
        return True

    def _setup_celery_service(self) -> bool:
        """Setup celery service for Enferno."""
        console.print("[cyan]Setting up celery service for Enferno...[/]")
        
        # Create celery service file
        celery_service_file = self.renderer.render_to_file("clry.service")
        
        if not self.ssh.upload_file(celery_service_file, "/tmp/clry.service"):
            console.print("[bold red]Failed to upload clry.service[/]")
            return False
        
        if not self.sudo_execute("mv /tmp/clry.service /etc/systemd/system/clry.service"):
            console.print("[bold red]Failed to move clry.service[/]")
            return False
        
        # Set permissions
        if not self.sudo_execute("chmod 644 /etc/systemd/system/clry.service"):
            console.print("[bold red]Failed to set permissions on clry.service[/]")
            return False
        
        # Enable service
        if not self.sudo_execute("systemctl enable clry"):
            console.print("[bold red]Failed to enable clry service[/]")
            return False
        
        console.print("[green]Successfully set up celery service for Enferno[/]")
        return True
        
    def start_services(self) -> bool:
        """Start Enferno and Celery services."""
        console.print("[cyan]Starting Enferno and Celery services...[/]")
        
        # Start Enferno service
        if not self.sudo_execute("systemctl start enferno"):
            console.print("[bold red]Failed to start enferno service[/]")
            return False
            
        # Start Celery service
        if not self.sudo_execute("systemctl start clry"):
            console.print("[bold red]Failed to start celery service[/]")
            return False
            
        # Ensure Nginx is running
        if not self.sudo_execute("systemctl restart nginx"):
            console.print("[bold red]Failed to restart nginx service[/]")
            return False
            
        console.print("[green]Successfully started all services[/]")
        return True 