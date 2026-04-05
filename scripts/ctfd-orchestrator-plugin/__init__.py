"""
CTFd Orchestrator Plugin

Automatically launches player instances for challenges via CTF platform orchestrator.
Integrates with the Player Instance Orchestrator API for on-demand challenge deployment.

Features:
- Automatic instance creation when player starts challenge
- Per-team instance quota enforcement (max 3 concurrent by default)
- TTL-based automatic cleanup
- Multiple players on same challenge support
- Real-time progress tracking and TTL countdown
"""

from CTFd.plugins import register_plugin_assets_directory, register_plugin_script

from .plugin import OrchestrationPlugin


def load(app):
    """Load the orchestrator plugin into CTFd."""
    plugin = OrchestrationPlugin(app)
    register_plugin_assets_directory(
        app, base_path="/plugins/ctfd_orchestrator_plugin/assets"
    )
    register_plugin_script("/plugins/ctfd_orchestrator_plugin/assets/orchestrator-ui.js")
    return plugin
