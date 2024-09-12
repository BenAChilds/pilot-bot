import os
import discord
import requests
import xml.etree.ElementTree as ET
from discord.ext import commands
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Static restricted role
STATIC_RESTRICTED_ROLE = '@everyone'

# Load restricted roles from the environment variable and split by comma
restricted_roles_env = os.getenv('RESTRICTED_ROLES', '')

# Split the comma-separated string into a list (if any are provided)
dynamic_restricted_roles = restricted_roles_env.split(',') if restricted_roles_env else []

# Combine static and dynamic restricted roles
RESTRICTED_ROLES = [STATIC_RESTRICTED_ROLE] + [role.strip() for role in dynamic_restricted_roles]


# Load the welcome message from a .md file
def load_welcome_message():
    with open("welcome_message.md", "r") as file:
        return file.read()

# Intents are required to handle certain events like member join
intents = discord.Intents.all()
intents.members = True
intents.message_content = True

# Create the bot object
bot = commands.Bot(command_prefix="!", intents=intents)

# This event will trigger when the bot is ready
@bot.event
async def on_ready():
    print(f'Bot is online as {bot.user}')
    logging.info(f'Bot is online as {bot.user}')
    
async def get_rules_link():
    # Link to rules
    CHANNEL_ID = os.getenv('RULES_CHANNEL_ID')
    MESSAGE_ID = os.getenv('RULES_MESSAGE_ID')
    message_link = f"https://discord.com/channels/{bot.guilds[0].id}/{CHANNEL_ID}/{MESSAGE_ID}"
    
    return message_link
    
async def get_welcome_message(user):
    welcome_message = load_welcome_message()
    rules_link = await get_rules_link()
    
    embed = discord.Embed(title="", description=f"Hey {user.mention}!", color=discord.Color.green())
    embed.description += f"\n\n{welcome_message}"
    embed.description += f"\n\nMake sure to read our rules before you dive in: {rules_link}"
    
    return embed

# This event will trigger when a new member joins the server
@bot.event
async def on_member_join(member):
    welcome_channel = bot.get_channel(int(WELCOME_CHANNEL_ID))
    
    embed = await get_welcome_message(member)
        
    # Send the embed
    await welcome_channel.send(embed=embed)
    
# Manually invoke the above
@bot.command(name="welcome")
async def welcome_message(ctx):    
    embed = await get_welcome_message(ctx.author)
        
    # Send the embed
    await ctx.send(embed=embed)

# Command to list available roles
@bot.command(name="roles")
async def list_roles(ctx, action=None, *, role_name=None):
    logging.info(f'Saw !roles from {ctx.author}')
    # Fetch all roles on the server, excluding restricted ones
    roles = [role for role in ctx.guild.roles if role.name not in RESTRICTED_ROLES]
    
    if action is None:
        # Create an embed to display roles
        embed = discord.Embed(title="Available Roles", description="Here are the roles you can select:\n", color=discord.Color.blue())
        
        # Create a string with roles formatted as bullet points
        role_list = "\n".join([f"• {role.name}" for role in roles])
        embed.description += f"\n{role_list}"
        embed.description += "\n\nUse `!roles add <name>` to select."
        
        # Send the embed
        await ctx.send(embed=embed)
    
    elif action.lower() == "add" and role_name:
        await add_role(ctx, role_name)
    
    elif action.lower() == "remove" and role_name:
        await remove_role(ctx, role_name)


async def add_role(ctx, role_name):
    member = ctx.author
    role_name_lower = role_name.lower()

    # Create a lookup by lowercased role names for comparison
    role_lookup = {role.name.lower(): role for role in ctx.guild.roles}

    # Check if the role exists by matching the lowercase name
    requested_role = role_lookup.get(role_name_lower)

    if requested_role is None:
        await ctx.send(f"Sorry, the role '{role_name}' does not exist.")
        return

    if requested_role.name in RESTRICTED_ROLES:
        await ctx.send(f"The role '{role_name}' cannot be added.")
        return

    if requested_role in member.roles:
        await ctx.send(f"You already have the role '{role_name}'.")
        return

    # Special case for 'ATC'
    if requested_role.name == 'ATC':
        await member.add_roles(requested_role)
        await ctx.send(f"Added role '{requested_role.name}' to {member.mention}.")
        return

    # Check for higher roles and remove lower roles
    higher_role = None
    for role in member.roles:
        if role.position < requested_role.position and role.name not in RESTRICTED_ROLES:
            higher_role = role

    if higher_role:
        if 'RPC' in [r.name for r in member.roles] and requested_role.name != 'RPC':
            if higher_role.name != 'RPC':
                await member.remove_roles(higher_role)
                await ctx.send(f"Removed lower role '{higher_role.name}'.")

    # Assign 'Member' role if user has no other roles
    if len(member.roles) <= 1:  # @everyone is always present
        member_role = role_lookup.get('member')
        if member_role is not None:
            await member.add_roles(member_role)
            await ctx.send(f"Assigned 'Member' role to {member.mention}.")

    # Add the requested role
    await member.add_roles(requested_role)
    await ctx.send(f"Added role '{requested_role.name}' to {member.mention}.")


# Helper function to remove a role
async def remove_role(ctx, role_name):
    member = ctx.author
    role = discord.utils.get(ctx.guild.roles, name=role_name)

    if role is None or role.name in RESTRICTED_ROLES:
        await ctx.send(f"The role '{role_name}' cannot be removed.")
        return

    if role not in member.roles:
        await ctx.send(f"You do not have the role '{role_name}'.")
        return

    await member.remove_roles(role)
    await ctx.send(f"Removed role '{role_name}' from {member.mention}.")
    
