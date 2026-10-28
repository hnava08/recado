"""Sirve la bandeja y vuelve a leer los feriados cuando se corre la tanda."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from recado.bandeja import MUESTRAS
from recado.calendario import cargar
from recado.reglas import armar

RAIZ = Path(__file__).resolve().parent / "estatico"
PUERTO = 8030
ESTADO = {"recados": [dict(fila) for fila in MUESTRAS], "seq": 38, "calendario": None}


def tanda():
    if ESTADO["calendario"] is None:
        ESTADO["calendario"] = cargar()
    return armar(ESTADO["recados"], ESTADO["calendario"])


def sumar(de: str, texto: str) -> None:
    ESTADO["seq"] += 1
    ESTADO["recados"].append(
        {
            "id": f"R-{ESTADO['seq']:03d}",
            "de": de.strip() or "Sin nombre",
            "hora": "ahora",
            "texto": texto.strip(),
        }
    )


def correr() -> None:
    ESTADO["calendario"] = cargar()


class handler(BaseHTTPRequestHandler):
    def log_message(self, formato, *args):
        return

    def _enviar(self, codigo: int, cuerpo: bytes, tipo: str) -> None:
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(cuerpo)

    def _json(self, codigo: int, datos: dict) -> None:
        self._enviar(codigo, json.dumps(datos, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self):
        ruta = urlparse(self.path).path
        if ruta == "/api/tanda":
            self._json(200, tanda())
            return
        if ruta in ("/", "/index.html"):
            self._enviar(200, (RAIZ / "index.html").read_bytes(), "text/html; charset=utf-8")
            return
        if ruta == "/app.css":
            self._enviar(200, (RAIZ / "app.css").read_bytes(), "text/css; charset=utf-8")
            return
        self._json(404, {"error": "No está"})

    def do_POST(self):
        ruta = urlparse(self.path).path
        largo = int(self.headers.get("Content-Length") or 0)
        if largo > 8000:
            self._json(413, {"error": "El recado es demasiado largo."})
            return
        crudo = self.rfile.read(largo) if largo else b""
        if ruta == "/api/correr":
            correr()
            self._json(200, tanda())
            return
        if ruta == "/api/recados":
            try:
                datos = json.loads(crudo.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._json(400, {"error": "El recado no se lee."})
                return
            texto = str(datos.get("texto") or "").strip()
            if not texto:
                self._json(422, {"error": "Falta el texto."})
                return
            sumar(str(datos.get("de") or ""), texto)
            parte = tanda()
            self._json(201, parte)
            return
        self._json(404, {"error": "No está"})


def main() -> None:
    servidor = ThreadingHTTPServer(("127.0.0.1", PUERTO), handler)
    print(f"Recado en http://127.0.0.1:{PUERTO}", flush=True)
    servidor.serve_forever()


if __name__ == "__main__":
    main()
