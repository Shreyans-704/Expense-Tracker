with open("app/services/telegram_service.py", "r", encoding="utf-8") as f:
    if "handle_update" in f.read():
        print("handle_update still there")
    else:
        print("handle_update removed")
