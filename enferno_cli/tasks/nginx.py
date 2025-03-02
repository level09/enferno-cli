"""Task for configuring Nginx web server."""

import os
from pathlib import Path

from rich.console import Console

from enferno_cli.core.task import Task

console = Console()


class NginxBasicTask(Task):
    """Task for setting up Nginx without SSL."""

    name = "nginx_basic"
    description = "Configure Nginx without SSL"
    depends_on = ["packages"]

    def run(self) -> bool:
        """Run the task."""
        console.print("[cyan]Configuring Nginx without SSL...[/]")
        
        # Remove default nginx configuration
        if not self.sudo_execute("rm -f /etc/nginx/conf.d/default.conf"):
            console.print("[bold red]Failed to remove default nginx configuration[/]")
            return False
        
        # Create nginx.conf
        nginx_conf = self.renderer.render_to_file("nginx.conf.j2")
        if not self.ssh.upload_file(nginx_conf, "/tmp/nginx.conf"):
            console.print("[bold red]Failed to upload nginx.conf[/]")
            return False
        
        if not self.sudo_execute("mv /tmp/nginx.conf /etc/nginx/nginx.conf"):
            console.print("[bold red]Failed to move nginx.conf[/]")
            return False
        
        # Create basic configuration
        basic_conf = self.renderer.render_to_file("basic.conf")
        if not self.ssh.upload_file(basic_conf, f"/tmp/{self.config.server_hostname}.conf"):
            console.print("[bold red]Failed to upload basic configuration[/]")
            return False
        
        if not self.sudo_execute(f"mv /tmp/{self.config.server_hostname}.conf /etc/nginx/conf.d/{self.config.server_hostname}.conf"):
            console.print("[bold red]Failed to move basic configuration[/]")
            return False
        
        # Reload nginx
        if not self.sudo_execute("systemctl reload nginx"):
            console.print("[bold red]Failed to reload nginx[/]")
            return False
        
        console.print("[green]Successfully configured Nginx without SSL[/]")
        return True


class NginxSSLTask(Task):
    """Task for setting up Nginx with SSL."""

    name = "nginx_ssl"
    description = "Configure Nginx with SSL"
    depends_on = ["nginx_basic"]

    def run(self) -> bool:
        """Run the task."""
        # Check if SSL is enabled in the config
        if not self.config.ssl_enabled:
            console.print("[yellow]SSL setup is disabled in configuration. Skipping...[/]")
            return True
            
        # Check if SSL email is provided
        if not self.config.ssl_email:
            console.print("[bold red]SSL email is required for Let's Encrypt. Please provide an email address.[/]")
            return False
            
        console.print("[cyan]Configuring Nginx with SSL...[/]")
        
        # Create initial SSL configuration
        initial_ssl_conf = self.renderer.render_to_file("initial-ssl.conf")
        if not self.ssh.upload_file(initial_ssl_conf, f"/tmp/{self.config.server_hostname}.conf"):
            console.print("[bold red]Failed to upload initial SSL configuration[/]")
            return False
        
        if not self.sudo_execute(f"mv /tmp/{self.config.server_hostname}.conf /etc/nginx/conf.d/{self.config.server_hostname}.conf"):
            console.print("[bold red]Failed to move initial SSL configuration[/]")
            return False
        
        # Reload nginx
        if not self.sudo_execute("systemctl reload nginx"):
            console.print("[bold red]Failed to reload nginx[/]")
            return False
        
        # Install certbot and obtain SSL certificate
        if not self._setup_ssl():
            return False
        
        console.print("[green]Successfully configured Nginx with SSL[/]")
        return True

    def _setup_ssl(self) -> bool:
        """Setup SSL with Certbot."""
        console.print("[cyan]Setting up SSL with Certbot...[/]")
        
        # Install certbot
        if not self.sudo_execute("apt update && apt install -y certbot python3-certbot-nginx"):
            console.print("[bold red]Failed to install certbot[/]")
            return False
        
        # Create webroot directory
        if not self.sudo_execute("mkdir -p /var/www/html/.well-known/acme-challenge"):
            console.print("[bold red]Failed to create webroot directory[/]")
            return False
        
        # Obtain SSL certificate
        certbot_cmd = (
            f"certbot certonly --webroot -w /var/www/html -d {self.config.server_hostname} "
            f"--non-interactive --agree-tos --email {self.config.ssl_email}"
        )
        if not self.sudo_execute(certbot_cmd):
            console.print("[bold red]Failed to obtain SSL certificate[/]")
            return False
        
        # Setup auto-renewal
        cron_cmd = (
            "crontab -l | grep -q 'certbot renew' || "
            "(crontab -l 2>/dev/null; echo '0 0 * * * certbot renew --quiet --no-self-upgrade && systemctl reload nginx') | crontab -"
        )
        if not self.sudo_execute(cron_cmd):
            console.print("[bold red]Failed to setup certbot auto-renewal[/]")
            return False
        
        # Create final nginx configuration
        final_conf = self.renderer.render_to_file("default.conf")
        if not self.ssh.upload_file(final_conf, f"/tmp/{self.config.server_hostname}.conf"):
            console.print("[bold red]Failed to upload final nginx configuration[/]")
            return False
        
        if not self.sudo_execute(f"mv /tmp/{self.config.server_hostname}.conf /etc/nginx/conf.d/{self.config.server_hostname}.conf"):
            console.print("[bold red]Failed to move final nginx configuration[/]")
            return False
        
        # Reload nginx
        if not self.sudo_execute("systemctl reload nginx"):
            console.print("[bold red]Failed to reload nginx[/]")
            return False
        
        console.print("[green]Successfully set up SSL with Certbot[/]")
        return True


