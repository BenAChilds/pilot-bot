import os
import re
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
        
def parse_conditions(metar_text):
    # Default conditions
    visibility = None
    ceiling = None

    # Regex for extracting visibility (e.g. 9999 or 10SM)
    vis_match = re.search(r'(\d{4})SM|\b(\d{4})\b', metar_text)
    if vis_match:
        visibility_str = vis_match.group(1) or vis_match.group(2)
        visibility = int(visibility_str)
        # Convert statute miles to meters if visibility is in SM
        if vis_match.group(1):
            visibility *= 1609.34

    # Regex for extracting cloud cover (e.g. BKN013, OVC025)
    cloud_matches = re.findall(r'\b(BKN|OVC|SCT|FEW)(\d{3})\b', metar_text)
    if cloud_matches:
        ceiling = min(int(cloud[1]) * 100 for cloud in cloud_matches)  # Convert to feet and get the lowest ceiling
    
    return visibility, ceiling

def determine_flight_rules(visibility, ceiling):
    if visibility is not None and ceiling is not None:
        # Convert visibility from meters to statute miles
        vis_sm = visibility / 1609.34
        
        # Debugging print statements
        print(f"Visibility (meters): {visibility}")
        print(f"Visibility (statute miles): {vis_sm}")
        print(f"Ceiling (feet): {ceiling}")

        if vis_sm >= 5 and ceiling >= 3000:
            return 'VFR', discord.Color.green()
        elif vis_sm >= 3 and ceiling >= 1000:
            return 'MVFR', discord.Color.blue()
        elif vis_sm >= 1 and ceiling >= 500:
            return 'IFR', discord.Color.red()
        else:
            return 'LIFR', discord.Color.purple()
    
    return 'Unknown', discord.Color.default()
        
def get_airservices_soap_request(station):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
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
        
