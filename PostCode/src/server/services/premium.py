from datetime import date, timedelta
from secrets import token_hex
import re
import calendar
from src.server.integrations.demo import CATALOG, payment

PLANS = {"personal": (2900, 5, 5000), "business": (29900, 3, 50000)}

def number(value, low, high):
    try:
        if isinstance(value, bool) or not re.fullmatch(r"[0-9]+", str(value)):
            raise ValueError
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError("Введите целое число.") from None
    if not low <= number <= high:
        raise ValueError(f"Введите число от {low} до {high}.")
    return number

def quote(plan, service, quantity):
    if plan not in PLANS or service not in CATALOG:
        raise ValueError("Неизвестный тариф или услуга.")
    n = number(quantity, 0, 1000)
    fee, rate, cap = PLANS[plan]
    price = CATALOG[service][1]
    unit = price * rate // 100 if service != "international" else 0
    discount = min(unit*n, cap)
    return dict(total=n*price, discount=discount, net=discount-fee,
                threshold=(fee+unit-1)//unit if unit else None)

def initial():
    return dict(csrf=token_hex(24), seen={}, status="inactive", end="", used=0,
                company=None, history=[], joined=False, feedback=False)

def roll(s, today):
    upgrade(s)
    if s["end"] and today >= date.fromisoformat(s["end"]):
        s["status"] = {"pausing":"paused","cancelling":"cancelled"}.get(s["status"],"expired")
        s["end"] = ""
        s["used"] = 0
    c = s["company"]
    if c and today >= date.fromisoformat(c["end"]):
        c["active"] = False

def require(condition, message):
    if not condition:
        raise ValueError(message)

def action(s, op, f, today=None):
    today = today or date.today()
    upgrade(s)
    roll(s,today)
    extra = extra_action(s, op, f, today)
    if extra is not None:
        return extra
    c = s["company"]
    if op == "join":
        require(not s["joined"], "Заявка уже сохранена.")
        email = f.get("email", "demo@example.invalid").strip()
        require(bool(re.fullmatch(r"[a-zA-Z0-9._+-]{1,80}@example\.invalid", email)), "Используйте тестовый адрес вида name@example.invalid.")
        s.update(joined=True, feedback=f.get("feedback")=="on", contact=email, consent_date=str(today), consent_version="2026-11-24")
        return "Заявка демо-профиля сохранена.", "waitlist_submitted"
    if op == "pay":
        require(not s["end"], "Текущий период уже оплачен.")
        if not payment(f.get("outcome")):
            s["payments"].append(dict(day=str(today), amount=2900, result="failed"))
            return "Оплата отклонена. Можно попробовать снова.", "payment_failed"
        s["payments"].append(dict(day=str(today), amount=2900, result="success"))
        s.update(status="active", end=str(next_month(today)), used=0)
        return "Демо-оплата прошла. Бонус доступен.", "payment_success"
    if op in ("pause","cancel","resume"):
        allowed = {"pause":["active"], "cancel":["active","pausing"], "resume":["pausing","cancelling"]}
        require(s["status"] in allowed[op],"Действие недоступно в текущем состоянии.")
        s["status"] = {"pause":"pausing","cancel":"cancelling","resume":"active"}[op]
        return "Настройки подписки сохранены.", op
    if op == "company":
        require(c is None or not c["active"],"Компания уже подключена.")
        if not payment(f.get("outcome")):
            return "Оплата счёта отклонена.", "business_payment_failed"
        end = str(next_month(today))
        if not c:
            c = s["company"] = dict(members={},invoices=[],role="admin",name="Маяк",reference="DEMO-001")
        require(c["role"]=="admin", "Оплата компании доступна администратору.")
        c.update(active=True,end=end,used=0)
        for m in c["members"].values(): m["used"] = 0
        c["invoices"].append(dict(id=len(c["invoices"])+1,start=str(today),end=end,amount=29900))
        return "Демо-счёт оплачен.", "business_payment_success"
    if op in ("member","budget","role","shipbiz"):
        require(c and (c["active"] or op=="role"),"Подключите компанию.")
        if op == "role":
            role = f.get("role")
            require(role in ("admin","accountant") or role in c["members"],"Неизвестная роль.")
            c["role"] = role
            return "Демо-профиль переключён.", None
        if op in ("member","budget"):
            require(c["role"]=="admin","Доступно администратору.")
            limit = number(f.get("budget"),0,500)*100
            if op == "member":
                require(len(c["members"])<3,"Заняты все пять мест, включая администратора и бухгалтера.")
                key = "Сотрудник "+str(c.get("next_member", len(c["members"])+1))
                c["next_member"] = int(key.split()[-1])+1
                c["members"][key] = dict(limit=limit,used=0)
            else:
                m = c["members"].get(f.get("member"))
                require(m and limit>=m["used"],"Лимит меньше использованной скидки.")
                m["limit"] = limit
            return "Лимит сотрудника сохранён.", None
    require(op in ("ship","shipbiz"),"Неизвестное действие.")
    biz = op=="shipbiz"
    if biz:
        member = c["members"].get(c["role"])
        require(member,"Выберите профиль сотрудника.")
    else:
        require(bool(s["end"]),"Сначала подключите подписку.")
    plan = "business" if biz else "personal"
    q = quote(plan,f.get("service"),1)
    owner = c if biz else s
    saving = min(q["discount"], PLANS[plan][2]-owner["used"])
    if biz: saving = min(saving,member["limit"]-member["used"])
    require(saving>0,"Скидка недоступна для услуги или лимит исчерпан.")
    owner["used"] += saving
    if biz: member["used"] += saving
    s["history"].append(dict(day=str(today),plan=plan,actor=c["role"] if biz else "Личный кабинет",
                             service=CATALOG[f["service"]][0],price=q["total"],saving=saving))
    return "Бонус применён. Операция сохранена в истории.", "benefit_used"


def next_month(today):
    year = today.year + today.month // 12
    month = today.month % 12 + 1
    return date(year, month, min(today.day, calendar.monthrange(year, month)[1]))

def upgrade(s):
    """Add fields to profiles created by earlier prototype versions."""
    for key, value in {"payments": [], "returns": [], "contact": "", "consent_date": "", "consent_version": ""}.items():
        s.setdefault(key, value)
    if s.get("company"):
        s["company"].setdefault("name", "Маяк")
        s["company"].setdefault("reference", "DEMO-001")
        s["company"].setdefault("reference", "DEMO-001")

def basket_quote(plan, quantities):
    require(plan in PLANS, "Неизвестный тариф.")
    fee, rate, cap = PLANS[plan]
    rows = []
    discount = 0
    total = 0
    for code, (label, price) in CATALOG.items():
        count = number(quantities.get(code, "0"), 0, 1000)
        raw = quote(plan, code, count)["discount"]
        saving = min(raw, cap-discount)
        rows.append(dict(code=code, label=label, quantity=count, total=count*price, discount=saving))
        discount += saving
        total += count*price
    return dict(rows=rows, total=total, discount=discount, fee=fee, net=discount-fee, remaining=cap-discount)

def extra_action(s, op, f, today):
    if op == "withdraw":
        s.update(joined=False, feedback=False, contact="", consent_date="", consent_version="")
        return "Заявка и согласие отозваны, контакт удалён.", "waitlist_withdrawn"
    if op == "return":
        require(bool(s["end"]), "Нет действующей подписки.")
        require(not any(r["status"]=="pending" for r in s["returns"]), "Запрос уже рассматривается.")
        reason = f.get("reason","").strip()
        require(5 <= len(reason) <= 500, "Опишите причину, от 5 до 500 символов.")
        s["returns"].append(dict(id=len(s["returns"])+1, day=str(today), reason=reason, status="pending"))
        s["status"] = "cancelling"
        return "Запрос принят, продление отключено. Возврат денег требует рассмотрения.", "return_requested"
    if op in ("remove_member", "company_details"):
        c = s["company"]
        require(c and c["role"]=="admin", "Доступно администратору.")
        if op == "remove_member":
            key = f.get("member")
            require(key in c["members"], "Сотрудник не найден.")
            del c["members"][key]
            return "Сотрудник отключён. История сохранена.", None
        name = f.get("name","").strip()
        require(2 <= len(name) <= 80, "Название должно содержать от 2 до 80 символов.")
        c["name"] = name
        return "Название компании сохранено.", None
    return None
