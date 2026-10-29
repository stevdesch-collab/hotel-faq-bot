# Hotel guest FAQ bot - step 2: a web page version.
# Uses the same answer_question function as the terminal version in faq_bot.py.

import gradio as gr

from faq_bot import answer_question


def message_text(content):
    """Gradio stores a message's content either as plain text or as a list of pieces; return the text."""
    if isinstance(content, str):
        return content
    text = ""
    for piece in content:
        if isinstance(piece, dict) and piece.get("type") == "text":
            text = text + piece["text"]
    return text


def chat(message, history):
    # Gradio calls this every time the guest sends a message.
    # "history" holds the earlier chat; we pass it along so Claude can follow the conversation.
    past = []
    for msg in history:
        text = message_text(msg["content"])
        if text:
            past.append({"role": msg["role"], "content": text})
    return answer_question(message, past)


demo = gr.ChatInterface(
    fn=chat,
    title="The Harbor View Hotel",
    description="Hi! I'm the hotel's virtual front desk. Ask me about check-in, parking, breakfast, pets and more.",
    examples=["What time is check-in?", "How much is parking?", "Can I bring my dog?"],
    cache_examples=False,  # don't call Claude for the examples until someone clicks one
    flagging_mode="never",
)

demo.launch()
