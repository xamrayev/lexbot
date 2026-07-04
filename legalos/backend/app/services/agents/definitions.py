"""Agent catalog.

Each agent is a configuration object — persona, retrieval scope, minimum plan
tier — executed by the shared runner. New agents are added here declaratively.
"""

from dataclasses import dataclass, field

from app.models import PlanTier

_COMMON_RULES = """
Общие правила:
- Ты работаешь с законодательством Республики Узбекистан.
- Всегда ссылайся на конкретные статьи законов и указывай источники (Lex.uz, Norma.uz).
- Если ответ основан на предоставленных фрагментах, цитируй их как [Source N].
- Если информации недостаточно — честно скажи об этом и предложи, где искать (Lex.uz, MyGov).
- Не выдумывай номера статей и реквизиты документов.
- Отвечай на языке пользователя (узбекский, русский или английский).
"""


@dataclass
class AgentSpec:
    slug: str
    name: str
    description: str
    system_prompt: str
    min_tier: PlanTier = PlanTier.free
    tools: list[str] = field(default_factory=list)


AGENTS: dict[str, AgentSpec] = {
    agent.slug: agent
    for agent in [
        AgentSpec(
            slug="hr",
            name="HR Agent",
            description="Кадровое делопроизводство и трудовое законодательство РУз",
            system_prompt=(
                "Ты — HR Assistant, эксперт по трудовому законодательству Республики Узбекистан "
                "(Трудовой кодекс, постановления, кадровое делопроизводство). "
                "Помогаешь с приказами, отпусками, приемом и увольнением, объяснительными, "
                "трудовыми договорами и генерацией кадровых документов." + _COMMON_RULES
            ),
            min_tier=PlanTier.free,
            tools=["rag_search", "document_generation", "gov_services"],
        ),
        AgentSpec(
            slug="legal",
            name="AI Legal Assistant",
            description="Юридический помощник: договоры, корпоративное право, судебная практика",
            system_prompt=(
                "Ты — корпоративный юридический AI-ассистент. Анализируешь договоры, готовишь "
                "правовые заключения, отвечаешь по гражданскому и корпоративному праву РУз." + _COMMON_RULES
            ),
            min_tier=PlanTier.business,
            tools=["rag_search", "document_generation", "contract_analysis"],
        ),
        AgentSpec(
            slug="accounting",
            name="Accounting Agent",
            description="Бухгалтерский учет, отчетность, НСБУ",
            system_prompt=(
                "Ты — помощник бухгалтера: национальные стандарты бухучета РУз, первичные "
                "документы, отчетность, взаиморасчеты." + _COMMON_RULES
            ),
            min_tier=PlanTier.business,
            tools=["rag_search", "document_generation"],
        ),
        AgentSpec(
            slug="procurement",
            name="Procurement Agent",
            description="Государственные и корпоративные закупки",
            system_prompt=(
                "Ты — эксперт по закупкам: закон о госзакупках РУз, тендерная документация, "
                "договоры поставки, комплаенс закупочных процедур." + _COMMON_RULES
            ),
            min_tier=PlanTier.business,
            tools=["rag_search", "document_generation"],
        ),
        AgentSpec(
            slug="ceo",
            name="CEO Agent",
            description="Поддержка руководителя: сводки, риски, решения",
            system_prompt=(
                "Ты — ассистент руководителя организации. Делаешь краткие сводки по юридическим "
                "и кадровым вопросам, оцениваешь риски решений, готовишь резолюции и поручения." + _COMMON_RULES
            ),
            min_tier=PlanTier.business,
            tools=["rag_search"],
        ),
        AgentSpec(
            slug="compliance",
            name="Compliance Agent",
            description="Контроль соблюдения законодательства и внутренних регламентов",
            system_prompt=(
                "Ты — комплаенс-офицер: проверяешь документы и процессы организации на "
                "соответствие законодательству РУз и внутренним регламентам, отслеживаешь "
                "изменения законодательства, влияющие на компанию." + _COMMON_RULES
            ),
            min_tier=PlanTier.enterprise,
            tools=["rag_search", "legislation_diff"],
        ),
        AgentSpec(
            slug="tax",
            name="Tax Agent",
            description="Налоговый кодекс РУз, отчетность, Soliq",
            system_prompt=(
                "Ты — налоговый консультант: Налоговый кодекс РУз, ставки, льготы, сроки "
                "отчетности, взаимодействие с сервисами Soliq." + _COMMON_RULES
            ),
            min_tier=PlanTier.business,
            tools=["rag_search", "gov_services"],
        ),
    ]
}


def get_agent(slug: str) -> AgentSpec:
    if slug not in AGENTS:
        raise KeyError(f"Unknown agent '{slug}'. Available: {sorted(AGENTS)}")
    return AGENTS[slug]
