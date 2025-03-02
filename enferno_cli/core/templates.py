"""Template rendering for server setup."""

import os
import tempfile
from pathlib import Path
from typing import Dict, Optional, Union

import jinja2
from rich.console import Console

from enferno_cli.core.config import ServerConfig

console = Console()

# Get the templates directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class TemplateRenderer:
    """Template renderer for server setup."""

    def __init__(self, config: ServerConfig):
        """Initialize template renderer with server configuration."""
        self.config = config
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(TEMPLATES_DIR),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render_to_string(self, template_name: str, extra_vars: Optional[Dict] = None) -> str:
        """Render a template to a string.
        
        Args:
            template_name: Name of the template file
            extra_vars: Additional variables to use in rendering
            
        Returns:
            Rendered template as a string
        """
        template = self.env.get_template(template_name)
        
        # Prepare variables
        variables = self.config.to_dict()
        if extra_vars:
            variables.update(extra_vars)
        
        # Render template
        return template.render(**variables)

    def render_to_file(
        self, 
        template_name: str, 
        output_path: Optional[Union[str, Path]] = None,
        extra_vars: Optional[Dict] = None
    ) -> Union[str, Path]:
        """Render a template to a file.
        
        Args:
            template_name: Name of the template file
            output_path: Path where to save the rendered template
            extra_vars: Additional variables to use in rendering
            
        Returns:
            Path to the rendered file
        """
        rendered_content = self.render_to_string(template_name, extra_vars)
        
        # If no output path is provided, create a temporary file
        if output_path is None:
            fd, output_path = tempfile.mkstemp(suffix=f".{template_name}")
            os.close(fd)
        
        # Write rendered content to file
        with open(output_path, "w") as f:
            f.write(rendered_content)
        
        console.print(f"[green]Rendered template {template_name} to {output_path}[/]")
        return output_path


def copy_templates():
    """Copy template files from the Ansible project to the templates directory."""
    # This function can be used to copy templates from an existing Ansible project
    # to the templates directory of this package
    pass 