class NginxWWWTask(Task):
    """Task for setting up Nginx with SSL and www redirection."""

    name = "nginx_www"
    description = "Configure Nginx with SSL and www redirection"
    depends_on = ["nginx_basic"]

    def run(self) -> bool:
        """Run the task."""
        # Check if SSL is enabled in the config
        if not self.config.ssl_enabled:
            console.print("[yellow]SSL setup is disabled in configuration. Skipping...[/]")
            return True
            
        # Check if SSL email is provided
        if not self.config.ssl_email:
            console.print("[bold red]SSL email is required for Let's Encrypt. Please provide an email address.[/]")
            return False
            
        console.print("[cyan]Configuring Nginx with SSL and www redirection...[/]")
        
        # Create initial SSL configuration
        initial_ssl_conf = self.renderer.render_to_file("initial-ssl.conf")
        if not self.ssh.upload_file(initial_ssl_conf, f"/tmp/{self.config.server_hostname}.conf"):
            console.print("[bold red]Failed to upload initial SSL configuration[/]")
            return False
        
        if not self.sudo_execute(f"mv /tmp/{self.config.server_hostname}.conf /etc/nginx/conf.d/{self.config.server_hostname}.conf"):
            console.print("[bold red]Failed to move initial SSL configuration[/]")
            return False
        
        # Reload nginx
        if not self.sudo_execute("systemctl reload nginx"):
            console.print("[bold red]Failed to reload nginx[/]")
            return False
        
        # Install certbot and obtain SSL certificate for both www and non-www
        if not self._setup_ssl():
            return False
        
        console.print("[green]Successfully configured Nginx with SSL and www redirection[/]")
        return True

    def _setup_ssl(self) -> bool:
        """Setup SSL with Certbot for both www and non-www domains."""
        console.print("[cyan]Setting up SSL with Certbot...[/]")
        
        # Install certbot
        if not self.sudo_execute("apt update && apt install -y certbot python3-certbot-nginx"):
            console.print("[bold red]Failed to install certbot[/]")
            return False
        
        # Create webroot directory
        if not self.sudo_execute("mkdir -p /var/www/html/.well-known/acme-challenge"):
            console.print("[bold red]Failed to create webroot directory[/]")
            return False
        
        # Obtain SSL certificate for both www and non-www
        certbot_cmd = (
            f"certbot certonly --webroot -w /var/www/html -d {self.config.server_hostname} "
            f"-d www.{self.config.server_hostname} "
            f"--non-interactive --agree-tos --email {self.config.ssl_email}"
        )
        if not self.sudo_execute(certbot_cmd):
            console.print("[bold red]Failed to obtain SSL certificate[/]")
            return False
        
        # Setup auto-renewal
        cron_cmd = (
            "crontab -l | grep -q 'certbot renew' || "
            "(crontab -l 2>/dev/null; echo '0 0 * * * certbot renew --quiet --no-self-upgrade && systemctl reload nginx') | crontab -"
        )
        if not self.sudo_execute(cron_cmd):
            console.print("[bold red]Failed to setup certbot auto-renewal[/]")
            return False
        
        # Create final nginx configuration with www redirection
        final_conf = self.renderer.render_to_file("ssl.conf")
        if not self.ssh.upload_file(final_conf, f"/tmp/{self.config.server_hostname}.conf"):
            console.print("[bold red]Failed to upload final nginx configuration[/]")
            return False
        
        if not self.sudo_execute(f"mv /tmp/{self.config.server_hostname}.conf /etc/nginx/conf.d/{self.config.server_hostname}.conf"):
            console.print("[bold red]Failed to move final nginx configuration[/]")
            return False
        
        # Reload nginx
        if not self.sudo_execute("systemctl reload nginx"):
            console.print("[bold red]Failed to reload nginx[/]")
            return False
        
        console.print("[green]Successfully set up SSL with Certbot for www and non-www domains[/]")
        return True


# For backward compatibility
class NginxTask(NginxSSLTask):
    """Task for setting up Nginx with SSL (legacy)."""

    name = "nginx"
    description = "Configure Nginx with SSL"
    depends_on = ["packages"] 