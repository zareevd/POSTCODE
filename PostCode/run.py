import argparse
import csv
import io
import json
import re
from http import HTTPStatus
from http.cookies import SimpleCookie, CookieError
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from secrets import compare_digest, token_hex
from urllib.parse import parse_qsl, urlsplit, urlencode
from datetime import date

from src.app import views
from src.server.integrations.demo import CATALOG
from src.server.services.premium import PLANS
from src.server.repositories import store
from src.server.services.premium import action, initial, quote, basket_quote, roll
from copy import deepcopy

ROOT = Path(__file__).resolve().parent
ASSETS = {"/style.css": (ROOT/"src/app/style.css", "text/css; charset=utf-8")}
for weight in ("regular","bold"):
    ASSETS[f"/golos-{weight}.woff2"] = (ROOT/f"sites/pochtatech-premium/dist/assets/golos-{weight}.woff2","font/woff2")

class Handler(BaseHTTPRequestHandler):
    def reply(self, code, content, kind="text/html; charset=utf-8", headers=None):
        if isinstance(content,str): content=content.encode()
        self.send_response(code)
        self.send_header("Content-Type",kind)
        self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Content-Length",str(len(content)))
        for k,v in (headers or {}).items(): self.send_header(k,v)
        self.end_headers()
        self.wfile.write(content)

    def profile(self, conn):
        cookie=SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie",""))
        except CookieError:
            cookie = SimpleCookie()
        raw=cookie.get("postcode")
        sid=raw.value if raw and re.fullmatch("[0-9a-f]{48}",raw.value) else ""
        state=store.read(conn,sid) if sid else None
        if not state:
            sid,state=token_hex(24),initial()
        roll(state,date.today())
        return sid,state

    def do_GET(self):
        url=urlsplit(self.path)
        args=dict(parse_qsl(url.query))
        if url.path in ASSETS:
            path,kind=ASSETS[url.path]
            return self.reply(200,path.read_bytes(),kind)
        if url.path == "/api/catalog":
            return self.reply(200,json.dumps({"version":"2026-11-24","currency":"RUB","amount_unit":"kopeck","demo":True,
                "services":[{"code":code,"name":label,"price":price,"eligible":code!="international"} for code,(label,price) in CATALOG.items()],
                "plans":[{"id":key,"monthly_price":v[0],"discount_percent":v[1],"discount_cap":v[2]} for key,v in PLANS.items()]},ensure_ascii=False),"application/json; charset=utf-8")
        if url.path == "/health":
            return self.reply(200,'{"status":"ok","app":"postcode"}',"application/json")
        if url.path in ("/api/quote","/api/basket"):

            try:
                result=quote(args.get("plan","personal"),args.get("service","parcel"),args.get("quantity","1"))
                if url.path == "/api/basket":
                    result = basket_quote(args.get("plan","personal"),args)
                return self.reply(200,json.dumps(result),"application/json")
            except ValueError as err:
                return self.reply(400,json.dumps({"error":str(err)}),"application/json")
        if url.path not in ("/","/calculator","/account","/business","/report.csv","/invoice","/terms","/economics","/analytics"):
            return self.reply(404,"Страница не найдена.")
        with store.transaction() as conn:
            sid,s=self.profile(conn)
            if url.path=="/report.csv":
                c=s["company"]
                if not c or c["role"] not in ("admin","accountant"):
                    return self.reply(403,"Отчёт доступен администратору и бухгалтеру.")
                out=io.StringIO()
                writer=csv.writer(out,delimiter=";")
                writer.writerow(["Дата","Сотрудник","Услуга","Цена, коп.","Скидка, коп."])
                for r in s["history"]:
                    if r["plan"]=="business":
                        writer.writerow([r[k] for k in ("day","actor","service","price","saving")])
                return self.reply(200,out.getvalue().encode("utf-8-sig"),"text/csv; charset=utf-8",{"Content-Disposition":"attachment; filename=usage.csv"})
            notice=s.pop("notice","")
            try:
                if url.path=="/":
                    body=views.landing(s)
                    store.event(conn,sid,"landing_view")
                elif url.path=="/calculator":
                    body=views.calculator(args)
                    if "parcel" in args or "quantity" in args: store.event(conn,sid,"calculator_completed")
                elif url.path=="/account":
                    body=views.account(s)
                    store.event(conn,sid,"subscribe_click" if args.get("from")=="cta" else "account_view")
                elif url.path=="/invoice":
                    body=views.invoice(s,args.get("id",""))
                elif url.path=="/terms":
                    body=views.terms()
                elif url.path=="/economics":
                    body=views.economics(args)
                elif url.path=="/analytics":
                    counts=dict(conn.execute("SELECT event,count(*) FROM events WHERE sid=? GROUP BY event",(sid,)))
                    body=views.analytics(counts)
                else:
                    body=views.business(s)
            except PermissionError as err:
                return self.reply(403,views.layout(url.path,"",str(err)))
            except ValueError as err:
                return self.reply(400,views.layout(url.path,views.link("/calculator","Вернуться к расчёту"),str(err)))
            store.save(conn,sid,s)
        self.reply(200,views.layout(url.path,body,notice),headers={"Set-Cookie":f"postcode={sid}; HttpOnly; SameSite=Strict; Path=/; Max-Age=2592000"})

    def do_POST(self):
        if self.path!="/action": return self.reply(404,"Неизвестный адрес.")
        try:
            size=int(self.headers.get("Content-Length","0"))
            if not 0<size<=8192: raise ValueError
            f=dict(parse_qsl(self.rfile.read(size).decode(),max_num_fields=16))
        except (ValueError,UnicodeError):
            return self.reply(400,"Некорректная форма.")
        with store.transaction() as conn:
            sid,s=self.profile(conn)
            if not compare_digest(f.get("csrf","").encode(),s["csrf"].encode()):
                return self.reply(403,"Обновите страницу и повторите действие.")
            key=f.get("id","")
            if not re.fullmatch("[0-9a-f]{32}",key): return self.reply(400,"Некорректный идентификатор операции.")
            op=f.get("op","")
            target={"/":"join withdraw","/account":"pay pause cancel resume ship return","/business":"company role member budget shipbiz remove_member company_details"}
            dest=next((p for p,ops in target.items() if op in ops.split()),None)
            if not dest: return self.reply(400,"Неизвестная операция.")
            if key not in s["seen"]:
                try:
                    candidate=deepcopy(s)
                    message,event=action(candidate,op,f)
                    s=candidate
                    if event: store.event(conn,sid,event)
                except ValueError as err:
                    message=str(err)
                s["seen"][key]=message
            s["notice"]=s["seen"][key]
            store.save(conn,sid,s)
        self.reply(303,b"",headers={"Location":dest})

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--port",type=int,default=4173)
    parser.add_argument("--open-browser", action="store_true", help="Open the local app after the server binds")
    args=parser.parse_args()
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError as err:
        import errno
        if not args.open_browser or err.errno != errno.EADDRINUSE:
            raise
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    with server:
        print(f"PostCode: http://127.0.0.1:{server.server_port}",flush=True)
        if args.open_browser:
            import threading
            import webbrowser
            threading.Thread(target=webbrowser.open, args=(f"http://127.0.0.1:{server.server_port}/",), daemon=True).start()
        server.serve_forever()
