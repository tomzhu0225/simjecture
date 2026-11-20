"""Process-local WSL proxy bridge to the existing Windows loopback proxy.

Does not change system networking, authentication, firewall or proxy settings.
Only encrypted model traffic crosses the relay; scientific execution stays remote.
"""

import socketserver
import subprocess
import threading


class ModelProxy(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, config):
        self.config = config
        super().__init__(("127.0.0.1", config["listen_port"]), Relay)


class Relay(socketserver.BaseRequestHandler):
    def handle(self):
        config = self.server.config
        code = (
            "import os,socket,sys,threading,msvcrt\n"
            "msvcrt.setmode(0,os.O_BINARY);msvcrt.setmode(1,os.O_BINARY)\n"
            "s=socket.create_connection(("
            + repr(config["windows_proxy_host"])
            + ","
            + str(config["windows_proxy_port"])
            + "),timeout=30);s.settimeout(None)\n"
            "def upload():\n"
            " try:\n"
            "  while b:=os.read(0,65536):s.sendall(b)\n"
            " except OSError:pass\n"
            " finally:\n"
            "  try:s.shutdown(socket.SHUT_WR)\n"
            "  except OSError:pass\n"
            "threading.Thread(target=upload,daemon=True).start()\n"
            "try:\n"
            " while b:=s.recv(65536):os.write(1,b)\n"
            "except OSError:pass\n"
        )
        process = subprocess.Popen(
            [config["windows_python"], "-c", code],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
        )

        def upload():
            try:
                while chunk := self.request.recv(65536):
                    process.stdin.write(chunk)
            except (OSError, ValueError):
                pass
            finally:
                process.stdin.close()

        thread = threading.Thread(target=upload, daemon=True)
        thread.start()
        try:
            while chunk := process.stdout.read(65536):
                self.request.sendall(chunk)
        except OSError:
            pass
        finally:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=10)


class model_network:
    def __init__(self, config):
        self.server = ModelProxy(config) if config else None

    def __enter__(self):
        if self.server is None:
            return None
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self.server

    def __exit__(self, *_):
        if self.server is None:
            return
        self.server.shutdown()
        self.server.server_close()
