"""Observabilidade do modulo intent_classifier.

- metrics.py:   instrumentos OpenTelemetry (o que medimos em PRODUCAO)
- drift.py:     PSI e KS entre a producao (janela deslizante) e a referencia
- reference.py: perfil dos modelos nos dados de REFERENCIA, exposto como gauges
                para comparar com a producao no Grafana
"""
