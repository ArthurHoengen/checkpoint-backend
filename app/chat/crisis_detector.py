"""
Sistema de detecção de crise para apoio emocional.
Combina análise de palavras-chave, padrões e IA para detectar risco suicida.
"""
import re
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from app.core.ollama_client import OllamaClient


class RiskLevel(Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CrisisAnalysis:
    risk_level: RiskLevel
    confidence: float  # 0.0 - 1.0
    keywords_found: List[str]
    requires_human: bool
    emergency_contact: bool  # Para casos críticos
    analysis_details: Dict[str, any]


class CrisisDetector:
    """Detector de crise com múltiplas estratégias de análise."""

    def __init__(self):
        self.ollama_client = OllamaClient()

        # Palavras-chave categorizadas por nível de risco
        self.keywords = {
            RiskLevel.CRITICAL: [
                "vou me matar", "vou me suicidar", "quero morrer agora",
                "tenho uma arma", "vou pular", "vou tomar remédios",
                "hoje é o último dia", "me despedindo", "acabou para mim"
            ],
            RiskLevel.HIGH: [
                "suicídio", "me matar", "acabar com tudo", "não aguento mais",
                "quero morrer", "melhor morto", "sem saída", "sem esperança",
                "mundo seria melhor sem mim", "cansei de viver", "vai me matar",
                "ameaça de morte", "ameaçado de morte"
            ],
            RiskLevel.MEDIUM: [
                "deprimido", "vazio", "sozinho", "triste demais",
                "sem sentido", "não vale a pena", "desisto", "acabou",
                "ninguém me ama", "sou um fardo"
            ],
            RiskLevel.LOW: [
                "triste", "down", "mal", "chateado", "preocupado",
                "ansioso", "estressado", "cansado"
            ]
        }

        # Padrões regex para detecção avançada
        self.critical_patterns = [
            r"(?i)vou.*(?:me matar|suicidar|morrer)",
            r"(?i)(?:tenho|vou usar).*(?:arma|faca|remédio|veneno)",
            r"(?i)(?:hoje|agora|logo).*(?:morrer|acabar|suicídio)",
            r"(?i)(?:escrevendo|deixando).*(?:carta|bilhete).*(?:despedida|adeus)",
            r"(?i)(?:ele|ela|eles).*(?:vai|vão).*me matar",
            r"(?i)ameaça.*(?:morte|matar)"
        ]

    async def analyze_message(self, message_text: str, session_context: Optional[List[str]] = None) -> CrisisAnalysis:
        """
        Analisa uma mensagem para detectar sinais de crise.

        Args:
            message_text: Texto da mensagem do usuário
            session_context: Mensagens anteriores da sessão para contexto

        Returns:
            CrisisAnalysis com o resultado da análise
        """
        # 1. Análise de palavras-chave
        keyword_analysis = self._analyze_keywords(message_text)

        # 2. Análise de padrões regex
        pattern_analysis = self._analyze_patterns(message_text)

        # 3. Análise com IA (Ollama)
        ai_analysis = await self._analyze_with_ai(message_text, session_context)

        # 4. Combinar resultados
        final_analysis = self._combine_analyses(
            keyword_analysis, pattern_analysis, ai_analysis, message_text
        )

        return final_analysis

    def _analyze_keywords(self, text: str) -> Dict[str, any]:
        """Analisa palavras-chave na mensagem."""
        text_lower = text.lower()
        found_keywords = []
        max_risk_level = RiskLevel.NONE

        for risk_level, keywords in self.keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    found_keywords.append(keyword)
                    # Comparar por índice na ordem: NONE < LOW < MEDIUM < HIGH < CRITICAL
                    if list(RiskLevel).index(risk_level) > list(RiskLevel).index(max_risk_level):
                        max_risk_level = risk_level

        return {
            "risk_level": max_risk_level,
            "keywords_found": found_keywords,
            "confidence": min(len(found_keywords) * 0.3, 1.0)
        }

    def _analyze_patterns(self, text: str) -> Dict[str, any]:
        """Analisa padrões regex críticos."""
        critical_patterns_found = []

        for pattern in self.critical_patterns:
            if re.search(pattern, text):
                critical_patterns_found.append(pattern)

        if critical_patterns_found:
            return {
                "risk_level": RiskLevel.CRITICAL,
                "patterns_found": critical_patterns_found,
                "confidence": 0.9
            }

        return {
            "risk_level": RiskLevel.NONE,
            "patterns_found": [],
            "confidence": 0.0
        }

    async def _analyze_with_ai(self, message_text: str, context: Optional[List[str]] = None) -> Dict[str, any]:
        """Usa IA (Ollama) para análise mais sofisticada."""
        try:
            prompt = f"""Você é um profissional de saúde mental treinado para avaliar mensagens de chat em português.

Sua tarefa: Classificar o nível de risco emocional desta mensagem.

Texto: "{message_text}"

Instruções:
- Analise o conteúdo emocional e psicológico
- Identifique sinais de angústia, tristeza ou crise
- Responda APENAS no formato: NIVEL:NUMERO
- Não adicione explicações ou comentários

Níveis disponíveis:
NONE:0.1
LOW:0.3
MEDIUM:0.6
HIGH:0.8
CRITICAL:0.9

EXEMPLO DE RESPOSTA: 'LOW:0.3'

Sua análise:"""

            response = self.ollama_client.ask(prompt, "llama3.2:3b")

            # Limpar resposta e tentar parsing
            clean_response = response.strip().upper()

            # Parse da resposta no formato LEVEL:CONFIDENCE
            if ":" in clean_response:
                parts = clean_response.split(":")
                if len(parts) >= 2:
                    level_str = parts[0].strip()
                    confidence_str = parts[1].strip()
                    try:
                        risk_level = RiskLevel(level_str.lower())
                        confidence = float(confidence_str)
                        confidence = max(0.0, min(1.0, confidence))  # Limitar entre 0-1
                    except (ValueError, KeyError):
                        # Se não conseguir parsear, usar fallback
                        risk_level = RiskLevel.NONE
                        confidence = 0.3
                else:
                    risk_level = RiskLevel.NONE
                    confidence = 0.3
            else:
                # Fallback se formato não esperado - analisar conteúdo da mensagem original
                # Se a IA falhou, fazer análise simples baseada em palavras críticas
                message_lower = message_text.lower()

                # Análise de fallback baseada no conteúdo da mensagem
                if any(word in message_lower for word in ["matar", "suicid", "morrer", "ameaça"]):
                    if any(word in message_lower for word in ["vou me", "vai me", "ameaça"]):
                        risk_level = RiskLevel.HIGH
                        confidence = 0.7
                    else:
                        risk_level = RiskLevel.MEDIUM
                        confidence = 0.5
                elif any(word in message_lower for word in ["triste", "deprim", "sozinho", "mal"]):
                    risk_level = RiskLevel.LOW
                    confidence = 0.4
                else:
                    risk_level = RiskLevel.NONE
                    confidence = 0.1

            return {
                "risk_level": risk_level,
                "ai_response": response,
                "confidence": confidence
            }

        except Exception as e:
            # Fallback em caso de erro na IA
            return {
                "risk_level": RiskLevel.NONE,
                "ai_response": f"Erro: {str(e)}",
                "confidence": 0.0
            }

    def _combine_analyses(self, keyword_analysis: Dict, pattern_analysis: Dict,
                         ai_analysis: Dict, original_text: str) -> CrisisAnalysis:
        """Combina os resultados das diferentes análises."""

        # Pegar o maior nível de risco
        analyses = [keyword_analysis, pattern_analysis, ai_analysis]
        max_risk_level = max(
            (analysis["risk_level"] for analysis in analyses),
            key=lambda x: list(RiskLevel).index(x)
        )

        # Calcular confiança combinada
        confidences = [analysis["confidence"] for analysis in analyses]
        combined_confidence = sum(confidences) / len(confidences)

        # Boost de confiança se múltiplas análises concordam
        if sum(1 for analysis in analyses if analysis["risk_level"] == max_risk_level) >= 2:
            combined_confidence = min(combined_confidence * 1.3, 1.0)

        # Determinar se requer intervenção humana
        requires_human = max_risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        emergency_contact = max_risk_level == RiskLevel.CRITICAL

        return CrisisAnalysis(
            risk_level=max_risk_level,
            confidence=combined_confidence,
            keywords_found=keyword_analysis.get("keywords_found", []),
            requires_human=requires_human,
            emergency_contact=emergency_contact,
            analysis_details={
                "keyword_analysis": keyword_analysis,
                "pattern_analysis": pattern_analysis,
                "ai_analysis": ai_analysis,
                "message_length": len(original_text),
                "timestamp": asyncio.get_event_loop().time()
            }
        )


# Instância global para uso nos serviços
crisis_detector = CrisisDetector()