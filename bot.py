import os
import asyncio
import aiohttp
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
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

async def check_username_url(session, site, url):
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=8), 
                               allow_redirects=True,
                               headers={"User-Agent": "Mozilla/5.0"}) as resp:
            if resp.status == 200:
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
    try:
        async with aiohttp.ClientSession() as session:
            # IP from domain
            async with session.get(f"https://ipapi.co/{domain}/json/", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results["ip"] = data.get("ip")
                    results["org"] = data.get("org")
                    results["country"] = data.get("country_name")
                    results["city"] = data.get("city")
    except:
        pass
    return results

# ── Bot Handlers ──────────────────────────────────────────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "🔍 *OSINT Search Bot*\n\n"
        "Kya search karna hai?\n\n"
        "Commands:\n"
        "`/username <name>` — 50+ platforms pe search\n"
        "`/email <email>` — breach check (HIBP)\n"
        "`/ip <address>` — IP info & location\n"
        "`/domain <domain>` — domain/site info\n\n"
        "Example: `/username volt`"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def cmd_username(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: `/username <name>`\nExample: `/username volt`", parse_mode=ParseMode.MARKDOWN)
        return

    username = ctx.args[0].strip().lstrip("@")
    msg = await update.message.reply_text(f"🔍 Searching `{username}` on {len(SHERLOCK_SITES)} platforms...", parse_mode=ParseMode.MARKDOWN)

    found = await search_username(username)

    if not found:
        await msg.edit_text(f"❌ `{username}` — koi bhi platform pe nahi mila.", parse_mode=ParseMode.MARKDOWN)
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

    email = ctx.args[0].strip()
    msg = await update.message.reply_text(f"🔍 Checking `{email}` for breaches...", parse_mode=ParseMode.MARKDOWN)

    if not HIBP_API_KEY:
        await msg.edit_text(
            "⚠️ *HIBP API key set nahi hai.*\n\n"
            "Free check ke liye manually visit karo:\n"
            f"👉 https://haveibeenpwned.com/account/{email}",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    breaches = await check_email_breach(email)
    if breaches is None:
        await msg.edit_text("❌ Error — try again.")
        return

    if not breaches:
        await msg.edit_text(f"✅ `{email}` — *koi breach nahi mila!* Safe hai.", parse_mode=ParseMode.MARKDOWN)
    else:
        breach_list = "\n".join([f"• {b}" for b in breaches])
        await msg.edit_text(
            f"⚠️ `{email}` *{len(breaches)} breaches mein mila:*\n\n{breach_list}",
            parse_mode=ParseMode.MARKDOWN
        )

async def cmd_ip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: `/ip <address>`\nExample: `/ip 8.8.8.8`", parse_mode=ParseMode.MARKDOWN)
        return

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
        "Commands use karo:\n"
        "`/username <name>`\n"
        "`/email <address>`\n"
        "`/ip <address>`\n"
        "`/domain <name>`",
        parse_mode=ParseMode.MARKDOWN
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("username", cmd_username))
    app.add_handler(CommandHandler("email", cmd_email))
    app.add_handler(CommandHandler("ip", cmd_ip))
    app.add_handler(CommandHandler("domain", cmd_domain))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
