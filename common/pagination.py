import discord
from typing import List


class OrgChartPaginationView(discord.ui.View):
    """
    Pagination view for organization chart embeds.
    Provides Previous/Next buttons to navigate between pages, a link to Spectrum friends, and a refresh button.
    """

    def __init__(self, embeds: List[discord.Embed], refresh_callback=None, timeout: int = None):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.current_page = 0
        self.total_pages = len(embeds)
        self.refresh_callback = refresh_callback

        # Add link button for Spectrum friends
        add_friends_button = discord.ui.Button(
            label="Add Friends on RSI",
            style=discord.ButtonStyle.green,
            url="https://robertsspaceindustries.com/spectrum/settings/friends"
        )
        self.add_item(add_friends_button)

        # Disable previous button on first page
        self.previous_button.disabled = self.current_page == 0

    @discord.ui.button(label="← Previous", style=discord.ButtonStyle.blurple)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self._update_button_states()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label="Next →", style=discord.ButtonStyle.blurple)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to next page"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self._update_button_states()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.grey)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Refresh the org chart"""
        try:
            await interaction.response.defer(ephemeral=True)
            if self.refresh_callback:
                await self.refresh_callback()
                await interaction.followup.send("✅ Organization chart refreshed", ephemeral=True)
            else:
                await interaction.followup.send("❌ Refresh not available", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error refreshing: {str(e)}", ephemeral=True)

    def _update_button_states(self):
        """Update button disabled states based on current page"""
        # Disable previous button if on first page
        self.previous_button.disabled = self.current_page == 0

        # Disable next button if on last page
        self.next_button.disabled = self.current_page == self.total_pages - 1
