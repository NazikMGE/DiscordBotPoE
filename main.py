import discord
from discord.ext import tasks
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
from typing import Optional

load_dotenv()

BASE_URL = 'https://cnlgaming.com'
BOT_1_TOKEN = os.getenv("BOT_1_TOKEN")
BOT_2_TOKEN = os.getenv("BOT_2_TOKEN")

# Scraper 
async def get_poe_prices_in_eur(session: aiohttp.ClientSession, address: str) -> Optional[str]:
    try:
        # Get the main page to obtain a CSRF token
        async with session.get(BASE_URL) as response:
            response.raise_for_status()
            text = await response.text()
            soup = BeautifulSoup(text, 'html.parser')
            csrf_token_tag = soup.find('meta', {'name': 'csrf-token'})
            if not csrf_token_tag or 'content' not in csrf_token_tag.attrs:
                print("Error: Could not find CSRF token on the main page.")
                return None
            csrf_token = csrf_token_tag['content']

        # Send an AJAX request to change the currency to EUR
        session.headers.update({'X-CSRF-TOKEN': csrf_token})
        ajax_url = f'{BASE_URL}/ajax/change-currency'
        async with session.post(ajax_url, data={'currency': 'EUR'}) as ajax_response:
            ajax_response.raise_for_status()
            currency_data = await ajax_response.json()
            if not (currency_data.get('error') == 0 and currency_data.get('currency') == 'EUR'):
                print(f"Error: Failed to change currency to EUR. Response: {currency_data}")
                return None

        # Step 3: Parse the actual product page
        async with session.get(address) as product_page_response:
            product_page_response.raise_for_status()
            product_text = await product_page_response.text()
            product_soup = BeautifulSoup(product_text, 'html.parser')
            
            # Find the price element, which seems to be in the first h4 tag
            target_element = product_soup.find('h4')
            if target_element:
                return target_element.get_text(strip=True)
            else:
                print(f"Error: Could not find the price element (h4) on page: {address}")
                return None

    except aiohttp.ClientError as e:
        print(f"A network error occurred: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during parsing: {e}")
        return None

# Bot setups
intents = discord.Intents.default()
bot1 = discord.Client(intents=intents)
bot2 = discord.Client(intents=intents)
session = None 

# Bot 1 events & tasks
@bot1.event
async def on_ready():
    print(f'Logged in as {bot1.user} (ID: {bot1.user.id})')
    print('------')
    if not update_status_task_bot1.is_running():
        update_status_task_bot1.start()

@tasks.loop(minutes=3)
async def update_status_task_bot1():
    print(f"[{bot1.user}] Starting status update...")
    price_string = await get_poe_prices_in_eur(session, "https://cnlgaming.com/game/path-of-exile/currency.html")
    
    if price_string:
        new_activity = discord.Activity(type=discord.ActivityType.watching, name=price_string)
        await bot1.change_presence(activity=new_activity)
        print(f"[{bot1.user}] Status updated successfully to: '{price_string}'")
    else:
        print(f"[{bot1.user}] Failed to fetch price data. Status not updated.")

# Bot 2 events & tasks
@bot2.event
async def on_ready():
    print(f'Logged in as {bot2.user} (ID: {bot2.user.id})')
    print('------')
    if not update_status_task_bot2.is_running():
        update_status_task_bot2.start()

@tasks.loop(minutes=3)
async def update_status_task_bot2():
    print(f"[{bot2.user}] Starting status update...")
    price_string = await get_poe_prices_in_eur(session, "https://cnlgaming.com/game/path-of-exile-2-currency/currency.html")
    
    if price_string:
        new_activity = discord.Activity(type=discord.ActivityType.watching, name=price_string)
        await bot2.change_presence(activity=new_activity)
        print(f"[{bot2.user}] Status updated successfully to: '{price_string}'")
    else:
        print(f"[{bot2.user}] Failed to fetch price data. Status not updated.")

async def main():
    global session
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest'
    }
    # Create a single session to be reused by both bots
    session = aiohttp.ClientSession(headers=headers)
    
    async with session:
        await asyncio.gather(
            bot1.start(BOT_1_TOKEN),
            bot2.start(BOT_2_TOKEN)
        )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bots are shutting down.")