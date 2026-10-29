# Hotel guest FAQ bot - step 2: a web page version.
# Uses the same answer_question function as the terminal version in faq_bot.py.

import gradio as gr

from faq_bot import answer_question


def chat(message, history):
    # Gradio calls this every time the guest sends a message.
    # "history" holds the earlier chat; we don't use it yet, so each question is answered on its own.
    return answer_question(message)


demo = gr.ChatInterface(
    fn=chat,
    title="The Harbor View Hotel",
    description="Hi! I'm the hotel's virtual front desk. Ask me about check-in, parking, breakfast, pets and more.",
    examples=["What time is check-in?", "How much is parking?", "Can I bring my dog?"],
    cache_examples=False,  # don't call Claude for the examples until someone clicks one
    flagging_mode="never",
)

demo.launch()
