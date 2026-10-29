# Hotel guest FAQ bot.
# Reads the hotel's info from hotel_info.txt, then answers guest questions with Claude.
# Run this file for the terminal version, or run app.py for the web page version.

import os
import sys

import anthropic

# Stop right away with a clear message if the API key hasn't been set
if not os.environ.get("ANTHROPIC_API_KEY"):
    print("No API key found. Run this first, then try again:")
    print('  export ANTHROPIC_API_KEY="paste-your-key-here"')
    sys.exit(1)

# Load the hotel's information so Claude can answer from it
fhand = open("hotel_info.txt")
hotel_info = fhand.read()
fhand.close()

# The "system prompt" tells Claude who it is and what rules to follow
system_prompt = """You are a friendly front desk assistant for a hotel.
Answer guest questions using ONLY the hotel information below.
If the answer is not in the information, say you're not sure and offer to
connect the guest with the front desk (dial 0). Never make up details.
Keep answers short and warm, like a good front desk agent would.

Hotel information:
""" + hotel_info

# Reads your API key from the ANTHROPIC_API_KEY environment variable
client = anthropic.Anthropic()


def answer_question(question, history=None):
    """Send a guest question to Claude and return the answer as a string.

    history is the conversation so far: a list of messages like
    {"role": "user", "content": "..."} and {"role": "assistant", "content": "..."}.
    Claude has no memory of its own, so we send the whole conversation every time.
    """
    messages = []
    if history:
        messages = list(history)
    messages.append({"role": "user", "content": question})

    try:
        response = client.beta.messages.create(
            model="claude-opus-5-5",
            max_tokens=16000,
            output_config={"effort": "low"},  # quick, simple answers
            # If the main model declines a request, retry on a fallback model automatically
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=system_prompt,
            messages=messages,
        )
    except anthropic.AuthenticationError:
        return "Your API key isn't working. Check ANTHROPIC_API_KEY."
    except anthropic.APIConnectionError:
        return "Couldn't reach Claude. Check your internet connection."
    except anthropic.APIStatusError as e:
        return "Something went wrong: " + e.message

    # The reply comes back as a list of "blocks"; join the text ones together
    answer = ""
    for block in response.content:
        if block.type == "text":
            answer = answer + block.text
    return answer


# This part only runs when you start this file directly (not when app.py imports it)
if __name__ == "__main__":
    print("Welcome! Ask me anything about the hotel. Type 'quit' to exit.")
    history = []

    while True:
        question = input("\nGuest: ")
        if question.strip().lower() in ("quit", "exit"):
            break
        if question.strip() == "":
            continue
        answer = answer_question(question, history)
        print("Bot:", answer)

        # Remember this exchange so follow-up questions make sense
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": answer})
