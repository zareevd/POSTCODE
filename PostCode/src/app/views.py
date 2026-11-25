from html import escape
from secrets import token_hex
from urllib.parse import urlencode
from src.server.integrations.demo import CATALOG
from src.server.services.premium import quote, basket_quote, upgrade

def e(v): return escape(str(v),quote=True)
def rub(k): return f"{k/100:,.2f}".replace(","," ").replace(".",",").removesuffix(",00")+" ₽"
def options(values,current=""):
    return "".join(f'<option value="{e(k)}" {"selected" if k==current else ""}>{e(v)}</option>' for k,v in values)
def service(current="parcel"):
    return '<label>Услуга<select name="service">'+options([(k,f"{v[0]} · {rub(v[1])}") for k,v in CATALOG.items()],current)+'</select></label>'
def form(s,op,label,fields=""):
    return f'<form method="post" action="/action"><input type="hidden" name="csrf" value="{s["csrf"]}"><input type="hidden" name="id" value="{token_hex(16)}"><input type="hidden" name="op" value="{op}">{fields}<button>{label}</button></form>'
def card(title,body): return '<article><h2>'+title+'</h2>'+body+'</article>'
def link(url,label): return f'<a class="btn" href="{url}">{label} →</a>'
def layout(page,body,msg=""):
    nav = [("/","О подписке"),("/calculator","Калькулятор"),("/account","Кабинет"),("/business","Для бизнеса"),("/economics","Экономика")]
    links="".join(f'<a href="{u}" aria-current="{"page" if u==page else "false"}">{v}</a>' for u,v in nav)
    notice=f'<p class="notice" role="status">{e(msg)}</p>' if msg else ""
    return f'<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Почта Премиум</title><link rel="stylesheet" href="/style.css"><header><a class="brand" href="/">Почта <b>Премиум</b></a><nav>{links}</nav></header><main>{notice}{body}</main><footer>Почта Премиум · Прототип команды PostCode. Тарифы демонстрационные, платежи имитируются. <a href="/terms">Условия</a> · <a href="/analytics">Моя воронка</a></footer></html>'
def landing(s):
    upgrade(s)
    hero='<section class="hero"><div><small>ПОДПИСКА ДЛЯ ОТПРАВИТЕЛЕЙ</small><h1>Выгода с каждой отправкой</h1><p>Дополнительная скидка 5% на посылки, письма и упаковку. До 50 ₽ за месяц.</p>'+link("/calculator","Рассчитать выгоду")+'</div><aside><small>ЛИЧНЫЙ ТАРИФ</small><strong>29 ₽</strong>за месяц</aside></section>'
    path=card("Как это работает",'<ol><li>Выберите услугу и посчитайте экономию.</li><li>Подключите тариф в кабинете.</li><li>Примените бонус и проверьте остаток лимита.</li></ol>'+link('/account?from=cta','Подключить за 29 ₽'))
    faq=card("Частые вопросы",'<details open><summary>Когда подписка окупится?</summary><p>На двух посылках по 400 ₽ скидка составит 40 ₽. После оплаты подписки останется 11 ₽ экономии.</p></details><details><summary>Какие ограничения?</summary><p>Международные отправления исключены. Остаток скидки не переносится. Цены услуг в демо синтетические.</p></details><details><summary>Как отменить?</summary><p>В кабинете отключите продление. Бонусы доступны до конца оплаченного периода.</p></details>')
    wait=card("Предзапись на пилот",'<p>Проверьте форму на тестовом контакте demo@example.invalid.</p>'+(("<p>Заявка принята. Контакт "+e(s["contact"])+".</p>"+form(s,"withdraw","Отозвать заявку и удалить контакт")) if s["joined"] else form(s,"join","Оставить демо-заявку",'<label>Тестовый email<input name="email" type="email" value="demo@example.invalid" required maxlength="96"></label><label><input type="checkbox" name="feedback"> Согласен на обратную связь по заявке</label>')))
    return hero+'<section class="grid">'+path+faq+'</section>'+wait
