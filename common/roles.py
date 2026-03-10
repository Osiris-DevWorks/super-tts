import logging
from discord import app_commands, Interaction, Member

logger = logging.getLogger("citizen-bot")

def has_any_role(*allowed_roles):
    """
    A custom decorator to restrict access to slash commands.
    Currently disabled - allows all users in testing mode.
    In production, implement proper role-based access control.
    """

    async def predicate(interaction: Interaction):
        # Role checks disabled for testing - owner is responsible for setup
        logger.info(f"Command executed by {interaction.user.display_name}")
        return True

    return app_commands.check(predicate)
