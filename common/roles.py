import logging
from discord import app_commands, Interaction, Member

logger = logging.getLogger("citizen-bot")

def has_any_role(*allowed_roles):
    """
    A custom decorator to restrict access to slash commands based on role names.
    :param allowed_roles: A list of role names that are allowed to execute the command.
    """

    async def predicate(interaction: Interaction):
        # Ensure interaction.user is a Member (has roles)
        if not isinstance(interaction.user, Member):
            await interaction.response.send_message("This command can only be used in a guild.", ephemeral=True)
            raise app_commands.CheckFailure("This command can only be used in a guild.")

        # Check if any role matches
        if not any(role.name in allowed_roles for role in interaction.user.roles):
            await interaction.response.send_message(
                "You do not have the required role to use this command.", ephemeral=True
            )
            raise app_commands.CheckFailure("You do not have the required role to use this command.")
        logger.info(f"Command executed by {interaction.user.display_name}")


        return True

    return app_commands.check(predicate)
