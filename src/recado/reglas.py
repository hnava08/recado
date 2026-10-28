"""Las reglas del mostrador. Cada recado sale con la regla que lo decidió."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, timedelta
from typing import Dict, List, Optional

from recado.calendario import HOY, Calendario

DIAS = {
    "lunes": 0,
    "martes": 1,
    "miercoles": 2,
    "jueves": 3,
    "viernes": 4,
    "sabado": 5,
    "domingo": 6,
}
MESES = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}
NOMBRE_DIA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
NOMBRE_MES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
MES_LARGO = (
    "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre"
).split()

QUEJA = re.compile(r"salio mal|letras corridas|molest|reclamo|queja|atraso|reimprim|enojad")
PAGO = re.compile(r"transferi|abone|deposite|ya pague|les pague")
PEDIDO = re.compile(r"invitacion|banner|volante|polera|tarjeta|cotiz|copia|pendon|lona|remera")
CANTIDAD = re.compile(r"(\d+)\s+(invitaciones|poleras|volantes|tarjetas|copias|lonas|remeras)")
MONTO = re.compile(r"(?:transferi|abone|deposite|pague)\D{0,16}(\d+)")
DIA_SEMANA = re.compile(
    r"\b(lunes|martes|miercoles|jueves|viernes|sabado|domingo)(?:\s+(\d{1,2}))?\b"
)
DIA_DE_MES = re.compile(
    r"\b(\d{1,2}) de (enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\b"
)
DIA_SUELTO = re.compile(r"\bel\s+(\d{1,2})\b")


def llano(texto: str) -> str:
    base = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in base if unicodedata.category(c) != "Mn")


def fecha_corta(dia: date) -> str:
    return f"{NOMBRE_DIA[dia.weekday()]} {dia.day} {NOMBRE_MES[dia.month - 1]}"


def fecha_larga(dia: date) -> str:
    return f"{dia.day} de {MES_LARGO[dia.month - 1]}"


def _fecha(anio: int, mes: int, dia: int) -> Optional[date]:
    try:
        return date(anio, mes, dia)
    except ValueError:
        return None


def _por_numero(numero: int, hoy: date, semana: Optional[int] = None) -> Optional[date]:
    for salto in range(0, 370):
        candidata = hoy + timedelta(days=salto)
        if candidata.day != numero:
            continue
        if semana is not None and candidata.weekday() != semana:
            continue
        return candidata
    return None


def extraer_fechas(texto: str, hoy: date) -> List[date]:
    plano = llano(texto)
    con_mes = []
    for numero, mes in DIA_DE_MES.findall(plano):
        dia = int(numero)
        mes_n = MESES[mes]
        candidata = _fecha(hoy.year, mes_n, dia)
        if candidata is not None and candidata < hoy and (hoy - candidata).days > 45:
            candidata = _fecha(hoy.year + 1, mes_n, dia)
        if candidata is not None:
            con_mes.append(candidata)
    if con_mes:
        return _unicas(con_mes)

    por_semana = []
    for nombre, numero in DIA_SEMANA.findall(plano):
        semana = DIAS[nombre]
        if numero:
            hallada = _por_numero(int(numero), hoy, semana)
            if hallada is None:
                hallada = _por_numero(int(numero), hoy, None)
        else:
            hallada = hoy + timedelta(days=(semana - hoy.weekday()) % 7)
        if hallada is not None:
            por_semana.append(hallada)
    if por_semana:
        return _unicas(por_semana)

    if re.search(r"\bhoy\b", plano):
        return [hoy]
    if re.search(r"\bmanana\b", plano):
        return [hoy + timedelta(days=1)]

    sueltos = []
    for numero in DIA_SUELTO.findall(plano):
        hallada = _por_numero(int(numero), hoy, None)
        if hallada is not None and int(numero) <= 31:
            sueltos.append(hallada)
    return _unicas(sueltos)


def _unicas(fechas: List[date]) -> List[date]:
    vistas = []
    for dia in fechas:
        if dia not in vistas:
            vistas.append(dia)
    return vistas


def _paso(texto: str, sello: bool = False) -> dict:
    return {"texto": texto, "sello": sello}


def _cantidad(plano: str) -> Optional[str]:
    hallada = CANTIDAD.search(plano)
    if not hallada:
        return None
    return f"{hallada.group(1)} {hallada.group(2)}"


def _monto(plano: str) -> Optional[str]:
    hallada = MONTO.search(plano)
    if not hallada:
        return None
    return hallada.group(1)


def decidir(recado: dict, calendario: Calendario, hoy: date = HOY) -> dict:
    texto = recado.get("texto") or ""
    plano = llano(texto)
    queja = QUEJA.search(plano) is not None
    pedido = PEDIDO.search(plano) is not None
    pago = PAGO.search(plano) is not None
    fechas = extraer_fechas(texto, hoy)
    cantidad = _cantidad(plano)
    monto = _monto(plano)
    pasos: List[dict] = []

    base = {
        "id": recado["id"],
        "de": recado["de"],
        "hora": recado["hora"],
        "texto": texto,
        "mezcla": queja and pedido,
        "camino": [],
        "fecha_pedida": None,
        "fecha": None,
    }

    if queja and pedido:
        pasos.append(_paso("Pide un trabajo y también trae una queja."))
        pasos.append(_paso("La queja frena el recado. No sale solo.", True))
        return _cerrar(base, "persona", "A mano", False, None, pasos)

    if queja:
        pasos.append(_paso("Trae una queja."))
        pasos.append(_paso("Una queja no sale sola.", True))
        return _cerrar(base, "persona", "A mano", False, None, pasos)

    if len(fechas) > 1:
        pasos.append(_paso("Menciona más de un día."))
        pasos.append(_paso("No elijo entre dos días. Lo lee el taller.", True))
        return _cerrar(base, "persona", "A mano", False, None, pasos)

    if pago and not pedido and not fechas:
        frase = f"Anoté el pago de Bs {monto}." if monto else "Anoté el pago."
        pasos.append(_paso("Habla de un pago y no pide día."))
        pasos.append(_paso(frase, True))
        return _cerrar(base, "anotar", "Anota el pago", True, frase, pasos)

    if not pedido and not fechas and not pago:
        frase = "Falta el pedido y el día."
        pasos.append(_paso("No hay pedido, fecha ni pago."))
        pasos.append(_paso(frase, True))
        return _cerrar(base, "preguntar", "Pregunta", True, frase, pasos)

    if not fechas:
        frase = "Falta el día."
        pasos.append(_paso("Hay un pedido y no hay día."))
        pasos.append(_paso(frase, True))
        return _cerrar(base, "preguntar", "Pregunta", True, frase, pasos)

    pedida = fechas[0]
    base["fecha_pedida"] = pedida.isoformat()
    if pedida < hoy:
        frase = f"El {fecha_larga(pedida)} ya pasó. Pasame otro día."
        pasos.append(_paso(f"El día pedido es el {fecha_corta(pedida)}."))
        pasos.append(_paso(frase, True))
        return _cerrar(base, "preguntar", "Pregunta", True, frase, pasos)

    turno = calendario.abrir(pedida)
    base["camino"] = [fila["fecha"] for fila in turno["camino"]]
    if not turno["seguro"]:
        frase = "Sin los feriados no confirmo ese día."
        pasos.append(_paso(f"Pide el {fecha_corta(pedida)}."))
        if turno["motivos"]:
            pasos.append(_paso("De camino hay " + ", ".join(turno["motivos"]) + "."))
        pasos.append(_paso(frase, True))
        return _cerrar(base, "persona", "A mano", False, None, pasos)

    destino = date.fromisoformat(turno["fecha"])
    base["fecha"] = destino.isoformat()
    if destino == pedida:
        frase = f"Queda para el {fecha_corta(destino)}"
        if cantidad:
            frase = f"{frase}, {cantidad}"
        frase = f"{frase}."
        pasos.append(_paso(f"Pide el {fecha_corta(pedida)}."))
        pasos.append(_paso("Ese día el taller abre.", True))
        return _cerrar(base, "confirmar", "Confirma", True, frase, pasos)

    motivos = ", ".join(turno["motivos"])
    cerca = f"Lo más cerca es el {fecha_corta(destino)}"
    if cantidad:
        cerca = f"{cerca}, {cantidad}"
    frase = f"El {fecha_corta(pedida)} no abre ({motivos}). {cerca}."
    pasos.append(_paso(f"Pide el {fecha_corta(pedida)}."))
    pasos.append(_paso(f"No abre: {motivos}.", True))
    return _cerrar(base, "mover", "Mueve el día", True, frase, pasos)


def _cerrar(base: dict, accion: str, etiqueta: str, sale: bool, respuesta: Optional[str], pasos: List[dict]) -> dict:
    base.update(
        {
            "accion": accion,
            "etiqueta": etiqueta,
            "sale": sale,
            "respuesta": respuesta,
            "pasos": pasos,
        }
    )
    return base


def hallazgo(recados: List[dict]) -> str:
    mano = [fila for fila in recados if not fila["sale"]]
    if not mano:
        return "Todos los recados salen solos."
    mezcla = next((fila for fila in mano if fila["mezcla"]), None)
    if mezcla:
        return f"El de {mezcla['de']} mezcla un pedido con una queja."
    return f"El de {mano[0]['de']} queda para el taller."


def armar(recados: List[dict], calendario: Calendario, hoy: date = HOY) -> dict:
    decididos = [decidir(fila, calendario, hoy) for fila in recados]
    a_mano = sum(1 for fila in decididos if not fila["sale"])
    return {
        "hoy": hoy.isoformat(),
        "taller": "Taller Murillo",
        "ciudad": "Santa Cruz",
        "a_mano": a_mano,
        "salen": len(decididos) - a_mano,
        "total": len(decididos),
        "hallazgo": hallazgo(decididos),
        "calendario_ok": calendario.ok,
        "feriados": [
            {"fecha": dia.isoformat(), "nombre": nombre}
            for dia, nombre in sorted(calendario.feriados.items())
        ],
        "recados": decididos,
    }


def fechas_que_frenan(recados: List[dict]) -> Dict[str, List[str]]:
    """Qué recados chocaron con cada día cerrado."""
    choques: Dict[str, List[str]] = {}
    for fila in recados:
        for dia in fila.get("camino") or []:
            choques.setdefault(dia, []).append(fila["de"])
    return choques
