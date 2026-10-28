# Recado

Bot de mostrador para Taller Murillo, en Santa Cruz. Lee el recado de un cliente y decide si confirma el día, lo mueve al siguiente día que el taller abre, anota un pago, pide lo que falta, o lo deja para una persona.

El taller no abre sábado ni domingo. Los feriados salen de [Nager.Date](https://date.nager.at) para Bolivia. Si esa lista no responde, el bot no inventa un lunes: el recado queda a mano.

Una queja frena todo, aunque el mismo mensaje pida un trabajo.

## Correrlo

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest
.venv/bin/recado
```

La bandeja queda en http://127.0.0.1:8030. La tanda de muestra está fechada el 28 oct 2026.

## Qué decide

| Recado | Sale |
| --- | --- |
| Pedido en un día que abre | Confirma |
| Pedido en sábado, domingo o feriado | Mueve al siguiente día abierto |
| Pago sin día | Anota el monto |
| Saludo, o día que ya pasó, o sin día | Pregunta |
| Queja, dos días, o feriados sin leer | Lo lee una persona |
