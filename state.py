games = {}  # user_id → Game объект
last_ui_msg_id = {}  # user_id → message_id главного UI
last_inv_msg_id = {}  # user_id → message_id инвентаря
last_request_time = {}  # user_id → timestamp последнего действия (кулдаун)