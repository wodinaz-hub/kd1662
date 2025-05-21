import discord.ui
import discord # Додайте, якщо потрібен discord.Embed або discord.Color

class PaginationView(discord.ui.View):
    def __init__(self, embeds: list[discord.Embed], timeout=180):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.current_page = 0
        self.message = None
        self.update_buttons() # Викликаємо після того, як кнопки будуть додані декораторами

    def update_buttons(self):
        if len(self.children) >= 2:
            self.children[0].disabled = (self.current_page == 0) # Кнопка "Previous"
            self.children[1].disabled = (self.current_page == len(self.embeds) - 1) # Кнопка "Next"

    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.blurple, custom_id="prev_page")
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.blurple, custom_id="next_page")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < len(self.embeds) - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
        else:
            await interaction.response.defer()

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass