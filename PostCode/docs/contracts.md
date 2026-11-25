# Контракты рабочей версии

Суммы передаются целыми копейками. Тарифы personal и business имеют версию 2026-11-24. Каталог доступен через GET /api/catalog, проверка готовности через GET /health.

GET /api/quote принимает plan, service, quantity. GET /api/basket принимает plan и количества parcel, letter, box, international. Ответ содержит total, discount, net, fee и rows (для корзины). Количества — целые 0–1000. Неверный ввод получает HTTP 400.

POST /action принимает HTML form-urlencoded с csrf, id и op. После операции следует HTTP 303 и сообщение на целевой странице. Один id применяется один раз. Транзакция SQLite и копия состояния гарантируют атомарность изменений.

| Область | op |
| --- | --- |
| Заявка | join, withdraw |
| Подписка | pay, pause, cancel, resume, return |
| Бонус | ship, shipbiz |
| Компания | company, role, member, budget, remove_member, company_details |

GET /report.csv и GET /invoice?id=N доступны ролям admin/accountant текущей демо-компании. Смена роли предназначена для демонстрации сценариев в одном профиле. Для реальной многопользовательской эксплуатации потребуется отдельная система идентификации.

Состояния подписки inactive, active, pausing, cancelling, paused, cancelled, expired. Пауза и отмена переходят в конечное состояние на границе календарного месяца. Новый период оплачивается явно. Старые профили мигрируют при чтении, история сохраняется.

Данные карты не вводятся, контакты в события аналитики не попадают.
