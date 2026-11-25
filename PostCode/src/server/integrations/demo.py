# Синтетические цены после обычных скидок, в копейках.
CATALOG = {"parcel": ("Посылка", 40000), "letter": ("Заказное письмо", 12000),
           "box": ("Упаковка", 8000), "international": ("Международная посылка", 120000)}
def payment(outcome):
    if outcome not in ("success","fail"):
        raise ValueError("Выберите результат тестовой оплаты.")
    return outcome == "success"