def calculator(args):
    plan = args.get("plan","personal")
    quantities = {code:args.get(code,"2" if code=="parcel" else "0") for code in CATALOG}
    q = basket_quote(plan, quantities)
    inputs = '<form action="/calculator"><label>Тариф<select name="plan">'+options([("personal","Личный · 29 ₽"),("business","Бизнес · 299 ₽")],plan)+'</select></label>'
    for code,(label,price) in CATALOG.items():
        inputs += f'<label>{e(label)} · {rub(price)}<input type="number" min="0" max="1000" name="{code}" value="{e(quantities[code])}" required></label>'
    inputs += '<button>Рассчитать экономию</button></form>'
    rows = "".join(f'<tr><td>{e(r["label"])} × {r["quantity"]}</td><td>{rub(r["total"])}</td><td>{rub(r["discount"])}</td></tr>' for r in q["rows"] if r["quantity"])
    verdict = "Подписка окупается при таком объёме." if q["net"]>0 else "При таком объёме подключение не даёт чистой экономии."
    result=f'<strong class="figure">{rub(q["net"])}</strong><p>{verdict}</p><p>Скидка {rub(q["discount"])}, подписка {rub(q["fee"])} за месяц.</p><div class="scroll"><table><tr><th>Услуга</th><th>Без подписки</th><th>Скидка</th></tr>{rows}</table></div>'
    threshold = quote(plan,"parcel",1)["threshold"]
    result+=f'<p>Для посылок по 400 ₽ плата окупается на операции № {threshold} в одном периоде. Международные отправления исключены. Общий месячный потолок применяется ко всей корзине.</p>'
    return '<h1>Ваша выгода за месяц</h1><p>Добавьте отправления и упаковку. Здесь используются демонстрационные цены после обычных скидок.</p><section class="grid">'+card("Состав отправлений",inputs)+card("Результат",result+link("/business" if plan=="business" else "/account?from=cta","Перейти к подключению"))+'</section>'

def history(s,plan,actor=None):
    rows=[r for r in reversed(s["history"]) if r["plan"]==plan and (not actor or r["actor"]==actor)]
    if not rows: return '<p>Операций пока нет.</p>'
    return '<div class="scroll"><table><tr><th>Дата</th><th>Профиль</th><th>Услуга</th><th>Цена</th><th>Скидка</th></tr>'+''.join('<tr>'+''.join(f'<td>{e(v)}</td>' for v in [r["day"],r["actor"],r["service"],rub(r["price"]),rub(r["saving"])])+'</tr>' for r in rows)+'</table></div>'
def checkout(s,op,label):
    return form(s,op,label,'<label>Тестовая оплата<select name="outcome"><option value="success">Успешная оплата</option><option value="fail">Отказ в оплате</option></select></label>')
def account(s):
    upgrade(s)
    states={"inactive":"Не подключена","active":"Активна","pausing":"Пауза со следующего периода","cancelling":"Продление отключено","paused":"На паузе","cancelled":"Отменена","expired":"Период завершён"}
    body='<h1>Личный кабинет</h1>'
    if not s["end"]:
        body+=card(states[s["status"]],'<p>29 ₽ за месяц. Скидка 5%, лимит 50 ₽. Реального списания и автоматических платежей в демо нет.</p>'+checkout(s,"pay","Оплатить 29 ₽ в демо"))
    else:
        controls=(form(s,"pause","Поставить на паузу") if s["status"]=="active" else form(s,"resume","Возобновить продление"))
        if s["status"]!="cancelling": controls+=form(s,"cancel","Отменить продление")
        body+='<section class="grid">'+card(states[s["status"]],f'<p>Бонусы действуют до {s["end"]} (исключительно). Пауза и отмена вступят в силу в конце периода.</p>'+controls)+card("Применить бонус",f'<p>Доступная скидка <b>{rub(5000-s["used"])}</b> из 50 ₽.</p>'+form(s,"ship","Применить к одной операции",service()))+'</section>'
    payments = "".join(f'<p>{e(p["day"])} · {rub(p["amount"])} · {"Оплачено" if p["result"]=="success" else "Отклонено"}</p>' for p in reversed(s["payments"])) or "<p>Платежей пока нет.</p>"
    returns = "".join(f'<p>Запрос № {r["id"]} от {e(r["day"])} · На рассмотрении</p>' for r in s["returns"])
    refund = form(s,"return","Отправить запрос",'<label>Причина<textarea name="reason" minlength="5" maxlength="500" required></textarea></label>') if s["end"] else ""
    return body+card("История использования",history(s,"personal"))+card("Платежи",payments)+card("Прекращение услуги и возврат",'<p>Запрос отключает продление. Сумма возврата определяется после рассмотрения. В прототипе деньги не списываются.</p>'+returns+refund)
def business(s):
    upgrade(s)
    c=s["company"]
    body='<h1>Для бизнеса</h1><p>299 ₽ за месяц · 5 пользователей · 3% на услуги · общий лимит скидок 500 ₽.</p>'
    if c and not c["active"]:
        body+=card("История компании", history(s,"business",c["role"] if c["role"] in c["members"] else None))
        if c["role"] in ("admin","accountant"):
            body+=card("Счета прошлых периодов","".join(f'<p><a href="/invoice?id={i["id"]}">Счёт № {i["id"]}</a> · {rub(i["amount"])}</p>' for i in reversed(c["invoices"]))+link("/report.csv","Отчёт CSV"))
        body+=form(s,"role","Открыть профиль",'<label>Профиль<select name="role">'+options([("admin","Администратор"),("accountant","Бухгалтер")]+[(k,k) for k in c["members"]],c["role"])+'</select></label>')
        if c["role"]!="admin":
            return body+card("Период завершён","<p>Новый период подключает администратор компании.</p>")
    if not c or not c["active"]:
        return body+card("Демо-компания «Маяк»",'<p>Подключите компанию с тестовыми реквизитами. Первый счёт появится после имитации оплаты.</p>'+checkout(s,"company","Оплатить счёт на 299 ₽"))
    role=c["role"]
    roles=[("admin","Администратор"),("accountant","Бухгалтер")]+[(k,k) for k in c["members"]]
    body+=card("Компания «"+e(c["name"])+"»",f'<p>До {c["end"]} · осталось {rub(50000-c["used"])} общей скидки.</p>'+form(s,"role","Открыть профиль",'<label>Демонстрационная смена роли<select name="role">'+options(roles,role)+'</select></label>'))
    if role=="admin":
        fields='<label>Лимит скидки на период, ₽<input type="number" min="0" max="500" name="budget" value="100" required></label>'
        admin=form(s,"company_details","Сохранить название",f'<label>Демонстрационное название компании<input name="name" value="{e(c["name"])}" minlength="2" maxlength="80" required></label>')
        admin+=f'<p>Занято {2+len(c["members"])} из 5 мест, включая администратора и бухгалтера.</p>'
        if len(c["members"])<3: admin+=form(s,"member","Добавить сотрудника",fields)
        for k,m in c["members"].items():
            admin+=f'<h3>{e(k)}</h3><p>Использовано {rub(m["used"])} из {rub(m["limit"])}.</p>'+form(s,"budget","Обновить лимит",f'<input type="hidden" name="member" value="{e(k)}">'+fields.replace('value="100"',f'value="{m["limit"]//100}"'))
            admin+=form(s,"remove_member","Отключить сотрудника",f'<input type="hidden" name="member" value="{e(k)}">')
        body+=card("Сотрудники и лимиты",admin)
    if role in c["members"]:
        m=c["members"][role]
        body+=card("Отправление сотрудника",f'<p>Личный остаток скидки {rub(m["limit"]-m["used"])}.</p>'+form(s,"shipbiz","Применить бонус",service()))
        return body+card("Мои операции",history(s,"business",role))
    invoices="".join(f'<p>Демо-счёт № {i["id"]} · {i["start"]} — {i["end"]} · {rub(i["amount"])} · Оплачен <a href="/invoice?id={i["id"]}">Открыть счёт</a></p>' for i in reversed(c["invoices"]))
    return body+card("Счета",invoices)+card("Отчёт по компании",history(s,"business")+link("/report.csv","Скачать CSV"))


