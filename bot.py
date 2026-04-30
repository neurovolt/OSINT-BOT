import os
import asyncio
import aiohttp
from aiohttp import web
import json
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode

# ── Config ────────────────────────────────────────────────────────────────────
ADMIN_CODE = os.getenv("ADMIN_CODE", "VOLT_ADMIN_2024")  # change this in Railway env vars
FREE_LIMIT = 5  # searches before ad

# ── Database ──────────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect("/app/users.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        is_admin INTEGER DEFAULT 0,
        searches_used INTEGER DEFAULT 0,
        ads_watched INTEGER DEFAULT 0
    )""")
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect("/app/users.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO users VALUES (?,0,0,0)", (user_id,))
        conn.commit()
        c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
    conn.close()
    return {"user_id": row[0], "is_admin": row[1], "searches_used": row[2], "ads_watched": row[3]}

def set_admin(user_id):
    conn = sqlite3.connect("/app/users.db")
    c = conn.cursor()
    c.execute("UPDATE users SET is_admin=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def increment_search(user_id):
    conn = sqlite3.connect("/app/users.db")
    c = conn.cursor()
    c.execute("UPDATE users SET searches_used=searches_used+1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def increment_ad(user_id):
    conn = sqlite3.connect("/app/users.db")
    c = conn.cursor()
    c.execute("UPDATE users SET ads_watched=ads_watched+1, searches_used=0 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def can_search(user):
    if user["is_admin"]:
        return True, None
    remaining = FREE_LIMIT - user["searches_used"]
    if remaining > 0:
        return True, remaining
    return False, 0

BOT_TOKEN = os.getenv("BOT_TOKEN", "8029167800:AAFJDZw7VGKARPh07QP63fD71Sb06teX6ro")
HIBP_API_KEY = os.getenv("HIBP_API_KEY", "")  # optional, for breach check

# 300+ sites for username search
SHERLOCK_SITES = {
    # Social Media
    "GitHub": "https://github.com/{}",
    "Twitter/X": "https://twitter.com/{}",
    "Instagram": "https://www.instagram.com/{}/",
    "Reddit": "https://www.reddit.com/user/{}",
    "TikTok": "https://www.tiktok.com/@{}",
    "YouTube": "https://www.youtube.com/@{}",
    "Twitch": "https://www.twitch.tv/{}",
    "Pinterest": "https://www.pinterest.com/{}/",
    "LinkedIn": "https://www.linkedin.com/in/{}",
    "Telegram": "https://t.me/{}",
    "Snapchat": "https://www.snapchat.com/add/{}",
    "VK": "https://vk.com/{}",
    "Ask.fm": "https://ask.fm/{}",
    "Clubhouse": "https://www.clubhouse.com/@{}",
    "MeWe": "https://mewe.com/i/{}",
    "Minds": "https://www.minds.com/{}",
    "Gab": "https://gab.com/{}",
    "Parler": "https://parler.com/{}",
    "Truth Social": "https://truthsocial.com/@{}",
    "Mastodon": "https://mastodon.social/@{}",
    "Bluesky": "https://bsky.app/profile/{}",
    "Threads": "https://www.threads.net/@{}",
    "Facebook": "https://www.facebook.com/{}",
    "WeHeartIt": "https://weheartit.com/{}",
    "Amino": "https://aminoapps.com/u/{}",
    "Fandom": "https://www.fandom.com/u/{}",
    "Livejournal": "https://{}.livejournal.com",
    "Lofter": "https://{}.lofter.com",
    # Gaming
    "Steam": "https://steamcommunity.com/id/{}",
    "Roblox": "https://www.roblox.com/user.aspx?username={}",
    "Minecraft/NameMC": "https://namemc.com/profile/{}",
    "Chess.com": "https://www.chess.com/member/{}",
    "Lichess": "https://lichess.org/@/{}",
    "Battlenet": "https://overwatch.blizzard.com/en-us/career/{}/",
    "Faceit": "https://www.faceit.com/en/players/{}",
    "HLTV": "https://www.hltv.org/profile/1/{}",
    "Speedrun.com": "https://www.speedrun.com/user/{}",
    "Gamespot": "https://www.gamespot.com/profile/{}/",
    "IGN": "https://www.ign.com/boards/members/{}/",
    "Newgrounds": "https://{}.newgrounds.com",
    "Kongregate": "https://www.kongregate.com/accounts/{}",
    "Armor Games": "https://armorgames.com/user/{}",
    "Itch.io": "https://{}.itch.io",
    "GameFAQs": "https://gamefaqs.gamespot.com/community/{}",
    "NintendoLife": "https://www.nintendolife.com/users/{}",
    "PSNProfiles": "https://psnprofiles.com/{}",
    "TrueAchievements": "https://www.trueachievements.com/gamer/{}",
    "Twitch Tracker": "https://twitchtracker.com/{}",
    "Duolingo": "https://www.duolingo.com/profile/{}",
    # Dev / Tech
    "GitLab": "https://gitlab.com/{}",
    "Bitbucket": "https://bitbucket.org/{}",
    "HuggingFace": "https://huggingface.co/{}",
    "Kaggle": "https://www.kaggle.com/{}",
    "StackOverflow": "https://stackoverflow.com/users/{}",
    "NPM": "https://www.npmjs.com/~{}",
    "PyPI": "https://pypi.org/user/{}/",
    "DockerHub": "https://hub.docker.com/u/{}",
    "Replit": "https://replit.com/@{}",
    "Codepen": "https://codepen.io/{}",
    "HackerNews": "https://news.ycombinator.com/user?id={}",
    "Keybase": "https://keybase.io/{}",
    "Hackerone": "https://hackerone.com/{}",
    "Bugcrowd": "https://bugcrowd.com/{}",
    "CTFtime": "https://ctftime.org/user/{}",
    "TryHackMe": "https://tryhackme.com/p/{}",
    "HackTheBox": "https://app.hackthebox.com/users/{}",
    "LeetCode": "https://leetcode.com/{}",
    "Codeforces": "https://codeforces.com/profile/{}",
    "CodeChef": "https://www.codechef.com/users/{}",
    "AtCoder": "https://atcoder.jp/users/{}",
    "TopCoder": "https://www.topcoder.com/members/{}",
    "HackerRank": "https://www.hackerrank.com/{}",
    "Exercism": "https://exercism.org/profiles/{}",
    "Codesignal": "https://app.codesignal.com/profile/{}",
    "Glitch": "https://glitch.com/@{}",
    "JSFiddle": "https://jsfiddle.net/user/{}/",
    "Shodan": "https://www.shodan.io/member/{}",
    # Creative / Art
    "DeviantArt": "https://www.deviantart.com/{}",
    "Behance": "https://www.behance.net/{}",
    "Dribbble": "https://dribbble.com/{}",
    "ArtStation": "https://www.artstation.com/{}",
    "Pixiv": "https://www.pixiv.net/en/users/{}",
    "Flickr": "https://www.flickr.com/people/{}",
    "500px": "https://500px.com/p/{}",
    "Unsplash": "https://unsplash.com/@{}",
    "EyeEm": "https://www.eyeem.com/u/{}",
    "Sketchfab": "https://sketchfab.com/{}",
    "Weasyl": "https://www.weasyl.com/~{}",
    "FurAffinity": "https://www.furaffinity.net/user/{}",
    "Cara.app": "https://cara.app/{}",
    # Music
    "Spotify": "https://open.spotify.com/user/{}",
    "SoundCloud": "https://soundcloud.com/{}",
    "Last.fm": "https://www.last.fm/user/{}",
    "Bandcamp": "https://{}.bandcamp.com",
    "Audiomack": "https://audiomack.com/{}",
    "Mixcloud": "https://www.mixcloud.com/{}",
    "ReverbNation": "https://www.reverbnation.com/{}",
    "Genius": "https://genius.com/{}",
    "Musescore": "https://musescore.com/user/{}",
    # Writing / Blogging
    "Medium": "https://medium.com/@{}",
    "Substack": "https://{}.substack.com",
    "WordPress": "https://{}.wordpress.com",
    "Blogger": "https://{}.blogspot.com",
    "Tumblr": "https://{}.tumblr.com",
    "Wattpad": "https://www.wattpad.com/user/{}",
    "Quotev": "https://www.quotev.com/{}",
    "Fanfiction.net": "https://www.fanfiction.net/u/{}",
    "Archive of Our Own": "https://archiveofourown.org/users/{}",
    "Pastebin": "https://pastebin.com/u/{}",
    "Quora": "https://www.quora.com/profile/{}",
    "Livejournal": "https://{}.livejournal.com",
    "Ghost": "https://{}.ghost.io",
    "Hashnode": "https://hashnode.com/@{}",
    "Dev.to": "https://dev.to/{}",
    # Video
    "Vimeo": "https://vimeo.com/{}",
    "Dailymotion": "https://www.dailymotion.com/{}",
    "Rumble": "https://rumble.com/user/{}",
    "Odysee": "https://odysee.com/@{}",
    "Bilibili": "https://space.bilibili.com/{}",
    "Niconico": "https://www.nicovideo.jp/user/{}",
    "Kick": "https://kick.com/{}",
    # Professional / Freelance
    "Fiverr": "https://www.fiverr.com/{}",
    "Freelancer": "https://www.freelancer.com/u/{}",
    "Upwork": "https://www.upwork.com/freelancers/~{}",
    "ProductHunt": "https://www.producthunt.com/@{}",
    "AngelList": "https://angel.co/u/{}",
    "Crunchbase": "https://www.crunchbase.com/person/{}",
    "Contra": "https://contra.com/{}",
    # Finance / Crypto
    "Venmo": "https://account.venmo.com/u/{}",
    "Cash App": "https://cash.app/${}",
    "Ko-fi": "https://ko-fi.com/{}",
    "Patreon": "https://www.patreon.com/{}",
    "Buy Me a Coffee": "https://www.buymeacoffee.com/{}",
    "OpenCollective": "https://opencollective.com/{}",
    "Etherscan": "https://etherscan.io/address/{}",
    # Links / Profile
    "Linktree": "https://linktr.ee/{}",
    "Carrd": "https://{}.carrd.co",
    "About.me": "https://about.me/{}",
    "Gravatar": "https://en.gravatar.com/{}",
    "Campsite": "https://campsite.bio/{}",
    "Beacons": "https://beacons.ai/{}",
    "Bento": "https://bento.me/{}",
    # Q&A / Forums
    "Quora": "https://www.quora.com/profile/{}",
    "Yahoo Answers": "https://answers.yahoo.com/user/profile/{}",
    "StackExchange": "https://stackexchange.com/users/{}",
    "Disqus": "https://disqus.com/{}",
    "Reddit": "https://www.reddit.com/user/{}",
    # Shopping / Reviews
    "Etsy": "https://www.etsy.com/shop/{}",
    "eBay": "https://www.ebay.com/usr/{}",
    "Amazon": "https://www.amazon.com/gp/profile/{}",
    "Depop": "https://www.depop.com/{}",
    "Poshmark": "https://poshmark.com/closet/{}",
    "Grailed": "https://www.grailed.com/{}",
    "Vinted": "https://www.vinted.com/member/{}",
    "Trustpilot": "https://www.trustpilot.com/users/{}",
    # Fitness / Health
    "Strava": "https://www.strava.com/athletes/{}",
    "Garmin Connect": "https://connect.garmin.com/modern/profile/{}",
    "Fitbit": "https://www.fitbit.com/user/{}",
    "MyFitnessPal": "https://www.myfitnesspal.com/profile/{}",
    "Nike Run Club": "https://www.nike.com/member/profile/{}",
    # Travel
    "TripAdvisor": "https://www.tripadvisor.com/members/{}",
    "Couchsurfing": "https://www.couchsurfing.com/people/{}",
    "Airbnb": "https://www.airbnb.com/users/show/{}",
    # Education
    "Academia.edu": "https://independent.academia.edu/{}",
    "ResearchGate": "https://www.researchgate.net/profile/{}",
    "Coursera": "https://www.coursera.org/user/{}",
    "Skillshare": "https://www.skillshare.com/profile/{}",
    "Khan Academy": "https://www.khanacademy.org/profile/{}",
    # Misc
    "Goodreads": "https://www.goodreads.com/{}",
    "Letterboxd": "https://letterboxd.com/{}",
    "IMDb": "https://www.imdb.com/user/{}/",
    "MyAnimeList": "https://myanimelist.net/profile/{}",
    "AniList": "https://anilist.co/user/{}",
    "Kitsu": "https://kitsu.app/users/{}",
    "Trakt": "https://trakt.tv/users/{}",
    "Grouvee": "https://www.grouvee.com/user/{}/",
    "RateYourMusic": "https://rateyourmusic.com/~{}",
    "Untappd": "https://untappd.com/user/{}",
    "Vivino": "https://www.vivino.com/users/{}",
    "Swap.com": "https://www.swap.com/closet/{}",
}

# ── Helpers ──────────────────────────────────────────────────────────────────

# Per-site "not found" indicators in response body
NOT_FOUND_STRINGS = {
    "GitHub": ["Not Found", "page not found"],
    "Instagram": ["Page Not Found", "isn't available"],
    "Reddit": ["page not found", "Sorry, nobody on Reddit goes by that name"],
    "TikTok": ["Couldn't find this account"],
    "YouTube": ["This page isn't available"],
    "Twitch": ["Sorry. Unless you've got a time machine"],
    "Pinterest": ["Hmm, we couldn't find that page"],
    "Steam": ["The specified profile could not be found"],
    "Roblox": ["Page cannot be found"],
    "Chess.com": ["Oops! That page can't be found"],
    "Lichess": ["404"],
    "Duolingo": ["couldn't find"],
    "DeviantArt": ["Not Found"],
    "Behance": ["Page Not Found"],
    "Dribbble": ["Whoops, that page is gone"],
    "ArtStation": ["Page Not Found"],
    "Medium": ["Page not found"],
    "Quora": ["Page Not Found"],
    "Replit": ["Page not found"],
    "GitLab": ["404"],
    "HackerNews": ["No such user"],
    "Keybase": ["isn't a Keybase user"],
    "Fiverr": ["Page Not Found"],
    "Pastebin": ["Page Not Found"],
    "Wattpad": ["Page not found"],
    "Goodreads": ["Page not found"],
    "Letterboxd": ["Letterboxd — Error"],
    "SoundCloud": ["We can't find that user"],
    "Last.fm": ["User not found"],
    "Spotify": ["Page not found"],
    "Tumblr": ["There's nothing here"],
    "Substack": ["Page not found"],
    "Itch.io": ["is not a valid page"],
    "Newgrounds": ["404"],
    "MyAnimeList": ["Invalid Username"],
    "AniList": ["404"],
    "Speedrun.com": ["No user found"],
    "Faceit": ["404"],
    "HackerRank": ["404"],
    "LeetCode": ["Page not found"],
    "Codeforces": ["404"],
    "Kaggle": ["Page not found"],
    "Linktree": ["Sorry, this page isn't available"],
    "Carrd": ["Hmm"],
    "Ko-fi": ["Page not found"],
    "Patreon": ["Page Not Found"],
    "Etsy": ["404"],
    "eBay": ["Page Not Found"],
    "Strava": ["404"],
    "Goodreads": ["Page not found"],
    "TryHackMe": ["404"],
}

async def check_username_url(session, site, url):
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=8),
                               allow_redirects=True,
                               headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}) as resp:
            if resp.status == 404:
                return site, url, False
            if resp.status == 200:
                # Check response body for "not found" strings if we have them for this site
                if site in NOT_FOUND_STRINGS:
                    try:
                        body = await resp.text(errors="ignore")
                        for bad_str in NOT_FOUND_STRINGS[site]:
                            if bad_str.lower() in body.lower():
                                return site, url, False
                    except:
                        pass
                return site, url, True
    except:
        pass
    return site, url, False

async def search_username(username: str) -> dict:
    found = {}
    async with aiohttp.ClientSession() as session:
        tasks = []
        for site, url_template in SHERLOCK_SITES.items():
            url = url_template.format(username)
            tasks.append(check_username_url(session, site, url))
        results = await asyncio.gather(*tasks)
        for site, url, exists in results:
            if exists:
                found[site] = url
    return found

async def check_email_breach(email: str) -> list:
    if not HIBP_API_KEY:
        return None  # no key
    url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}"
    headers = {
        "hibp-api-key": HIBP_API_KEY,
        "User-Agent": "OSINT-TelegramBot"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [b["Name"] for b in data]
                elif resp.status == 404:
                    return []
    except:
        pass
    return None

async def get_ip_info(ip: str) -> dict:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://ipapi.co/{ip}/json/", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    return await resp.json()
    except:
        pass
    return None

async def get_domain_info(domain: str) -> dict:
    results = {}
    import socket
    try:
        ip = socket.gethostbyname(domain)
        results["ip"] = ip
    except:
        return results
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://ipapi.co/{ip}/json/", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results["org"] = data.get("org")
                    results["country"] = data.get("country_name")
                    results["city"] = data.get("city")
    except:
        pass
    return results

# ── Bot Handlers ──────────────────────────────────────────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    init_db()
    user = get_user(update.effective_user.id)
    if user["is_admin"]:
        status = "👑 *Admin — Unlimited access*"
    else:
        remaining = FREE_LIMIT - user["searches_used"]
        status = f"🔢 *Free searches remaining: {remaining}/{FREE_LIMIT}*\nWatch an ad with /watchad to get {FREE_LIMIT} more."
    text = (
        f"🔍 *OSINT Search Bot*\n\n{status}\n\n"
        "Available Commands:\n"
        "`/username <name>` — search 180+ platforms\n"
        "`/email <email>` — data breach check\n"
        "`/ip <address>` — IP info & location\n"
        "`/domain <domain>` — domain info\n"
        "`/watchad` — watch ad to get more searches\n"
        "`/activate <code>` — enter special code"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def cmd_activate(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: `/activate <code>`", parse_mode=ParseMode.MARKDOWN)
        return
    code = ctx.args[0].strip()
    if code == ADMIN_CODE:
        set_admin(update.effective_user.id)
        await update.message.reply_text("👑 *Admin access granted! Unlimited searches.*", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("❌ Invalid code.", parse_mode=ParseMode.MARKDOWN)

async def cmd_watchad(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    init_db()
    user = get_user(update.effective_user.id)
    if user["is_admin"]:
        await update.message.reply_text("👑 You're an admin — unlimited searches already!", parse_mode=ParseMode.MARKDOWN)
        return
    # Show the ad (put your actual ad link/image/text here)
    keyboard = [[InlineKeyboardButton("✅ I watched the ad — give me searches!", callback_data="ad_done")]]
    await update.message.reply_text(
        "📺 *Watch this ad to get 5 more searches:*\n\n"
        "👉 https://www.youtube.com/watch?v=dQw4w9WgXcQ\n\n"  # replace with your actual ad link
        "_After watching, press the button below._",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True
    )

async def ad_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "ad_done":
        init_db()
        increment_ad(query.from_user.id)
        await query.edit_message_text(
            f"✅ *Thanks! You got {FREE_LIMIT} more searches.*",
            parse_mode=ParseMode.MARKDOWN
        )

async def check_limit(update: Update) -> bool:
    """Returns True if user can search, False if blocked."""
    init_db()
    user = get_user(update.effective_user.id)
    allowed, remaining = can_search(user)
    if not allowed:
        keyboard = [[InlineKeyboardButton("📺 Watch Ad for more searches", callback_data="watch_ad_prompt")]]
        await update.message.reply_text(
            "❌ *You've used all your free searches!*\n\n"
            "Watch a short ad to get 5 more searches.\n"
            "Use /watchad to continue.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return False
    return True

async def cmd_username(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: `/username <name>`\nExample: `/username john`", parse_mode=ParseMode.MARKDOWN)
        return

    if not await check_limit(update):
        return
    increment_search(update.effective_user.id)
    username = ctx.args[0].strip().lstrip("@")
    msg = await update.message.reply_text(f"🔍 Searching `{username}` on {len(SHERLOCK_SITES)} platforms...", parse_mode=ParseMode.MARKDOWN)

    found = await search_username(username)

    if not found:
        await msg.edit_text(f"❌ `{username}` — not found on any platform.", parse_mode=ParseMode.MARKDOWN)
        return

    lines = [f"✅ *Found `{username}` on {len(found)} platforms:*\n"]
    for site, url in found.items():
        lines.append(f"• [{site}]({url})")

    # Telegram message limit — split if needed
    text = "\n".join(lines)
    if len(text) > 4000:
        chunks = []
        chunk = lines[0]
        for line in lines[1:]:
            if len(chunk) + len(line) + 1 > 4000:
                chunks.append(chunk)
                chunk = line
            else:
                chunk += "\n" + line
        chunks.append(chunk)
        await msg.edit_text(chunks[0], parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        for c in chunks[1:]:
            await update.message.reply_text(c, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    else:
        await msg.edit_text(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

async def cmd_email(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: `/email <address>`\nExample: `/email test@gmail.com`", parse_mode=ParseMode.MARKDOWN)
        return

    if not await check_limit(update):
        return
    increment_search(update.effective_user.id)
    email = ctx.args[0].strip()
    msg = await update.message.reply_text(f"🔍 Checking `{email}` for breaches...", parse_mode=ParseMode.MARKDOWN)

    await msg.edit_text(
        f"🔍 *Email Breach Check*\n\n"
        f"Check if `{email}` has been in any data breaches:\n\n"
        f"👉 [Click here to check on HIBP](https://haveibeenpwned.com/account/{email})\n\n"
        f"_Have I Been Pwned is the most trusted breach database._",
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )

async def cmd_ip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: `/ip <address>`\nExample: `/ip 8.8.8.8`", parse_mode=ParseMode.MARKDOWN)
        return

    if not await check_limit(update):
        return
    increment_search(update.effective_user.id)
    ip = ctx.args[0].strip()
    msg = await update.message.reply_text(f"🔍 Looking up `{ip}`...", parse_mode=ParseMode.MARKDOWN)

    data = await get_ip_info(ip)
    if not data or data.get("error"):
        await msg.edit_text("❌ Invalid IP ya lookup failed.")
        return

    text = (
        f"🌐 *IP Info: `{ip}`*\n\n"
        f"📍 Country: {data.get('country_name', 'N/A')} {data.get('country_code', '')}\n"
        f"🏙 City: {data.get('city', 'N/A')}\n"
        f"📮 Region: {data.get('region', 'N/A')}\n"
        f"🏢 ISP/Org: {data.get('org', 'N/A')}\n"
        f"🔢 ASN: {data.get('asn', 'N/A')}\n"
        f"🕐 Timezone: {data.get('timezone', 'N/A')}\n"
        f"📡 Type: {'Mobile' if data.get('mobile') else 'VPN/Proxy' if data.get('proxy') else 'Regular'}\n"
        f"🗺 Coords: {data.get('latitude', 'N/A')}, {data.get('longitude', 'N/A')}"
    )
    await msg.edit_text(text, parse_mode=ParseMode.MARKDOWN)

async def cmd_domain(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: `/domain <name>`\nExample: `/domain google.com`", parse_mode=ParseMode.MARKDOWN)
        return

    if not await check_limit(update):
        return
    increment_search(update.effective_user.id)
    domain = ctx.args[0].strip().replace("https://", "").replace("http://", "").rstrip("/")
    msg = await update.message.reply_text(f"🔍 Looking up `{domain}`...", parse_mode=ParseMode.MARKDOWN)

    data = await get_domain_info(domain)

    text = (
        f"🌐 *Domain Info: `{domain}`*\n\n"
        f"🔢 IP: `{data.get('ip', 'N/A')}`\n"
        f"🏢 Org/Host: {data.get('org', 'N/A')}\n"
        f"📍 Country: {data.get('country', 'N/A')}\n"
        f"🏙 City: {data.get('city', 'N/A')}\n\n"
        f"🔗 Shodan: https://www.shodan.io/host/{data.get('ip', '')}\n"
        f"📋 VirusTotal: https://www.virustotal.com/gui/domain/{domain}"
    )
    await msg.edit_text(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Please use a command:\n"
        "`/username <name>`\n"
        "`/email <address>`\n"
        "`/ip <address>`\n"
        "`/domain <name>`",
        parse_mode=ParseMode.MARKDOWN
    )

# ── HTTP Webhook Server for Adsgram Reward URL ───────────────────────────────

async def handle_reward(request):
    """Adsgram calls this URL after user watches ad."""
    user_id = request.rel_url.query.get("userid")
    if user_id:
        try:
            init_db()
            increment_ad(int(user_id))
            print(f"Reward granted to user {user_id}")
            # Notify user in Telegram
            try:
                bot_app = request.app["bot_app"]
                await bot_app.bot.send_message(
                    chat_id=int(user_id),
                    text=f"✅ *Ad watched! You got {FREE_LIMIT} more searches.*",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                print(f"Could not notify user: {e}")
        except Exception as e:
            print(f"Reward error: {e}")
    return web.Response(text="OK", status=200)

async def handle_health(request):
    return web.Response(text="Bot is running!", status=200)

async def run_web_server(bot_app):
    web_app = web.Application()
    web_app["bot_app"] = bot_app
    web_app.router.add_get("/reward", handle_reward)
    web_app.router.add_get("/", handle_health)
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    print("HTTP server running on port 8080")
    return runner

async def main_async():
    bot_app = Application.builder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("username", cmd_username))
    bot_app.add_handler(CommandHandler("email", cmd_email))
    bot_app.add_handler(CommandHandler("ip", cmd_ip))
    bot_app.add_handler(CommandHandler("domain", cmd_domain))
    bot_app.add_handler(CommandHandler("activate", cmd_activate))
    bot_app.add_handler(CommandHandler("watchad", cmd_watchad))
    bot_app.add_handler(CallbackQueryHandler(ad_callback))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Start HTTP server
    runner = await run_web_server(bot_app)

    # Start bot
    print("Bot running...")
    async with bot_app:
        await bot_app.initialize()
        await bot_app.start()
        await bot_app.updater.start_polling()
        # Keep running forever
        try:
            await asyncio.Event().wait()
        finally:
            await bot_app.updater.stop()
            await bot_app.stop()
            await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main_async())
