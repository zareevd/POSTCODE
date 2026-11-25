import concurrent.futures
from datetime import date,timedelta
import io
from http.client import HTTPResponse
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import threading
import unittest
from urllib.parse import urlencode
from urllib.error import HTTPError

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from run import Handler, ThreadingHTTPServer
from src.server.services.premium import initial,action,roll,next_month,basket_quote

class Quiet(Handler):
    def log_message(self,*args): pass

class Wire:
    """Pass a real HTTP request to BaseHTTPRequestHandler through byte streams."""
    def __init__(self, request):
        self.input = io.BytesIO(request)
        self.output = io.BytesIO()
    def makefile(self, *args): return self.input
    def sendall(self, data): self.output.write(data)

class Browser:
    def __init__(self): self.cookie = ""
    def open(self, path, data=None):
        method = "POST" if data is not None else "GET"
        body = data or b""
        headers = [f"{method} {path} HTTP/1.0", "Host: localhost",
                   f"Cookie: {self.cookie}", f"Content-Length: {len(body)}", "", ""]
        wire = Wire("\r\n".join(headers).encode()+body)
        Quiet(wire, ("127.0.0.1", 0), None)
        response = HTTPResponse(type("Reply", (), {"makefile": lambda _, *a: io.BytesIO(wire.output.getvalue())})())
        response.begin()
        cookie = response.getheader("Set-Cookie")
        if cookie: self.cookie = cookie.split(";")[0]
        if response.status == 303: return self.open(response.getheader("Location"))
        if response.status >= 400: raise HTTPError(path,response.status,response.reason,response.headers,None)
        return response

