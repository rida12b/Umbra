"""Gateways: the only modules allowed to start external programs (ADR-0004).

A gateway never reads Project files itself, and every output it returns has gone through
`umbra_engine.guard.redact_output` first.
"""
