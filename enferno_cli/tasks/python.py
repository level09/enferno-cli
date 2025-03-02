"""Task for installing modern Python version."""

from rich.console import Console

from enferno_cli.core.task import Task

console = Console()


class PythonTask(Task):
    """Task for installing modern Python version."""

    name = "python"
    description = "Install Python 3.13 (or 3.9+ for compatibility with modern packages)"
    depends_on = ["packages"]

    def run(self) -> bool:
        """Run the task."""
        console.print("[cyan]Checking Python version...[/]")
        
        # Check current Python version
        check_cmd = "python3 --version"
        exit_code, stdout, stderr = self.ssh.execute(check_cmd)
        
        if exit_code != 0:
            console.print("[yellow]Failed to check Python version. Will install Python 3.13.[/]")
            current_version = "unknown"
        else:
            current_version = stdout.strip()
            console.print(f"[cyan]Current Python version: {current_version}[/]")
        
        # Check if we need to upgrade - prioritize 3.13, but accept 3.9+
        if "Python 3.13" in current_version:
            console.print("[green]Python 3.13 is already installed. No upgrade needed.[/]")
            return True
        elif "Python 3.9" in current_version or "Python 3.10" in current_version or "Python 3.11" in current_version or "Python 3.12" in current_version:
            console.print("[yellow]Python 3.9+ is installed, but not the latest 3.13. Proceeding with current version.[/]")
            console.print("[yellow]Consider upgrading to Python 3.13 for the latest features and security updates.[/]")
            return True
        
        # Install Python 3.13 using deadsnakes PPA
        console.print("[cyan]Installing Python 3.13 from deadsnakes PPA...[/]")
        
        # Add deadsnakes PPA
        if not self.sudo_execute("apt update"):
            console.print("[bold red]Failed to update apt cache[/]")
            return False
            
        if not self.sudo_execute("apt install -y software-properties-common"):
            console.print("[bold red]Failed to install software-properties-common[/]")
            return False
            
        if not self.sudo_execute("add-apt-repository -y ppa:deadsnakes/ppa"):
            console.print("[bold red]Failed to add deadsnakes PPA[/]")
            return False
            
        if not self.sudo_execute("apt update"):
            console.print("[bold red]Failed to update apt cache after adding PPA[/]")
            return False
        
        # Install Python 3.13-full instead of just python3.13 to get a more complete installation
        install_cmd = "apt install -y python3.13-full"
        if not self.sudo_execute(install_cmd):
            console.print("[yellow]Failed to install Python 3.13. Falling back to Python 3.9...[/]")
            # Fall back to Python 3.9 if 3.13 installation fails
            fallback_cmd = "apt install -y python3.9-full"
            if not self.sudo_execute(fallback_cmd):
                console.print("[bold red]Failed to install Python 3.9 fallback[/]")
                return False
            else:
                console.print("[yellow]Successfully installed Python 3.9 as fallback[/]")
                python_version = "3.9"
        else:
            console.print("[green]Successfully installed Python 3.13[/]")
            python_version = "3.13"
            
        # Install pip using the ensurepip module (recommended method)
        if not self.sudo_execute(f"python{python_version} -m ensurepip --upgrade"):
            console.print(f"[yellow]Warning: Failed to install pip for Python {python_version} using ensurepip[/]")
            # Try alternative method
            if not self.sudo_execute(f"apt install -y python{python_version}-pip"):
                console.print(f"[yellow]Warning: Failed to install pip for Python {python_version} using apt[/]")
                # Not a critical failure, continue anyway
        else:
            # Upgrade pip to the latest version
            self.sudo_execute(f"python{python_version} -m pip install --upgrade pip")
            
        # Verify installation
        verify_cmd = f"python{python_version} --version"
        exit_code, stdout, stderr = self.ssh.execute(verify_cmd)
        
        if exit_code != 0:
            # Try with python3.x format
            verify_cmd = f"python3.{python_version.split('.')[-1]} --version"
            exit_code, stdout, stderr = self.ssh.execute(verify_cmd)
            
            if exit_code != 0:
                console.print(f"[bold red]Failed to verify Python {python_version} installation[/]")
                return False
            
        console.print(f"[green]Successfully installed {stdout.strip()}[/]")
        
        # Verify pip installation
        pip_verify_cmd = f"python{python_version} -m pip --version"
        exit_code, stdout, stderr = self.ssh.execute(pip_verify_cmd)
        
        if exit_code == 0:
            console.print(f"[green]Successfully installed pip: {stdout.strip()}[/]")
        
        # Make the installed Python version the default python3
        console.print(f"[cyan]Setting Python {python_version} as the default python3...[/]")
        
        # Use update-alternatives to set the installed Python as the default
        python_bin = f"python3.{python_version.split('.')[-1]}"
        if not self.sudo_execute(f"update-alternatives --install /usr/bin/python3 python3 /usr/bin/{python_bin} 1"):
            console.print(f"[yellow]Warning: Failed to set {python_bin} as the default python3[/]")
            # Not a critical failure, continue anyway
        
        # Verify default Python version
        default_cmd = "python3 --version"
        exit_code, stdout, stderr = self.ssh.execute(default_cmd)
        
        if exit_code == 0:
            console.print(f"[green]Default Python version is now: {stdout.strip()}[/]")
        
        return True