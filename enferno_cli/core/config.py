"""Configuration management for server setup."""

import os
import getpass
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Confirm, Prompt

console = Console()


def get_password(prompt_text: str) -> str:
    """Get a password from the user without echoing."""
    console.print(f"[bold]{prompt_text}[/]", end="")
    return getpass.getpass(" ")


# Constants
DEFAULT_CONFIG_FILE = ".env"
DEFAULT_SSH_PORT = 22
DEFAULT_PYTHON_PORT = 5000
DEFAULT_SSL_ENABLED = True


@dataclass
class ServerConfig:
    """Server configuration class."""

    # Server details
    host: str
    server_hostname: str
    user_name: str
    password: str
    
    # Python settings
    python_port: int = DEFAULT_PYTHON_PORT
    
    # SSH settings
    ssh_port: int = DEFAULT_SSH_PORT
    ssh_key_path: Optional[str] = None
    
    # SSL settings
    ssl_enabled: bool = DEFAULT_SSL_ENABLED
    ssl_email: Optional[str] = None
    use_www: bool = False
    
    # Additional settings
    cloudflare_enabled: bool = False
    postgres_enabled: bool = False
    
    # Task selection
    selected_tasks: List[str] = field(default_factory=list)
    
    # Connection settings
    ansible_user: str = "root"
    
    @property
    def use_sudo(self) -> bool:
        """Determine if sudo should be used based on the ansible_user."""
        return self.ansible_user != "root"
    
    def validate_selected_tasks(self) -> None:
        """Validate and normalize selected_tasks to ensure it's a list of strings."""
        # Ensure selected_tasks is a list
        if not isinstance(self.selected_tasks, list):
            if isinstance(self.selected_tasks, str):
                # If it's a string, split by comma and filter empty strings
                self.selected_tasks = [t.strip() for t in self.selected_tasks.split(",") if t.strip()]
            else:
                # If it's something else, convert to empty list
                self.selected_tasks = []
        
        # Filter out any non-string or empty string elements
        self.selected_tasks = [str(task) for task in self.selected_tasks if task]
        
        # Clean up any remaining string artifacts (quotes, brackets)
        cleaned_tasks = []
        for task in self.selected_tasks:
            # Remove quotes and brackets if present
            task = task.strip("'\"[]")
            if task:
                cleaned_tasks.append(task)
        
        self.selected_tasks = cleaned_tasks
    
    def to_dict(self) -> Dict:
        """Convert config to dictionary."""
        return {k: v for k, v in self.__dict__.items() if v is not None}
    
    def to_env_file(self, path: str = DEFAULT_CONFIG_FILE) -> None:
        """Save configuration to .env file."""
        with open(path, "w") as f:
            for key, value in self.to_dict().items():
                if isinstance(value, bool):
                    value = str(value).lower()
                f.write(f"{key.upper()}={value}\n")
        
        console.print(f"Configuration saved to [bold green]{path}[/]")
    
    @classmethod
    def from_env(cls, env_file: str = DEFAULT_CONFIG_FILE) -> Optional["ServerConfig"]:
        """Load configuration from environment variables or .env file."""
        # Try to load from .env file
        if Path(env_file).exists():
            load_dotenv(env_file)
        else:
            return None
        
        # Required fields
        host = os.getenv("HOST")
        server_hostname = os.getenv("SERVER_HOSTNAME")
        user_name = os.getenv("USER_NAME")
        password = os.getenv("PASSWORD")
        
        # If any required field is missing, return None
        if not all([host, server_hostname, user_name, password]):
            return None
        
        # Optional fields with defaults
        python_port = int(os.getenv("PYTHON_PORT", DEFAULT_PYTHON_PORT))
        ssh_port = int(os.getenv("SSH_PORT", DEFAULT_SSH_PORT))
        ssh_key_path = os.getenv("SSH_KEY_PATH")
        ssl_enabled = os.getenv("SSL_ENABLED", str(DEFAULT_SSL_ENABLED)).lower() in ("true", "1", "yes")
        ssl_email = os.getenv("SSL_EMAIL")
        use_www = os.getenv("USE_WWW", "false").lower() in ("true", "1", "yes")
        cloudflare_enabled = os.getenv("CLOUDFLARE_ENABLED", "false").lower() in ("true", "1", "yes")
        postgres_enabled = os.getenv("POSTGRES_ENABLED", "false").lower() in ("true", "1", "yes")
        
        # Task selection
        tasks_str = os.getenv("SELECTED_TASKS", "")
        selected_tasks = [t.strip() for t in tasks_str.split(",")] if tasks_str else []
        
        # Connection settings
        ansible_user = os.getenv("ANSIBLE_USER", "root")
        
        config = cls(
            host=host,
            server_hostname=server_hostname,
            user_name=user_name,
            password=password,
            python_port=python_port,
            ssh_port=ssh_port,
            ssh_key_path=ssh_key_path,
            ssl_enabled=ssl_enabled,
            ssl_email=ssl_email,
            use_www=use_www,
            cloudflare_enabled=cloudflare_enabled,
            postgres_enabled=postgres_enabled,
            selected_tasks=selected_tasks,
            ansible_user=ansible_user,
        )
        
        # Validate selected tasks
        config.validate_selected_tasks()
        
        return config
    
    @classmethod
    def interactive(cls, host: Optional[str] = None, env_file: str = DEFAULT_CONFIG_FILE, skip_ssl: bool = False) -> "ServerConfig":
        """Create configuration interactively.
        
        Args:
            host: Optional host to use (overrides env value)
            env_file: Path to .env file to read defaults from
            skip_ssl: Whether to skip SSL setup
            
        Returns:
            ServerConfig instance
        """
        console.print("[bold]Server Setup Configuration[/]")
        console.print("Please provide the following information:")
        
        # Load defaults from environment if available
        if Path(env_file).exists():
            load_dotenv(env_file)
            console.print("[dim]Using defaults from existing configuration where available[/]")
        
        # Server details
        if not host:
            env_host = os.getenv("HOST")
            host = Prompt.ask("[bold]Server IP or hostname[/]", default=env_host or "")
        
        server_hostname = Prompt.ask(
            "[bold]Domain name[/] (e.g., example.com)",
            default=os.getenv("SERVER_HOSTNAME") or ""
        )
        
        user_name = Prompt.ask(
            "[bold]Username[/] for the server account",
            default=os.getenv("USER_NAME") or ""
        )
        
        # For password, we don't show the default but inform if one exists
        env_password = os.getenv("PASSWORD")
        if env_password:
            console.print("[dim]A password is already set in the environment. Press Enter to keep it or type a new one.[/]")
            password_input = get_password("Password for the user account")
            password = password_input if password_input else env_password
        else:
            password = get_password("Password for the user account")
        
        # Python port
        env_python_port = os.getenv("PYTHON_PORT")
        python_port_default = env_python_port or str(DEFAULT_PYTHON_PORT)
        python_port = int(Prompt.ask(
            "[bold]Python application port[/]",
            default=python_port_default
        ))
        
        # SSH settings
        env_ssh_port = os.getenv("SSH_PORT")
        ssh_port_default = env_ssh_port or str(DEFAULT_SSH_PORT)
        ssh_port = int(Prompt.ask(
            "[bold]SSH port[/]",
            default=ssh_port_default
        ))
        
        env_ssh_key = os.getenv("SSH_KEY_PATH")
        use_ssh_key = Confirm.ask(
            "[bold]Use SSH key for authentication?[/]", 
            default=bool(env_ssh_key)
        )
        
        ssh_key_path = None
        if use_ssh_key:
            ssh_key_default = env_ssh_key or "~/.ssh/id_rsa"
            ssh_key_path = Prompt.ask("[bold]Path to SSH key[/]", default=ssh_key_default)
            ssh_key_path = os.path.expanduser(ssh_key_path)
        
        # PostgreSQL setup
        env_postgres_enabled = os.getenv("POSTGRES_ENABLED")
        postgres_default = False
        if env_postgres_enabled is not None:
            postgres_default = env_postgres_enabled.lower() in ("true", "1", "yes")
            
        postgres_enabled = Confirm.ask(
            "[bold]Set up PostgreSQL database?[/]", 
            default=postgres_default
        )
        
        # SSL settings
        if skip_ssl:
            console.print("[yellow]SSL setup will be skipped as requested with --skip-ssl[/]")
            ssl_enabled = False
            ssl_email = None
            use_www = False
        else:
            env_ssl_enabled = os.getenv("SSL_ENABLED")
            ssl_default = True
            if env_ssl_enabled is not None:
                ssl_default = env_ssl_enabled.lower() in ("true", "1", "yes")
                
            ssl_enabled = Confirm.ask(
                "[bold]Enable SSL with Let's Encrypt?[/]", 
                default=ssl_default
            )
            
            ssl_email = None
            use_www = False
            if ssl_enabled:
                ssl_email = Prompt.ask(
                    "[bold]Email for SSL certificate[/]",
                    default=os.getenv("SSL_EMAIL") or ""
                )
                
                # Ask about www redirection preference
                env_use_www = os.getenv("USE_WWW")
                use_www_default = False
                if env_use_www is not None:
                    use_www_default = env_use_www.lower() in ("true", "1", "yes")
                    
                use_www = Confirm.ask(
                    "[bold]Redirect to www subdomain?[/] (e.g., example.com → www.example.com)", 
                    default=use_www_default
                )
        
        # Additional settings
        env_cloudflare = os.getenv("CLOUDFLARE_ENABLED")
        cloudflare_default = False
        if env_cloudflare is not None:
            cloudflare_default = env_cloudflare.lower() in ("true", "1", "yes")
            
        cloudflare_enabled = Confirm.ask(
            "[bold]Is this server behind Cloudflare?[/]", 
            default=cloudflare_default
        )
        
        # Connection settings
        ansible_user = Prompt.ask(
            "[bold]Initial SSH user[/] (usually root or ubuntu)", 
            default=os.getenv("ANSIBLE_USER") or "root"
        )
        
        # Create config
        config = cls(
            host=host,
            server_hostname=server_hostname,
            user_name=user_name,
            password=password,
            python_port=python_port,
            ssh_port=ssh_port,
            ssh_key_path=ssh_key_path,
            ssl_enabled=ssl_enabled,
            ssl_email=ssl_email,
            use_www=use_www,
            cloudflare_enabled=cloudflare_enabled,
            postgres_enabled=postgres_enabled,
            ansible_user=ansible_user,
        )
        
        # Determine tasks based on configuration
        config.selected_tasks = []
        
        # Always include these tasks
        config.selected_tasks.extend(["packages", "user", "firewall"])
        
        # Add PostgreSQL if enabled
        if postgres_enabled:
            config.selected_tasks.append("database")
        
        # Add Nginx task based on SSL and www preferences
        if ssl_enabled:
            if use_www:
                config.selected_tasks.append("nginx_www")
            else:
                config.selected_tasks.append("nginx_ssl")
        else:
            config.selected_tasks.append("nginx_basic")
        
        # Add Enferno task
        config.selected_tasks.append("enferno")
        
        # Add service task
        config.selected_tasks.append("service")
        
        # Save configuration to .env file
        config.to_env_file(env_file)
        
        return config 