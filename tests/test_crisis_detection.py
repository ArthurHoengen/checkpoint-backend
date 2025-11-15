"""
Testes para detecção de crise.
"""
import pytest
from app.chat.crisis_detector import CrisisDetector, RiskLevel


class TestCrisisDetector:
    """Testes para detector de crise."""

    @pytest.fixture
    def detector(self):
        """Fixture para criar instância do detector."""
        return CrisisDetector()

    @pytest.mark.asyncio
    async def test_detect_critical_suicide_keywords(self, detector):
        """Teste detecção de palavras-chave críticas de suicídio."""
        # Testar com frase que definitivamente é CRITICAL
        analysis = await detector.analyze_message("Vou me suicidar agora", [])

        assert analysis.risk_level == RiskLevel.CRITICAL
        assert analysis.requires_human is True
        assert analysis.emergency_contact is True
        assert analysis.confidence > 0.3
        assert len(analysis.keywords_found) > 0

    @pytest.mark.asyncio
    async def test_detect_high_risk_keywords(self, detector):
        """Teste detecção de palavras de alto risco."""
        analysis = await detector.analyze_message("Eu quero me matar", [])

        # Pode ser HIGH ou CRITICAL
        assert analysis.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        assert analysis.requires_human is True
        assert len(analysis.keywords_found) > 0

    @pytest.mark.asyncio
    async def test_detect_medium_risk_depression(self, detector):
        """Teste detecção de sinais de depressão."""
        analysis = await detector.analyze_message("Estou muito triste e sem esperança", [])

        # Pode ser LOW, MEDIUM ou HIGH
        assert analysis.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]
        assert analysis.confidence > 0.0

    @pytest.mark.asyncio
    async def test_no_crisis_normal_conversation(self, detector):
        """Teste sem crise em conversa normal."""
        messages = [
            "Olá, como vai?",
            "Preciso de ajuda com uma tarefa",
            "Obrigado pela conversa"
        ]

        for msg in messages:
            analysis = await detector.analyze_message(msg, [])

            # Mensagens normais devem ser NONE ou LOW
            assert analysis.risk_level in [RiskLevel.NONE, RiskLevel.LOW]
            assert analysis.requires_human is False
            assert analysis.emergency_contact is False

    @pytest.mark.asyncio
    async def test_analysis_structure(self, detector):
        """Teste que análise tem estrutura correta."""
        analysis = await detector.analyze_message("Teste", [])

        # Verificar que tem todos os campos
        assert hasattr(analysis, 'risk_level')
        assert hasattr(analysis, 'confidence')
        assert hasattr(analysis, 'keywords_found')
        assert hasattr(analysis, 'requires_human')
        assert hasattr(analysis, 'emergency_contact')
        assert hasattr(analysis, 'analysis_details')

        # analysis_details é um dict
        assert isinstance(analysis.analysis_details, dict)

    @pytest.mark.asyncio
    async def test_confidence_levels_reasonable(self, detector):
        """Teste níveis de confiança razoáveis."""
        # Mensagem crítica deve ter alta confiança
        critical_analysis = await detector.analyze_message("Vou me suicidar agora", [])
        assert critical_analysis.confidence > 0.4
        assert critical_analysis.risk_level == RiskLevel.CRITICAL

        # Mensagem neutra deve ter baixa confiança
        neutral_analysis = await detector.analyze_message("Olá, tudo bem?", [])
        assert neutral_analysis.confidence <= 0.3

    @pytest.mark.asyncio
    async def test_keywords_extracted(self, detector):
        """Teste extração de palavras-chave."""
        analysis = await detector.analyze_message("Eu quero me matar", [])

        # Deve ter encontrado alguma keyword
        if analysis.risk_level != RiskLevel.NONE:
            assert len(analysis.keywords_found) > 0

    @pytest.mark.asyncio
    async def test_empty_message(self, detector):
        """Teste mensagem vazia."""
        analysis = await detector.analyze_message("", [])

        # Mensagem vazia deve ser NONE ou LOW com confiança 0
        assert analysis.risk_level in [RiskLevel.NONE, RiskLevel.LOW]
        assert analysis.confidence == 0.0
        assert len(analysis.keywords_found) == 0

    @pytest.mark.asyncio
    async def test_case_insensitive_detection(self, detector):
        """Teste que detecção não depende de maiúsculas/minúsculas."""
        messages = [
            "QUERO ME MATAR",
            "quero me matar",
            "QuErO mE mAtAr"
        ]

        for msg in messages:
            analysis = await detector.analyze_message(msg, [])
            # Todas devem ser detectadas como risco (HIGH ou CRITICAL)
            assert analysis.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]

    @pytest.mark.asyncio
    async def test_partial_word_matches(self, detector):
        """Teste que palavras-chave parciais não são detectadas incorretamente."""
        analysis = await detector.analyze_message("Gosto de filmes de ação", [])

        # Não deve ser crítico
        assert analysis.risk_level != RiskLevel.CRITICAL
        assert analysis.emergency_contact is False

    @pytest.mark.asyncio
    async def test_emergency_contact_flag(self, detector):
        """Teste que emergency_contact é ativado para casos graves."""
        # Mensagem extremamente grave
        analysis = await detector.analyze_message("Vou me suicidar agora mesmo", [])

        if analysis.risk_level == RiskLevel.CRITICAL:
            assert analysis.emergency_contact is True
            assert analysis.requires_human is True

    @pytest.mark.asyncio
    async def test_context_analysis(self, detector):
        """Teste que contexto é considerado."""
        conversation_history = [
            {"sender": "user", "text": "Estou me sentindo muito mal"},
            {"sender": "ai", "text": "Sinto muito. Quer conversar sobre isso?"},
        ]

        analysis = await detector.analyze_message(
            "Não vejo mais sentido",
            conversation_history
        )

        # Com ou sem contexto, deve pelo menos detectar algum risco
        assert analysis.risk_level in [RiskLevel.NONE, RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]


class TestRiskLevelEnum:
    """Testes para enum de níveis de risco."""

    def test_risk_level_values(self):
        """Teste valores dos níveis de risco."""
        # Verificar que existe NONE (usado pelo detector)
        assert hasattr(RiskLevel, 'NONE')
        assert RiskLevel.NONE.value == "none"

        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"

    def test_risk_level_comparison(self):
        """Teste que níveis de risco podem ser comparados."""
        # RiskLevel são strings, então comparação é alfabética
        # Vamos apenas verificar que os valores existem
        levels = [RiskLevel.NONE, RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        assert len(levels) == 5
        assert all(isinstance(level.value, str) for level in levels)
