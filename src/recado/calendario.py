"""Días que el taller abre, con los feriados públicos de Bolivia."""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Callable, Dict, List, Optional
from urllib.request import urlopen

HOY = date(2026, 10, 28)
FUENTE = "https://date.nager.at/api/v3/PublicHolidays/{anio}/BO"


def traer_url(url: str) -> str:
    with urlopen(url, timeout=8) as respuesta:
        return respuesta.read().decode("utf-8")


def leer_feriados(anios: List[int], traer: Callable[[str], str]) -> Dict[date, str]:
    salida: Dict[date, str] = {}
    for anio in anios:
        datos = json.loads(traer(FUENTE.format(anio=anio)))
        for fila in datos:
            salida[date.fromisoformat(fila["date"])] = fila["localName"]
    return salida


class Calendario:
    def __init__(self, feriados: Optional[Dict[date, str]], ok: bool) -> None:
        self.feriados = feriados or {}
        self.ok = ok

    def motivo(self, dia: date) -> Optional[str]:
        if dia.weekday() == 5:
            return "sábado"
        if dia.weekday() == 6:
            return "domingo"
        if not self.ok:
            return None
        return self.feriados.get(dia)

    def abrir(self, pedido: date) -> dict:
        """El primer día que el taller abre, y los días cerrados que hubo que saltar."""
        camino: List[dict] = []
        if not self.ok and pedido.weekday() < 5:
            return {
                "fecha": pedido.isoformat(),
                "abre": False,
                "seguro": False,
                "camino": [],
                "motivos": [],
            }
        dia = pedido
        for _ in range(21):
            motivo = self.motivo(dia)
            if motivo is None and not self.ok and dia.weekday() < 5:
                return {
                    "fecha": None,
                    "abre": False,
                    "seguro": False,
                    "camino": camino,
                    "motivos": [fila["motivo"] for fila in camino],
                }
            if motivo is None:
                return {
                    "fecha": dia.isoformat(),
                    "abre": dia == pedido,
                    "seguro": True,
                    "camino": camino,
                    "motivos": [fila["motivo"] for fila in camino],
                }
            camino.append({"fecha": dia.isoformat(), "motivo": motivo})
            dia += timedelta(days=1)
        return {
            "fecha": None,
            "abre": False,
            "seguro": False,
            "camino": camino,
            "motivos": [fila["motivo"] for fila in camino],
        }


def cargar(traer: Callable[[str], str] = traer_url) -> Calendario:
    try:
        feriados = leer_feriados([HOY.year, HOY.year + 1], traer)
    except (OSError, ValueError, KeyError, TypeError):
        return Calendario(None, False)
    return Calendario(feriados, True)
