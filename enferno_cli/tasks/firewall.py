"""Task for configuring UFW firewall."""

from rich.console import Console

from enferno_cli.core.task import Task

console = Console()


class FirewallTask(Task):
    """Task for setting up the firewall."""

    name = "firewall"
    description = "Configure UFW firewall"
    depends_on = ["packages"]

    def run(self) -> bool:
        """Run the task."""
        console.print("[cyan]Configuring UFW firewall...[/]")
        
        # Reset UFW
        if not self.sudo_execute("ufw --force reset"):
            console.print("[bold red]Failed to reset UFW[/]")
            return False
        
        # Set default policies
        if not self.sudo_execute("ufw default deny incoming"):
            console.print("[bold red]Failed to set default incoming policy[/]")
            return False
        
        if not self.sudo_execute("ufw default allow outgoing"):
            console.print("[bold red]Failed to set default outgoing policy[/]")
            return False
        
        # Allow SSH
        ssh_port = self.config.ssh_port
        if not self.sudo_execute(f"ufw allow {ssh_port}/tcp"):
            console.print(f"[bold red]Failed to allow SSH on port {ssh_port}[/]")
            return False
        
        # Allow HTTP and HTTPS
        if not self.sudo_execute("ufw allow 80/tcp"):
            console.print("[bold red]Failed to allow HTTP[/]")
            return False
        
        if not self.sudo_execute("ufw allow 443/tcp"):
            console.print("[bold red]Failed to allow HTTPS[/]")
            return False
        
        # Enable UFW
        if not self.sudo_execute("echo 'y' | ufw enable"):
            console.print("[bold red]Failed to enable UFW[/]")
            return False
        
        # Check UFW status
        exit_code, stdout, stderr = self.ssh.execute("sudo ufw status", sudo=True)
        if exit_code != 0:
            console.print("[bold red]Failed to get UFW status[/]")
            return False
        
        console.print(f"[dim]{stdout}[/]")
        console.print("[green]Successfully configured UFW firewall[/]")
        return True 