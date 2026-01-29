import discord
from discord import app_commands
from discord.ext import commands
import json
import os

from parser import (
    detect_template_type,
    parse_system_entry,
    parse_planet_entry,
    parse_flora_entry,
    parse_fauna_entry,
    parse_archaeology_entry,
    parse_mineral_entry
)


class Collector(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="collect_entry",
        description="Scan this entire thread, parse all valid templates, and export them to JSON."
    )
    async def collect_entry(self, interaction: discord.Interaction):

        channel = interaction.channel

        # Must be used inside a thread
        if not isinstance(channel, discord.Thread):
            return await interaction.response.send_message(
                "This command must be used inside a thread containing data entries.",
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        # Fetch ALL messages in the thread
        messages = [m async for m in channel.history(limit=None)]

        parsed_entries = []

        # Counters for summary
        counts = {
            "system": 0,
            "planet": 0,
            "flora": 0,
            "fauna": 0,
            "archaeology": 0,
            "mineral": 0
        }

        # Process each message
        for msg in messages:
            text = msg.content or ""
            entry_type = detect_template_type(text)

            if not entry_type:
                continue  # skip non-template messages

            # Route to correct parser
            if entry_type == "system":
                parsed = parse_system_entry(msg)
                counts["system"] += 1

            elif entry_type == "planet":
                parsed = parse_planet_entry(msg)
                counts["planet"] += 1

            elif entry_type == "flora":
                parsed = parse_flora_entry(msg)
                counts["flora"] += 1

            elif entry_type == "fauna":
                parsed = parse_fauna_entry(msg)
                counts["fauna"] += 1

            elif entry_type == "archaeology":
                parsed = parse_archaeology_entry(msg)
                counts["archaeology"] += 1

            elif entry_type == "mineral":
                parsed = parse_mineral_entry(msg)
                counts["mineral"] += 1

            else:
                continue

            parsed_entries.append(parsed)

        # Export to JSON
        export_filename = f"thread_{channel.id}_export.json"

        with open(export_filename, "w", encoding="utf-8") as f:
            json.dump(parsed_entries, f, indent=4)

        # Build summary message
        summary_lines = []
        for key, value in counts.items():
            if value > 0:
                summary_lines.append(f"- {key.capitalize()}: {value}")

        if not summary_lines:
            summary = "No valid templates were found in this thread."
        else:
            summary = (
                "Collected the following entries:\n"
                + "\n".join(summary_lines)
                + f"\n\nExported to `{export_filename}`"
            )

        await interaction.followup.send(summary, ephemeral=True)