# Helper function to ban a user
@bot.command(name="ban")
@commands.has_permissions(administrator=True)
@commands.has_role("Mod")
async def ban_user(ctx, user_input):
    try:
        # Check if user_input is an integer (user ID)
        user = await bot.fetch_user(int(user_input))
        
        # Ban the user by ID
        await ctx.guild.ban(user)
        await ctx.send(f"User {user.id} has been banned.")
    except ValueError:
        # If user_input is not an integer, it is treated as a username
        username = user_input
        member = discord.utils.get(ctx.guild.members, name=username)
        
        if member:
            await ctx.guild.ban(member)
            await ctx.send(f"User {member.name}#{member.discriminator} has been banned.")
        else:
            await ctx.send(f"User with username '{username}' not found.")
    except discord.Forbidden:
        await ctx.send("I don't have permission to ban this user.")
    except discord.HTTPException as e:
        await ctx.send(f"Failed to ban user: {e}")

# Error handling for missing roles
@ban_user.error
async def ban_user_error(ctx, error):
    if isinstance(error, commands.MissingAnyRole):
        await ctx.send("You do not have the required roles to use this command.")
    else:
        await ctx.send("An error occurred while trying to ban the user.")
        
@bot.command()
async def metar(ctx, station: str):
    # Ensure input is up to 4 alphanumeric characters
    if not station.isalnum() or len(station) > 4:
        await ctx.send("Error: Please provide a valid 4-character station identifier.")
        return
    
    # Prepare the URL and query parameters
    url = "https://aviationweather.gov/api/data/metar"
    params = {
        "ids": station.upper(),
        "format": "raw",
        "taf": "false"
    }
    
    try:
        # Make the GET request to the aviationweather API
        response = requests.get(url, params=params)
        
        # Check for a successful request
        if response.status_code == 200:
            metar_data = response.text  # This will give us the raw METAR data
            
            # Create an embed to return the METAR data
            embed = discord.Embed(
                title=f"METAR for {station.upper()}",
                description=metar_data,
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
        else:
            # Handle errors or non-200 responses
            await ctx.send(f"Error: Could not retrieve METAR for {station.upper()}. (HTTP {response.status_code})")
    
    except requests.RequestException as e:
        # Handle request exceptions (like timeouts or connectivity issues)
        await ctx.send(f"Error: Failed to retrieve data due to network issue. {e}")
        
@bot.command()
async def atis(ctx, station: str):
    # Check if the station starts with 'Y' (for Australian airports)
    if not station.lower().startswith('y') or len(station) != 4:
        await ctx.send("Error: Only Australian airports (starting with 'Y') are currently supported.")
        return

    # Construct the SOAP request body
    soap_request = f'''<?xml version="1.0" encoding="UTF-8"?>
    <SOAP-ENV:Envelope
        xmlns:ns0="http://schemas.xmlsoap.org/soap/envelope/"
        xmlns:ns1="http://www.airservicesaustralia.com/naips/xsd"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
        <SOAP-ENV:Header/>
        <ns0:Body>
            <ns1:loc-brief-rqs password="{AIRSERVICES_PASSWORD}" requestor="{AIRSERVICES_USERNAME}" source="atis">
                <ns1:loc>{station.upper()}</ns1:loc>
                <ns1:flags met="true"/>
            </ns1:loc-brief-rqs>
        </ns0:Body>
    </SOAP-ENV:Envelope>'''

    try:
        # Make the SOAP request to the AirServices API
        response = requests.post(
            AIRSERVICES_URL,
            headers={
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': ''
            },
            data=soap_request
        )

        # Check if the request was successful
        if response.status_code == 200:
            try:
                # Parse the response XML to extract the content
                root = ET.fromstring(response.text)
                content_tag = root.find('.//{http://www.airservicesaustralia.com/naips/xsd}content')

                if content_tag is not None:
                    content = content_tag.text

                    # Extract the part starting from "ATIS"
                    atis_index = content.find("ATIS")
                    if atis_index != -1:
                        # Strip leading and trailing whitespace from the ATIS content
                        atis_content = content[atis_index:].lstrip()  # Removes only leading whitespace

                        # Send the extracted ATIS information
                        embed = discord.Embed(
                            title=f"ATIS for {station.upper()}",
                            description=f"```{atis_content}```",
                            color=discord.Color.green()
                        )
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send(f"Error: No ATIS found in the response for {station.upper()}.")
                else:
                    await ctx.send(f"Error: No ATIS content found for {station.upper()}.")

            except ET.ParseError:
                await ctx.send("Error: Failed to parse the ATIS response.")
        else:
            # Handle non-200 responses
            await ctx.send(f"Error: Could not retrieve ATIS for {station.upper()}. (HTTP {response.status_code})")
    
    except requests.RequestException as e:
        # Handle request exceptions (like timeouts or connectivity issues)
        await ctx.send(f"Error: Failed to retrieve ATIS data due to network issue. {e}")

# Load from environment variable
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
WELCOME_CHANNEL_ID = os.getenv('WELCOME_CHANNEL_ID')
# Get the AirServices Australia credentials from environment variables
AIRSERVICES_USERNAME = os.getenv("AIRSERVICES_USERNAME")
AIRSERVICES_PASSWORD = os.getenv("AIRSERVICES_PASSWORD")
# Base URL for the AirServices Australia SOAP service
AIRSERVICES_URL = "https://www.airservicesaustralia.com/naips/briefing-service?wsdl"

if DISCORD_TOKEN is None:
    raise ValueError("No Discord token provided. Set the DISCORD_TOKEN environment variable.")

# Run the bot
bot.run(DISCORD_TOKEN)
