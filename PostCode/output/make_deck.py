import zipfile
from xml.sax.saxutils import escape
from pathlib import Path
out=Path(__file__).with_name('pochtatech_subscription.pptx')
slides=[
('2942BB',[
(.7,.5,12,.5,17,'FFFFFF','Почта Премиум · концепция PostCode'),
(.7,1.5,11,1.6,38,'FFFFFF','Подписка для регулярных отправок'),
(.7,3.1,7,1.2,23,'FFFFFF','В приложении Почты России клиент подключает пакет и сразу видит свою экономию.'),
(9,3,3.7,1,49,'FFFFFF','299 ₽/мес.'),
(.7,5.1,3.7,1.3,24,'FFFFFF','1 забор курьером\nс доступного адреса'),
(4.9,5.1,3.6,1.3,24,'FFFFFF','2 скидки по 60 ₽\nна онлайн-отправки'),
(9,5.1,3.6,1.3,24,'FFFFFF','171 ₽ экономии\nпри использовании пакета'),
(.7,6.95,12,.3,12,'FFFFFF','Гипотеза команды. Экономия при цене забора 350 ₽ и покупке всех услуг отдельно.')]),
('F4F6FC',[
(.7,.6,12,1,32,'172142','Понятная выгода помогает продлевать подписку'),
(.7,1.9,3.5,.6,25,'2942BB','Клиент понимает цену'),
(.7,2.65,3.5,2.4,22,'172142','Калькулятор сравнивает пакет с обычной онлайн-ценой с учётом действующих скидок.\nДо оплаты видна доступность курьера.'),
(4.9,1.9,3.5,.6,25,'2942BB','Бизнес задаёт лимиты'),
(4.9,2.65,3.5,2.4,22,'172142','Один забор и две скидки ограничивают расходы на льготы.\nИстория операций показывает использование пакета.'),
(9.1,1.9,3.5,.6,25,'2942BB','Почтатех развивает сервис'),
(9.1,2.65,3.5,2.4,22,'172142','Оформление, применение льготы и продление работают в одном сценарии.\nПилот проверяет рост повторных отправок.'),
(.7,5.65,12,.9,24,'172142','В демо показываем подключение, отправку, применение скидки и возврат льготы после отмены забора.'),
(.7,6.9,12,.4,12,'65708D','Эффекты удержания и снижения обращений требуют проверки. Почтатех создаёт ИТ-сервисы Почты России.')]),
('FFFFFF',[
(.7,.6,12,1,33,'172142','Как зарабатывает оператор Почты России'),
(.7,1.65,7,.5,19,'65708D','Один подписчик за месяц при полном использовании'),
(.7,2.4,7,2.8,24,'172142','299 ₽   выручка от подписки\n−140 ₽   себестоимость курьерского забора\n−120 ₽   две скидки по 60 ₽\n−20 ₽   прочие переменные затраты'),
(9,2.4,3.6,.9,54,'2942BB','19 ₽'),
(9,3.5,3.6,1.5,21,'172142','вклад в покрытие постоянных расходов на подписчика в месяц'),
(.7,5.3,7.2,1.1,23,'172142','Порог стоимости забора — 159 ₽.\nПри заборе за 200 ₽ вклад составит −41 ₽.'),
(9,5.3,3.6,1.1,21,'2942BB','10 000 подписчиков\n190 000 ₽ вклада в месяц'),
(.7,6.65,12,.65,12,'65708D','Все затраты условны. Расчёт до налогов, привлечения и постоянных расходов. В пилоте учитываем потерю маржи обычных продаж. Доход Почтатеха зависит от внутренних договоров.')])]
ns='http://schemas.openxmlformats.org/'
def tx(i,a):
 x,y,w,h,size,c,t=a
 ps=''.join('<a:p><a:r><a:rPr lang="ru-RU" sz="%d"><a:solidFill><a:srgbClr val="%s"/></a:solidFill><a:latin typeface="Arial"/></a:rPr><a:t>%s</a:t></a:r></a:p>'%(size*100,c,escape(line)) for line in t.split('\n'))
 return f'<p:sp><p:nvSpPr><p:cNvPr id="{i}" name="Text {i}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="{int(x*914400)}" y="{int(y*914400)}"/><a:ext cx="{int(w*914400)}" cy="{int(h*914400)}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr><p:txBody><a:bodyPr wrap="square"/><a:lstStyle/>{ps}</p:txBody></p:sp>'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
 z.writestr('[Content_Types].xml','<Types xmlns="'+ns+'package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'+''.join(f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>' for i in range(1,4))+'</Types>')
 z.writestr('_rels/.rels','<Relationships xmlns="'+ns+'package/2006/relationships"><Relationship Id="rId1" Type="'+ns+'officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/></Relationships>')
 z.writestr('ppt/presentation.xml','<p:presentation xmlns:p="'+ns+'presentationml/2006/main" xmlns:r="'+ns+'officeDocument/2006/relationships"><p:sldIdLst>'+''.join(f'<p:sldId id="{256+i}" r:id="rId{i}"/>' for i in range(1,4))+'</p:sldIdLst><p:sldSz cx="12192000" cy="6858000"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>')
 z.writestr('ppt/_rels/presentation.xml.rels','<Relationships xmlns="'+ns+'package/2006/relationships">'+''.join(f'<Relationship Id="rId{i}" Type="{ns}officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>' for i in range(1,4))+'</Relationships>')
 for i,(bg,els) in enumerate(slides,1):
  z.writestr(f'ppt/slides/slide{i}.xml',f'<p:sld xmlns:p="{ns}presentationml/2006/main" xmlns:a="{ns}drawingml/2006/main"><p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="{bg}"/></a:solidFill><a:effectLst/></p:bgPr></p:bg><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>'+''.join(tx(j,a) for j,a in enumerate(els,2))+'</p:spTree></p:cSld></p:sld>')
import xml.etree.ElementTree as ET
with zipfile.ZipFile(out) as z:
 for name in z.namelist(): ET.fromstring(z.read(name))
print(out)
