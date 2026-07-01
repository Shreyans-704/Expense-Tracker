with open("app/services/telegram_service.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
# Regex to match handle_update and its body until the next @staticmethod
content = re.sub(r'\s+async def handle_update\(self, update: Update\) -> None:.*?(?=\s+@staticmethod\s+async def handle_start)', '', content, flags=re.DOTALL)

with open("app/services/telegram_service.py", "w", encoding="utf-8") as f:
    f.write(content)
