# Addendum to CLI Specification

## A.1 Enhanced Repository Management

Based on implementation experience, several significant improvements have been made to the CLI's repository management capabilities:

### A.1.1 Integrated Repository Mounting

The repository mounting functionality has been fully integrated into the CLI's ingest commands:

```bash
# Start ingestion with automatic repository mounting
codestory ingest start /path/to/your/repository

# Mount a repository without starting ingestion
codestory ingest mount /path/to/your/repository
```

This integration provides:
- Seamless repository mounting for users
- Elimination of external scripts and dependencies
- Consistent user experience across different environments
- Clear, informative feedback during the mounting process

### A.1.2 New Repository Mount Command

A dedicated command for repository mounting has been added:

```bash
codestory ingest mount /path/to/your/repository [options]
```

Options include:
- `--force-remount`: Force remount even if repository appears to be mounted
- `--debug`: Show detailed debug information

This command allows users to:
- Mount repositories without starting ingestion
- Verify repository mounts are working correctly
- Troubleshoot mounting issues with detailed diagnostics
- Prepare repositories for later ingestion

### A.1.3 Enhanced Ingestion Options

The `ingest start` command has been enhanced with several repository-related options:

```bash
codestory ingest start /path/to/your/repository [options]
```

New options:
- `--no-progress`: Don't show progress updates during ingestion
- `--container`: Force container path mapping
- `--path-prefix PATH`: Custom container path prefix (default: /repositories)
- `--auto-mount`: Explicitly enable automatic mounting (default)
- `--no-auto-mount`: Disable automatic repository mounting
- `--force-remount`: Force remount even if repository appears to be mounted
- `--debug`: Show detailed debug information

These options provide significant flexibility for different workflows and environments.

### A.1.4 Improved Error Handling

Error handling for repository-related operations has been significantly enhanced:

```python
# Provide specific troubleshooting for path-related errors
if "does not exist" in str(e):
    console.print("\n[yellow]Troubleshooting Suggestions:[/]")
    console.print("1. Make sure your repository is properly mounted:")
    console.print(f"   - Try with force remount: [bold]codestory ingest start \"{local_path}\" --force-remount[/]")
    console.print("2. Or manually mount your repository:")
    console.print(f"   - Run: [bold]export REPOSITORY_PATH=\"{local_path}\"[/]")
    console.print("   - Run: [bold]docker-compose down && docker-compose up -d[/]")
    console.print("3. For detailed instructions, see: [bold]docs/deployment/repository_mounting.md[/]")
```

This provides:
- Clear error messages for common problems
- Specific troubleshooting steps for users
- References to relevant documentation
- Guidance for different error scenarios

### A.1.5 Additional CLI Architecture Updates

The CLI architecture has been enhanced with several key improvements:

1. **CLI Factory Functions**: Core functions like `is_repo_mounted` and `setup_repository_mount` now use factory pattern for better testability and reuse.

2. **Path Mapping**: Automatic path mapping between host and container:
   ```python
   # Get the repository name from the path (last part)
   repo_name = os.path.basename(local_path)
   
   # Create container path
   container_path = os.path.join(path_prefix, repo_name)
   ```

3. **Enhanced Debugging**: Detailed debug output with the `--debug` flag:
   ```python
   if debug:
       console.print("[dim]Debug information:[/]")
       console.print(f"[dim]  Repository path: {local_path}[/]")
       console.print(f"[dim]  Repository name: {repo_name}[/]")
       console.print(f"[dim]  Container path: {container_path}[/]")
       # Additional detailed debug information...
   ```

4. **Mount Verification**: Multi-stage verification ensures repositories are properly mounted:
   ```python
   # Verify mount was successful
   verify_check = subprocess.run(
       ["docker", "exec", "codestory-service", "ls", "-la", container_path],
       capture_output=True, text=True, check=False
   )
   
   if verify_check.returncode == 0 and len(verify_check.stdout.strip()) > 0:
       console.print(f"[green]Repository successfully mounted at {container_path}![/]")
       console.print(f"[dim]Directory contents:\n{verify_check.stdout}[/]", style="dim")
   ```

These architectural improvements ensure the CLI provides a robust, user-friendly interface for repository management and ingestion.