class Journey(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        os.environ["POSTCODE_DB"]=str(Path(tmp.name)/"test.sqlite3")
        self.addCleanup(os.environ.pop,"POSTCODE_DB")
        self.browser=Browser()
        self.base=""

    def get(self,path):
        return self.browser.open(self.base+path).read().decode("utf-8-sig")

    def fields(self,page,op,**fields):
        html=self.get(page)
        fragment=next(row for row in html.split("<form") if f'name="op" value="{op}"' in row.split("</form>")[0])
        return dict(re.findall(r'name="(csrf|id|op)" value="([^"]+)"',fragment),**fields)

    def submit(self,fields):
        return self.browser.open(self.base+"/action",urlencode(fields).encode()).read().decode()

    def test_personal(self):
        self.assertIn("Заявка",self.submit(self.fields("/","join",feedback="on")))
        for n,expected in enumerate([-2900,-900,1100,2100]):
            self.assertEqual(json.loads(self.get(f"/api/quote?quantity={n}"))["net"],expected)
        self.assertIn("отклонена",self.submit(self.fields("/account","pay",outcome="fail")))
        self.submit(self.fields("/account","pay",outcome="success"))
        same=self.fields("/account","ship",service="parcel")
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            list(pool.map(self.submit,[same,same]))
        page=self.get("/account")
        self.assertIn("30 ₽</b>",page)
        self.assertEqual(page.count("<td>Посылка</td>"),1)
        for op in ["pause","resume","cancel"]:
            self.submit(self.fields("/account",op))
        self.assertIn("Продление отключено",self.get("/account"))

    def test_business(self):
        self.submit(self.fields("/business","company",outcome="success"))
        self.submit(self.fields("/business","member",budget="15"))
        self.submit(self.fields("/business","role",role="Сотрудник 1"))
        for _ in range(3):
            page=self.submit(self.fields("/business","shipbiz",service="parcel"))
        self.assertIn("лимит исчерпан",page)
        with self.assertRaises(HTTPError) as err: self.get("/report.csv")
        self.assertEqual(err.exception.code,403)
        self.submit(self.fields("/business","role",role="accountant"))
        csv=self.get("/report.csv")
        self.assertIn("40000;1200",csv)
        self.assertIn("40000;300",csv)
        another=Browser()
        self.assertNotIn("Демо-счёт №",another.open(self.base+"/business").read().decode())

    def test_extended_journey(self):
        self.submit(self.fields("/", "join", email="alpha@example.invalid"))
        self.assertIn("alpha@example.invalid", self.get("/"))
        self.submit(self.fields("/", "withdraw"))
        self.assertNotIn("alpha@example.invalid", self.get("/"))
        self.submit(self.fields("/account","pay",outcome="success"))
        self.submit(self.fields("/account","return",reason="Хочу прекратить подписку"))
        self.assertIn("Запрос № 1",self.get("/account"))
        result=json.loads(self.get("/api/basket?parcel=2&box=5&plan=personal"))
        self.assertEqual(result["discount"],5000)
        self.assertEqual(result["net"],2100)
        self.assertIn("LTV/CAC",self.get("/economics"))
        self.assertIn("События",self.get("/analytics"))
        self.submit(self.fields("/business","company",outcome="success"))
        self.submit(self.fields("/business","member",budget="100"))
        self.assertIn("Демонстрационный счёт № 1",self.get("/invoice?id=1"))
        self.submit(self.fields("/business","remove_member",member="Сотрудник 1"))
        self.submit(self.fields("/business","member",budget="100"))
        self.assertIn("Сотрудник 2",self.get("/business"))
        self.assertNotIn("Сотрудник 1",self.get("/business"))

    def test_invalid_input_and_csrf(self):
        with self.assertRaises(HTTPError) as err:
            self.browser.open("/action",urlencode({"op":"pay","csrf":"bad","id":"a"*32}).encode())
        self.assertEqual(err.exception.code,403)
        with self.assertRaises(HTTPError):
            self.get("/api/quote?quantity=1.2")
        self.submit(self.fields("/business","company",outcome="success"))
        self.submit(self.fields("/business","member",budget="20"))
        self.submit(self.fields("/business","role",role="Сотрудник 1"))
        with self.assertRaises(HTTPError):
            self.get("/invoice?id=1")

    def test_company_permissions_and_expiry(self):
        self.submit(self.fields("/business","company",outcome="success"))
        admin_fields=self.fields("/business","member",budget="100")
        self.submit(self.fields("/business","role",role="accountant"))
        self.assertIn("администратору",self.submit(admin_fields))
        self.assertNotIn("Сотрудник 1",self.get("/business"))
        self.submit(self.fields("/business","role",role="admin"))
        self.submit(self.fields("/business","company_details",name="<script>example</script>"))
        page=self.get("/business")
        self.assertIn("&lt;script&gt;",page)
        self.assertNotIn("<script>example",page)
        from src.server.repositories import store
        sid=self.browser.cookie.split("=")[1]
        with store.transaction() as conn:
            state=store.read(conn,sid)
            state["company"]["end"]="2020-01-01"
            store.save(conn,sid,state)
        self.assertIn("Счета прошлых периодов",self.get("/business"))
        self.assertIn("Демонстрационный счёт",self.get("/invoice?id=1"))
        self.submit(self.fields("/business","company",outcome="success"))
        self.assertIn("Счёт № 2",self.get("/business").replace("Демо-счёт","Счёт"))

    def test_failed_mutation_keeps_state(self):
        self.submit(self.fields("/account","pay",outcome="success"))
        self.submit(self.fields("/account","ship",service="international"))
        self.assertIn("50 ₽</b>",self.get("/account"))
        with self.assertRaises(HTTPError):
            self.get("/api/basket?parcel=-1")
        self.assertTrue(json.loads(self.get("/api/catalog"))["demo"])

    def test_legacy_profile(self):
        from src.server.repositories import store
        self.get("/")
        sid=self.browser.cookie.split("=")[1]
        with store.transaction() as conn:
            state=store.read(conn,sid)
            state.pop("payments")
            state.pop("returns")
            state["company"]={"members":{},"invoices":[{"id":1,"start":"2026-01-01","end":"2026-02-01","amount":29900}],"role":"admin","active":False,"end":"2026-02-01","used":0}
            store.save(conn,sid,state)
        self.assertIn("DEMO-001",self.get("/invoice?id=1"))
        self.assertIn("История использования",self.get("/account"))

    def test_calendar(self):
        self.assertEqual(next_month(date(2026,1,31)),date(2026,2,28))
        self.assertEqual(next_month(date(2028,1,31)),date(2028,2,29))
        self.assertEqual(next_month(date(2026,12,31)),date(2027,1,31))

    def test_period(self):
        for op,expected in [("cancel","cancelled"),("pause","paused")]:
            state=initial()
            start=date(2026,11,24)
            action(state,"pay",{"outcome":"success"},start)
            action(state,op,{},start)
            roll(state,next_month(start))
            self.assertEqual(state["status"],expected)
            with self.assertRaises(ValueError): action(state,"ship",{"service":"parcel"},next_month(start))

if __name__=="__main__": unittest.main()