@bot.command()
async def brief(ctx, station: str):
    # Check if the station starts with 'Y' (for Australian airports)
    if not station.lower().startswith('y') or len(station) != 4:
        await ctx.send("Error: Only Australian airports (starting with 'Y') are supported.")
        return

    # Construct the SOAP request body
    soap_request = get_airservices_soap_request(station.upper())

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
            # Parse the response XML to extract the <content> tag
            root = ET.fromstring(response.text)
            content = root.find('.//{http://www.airservicesaustralia.com/naips/xsd}content')

            if content is not None:
                # Extract text content
                atis_data = content.text

                # Replace AIRSERVICES_USERNAME with the user's display name
                atis_data = atis_data.replace(AIRSERVICES_USERNAME, ctx.author.display_name)

                # Create and send the embed with the updated content
                embed = discord.Embed(
                    title=f"Location Briefing for {station.upper()}",
                    description="NOTE: Not for flight planning purposes. Simulation use only.\n\n" + atis_data,
                    color=discord.Color.orange()
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("Error: Unable to retrieve briefing content.")
        else:
            # Handle non-200 responses
            await ctx.send(f"Error: Could not retrieve briefing for {station.upper()}. (HTTP {response.status_code})")
    
    except requests.RequestException as e:
        # Handle request exceptions (like timeouts or connectivity issues)
        await ctx.send(f"Error: Failed to retrieve briefing data due to network issue. {e}")
        
@bot.command()
async def metar(ctx, station: str):
    if not station.lower().startswith('y') or len(station) != 4:
        # Handle non-Australian stations
        try:
            response = requests.get(
                'https://aviationweather.gov/api/data/metar',
                params={'ids': station, 'format': 'raw'}
            )

            if response.status_code == 200:
                metar_data = response.text
                
                # Parse visibility and ceiling
                visibility, ceiling = parse_conditions(metar_data)

                # Determine flight rules and embed color
                flight_rules, color = determine_flight_rules(visibility, ceiling)

                embed = discord.Embed(
                    title=f"METAR for {station.upper()}",
                    description=f"{metar_data}\n\nFlight Conditions: **{flight_rules}**",
                    color=color
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"Error: Could not retrieve METAR for {station.upper()}. (HTTP {response.status_code})")

        except requests.RequestException as e:
            await ctx.send(f"Error: Failed to retrieve METAR data due to network issue. {e}")
        return

    soap_request = get_airservices_soap_request(station.upper())

    try:
        response = requests.post(AIRSERVICES_URL, headers={'Content-Type': 'text/xml; charset=utf-8'}, data=soap_request)
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            content = root.find('.//{http://www.airservicesaustralia.com/naips/xsd}content')

            if content is not None:
                metar_data = content.text
                metar_data = metar_data.replace(AIRSERVICES_USERNAME, ctx.author.display_name)

                # Filter only METAR and optional SPECI from the text
                metar_section = "\n".join([line for line in metar_data.splitlines() if "METAR" in line or "SPECI" in line])
                
                # Parse visibility and ceiling
                visibility, ceiling = parse_conditions(metar_section)

                # Determine flight rules and embed color
                flight_rules, color = determine_flight_rules(visibility, ceiling)

                embed = discord.Embed(title=f"METAR for {station.upper()}", description=f"{metar_section}\n\nFlight Conditions: **{flight_rules}**", color=color)
                await ctx.send(embed=embed)
            else:
                await ctx.send("Error: Unable to retrieve METAR data.")
        else:
            await ctx.send(f"Error: Could not retrieve METAR for {station.upper()}. (HTTP {response.status_code})")
    
    except requests.RequestException as e:
        await ctx.send(f"Error: Failed to retrieve METAR data due to network issue. {e}")
        
@bot.command()
async def taf(ctx, station: str):
    if not station.lower().startswith('y') or len(station) != 4:
        # Handle non-Australian stations
        try:
            response = requests.get(
                'https://aviationweather.gov/api/data/taf',
                params={'ids': station, 'format': 'raw'}
            )

            if response.status_code == 200:
                taf_data = response.text
                
                # Parse visibility and ceiling
                visibility, ceiling = parse_conditions(taf_data)

                # Determine flight rules and embed color
                flight_rules, color = determine_flight_rules(visibility, ceiling)

                embed = discord.Embed(
                    title=f"TAF for {station.upper()}",
                    description=f"{taf_data}\n\nFlight Conditions: **{flight_rules}**",
                    color=color
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"Error: Could not retrieve TAF for {station.upper()}. (HTTP {response.status_code})")
        except requests.RequestException as e:
            await ctx.send(f"Error: Failed to retrieve TAF data due to network issue. {e}")
        return

    soap_request = get_airservices_soap_request(station.upper())

    try:
        response = requests.post(AIRSERVICES_URL, headers={'Content-Type': 'text/xml; charset=utf-8'}, data=soap_request)
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            content = root.find('.//{http://www.airservicesaustralia.com/naips/xsd}content')

            if content is not None:
                taf_data = content.text
                taf_data = taf_data.replace(AIRSERVICES_USERNAME, ctx.author.display_name)
                
                 # Filter only METAR and optional SPECI from the text
                metar_section = "\n".join([line for line in taf_data.splitlines() if "METAR" in line or "SPECI" in line])
                
                # Parse visibility and ceiling
                visibility, ceiling = parse_conditions(metar_section)

                # Determine flight rules and embed color
                flight_rules, color = determine_flight_rules(visibility, ceiling)

                # Filter to capture TAF section and weather conditions after it
                lines = taf_data.splitlines()
                taf_section = []
                capturing_taf = False

                for line in lines:
                    if "TAF" in line:
                        capturing_taf = True
                    if capturing_taf:
                        # Stop capturing once the ATIS, METAR, or SPECI section begins
                        if any(keyword in line for keyword in ["METAR", "SPECI", "ATIS"]):
                            break
                        taf_section.append(line)

                taf_text = "\n".join(taf_section)

                embed = discord.Embed(title=f"TAF for {station.upper()}", description=f"{taf_text}\n\nFlight Conditions: **{flight_rules}**", color=color)
                await ctx.send(embed=embed)
            else:
                await ctx.send("Error: Unable to retrieve TAF data.")
        else:
            await ctx.send(f"Error: Could not retrieve TAF for {station.upper()}. (HTTP {response.status_code})")
    
    except requests.RequestException as e:
        await ctx.send(f"Error: Failed to retrieve TAF data due to network issue. {e}")
        
@bot.command()
async def atis(ctx, station: str):
    if not station.lower().startswith('y') or len(station) != 4:
        await ctx.send("Error: Only Australian airports (starting with 'Y') are supported.")
        return

    soap_request = get_airservices_soap_request(station.upper())

    try:
        response = requests.post(AIRSERVICES_URL, headers={'Content-Type': 'text/xml; charset=utf-8'}, data=soap_request)
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            content = root.find('.//{http://www.airservicesaustralia.com/naips/xsd}content')

            if content is not None:
                atis_data = content.text
                atis_data = atis_data.replace(AIRSERVICES_USERNAME, ctx.author.display_name)

                # Filter to capture ATIS section
                lines = atis_data.splitlines()
                atis_section = []
                capturing_atis = False

                for line in lines:
                    if "ATIS" in line:
                        capturing_atis = True
                    if capturing_atis:
                        # Stop capturing once another section like METAR, TAF, or SPECI starts
                        if any(keyword in line for keyword in ["METAR", "TAF", "SPECI"]):
                            break
                        atis_section.append(line)

                atis_text = "\n".join(atis_section)

                embed = discord.Embed(title=f"ATIS for {station.upper()}", description=atis_text, color=discord.Color.orange())
                await ctx.send(embed=embed)
            else:
                await ctx.send("Error: Unable to retrieve ATIS data.")
        else:
            await ctx.send(f"Error: Could not retrieve ATIS for {station.upper()}. (HTTP {response.status_code})")
    
    except requests.RequestException as e:
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