def invoice(s, number):
    c=s["company"]
    if not c or c["role"] not in ("admin","accountant"):
        raise PermissionError("Счета доступны администратору и бухгалтеру.")
    record=next((i for i in c["invoices"] if str(i["id"])==number),None)
    if record is None:
        raise ValueError("Счёт не найден.")
    return card(f'Демонстрационный счёт № {record["id"]}',f'<p>Получатель — компания «{e(c["name"])}», код {e(c["reference"])}.</p><p>Почта Премиум Бизнес, период {record["start"]} — {record["end"]}.</p><strong class="figure">{rub(record["amount"])}</strong><p>Статус — оплачено в симуляции. Банковские реквизиты и фискальный документ не формируются.</p><p>Для печати используйте Ctrl+P.</p>')

def terms():
    return '<h1>Условия демонстрации</h1>'+card("Тарифы",'<p>Личный — 29 ₽/месяц, скидка 5%, предел 50 ₽. Бизнес — 299 ₽/месяц, скидка 3%, предел 500 ₽ на компанию, до пяти мест с учётом администратора и бухгалтера.</p><p>Скидки доступны на внутренние отправления и упаковку. Международные услуги исключены. Остатки лимитов не переносятся. В этой версии новый период оплачивается вручную. Календарный месяц начинается в день подключения.</p>')+card("Управление",'<p>Пауза и отмена действуют с окончания оплаченного периода. Запрос на прекращение услуги и возврат доступен отдельно в кабинете. Платежи, отправления и счета имитируются.</p>')+card("Данные",'<p>Используйте синтетические названия и контакты @example.invalid. Данные хранятся локально в SQLite, а cookie связывает браузер с демо-профилем. Заявку можно отозвать на главной странице. Согласие на обратную связь необязательно.</p><p>Партнёрские предложения в тариф не включены. Реальных договорённостей с партнёрами нет.</p>')

def economics(args):
    defaults={"customers":1000,"price":29,"discount":24,"uplift":0.4,"margin":80,"churn":8,"cac":100}
    values={}
    for key,default in defaults.items():
        try:
            value=float(args.get(key,default))
        except ValueError:
            raise ValueError("Введите числовые параметры.") from None
        if not 0<=value<=1000000 or (key in ("churn","cac") and value<=0) or (key=="churn" and value>100):
            raise ValueError("Некорректное значение параметра.")
        values[key]=value
    labels=["Платящих клиентов","Цена подписки, ₽","Средняя скидка, ₽","Прирост отправлений на клиента","Маржа доп. отправления, ₽","Месячный отток, %","CAC, ₽"]
    inputs='<form action="/economics">'+''.join(f'<label>{label}<input type="number" name="{key}" step="any" min="0" value="{values[key]}" required></label>' for key,label in zip(defaults,labels))+'<button>Пересчитать</button></form>'
    contribution=values["price"]*.97-values["discount"]-4+values["uplift"]*values["margin"]
    ltv=contribution/(values["churn"]/100)
    results=f'<p>MRR <b>{values["customers"]*values["price"]:,.0f} ₽</b></p><p>Вклад на клиента <b>{contribution:.2f} ₽/мес.</b></p><p>LTV по вкладу <b>{ltv:.2f} ₽</b></p><p>LTV/CAC <b>{ltv/values["cac"]:.2f}</b></p>'
    results+=f'<p>Окупаемость CAC {values["cac"]/contribution:.1f} мес.</p>' if contribution>0 else '<p>При отрицательном или нулевом вкладе CAC не окупается.</p>'
    return '<h1>Экономика гипотезы</h1><p>Редактируйте параметры и сравнивайте сценарии. Это допущения команды, а не результаты продаж.</p><section class="grid">'+card("Параметры",inputs)+card("Результат",results+'<p>Эквайринг 3% платы, обслуживание и резерв 4 ₽/клиента. Скидка вычитается полностью. Прирост должен быть подтверждён контрольной группой. Постоянные расходы и налоги не включены.</p>')+'</section>'

def analytics(counts):
    labels={"landing_view":"Лендинг","calculator_completed":"Расчёт","subscribe_click":"Подключение","waitlist_submitted":"Заявка","payment_success":"Оплата","benefit_used":"Бонус"}
    return '<h1>Воронка вашего демо-профиля</h1>'+card("События",'<p>Показаны события текущего браузерного профиля. Совокупные уникальные конверсии доступны через python tools/funnel.py.</p>'+''.join(f'<p>{label} <b>{counts.get(key,0)}</b></p>' for key,label in labels.items()))
