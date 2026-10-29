# Hotel guest FAQ bot.
# Each hotel's info lives in its own text file in the "hotels" folder.
# The first line of each file is the hotel's name.
# Run this file for the terminal version, or run app.py for the web page version.

import os
import sys

import anthropic

# Stop right away with a clear message if the API key hasn't been set
if not os.environ.get("ANTHROPIC_API_KEY"):
    print("No API key found. Run this first, then try again:")
    print('  export ANTHROPIC_API_KEY="paste-your-key-here"')
    sys.exit(1)

# The "hotels" folder sits next to this file
HOTELS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hotels")


def load_hotels():
    """Read every .txt file in the hotels folder.

    Returns a dictionary mapping each hotel's name to its full information.
    """
    hotels = {}
    for filename in sorted(os.listdir(HOTELS_FOLDER)):
        if not filename.endswith(".txt"):
            continue
        fhand = open(os.path.join(HOTELS_FOLDER, filename))
        info = fhand.read()
        fhand.close()
        name = info.strip().split("\n")[0]  # first line is the hotel's name
        hotels[name] = info
    return hotels


hotels = load_hotels()
hotel_names = list(hotels.keys())


def make_system_prompt(hotel_name):
    """The "system prompt" tells Claude who it is and what rules to follow."""
    return """You are a friendly front desk assistant for """ + hotel_name + """.
Answer guest questions using ONLY the hotel information below.
If the answer is not in the information, say you're not sure and offer to
connect the guest with the front desk, using the contact details in the
information. Never make up details.
Keep answers short and warm, like a good front desk agent would.

Hotel information:
""" + hotels[hotel_name]


# Reads your API key from the ANTHROPIC_API_KEY environment variable
client = anthropic.Anthropic()

MAX_QUESTION_LENGTH = 500  # characters per guest message
MAX_HISTORY_MESSAGES = 20  # about 10 back-and-forth exchanges per conversation


def answer_question(question, history, hotel_name):
    """Send a guest question about one hotel to Claude and return the answer as a string.

    history is the conversation so far: a list of messages like
    {"role": "user", "content": "..."} and {"role": "assistant", "content": "..."}.
    Claude has no memory of its own, so we send the whole conversation every time.
    """
    # Limits so a public version can't run up a big bill
    if len(question) > MAX_QUESTION_LENGTH:
        return "Sorry, that message is a bit long for me. Could you ask it in fewer words?"
    if len(history) >= MAX_HISTORY_MESSAGES:
        return "We've covered a lot! Please clear the chat to start a new conversation."

    messages = list(history)
    messages.append({"role": "user", "content": question})

    try:
        response = client.beta.messages.create(
            model="claude-opus-5-5",
            max_tokens=2000,  # front desk answers are short; this caps the cost of each reply
            output_config={"effort": "low"},  # quick, simple answers
            # If the main model declines a request, retry on a fallback model automatically
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=make_system_prompt(hotel_name),
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
    print("Which hotel are you staying at?")
    for i in range(len(hotel_names)):
        print(" ", i + 1, hotel_names[i])

    choice = input("Enter a number: ")
    if not choice.strip().isdigit() or not 1 <= int(choice) <= len(hotel_names):
        print("That's not one of the options.")
        sys.exit(1)
    hotel_name = hotel_names[int(choice) - 1]

    print("\nWelcome to " + hotel_name + "! Ask me anything. Type 'quit' to exit.")
    history = []

    while True:
        question = input("\nGuest: ")
        if question.strip().lower() in ("quit", "exit"):
            break
        if question.strip() == "":
            continue
        answer = answer_question(question, history, hotel_name)
        print("Bot:", answer)

        # Remember this exchange so follow-up questions make sense
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": answer})
