"""SSH connection management for server setup."""

import os
import time
from pathlib import Path
from typing import List, Optional, Tuple, Union

import paramiko
from rich.console import Console
from rich.progress import Progress

from enferno_cli.core.config import ServerConfig

console = Console()


class SSHClient:
    """SSH client for executing commands on remote servers."""

    def __init__(self, config: ServerConfig):
        """Initialize SSH client with server configuration."""
        self.config = config
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._connected = False

    def connect(self) -> bool:
        """Connect to the remote server."""
        try:
            connect_kwargs = {
                "hostname": self.config.host,
                "port": self.config.ssh_port,
                "username": self.config.ansible_user,
                "timeout": 10,
            }

            # Use key-based authentication if a key path is provided
            if self.config.ssh_key_path:
                key_path = os.path.expanduser(self.config.ssh_key_path)
                if os.path.exists(key_path):
                    connect_kwargs["key_filename"] = key_path
                else:
                    console.print(f"[bold red]SSH key not found at {key_path}[/]")
                    return False
            else:
                # Use password authentication
                connect_kwargs["password"] = self.config.password

            with Progress() as progress:
                task = progress.add_task("[cyan]Connecting to server...", total=1)
                self.client.connect(**connect_kwargs)
                progress.update(task, completed=1)

            self._connected = True
            console.print(f"[bold green]Connected to {self.config.host}[/]")
            return True
        except Exception as e:
            console.print(f"[bold red]Failed to connect: {str(e)}[/]")
            return False

    def disconnect(self) -> None:
        """Disconnect from the remote server."""
        if self._connected:
            self.client.close()
            self._connected = False
            console.print(f"[bold green]Disconnected from {self.config.host}[/]")

    def execute(self, command: str, sudo: bool = False, timeout: int = 60) -> Tuple[int, str, str]:
        """Execute a command on the remote server.
        
        Args:
            command: The command to execute
            sudo: Whether to run the command with sudo
            timeout: Timeout in seconds for command execution (kept for compatibility)
            
        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        if not self._connected:
            if not self.connect():
                return (-1, "", "Not connected to server")

        # Add sudo if needed
        if sudo and not command.startswith("sudo "):
            command = f"sudo {command}"

        console.print(f"[dim]Executing: {command}[/]")
        
        try:
            # Use timeout parameter for the exec_command call
            stdin, stdout, stderr = self.client.exec_command(command, get_pty=True, timeout=timeout)
            exit_status = stdout.channel.recv_exit_status()
            
            stdout_str = stdout.read().decode("utf-8")
            stderr_str = stderr.read().decode("utf-8")
            
            if exit_status != 0:
                console.print(f"[bold red]Command failed with exit code {exit_status}[/]")
                if stderr_str:
                    console.print(f"[red]{stderr_str}[/]")
            
            return (exit_status, stdout_str, stderr_str)
        except Exception as e:
            console.print(f"[bold red]Error executing command: {str(e)}[/]")
            return (-1, "", str(e))

    def upload_file(self, local_path: Union[str, Path], remote_path: str) -> bool:
        """Upload a file to the remote server.
        
        Args:
            local_path: Path to the local file
            remote_path: Path where to save the file on the remote server
            
        Returns:
            True if successful, False otherwise
        """
        if not self._connected:
            if not self.connect():
                return False

        try:
            sftp = self.client.open_sftp()
            sftp.put(str(local_path), remote_path)
            sftp.close()
            console.print(f"[green]Uploaded {local_path} to {remote_path}[/]")
            return True
        except Exception as e:
            console.print(f"[bold red]Failed to upload file: {str(e)}[/]")
            return False

    def download_file(self, remote_path: str, local_path: Union[str, Path]) -> bool:
        """Download a file from the remote server.
        
        Args:
            remote_path: Path to the file on the remote server
            local_path: Path where to save the file locally
            
        Returns:
            True if successful, False otherwise
        """
        if not self._connected:
            if not self.connect():
                return False

        try:
            sftp = self.client.open_sftp()
            sftp.get(remote_path, str(local_path))
            sftp.close()
            console.print(f"[green]Downloaded {remote_path} to {local_path}[/]")
            return True
        except Exception as e:
            console.print(f"[bold red]Failed to download file: {str(e)}[/]")
            return False

    def file_exists(self, remote_path: str) -> bool:
        """Check if a file exists on the remote server.
        
        Args:
            remote_path: Path to the file on the remote server
            
        Returns:
            True if the file exists, False otherwise
        """
        if not self._connected:
            if not self.connect():
                return False

        try:
            sftp = self.client.open_sftp()
            sftp.stat(remote_path)
            sftp.close()
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            console.print(f"[bold red]Error checking if file exists: {str(e)}[/]")
            return False

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect() 