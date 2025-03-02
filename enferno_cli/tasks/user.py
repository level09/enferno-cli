"""Task for creating user account with sudo privileges."""

import os
from pathlib import Path

from rich.console import Console

from enferno_cli.core.task import Task

console = Console()


class UserTask(Task):
    """Task for setting up the user account."""

    name = "user"
    description = "Create user account with sudo privileges"
    depends_on = []

    def run(self) -> bool:
        """Run the task."""
        console.print(f"[cyan]Creating user {self.config.user_name}...[/]")
        
        # Create user group
        if not self.sudo_execute(f"groupadd -f {self.config.user_name}"):
            console.print(f"[bold red]Failed to create group {self.config.user_name}[/]")
            return False
        
        # Create user with sudo privileges
        create_user_cmd = (
            f"id -u {self.config.user_name} &>/dev/null || "
            f"useradd -m -s /bin/bash -g {self.config.user_name} -G sudo {self.config.user_name}"
        )
        if not self.sudo_execute(create_user_cmd):
            console.print(f"[bold red]Failed to create user {self.config.user_name}[/]")
            return False
        
        # Set password
        set_password_cmd = f"echo '{self.config.user_name}:{self.config.password}' | chpasswd"
        if not self.sudo_execute(set_password_cmd):
            console.print(f"[bold red]Failed to set password for {self.config.user_name}[/]")
            return False
        
        # Setup SSH key
        self._setup_ssh_key()
        
        # Setup sudoers
        if not self._setup_sudoers():
            return False
        
        console.print(f"[green]Successfully created user {self.config.user_name}[/]")
        return True

    def _setup_ssh_key(self) -> bool:
        """Setup SSH key for the user."""
        # Get local SSH public key
        local_key_path = os.path.expanduser("~/.ssh/id_rsa.pub")
        if not os.path.exists(local_key_path):
            console.print("[yellow]No SSH key found, skipping SSH key setup[/]")
            return True
        
        # Read local SSH key
        with open(local_key_path, "r") as f:
            ssh_key = f.read().strip()
        
        # Create .ssh directory
        ssh_dir = f"/home/{self.config.user_name}/.ssh"
        if not self.sudo_execute(f"mkdir -p {ssh_dir}"):
            console.print(f"[bold red]Failed to create {ssh_dir}[/]")
            return False
        
        # Create authorized_keys file
        auth_keys_path = f"{ssh_dir}/authorized_keys"
        if not self.sudo_execute(f"echo '{ssh_key}' > {auth_keys_path}"):
            console.print(f"[bold red]Failed to create {auth_keys_path}[/]")
            return False
        
        # Set permissions
        if not self.sudo_execute(f"chmod 700 {ssh_dir}"):
            console.print(f"[bold red]Failed to set permissions on {ssh_dir}[/]")
            return False
        
        if not self.sudo_execute(f"chmod 600 {auth_keys_path}"):
            console.print(f"[bold red]Failed to set permissions on {auth_keys_path}[/]")
            return False
        
        if not self.sudo_execute(f"chown -R {self.config.user_name}:{self.config.user_name} {ssh_dir}"):
            console.print(f"[bold red]Failed to set ownership on {ssh_dir}[/]")
            return False
        
        console.print(f"[green]Successfully set up SSH key for {self.config.user_name}[/]")
        return True

    def _setup_sudoers(self) -> bool:
        """Setup sudoers for the user."""
        # Create sudoers.d directory if it doesn't exist
        if not self.sudo_execute("mkdir -p /etc/sudoers.d"):
            console.print("[bold red]Failed to create /etc/sudoers.d[/]")
            return False
        
        # Ensure includedir is in sudoers
        if not self.sudo_execute("grep -q '^#includedir /etc/sudoers.d' /etc/sudoers || echo '#includedir /etc/sudoers.d' >> /etc/sudoers"):
            console.print("[bold red]Failed to add includedir to /etc/sudoers[/]")
            return False
        
        # Create sudoers file for user
        sudoers_content = f"{self.config.user_name} ALL=(ALL) NOPASSWD:ALL"
        sudoers_file = f"/etc/sudoers.d/{self.config.user_name}"
        
        # Write sudoers file
        if not self.sudo_execute(f"echo '{sudoers_content}' > {sudoers_file}"):
            console.print(f"[bold red]Failed to create {sudoers_file}[/]")
            return False
        
        # Set permissions
        if not self.sudo_execute(f"chmod 0440 {sudoers_file}"):
            console.print(f"[bold red]Failed to set permissions on {sudoers_file}[/]")
            return False
        
        # Validate sudoers file
        if not self.sudo_execute(f"visudo -cf {sudoers_file}"):
            console.print(f"[bold red]Invalid sudoers file: {sudoers_file}[/]")
            self.sudo_execute(f"rm {sudoers_file}")
            return False
        
        console.print(f"[green]Successfully set up sudoers for {self.config.user_name}[/]")
        return True 