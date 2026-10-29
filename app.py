# Hotel guest FAQ bot - the web page version.
# Uses the same answer_question function as the terminal version in faq_bot.py.

import os

import gradio as gr

from faq_bot import answer_question, hotel_names


def message_text(content):
    """Gradio stores a message's content either as plain text or as a list of pieces; return the text."""
    if isinstance(content, str):
        return content
    text = ""
    for piece in content:
        if isinstance(piece, dict) and piece.get("type") == "text":
            text = text + piece["text"]
    return text


def chat(message, history, hotel_name):
    # Gradio calls this every time the guest sends a message.
    # "history" holds the earlier chat; we pass it along so Claude can follow the conversation.
    # "hotel_name" comes from the dropdown at the top of the page.
    past = []
    for msg in history:
        text = message_text(msg["content"])
        if text:
            past.append({"role": msg["role"], "content": text})
    return answer_question(message, past, hotel_name)


with gr.Blocks(title="Hotel Front Desk Bot") as demo:
    gr.Markdown("# Hotel Front Desk Bot")
    gr.Markdown("Hi! I'm a virtual front desk. Pick your hotel, then ask me about check-in, parking, breakfast, pets and more.")

    hotel_picker = gr.Dropdown(choices=hotel_names, value=hotel_names[0], label="Your hotel")

    chat_box = gr.ChatInterface(
        fn=chat,
        additional_inputs=[hotel_picker],
        examples=[["What time is check-in?"], ["Is there parking?"], ["Can I bring my dog?"]],
        cache_examples=False,  # don't call Claude for the examples until someone clicks one
        flagging_mode="never",
    )

    # Switching hotels starts a fresh conversation.
    # Gradio keeps the chat in a few places (what's on screen plus hidden copies), so clear them all.
    def clear_chat():
        return [], [], []

    hotel_picker.change(
        clear_chat,
        outputs=[chat_box.chatbot, chat_box.chatbot_state, chat_box.chatbot_value],
    )


if __name__ == "__main__":
    # Hosting services like Render tell the app which port to use through the PORT setting.
    # On your own Mac there's no PORT, so it runs at http://localhost:7860 like before.
    if os.environ.get("PORT"):
        demo.launch(server_name="0.0.0.0", server_port=int(os.environ["PORT"]))
    else:
        demo.launch()
