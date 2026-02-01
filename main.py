import os
import smtplib
import time
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import feedparser
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def get_channel_rss_url(channel_input):
    """
    Determines the RSS URL from a channel input (ID or URL).
    Simple heuristic: if it looks like a URL, use it; otherwise assume it's a channel ID.
    """
    channel_input = channel_input.strip()
    if channel_input.startswith("http"):
        # If it's already a feed URL
        if "feeds/videos.xml" in channel_input:
            return channel_input
        # If it's a standard channel URL, we might need to extract ID (complex),
        # but for now, we'll assume the user provides the ID or the correct RSS Feed.
        # A simple fallback for "channel/ID" format:
        if "youtube.com/channel/" in channel_input:
            channel_id = channel_input.split("youtube.com/channel/")[1].split("/")[0]
            return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        
        # User might have provided a username URL (@), which is harder to parse without API/Scraping.
        print(f"Warning: automatic RSS discovery for '{channel_input}' might not work. Please use Channel ID or RSS Feed URL.")
        return channel_input
    else:
        # Assume it is a Channel ID
        return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_input}"

def get_videos_last_24h(rss_url):
    """Parses the RSS feed and returns videos published in the last 24 hours."""
    feed = feedparser.parse(rss_url)
    if feed.bozo:
        print(f"Error parsing feed: {rss_url}")
        return []

    new_videos = []
    now = datetime.datetime.now(datetime.timezone.utc)
    one_day_ago = now - datetime.timedelta(hours=24)

    for entry in feed.entries:
        # entry.published_parsed is a struct_time, convert to datetime
        if not hasattr(entry, 'published_parsed'):
            continue
            
        published_ts = datetime.datetime.fromtimestamp(time.mktime(entry.published_parsed), datetime.timezone.utc)
        
        if published_ts > one_day_ago:
            new_videos.append({
                'title': entry.title,
                'link': entry.link,
                'video_id': entry.yt_videoid,
                'published': published_ts,
                'channel': feed.feed.title
            })
    return new_videos

def get_transcript(video_id):
    """Fetches transcript for a video."""
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        # Combine text
        full_text = " ".join([t['text'] for t in transcript_list])
        return full_text
    except Exception as e:
        print(f"Could not retrieve transcript for {video_id}: {e}")
        return None

def summarize_video(text, video_title):
    """Uses Gemini to summarize the transcript."""
    if not GEMINI_API_KEY:
        return "Gemini API Key not found. Cannot summarize."

    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"Please summarize the following YouTube video transcript titled '{video_title}'. Capture the key points and takeaways in a bulleted list.\n\nTranscript:\n{text}"
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating summary: {e}"

def send_email(email_body):
    """Sends the daily digest email."""
    if not EMAIL_SENDER or not EMAIL_PASSWORD or not EMAIL_RECEIVER:
        print("Email credentials not set. skipping email.")
        print("---" + " Email Body " + "---")
        print(email_body)
        print("------------------")
        return

    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = f"YouTube Daily Digest - {datetime.date.today()}"

    msg.attach(MIMEText(email_body, 'plain'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, text)
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

def main():
    if not os.path.exists("channels.txt"):
        print("channels.txt not found.")
        return

    with open("channels.txt", "r") as f:
        channels = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    all_summaries = []

    for channel_input in channels:
        rss_url = get_channel_rss_url(channel_input)
        print(f"Checking {rss_url}...")
        videos = get_videos_last_24h(rss_url)
        
        for video in videos:
            print(f"Found new video: {video['title']}")
            transcript = get_transcript(video['video_id'])
            
            if transcript:
                print(f"Summarizing {video['title']}...")
                summary = summarize_video(transcript, video['title'])
                all_summaries.append(f"CHANNEL: {video['channel']}\nVIDEO: {video['title']}\nLINK: {video['link']}\n\nSUMMARY:\n{summary}\n\n" + "-"*40 + "\n")
            else:
                all_summaries.append(f"CHANNEL: {video['channel']}\nVIDEO: {video['title']}\nLINK: {video['link']}\n\n(No transcript available for summarization)\n\n" + "-"*40 + "\n")

    if all_summaries:
        full_body = "Here is your daily YouTube summary:\n\n" + "\n".join(all_summaries)
        send_email(full_body)
    else:
        print("No new videos found in the last 24 hours.")

if __name__ == "__main__":
    main()
