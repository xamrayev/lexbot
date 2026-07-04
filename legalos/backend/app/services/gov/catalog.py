"""Government services directory (MyGov, Soliq, and other official portals).

Deterministic keyword matching so results are reproducible and testable; the
frontend shows matched services as deep links next to agent answers
("Как зарегистрировать ООО?" → официальный сервис регистрации бизнеса).
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GovService:
    slug: str
    title_ru: str
    title_uz: str
    url: str
    agency: str
    keywords: frozenset[str] = field(default_factory=frozenset)


def _kw(*words: str) -> frozenset[str]:
    return frozenset(w.lower() for w in words)


GOV_SERVICES: list[GovService] = [
    GovService(
        slug="business-registration",
        title_ru="Государственная регистрация бизнеса (ООО, ИП)",
        title_uz="Tadbirkorlik subyektlarini davlat ro'yxatidan o'tkazish",
        url="https://fo.birdarcha.uz",
        agency="Минюст / Госуслуги",
        keywords=_kw("ооо", "регистрация", "бизнес", "ип", "фирма", "компания", "mchj", "yatt", "biznes", "royxat"),
    ),
    GovService(
        slug="mygov-portal",
        title_ru="Единый портал государственных услуг",
        title_uz="Yagona interaktiv davlat xizmatlari portali",
        url="https://my.gov.uz",
        agency="MyGov",
        keywords=_kw("госуслуги", "портал", "услуга", "справка", "davlat", "xizmat", "portal", "mygov"),
    ),
    GovService(
        slug="tax-cabinet",
        title_ru="Персональный кабинет налогоплательщика",
        title_uz="Soliq to'lovchining shaxsiy kabineti",
        url="https://my.soliq.uz",
        agency="Налоговый комитет",
        keywords=_kw("налог", "ндс", "инн", "отчетность", "декларация", "soliq", "qqs", "stir", "hisobot"),
    ),
    GovService(
        slug="digital-signature",
        title_ru="Получение электронной цифровой подписи (ЭЦП)",
        title_uz="Elektron raqamli imzo olish",
        url="https://e-imzo.uz",
        agency="НИЦ цифровой подписи",
        keywords=_kw("эцп", "подпись", "электронная", "imzo", "kalit", "e-imzo"),
    ),
    GovService(
        slug="employment",
        title_ru="Электронная трудовая книжка и учет договоров",
        title_uz="Elektron mehnat daftarchasi va shartnomalar hisobi",
        url="https://mehnat.uz",
        agency="Минтруда",
        keywords=_kw("трудовая", "книжка", "договор", "кадры", "работник", "mehnat", "daftarcha", "xodim", "shartnoma"),
    ),
    GovService(
        slug="pension",
        title_ru="Пенсионный фонд: взносы и выписки",
        title_uz="Pensiya jamg'armasi: badallar va ma'lumotnomalar",
        url="https://pfru.uz",
        agency="Пенсионный фонд",
        keywords=_kw("пенсия", "взнос", "стаж", "pensiya", "badal", "staj"),
    ),
    GovService(
        slug="licensing",
        title_ru="Лицензии и разрешительные документы",
        title_uz="Litsenziya va ruxsatnomalar",
        url="https://license.gov.uz",
        agency="Госуслуги",
        keywords=_kw("лицензия", "разрешение", "litsenziya", "ruxsatnoma"),
    ),
    GovService(
        slug="lex-uz",
        title_ru="Национальная база законодательства",
        title_uz="Qonunchilik milliy bazasi",
        url="https://lex.uz",
        agency="Минюст",
        keywords=_kw("закон", "кодекс", "постановление", "статья", "qonun", "kodeks", "modda", "qaror"),
    ),
    GovService(
        slug="social-insurance",
        title_ru="Единый портал социальной защиты",
        title_uz="Ijtimoiy himoya yagona portali",
        url="https://ish.gov.uz",
        agency="Минтруда",
        keywords=_kw("пособие", "безработица", "субсидия", "nafaqa", "ishsizlik", "subsidiya", "вакансия", "ish"),
    ),
]


def find_services(query: str, limit: int = 3) -> list[GovService]:
    """Rank services by keyword overlap with the query. Empty list = no match."""
    tokens = {t.strip(".,!?;:()«»\"'").lower() for t in query.split()}
    tokens.discard("")
    scored = []
    for service in GOV_SERVICES:
        score = len(tokens & service.keywords)
        if score > 0:
            scored.append((score, service))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [service for _, service in scored[:limit]]
