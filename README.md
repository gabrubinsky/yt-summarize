# YouTube Daily Digest

This tool checks your favorite YouTube channels for videos published in the last 24 hours, summarizes them using AI (Gemini), and emails you a digest.

## Setup

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Configuration:**
    *   Copy `.env.example` to `.env`:
        ```bash
        cp .env.example .env
        ```
    *   Fill in your API keys and email credentials in `.env`:
        *   `GEMINI_API_KEY`: Get one from [Google AI Studio](https://aistudio.google.com/).
        *   `EMAIL_SENDER`: Your Gmail address.
        *   `EMAIL_PASSWORD`: Your Gmail App Password (not your login password). [How to create an App Password](https://support.google.com/accounts/answer/185833).
        *   `EMAIL_RECEIVER`: The email address to receive the digest.

3.  **Add Channels:**
    *   Open `channels.txt` and add the Channel IDs of the YouTube channels you want to follow.

## Usage

Run the script manually:

```bash
python main.py
```

## Automation

To run this automatically every day (e.g., at 8 AM), you can use `cron` on macOS/Linux.

1.  Open crontab:
    ```bash
    crontab -e
    ```
2.  Add a line like this (adjust paths):
    ```bash
    0 8 * * * cd /Users/gaby/Documents/Code/yt-summarize && /Users/gaby/Documents/Code/yt-summarize/venv/bin/python main.py >> output.log 2>&1
    ```
