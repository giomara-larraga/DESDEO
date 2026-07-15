class FakeWebSocket:
    def __init__(self):
        self.messages: list[str] = []

    async def send_text(self, message: str):
        self.messages.append(message)