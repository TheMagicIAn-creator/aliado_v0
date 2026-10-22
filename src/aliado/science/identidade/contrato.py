"""O contrato dos arquivos de uma rodada (lote 54): quem lê um arquivo que declara o contrato exige cada campo e nunca
preenche o que falta por suposição. As rodadas de antes do contrato aparecem como tais, sem campos inventados."""

from __future__ import annotations

CONTRACT = 1
PRIOR = "anterior ao contrato"
NOT_RECORDED = "não gravado"


class ContractViolationError(ValueError):
    """Um arquivo que declara o contrato está sem um campo obrigatório, com uma versão desconhecida ou com um valor
    que não confere."""


def require(record: dict, fields, where: str) -> None:
    """Levanta `ContractViolationError` com os campos que faltam em `record`."""
    missing = [field for field in fields if field not in record]
    if missing:
        raise ContractViolationError(f"{where}: faltam os campos do contrato {', '.join(missing)}.")


def check_version(record: dict, where: str) -> int | None:
    """A versão do contrato declarada em `record`: None se o registro é anterior ao contrato; erro se desconhecida."""
    if record.get("contrato") is None:
        return None
    if record["contrato"] != CONTRACT:
        raise ContractViolationError(f"{where}: versão {record['contrato']!r} do contrato desconhecida.")
    return CONTRACT
