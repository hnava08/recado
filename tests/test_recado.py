from datetime import date

from recado.bandeja import MUESTRAS
from recado.calendario import HOY, Calendario, leer_feriados
from recado.reglas import armar, decidir, extraer_fechas

FERIADOS = {
    date(2026, 5, 1): "Dia del trabajo",
    date(2026, 11, 2): "Todos Santos",
    date(2026, 12, 25): "Navidad",
    date(2027, 5, 1): "Dia del trabajo",
}


def calendario():
    return Calendario(FERIADOS, True)


def uno(texto, de="Cliente"):
    return decidir({"id": "R-001", "de": de, "hora": "10:00", "texto": texto}, calendario())


def test_la_queja_frena_aunque_pida_trabajo():
    recado = uno("Cotización de 40 poleras y también estoy molesto con el atraso.", "Pablo Rojas")
    assert recado["accion"] == "persona"
    assert recado["sale"] is False
    assert recado["mezcla"] is True
    assert recado["respuesta"] is None
    assert recado["pasos"][-1]["sello"] is True
    assert sum(1 for paso in recado["pasos"] if paso["sello"]) == 1


def test_una_queja_sola_tambien_queda_a_mano():
    recado = uno("El trabajo salió mal, las letras están corridas. Quiero que lo reimpriman hoy.")
    assert recado["accion"] == "persona"
    assert recado["mezcla"] is False


def test_el_viernes_que_abre_se_confirma():
    recado = uno("Necesito 200 invitaciones para el viernes.", "Ana Prado")
    assert recado["accion"] == "confirmar"
    assert recado["fecha"] == "2026-10-30"
    assert recado["sale"] is True
    assert "200 invitaciones" in recado["respuesta"]
    assert "viernes 30 oct" in recado["respuesta"]


def test_el_sabado_cruza_el_feriado():
    recado = uno("Quiero el banner para el sábado.")
    assert recado["accion"] == "mover"
    assert recado["fecha_pedida"] == "2026-10-31"
    assert recado["fecha"] == "2026-11-03"
    assert recado["camino"] == ["2026-10-31", "2026-11-01", "2026-11-02"]
    assert "Todos Santos" in recado["respuesta"]


def test_navidad_cae_en_el_lunes_siguiente():
    recado = uno("Necesito 80 tarjetas para el 25 de diciembre.")
    assert recado["fecha_pedida"] == "2026-12-25"
    assert recado["fecha"] == "2026-12-28"
    assert "Navidad" in recado["respuesta"]
    assert "80 tarjetas" in recado["respuesta"]


def test_el_domingo_no_cuenta_el_sabado():
    recado = uno("Pueden mover la entrega al domingo?")
    assert recado["fecha_pedida"] == "2026-11-01"
    assert recado["fecha"] == "2026-11-03"
    assert "2026-10-31" not in recado["camino"]
    assert "2026-11-02" in recado["camino"]


def test_un_pago_sin_dia_se_anota():
    recado = uno("Ya transferí 350 por el trabajo de la semana pasada.")
    assert recado["accion"] == "anotar"
    assert recado["sale"] is True
    assert "Bs 350" in recado["respuesta"]


def test_un_saludo_pide_el_pedido():
    recado = uno("Hola buenos días")
    assert recado["accion"] == "preguntar"
    assert "Falta el pedido" in recado["respuesta"]


def test_el_dia_suelto_cae_en_todos_santos():
    recado = uno("Para el 2 necesitamos 500 volantes.")
    assert recado["fecha_pedida"] == "2026-11-02"
    assert recado["fecha"] == "2026-11-03"


def test_un_dia_reciente_que_ya_paso_no_se_confirma():
    recado = uno("Lo quiero para el 1 de octubre.")
    assert recado["accion"] == "preguntar"
    assert recado["fecha_pedida"] == "2026-10-01"
    assert "ya pasó" in recado["respuesta"]


def test_mayo_dicho_en_octubre_es_el_ano_que_viene():
    assert extraer_fechas("para el 1 de mayo", HOY) == [date(2027, 5, 1)]


def test_dos_dias_no_se_eligen_solos():
    recado = uno("Puede ser el viernes o el domingo.")
    assert recado["accion"] == "persona"
    assert "dos días" in recado["pasos"][-1]["texto"]


def test_sin_feriados_no_confirma_un_dia_de_semana():
    ciego = Calendario(None, False)
    recado = decidir(
        {"id": "R-002", "de": "Ana", "hora": "10:00", "texto": "200 invitaciones para el viernes."},
        ciego,
    )
    assert recado["accion"] == "persona"
    assert recado["sale"] is False


def test_sin_feriados_un_finde_tampoco_inventa_el_lunes():
    ciego = Calendario(None, False)
    recado = decidir(
        {"id": "R-003", "de": "Feria", "hora": "10:00", "texto": "El banner para el sábado."},
        ciego,
    )
    assert recado["accion"] == "persona"
    assert recado["fecha"] is None


def test_la_tanda_cuadra_y_el_hallazgo_nombra_la_mezcla():
    parte = armar(MUESTRAS, calendario())
    assert parte["total"] == 8
    assert parte["a_mano"] + parte["salen"] == parte["total"]
    assert parte["a_mano"] == 2
    assert parte["hallazgo"] == "El de Pablo Rojas mezcla un pedido con una queja."
    assert [fila["accion"] for fila in parte["recados"]] == [
        "persona",
        "persona",
        "confirmar",
        "mover",
        "mover",
        "mover",
        "anotar",
        "preguntar",
    ]


def test_lee_el_json_de_feriados():
    def traer(url):
        assert url.endswith("/2026/BO")
        return '[{"date":"2026-11-02","localName":"Todos Santos"}]'

    feriados = leer_feriados([2026], traer)
    assert feriados[date(2026, 11, 2)] == "Todos Santos"
