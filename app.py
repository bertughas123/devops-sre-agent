"""OpsGuard Ana Uygulama."""
import chainlit as cl

@cl.on_chat_start
async def start():
    await cl.Message(content="🛡️ OpsGuard Aktif — Faz 0 İskelet").send()

@cl.on_message
async def main(message: cl.Message):
    await cl.Message(
        content=f"Mesajın alındı: {message.content}\n\n_(Agent henüz aktif değil — Faz 1'de gelecek)_"
    ).send()
