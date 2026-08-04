import requests

token = "8830800402:AAHeSDg9Hvuay-M5bt7gwIwfH8t_zF4JDUo"
chat_id = 8950733976
text = "👋 <b>Important Update:</b>\n\nYour Telegram cache prevented the Dashboard from updating. Please use the button below to open the new Dashboard."
reply_markup = {
    "inline_keyboard": [
        [{"text": "🖥 Open Dashboard (Updated)", "web_app": {"url": "https://www.hunterstar.online/?v=3"}}]
    ]
}
url = f"https://api.telegram.org/bot{token}/sendMessage"
res = requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML", "reply_markup": reply_markup})
print(res.json())
