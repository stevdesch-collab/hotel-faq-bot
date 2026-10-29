# Hotel Guest FAQ Bot

A virtual front desk assistant that answers hotel guests' questions — check-in times, parking, breakfast, pet policy, and more — using Claude.

I spent years in hospitality, where the same handful of guest questions come up all day. This project is my first step in applying AI to that problem: a bot that answers from the hotel's own information, and hands off to a human when it doesn't know.

## How it works

- `hotel_info.txt` holds the hotel's details in plain text. Edit this file to use the bot for a different hotel.
- `faq_bot.py` sends the guest's question to Claude along with a **system prompt** containing the hotel info and a few rules:
  - Answer only from the hotel information.
  - If the answer isn't there, say so and offer to connect the guest with the front desk. **Never make up details.**
  - Keep answers short and warm, like a good front desk agent.
- `app.py` puts a chat web page in front of the bot using [Gradio](https://www.gradio.app/).

The "don't make things up" rule matters most. A bot that confidently invents a pool or a spa is worse than no bot at all, so a good test is asking about something the hotel doesn't have.

## Example

The sample hotel allows dogs under 50 lbs, so asking "Can I bring my 80 lb dog?" should get a friendly no that explains the limit, not a made-up exception. Asking "Is there a spa?" (there isn't one) should get an offer to connect you with the front desk.

## Running it yourself

You'll need Python 3 and an [Anthropic API key](https://console.anthropic.com).

```bash
git clone https://github.com/stevdesch-collab/hotel-faq-bot.git
cd hotel-faq-bot
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-key-here"
```

Then start the web page and open http://localhost:7860:

```bash
.venv/bin/python app.py
```

Or chat in the terminal:

```bash
.venv/bin/python faq_bot.py
```

## What I'd add next

- Conversation memory, so follow-up questions like "and how much is it?" make sense.
- Hosting it online so anyone can try it.
- Loading info for multiple hotels.

## Built with

Python · [Anthropic Claude API](https://docs.anthropic.com) · [Gradio](https://www.gradio.app/)

Built after completing *Python for Everybody* (University of Michigan, Coursera) and *ChatGPT Prompt Engineering for Developers* (DeepLearning.AI).
