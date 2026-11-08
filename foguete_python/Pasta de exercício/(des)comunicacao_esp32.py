import socket
import time


class UDPManager:
    """Gerencia a comunicação UDP com o ESP32."""

    def __init__(self, **kwargs):
        self.ip = kwargs.get("ip", "0.0.0.0")
        self.porta = int(kwargs.get("porta", 4210))
        self.buffer_size = int(kwargs.get("buffer_size", 1024))
        self.socket_udp = None

    def _conectar(self):
        try:
            if not self.ip:
                print("IP do socket UDP não informado.")
                return False

            self.socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket_udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket_udp.bind((self.ip, self.porta))
            self.socket_udp.settimeout(2.0)

            print(f"Escutando UDP em {self.ip}:{self.porta}...")
            return True
        except (OSError, TypeError, ValueError) as erro:
            print(f"Não foi possível abrir o socket UDP: {erro}")
            return False

    def formatar_bytes(self, linhas_recebidas):
        """Converte algo como 'X:0.052,Y:-0.013' em (x, y)."""
        try:
            linhas_recebidas = linhas_recebidas.strip()
            if "," not in linhas_recebidas or ":" not in linhas_recebidas:
                return None

            parte_x, parte_y = linhas_recebidas.split(",")
            valor_x = float(parte_x.split(":")[1])
            valor_y = float(parte_y.split(":")[1])
            return (valor_x, valor_y)
        except (ValueError, IndexError) as erro:
            print(f"[Aviso] Linha descartada: {erro}")
            return None

    def iniciar_leitura(self):
        if not self._conectar():
            print("Código encerrado, por falha ao abrir o socket UDP")
            return

        print("Recebendo dados... (Ctrl+C para parar)\n")

        try:
            while True:
                try:
                    dados_brutos, endereco_origem = self.socket_udp.recvfrom(self.buffer_size)
                    linha_texto = dados_brutos.decode("utf-8", errors="ignore")

                    if not linha_texto.strip():
                        continue

                    print(f"Recebi de {endereco_origem}: {linha_texto}")

                    resultado = self.formatar_bytes(linha_texto)
                    if resultado is not None:
                        x, y = resultado
                        print(f"Aceleração recebida -> X: {x:.3f} | Y: {y:.3f}")
                    else:
                        print(f"[Pacote ignorado, formato inesperado]: {linha_texto.strip()}")

                except socket.timeout:
                    print("Aguardando pacote UDP...")
                    time.sleep(0.5)

        except KeyboardInterrupt:
            print("\nEncerrando leitura...")
        finally:
            if self.socket_udp is not None:
                self.socket_udp.close()
                print("Socket UDP fechado.")


class SerialManager(UDPManager):
    """Compatibilidade com a estrutura anterior do projeto."""
    def __init__(self, **kwargs):
        self.porta_serial = kwargs.get("porta_serial")
        self.baud_rate = kwargs.get("baud_rate")
        self.timeout = kwargs.get("timeout")
        super().__init__(**kwargs)
