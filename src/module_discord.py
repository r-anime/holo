from logging import debug, info, warning, error
from functools import partial

import discord
from discord import app_commands


def main(config, db):
	intents = discord.Intents.default()
	guild = discord.Object(config.d_guild)
	client = Lovepon(intents=intents, guild=guild)

	@client.tree.command(guild=guild)
	@app_commands.describe(
			anime='The anime you want to post a thread for.',
			episode='The episode number.',
	)
	async def post(interaction: discord.Interaction, anime: str, episode: int):
		if anime.isdigit():
			await post_thread(interaction, config, db, db.get_show(anime), episode)
			return

		anime = anime.lower()
		show = db.get_show_by_name_fuzzy(anime)
		if show is None:
			await interaction.response.send_message(f'Cannot identify {anime}', ephemeral=True)
			return

		if anime != show.name.lower() and (not show.name_en or anime != show.name_en.lower()):
			view  = Confirmation_Button(partial(post_thread, config=config, db=db, show=show, episode=episode))
			await interaction.response.send_message(f'Post a discussion thread for epsiode {episode} of {show.name}?', view=view, ephemeral=True)
		else:
			await post_thread(interaction, config, db, show, episode)

	@client.tree.command(guild=guild)
	@app_commands.describe(
			anime='The anime you want to post a thread for.',
			count='The number of episodes to post.',
	)
	async def batch(interaction: discord.Interaction, anime: str, count: int):
		if anime.isdigit():
			await post_batch(interaction, config, db, db.get_show(anime), count)
			return

		anime = anime.lower()
		show = db.get_show_by_name_fuzzy(anime)
		if show is None:
			await interaction.response.send_message(f'Cannot identify {anime}', ephemeral=True)
			return

		if anime != show.name.lower() and (not show.name_en or anime != show.name_en.lower()):
			view  = Confirmation_Button(partial(post_batch, config=config, db=db, show=show, count=count))
			await interaction.response.send_message(f'Create a {count} episode batch for {show.name}?', view=view, ephemeral=True)
		else:
			await post_batch(interaction, config, db, show, count)

	@client.tree.command(guild=guild)
	@app_commands.describe(
			anime='The anime title you want to search.'
	)
	async def search(interaction: discord.Interaction, anime: str):
		shows = db.get_show_by_name_fuzzy(anime, 10)
		if shows is None:
			await interaction.response.send_message(f'Cannot identify {anime}')
			return

		format = "### Matching Shows:\n"
		for show in shows:
			format += f"**{show.id}**:  {show.name}"
			format += f" • {show.name_en}\n" if show.name_en else "\n"
		await interaction.response.send_message(format, ephemeral=True)
			

	client.run(config.d_token)

class Lovepon(discord.Client):
	def __init__(self, *, intents, guild):
		super().__init__(intents=intents)

		self.tree = app_commands.CommandTree(self)
		self.guild = guild

	async def setup_hook(self):
		await self.tree.sync(guild=self.guild)

	async def on_ready(self):
		info(f'Logged on to discord as {self.user}.')

class Confirmation_Button(discord.ui.View):
	def __init__(self, yesfunc):
		super().__init__()
		self.yesfunc = yesfunc

	@discord.ui.button(label='Yes', style=discord.ButtonStyle.success)
	async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
		await self.yesfunc(interaction)
		self.stop()

	@discord.ui.button(label='No', style=discord.ButtonStyle.danger)
	async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
		await interaction.response.send_message("Post Canceled", ephemeral=True)
		self.stop()

async def post_thread(interaction, config, db, show, episode):
	info(f"Creating new thread for {show.name} episode {episode}.")

	# When there are a lot of other threads to edit, we exceed discord's 3 second window.
	await interaction.response.defer()
	import module_create_threads as m
	post_url = m.main(config, db, show.name, episode)
	await interaction.followup.send(f'Created thread for epsiode {episode} of {show.name}: {post_url}')

async def post_batch(interaction, config, db, show, count):
	info(f"Creating {count} episode batch for {show.name}.")

	# Creating a large batch exceeds discord's 3 second window.
	await interaction.response.defer()
	import module_batch_create as m
	post_url = m.main(config, db, show.name, count)
	await interaction.followup.send(f'Created {count} episode batch for {show.name}: https://redd.it/{post_url}')
