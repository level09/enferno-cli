# Enferno CLI

A Python CLI tool that automates the deployment of Enferno framework applications on Ubuntu servers. Set up your entire production environment with a single command - including Python 3.13, Nginx with proper static file paths, SSL certificates, PostgreSQL/SQLite databases, and systemd services.

## Features

- **Automated Server Provisioning**: Quickly set up Ubuntu servers with all necessary components for running Enferno applications
- **Python Management**: Installs Python 3.13 (with fallback to 3.9+) using the recommended methods from the deadsnakes PPA
- **Nginx Configuration**: Sets up Nginx with proper static file paths to avoid 404 errors, with support for both HTTP and HTTPS
- **SSL Support**: Integrates Let's Encrypt for free SSL certificates with automatic renewal
- **Database Options**: Configurable PostgreSQL setup with optional SQLite fallback
- **User Management**: Creates dedicated user accounts with appropriate permissions
- **Service Configuration**: Sets up systemd services for the Enferno application and Celery workers
- **Interactive Mode**: Guided setup process with sensible defaults
- **Configuration Management**: Saves and loads configurations from .env files for repeatable deployments

## Enferno Setup

This tool automates the complete setup process for Enferno applications:

1. **Server Preparation**: Installs all required packages and dependencies
2. **User Setup**: Creates a dedicated user account for running the application
3. **Database Setup**: (Optional) Creates a PostgreSQL database with the user having superuser privileges
4. **Enferno Download**: Clones the Enferno repository from GitHub
5. **Application Setup**: Runs the Enferno setup script which generates its own .env file
6. **Database Initialization**: Runs `flask create-db` to initialize the database (uses SQLite by default)
7. **Service Configuration**: Sets up systemd services for Enferno and Celery
8. **Web Server**: Configures Nginx with SSL for serving the application

The entire process is automated and can be completed with a single command.

> **Note**: By default, Enferno uses SQLite as its database. If you want to use PostgreSQL instead, you can enable it during the interactive setup or by setting `POSTGRES_ENABLED=true` in your `.env` file.

## Installation

```bash
pip install enferno_cli
```

## Usage

### Using environment variables

Create a `.env` file with your configuration:

```
SERVER_HOSTNAME=example.com
USER_NAME=myuser
PASSWORD=securepassword
SSL_EMAIL=your@email.com
```

Then run:

```bash
enferno setup --host your.server.ip
```

### Interactive mode

If no `.env` file is found, the tool will run in interactive mode:

```bash
enferno setup --host your.server.ip --interactive
```

The interactive mode will use values from an existing `.env` file as defaults if available, making it easy to update an existing configuration.

### Advanced usage

```bash
# Show help
enferno --help

# Use a specific SSH key
enferno setup --host your.server.ip --ssh-key /path/to/key

# Specify a custom SSH port
enferno setup --host your.server.ip --ssh-port 2222

# Run only specific tasks
enferno setup --host your.server.ip --tasks packages,user,nginx
```

### Setting up servers before DNS propagation

If you're setting up a new server and DNS hasn't been configured or propagated yet, you can use the `--skip-ssl` option to set up the server without SSL initially:

```bash
enferno setup --host your.server.ip --skip-ssl
```

This will:
1. Skip the SSL configuration prompt in interactive mode
2. Configure Nginx without SSL
3. Skip the Let's Encrypt certificate generation
4. Provide instructions for enabling SSL later

Once your DNS has propagated (domain points to your server), you can enable SSL by running:

```bash
enferno setup --host your.server.ip --tasks=nginx_ssl
```

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| SERVER_HOSTNAME | Domain name for the server | None |
| USER_NAME | Username for the server account | None |
| PASSWORD | Password for the user account | None |
| SSL_EMAIL | Email for SSL certificate registration | None |
| SSH_PORT | SSH port for the server | 22 |
| PYTHON_PORT | Port for the Python application | 5000 |
| POSTGRES_ENABLED | Whether to set up PostgreSQL database | false |

## Available Tasks

You can run specific tasks using the `--tasks` option:

| Task | Description |
|------|-------------|
| packages | Install essential packages |
| user | Create user account with sudo privileges |
| firewall | Configure UFW firewall |
| database | (Optional) Set up PostgreSQL database for Enferno |
| nginx_basic | Configure Nginx without SSL |
| nginx_ssl | Configure Nginx with SSL (requires DNS to be configured) |
| enferno | Download and set up Enferno application |
| service | Configure systemd services for Enferno |

## Security Notes

- The configuration is stored in a `.env` file which contains sensitive information like passwords
- Make sure to add `.env` to your `.gitignore` file to prevent accidentally committing credentials
- For production use, consider using a more secure method for managing secrets
- The Enferno setup script generates its own `.env` file with default values that should be reviewed and updated as needed
- If you use the optional database task, the PostgreSQL user created during setup has superuser privileges, allowing full management of databases without needing to switch to the postgres user

## Troubleshooting

### Database Issues

Enferno uses SQLite by default, which requires minimal configuration. However, if you've enabled PostgreSQL or are experiencing database issues:

1. **SQLite database initialization fails**: You can manually initialize the SQLite database:
   ```bash
   cd /home/your_username/your_domain
   source venv/bin/activate
   FLASK_APP=run.py flask create-db
   ```

2. **PostgreSQL not starting**: If you've enabled PostgreSQL and it's not starting, try manually starting the service:
   ```bash
   sudo systemctl start postgresql
   sudo systemctl status postgresql
   ```

3. **PostgreSQL database creation fails**: Ensure PostgreSQL is installed and running:
   ```bash
   sudo apt update
   sudo apt install -y postgresql postgresql-contrib
   sudo systemctl enable postgresql
   sudo systemctl start postgresql
   ```

4. **PostgreSQL authentication issues**: If you're having trouble connecting to PostgreSQL, you may need to modify the PostgreSQL authentication settings:
   ```bash
   sudo nano /etc/postgresql/*/main/pg_hba.conf
   ```
   Add or modify the following line:
   ```
   local   all             all                                     md5
   ```
   Then restart PostgreSQL:
   ```bash
   sudo systemctl restart postgresql
   ```

## Technology

This tool uses pure Python with SSH for server deployment, rather than relying on Ansible or other configuration management tools. This approach has several advantages:

1. **Simplicity**: No need to install Ansible or other external dependencies on your local machine.
2. **Portability**: Works on any platform that supports Python.
3. **Customizability**: Easy to modify and extend for specific requirements.
4. **Reliability**: Uses standard SSH connections and shell commands, which are well-tested and reliable.

While Ansible is a powerful tool for infrastructure automation, this tool provides a more lightweight and focused solution specifically for setting up Enferno applications on Ubuntu servers.

## License

MIT 