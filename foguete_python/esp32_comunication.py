import socket
import time
from threading import Thread, Lock
import numpy as np

class UDPManager():
    """ Classe que gerencia a comunicação UDP com o ESP32. """

    

    def __init__(self, **kwargs):
        """ Construtor da classe UDPManager """
        # Passar variaveis de inicialização
        self.serial_port = kwargs.get("porta_serial")
        self.baud_rate = int(kwargs.get("baud_rate"))
        self.timeout = int(kwargs.get("timeout"))
        self.ip = kwargs.get("ip")
        self.porta = int(kwargs.get("porta"))
        self.buffer_size = int(kwargs.get("buffer_size"))

        self._lock = Lock()
        self._socket_udp = None

        # Guardar os últimos valores recebidos (x,y,z)
        self._save_x = 0.0
        self._save_y = 0.0
        self._save_z = 0.0

        # Timestamp da última leitura válida — nossa base para o
        # "watchdog" que detecta perda de conexão.
        self._ultima_atualizacao = 0.0

        # Flag que controla quando a thread de fundo deve parar.
        self._rodando = False
        self._thread = None

        # Calibração do sensor 
        self._calibrando = True
        self._amostras_calibracao_x = []
        self._amostras_calibracao_y = []
        self._offset_x = 0.0
        self._offset_y = 0.0


    def _conectar(self):
        """
            Inicializa o socket UDP e inicia a thread responsável por receber os dados
            do cliente ESP32.

            A função valida o endereço IP configurado, cria o socket UDP, vincula-o
            à porta informada e define um timeout para leitura. Em seguida, ativa a
            flag de execução e inicia a thread de monitoramento em segundo plano.

            Returns:
                bool: True se a conexão foi criada com sucesso; 
                      False se o IP não foi informado ou se ocorreu algum 
                      erro ao abrir o socket.
        """
        try:
            if not self.ip:
                print("IP do socket não informado.")
                return False

            self._socket_udp = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
            self._socket_udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket_udp.bind((self.ip,self.porta))
            self._socket_udp.settimeout(2.0)

            print(f"Escutando UDP em {self.ip}:{self.porta}...")
            self._rodando = True
            # Inicialização da thread
            if self._thread is None or not self._thread.is_alive():
              self._thread = Thread(target=self._update, daemon=True)
              self._thread.start()  
            return True
        except (OSError, TypeError, ValueError) as erro:
            print(f"Não foi possível abrir o socket UDP: {erro}")
            return False

    def _formatar_bytes(self, linhas_recebidas):
        """
            Interpreta uma string recebida via UDP no formato
            'X:valor_x,Y:valor_y' e converte para uma tupla com os valores numéricos.

            A entrada esperada segue o padrão de duas partes separadas por vírgula,
            onde cada parte contém um rótulo seguido de um valor em ponto flutuante.
            Exemplo: 'X:0.052,Y:-0.013'.

            Args:
                linhas_recebidas (str): Texto bruto recebido pela conexão UDP.

            Returns:
                tuple | None: Tupla contendo os valores convertidos na ordem
                (x, y) quando a string estiver em um formato válido. Caso o texto
                seja inválido ou não possa ser convertido, retorna None.
        """
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

    def _update(self):
        """
            Loop de leitura em segundo plano da comunicação UDP.

            Este método executa dentro de uma thread separada e permanece aguardando
            pacotes enviados pelo cliente ESP32. Cada mensagem recebida é convertida
            para texto, validada pelo formato esperado e, quando correta, os valores
            de aceleração são armazenados nos atributos compartilhados da classe.

            O processo segue assim:
                1. Recebe os dados via socket UDP.
                2. Decodifica a mensagem em UTF-8.
                3. Verifica se a string não está vazia.
                4. Tenta converter o conteúdo com o método formatar_bytes.
                5. Se for válida, atualiza os valores x, y e o timestamp da última leitura.
                6. Repete enquanto a flag `_rodando` estiver ativa.

            Em casos de timeout, o método apenas aguarda novamente. Quando a conexão é
            encerrada, o socket é fechado no bloco `finally`.

            Note:
                Este método é executado em background e usa um lock para garantir a
                consistência dos dados compartilhados entre threads.
        """
        AMOSTRAS_TOTAL = 50
        print("Recebendo dados... (Ctrl+C para parar)\n")
        
        try:
            while self._rodando:
                try:
                    dados_brutos, endereco_origem = self._socket_udp.recvfrom(self.buffer_size)
                    linha_texto = dados_brutos.decode("utf-8", errors="ignore")

                    if not linha_texto.strip():
                        continue

                    print(f"Recebi de {endereco_origem}: {linha_texto}")

                    resultado = self._formatar_bytes(linha_texto)

                    if resultado is not None:
                        x, y = resultado
                        print(f"Aceleração recebida -> X: {x:.3f} | Y: {y:.3f}")

                        # Calibração
                        if self._calibrando:
                            self._amostras_calibracao_x.append(x)
                            self._amostras_calibracao_y.append(y)
                            if ((len(self._amostras_calibracao_x) == AMOSTRAS_TOTAL) and 
                                (len(self._amostras_calibracao_y) == AMOSTRAS_TOTAL)):
                                self._offset_x = np.mean(self._amostras_calibracao_x)
                                self._offset_y = np.mean(self._amostras_calibracao_y)
                                self._calibrando = False
                                print(f"Calibração concluída! Offset X: {self._offset_x}, Offset Y: {self._offset_y}")
                        else:
                            with self._lock:
                                self._save_x = x - self._offset_x
                                self._save_y = y - self._offset_y
                                self._ultima_atualizacao = time.time()
                    else:
                        print(f"[Pacote ignorado, formato inesperado]: {linha_texto.strip()}")                      
                            

                    #Limpeza dos dados
                    #x = None
                    #y = None

                except socket.timeout:
                    print("Aguardando pacote UDP...")
                    time.sleep(0.5)
                except OSError as erro:
                    print(f"Erro: {erro}")

        except KeyboardInterrupt:
            print("\nEncerrando leitura...")
        finally:
            if self._socket_udp is not None:
                self._socket_udp.close()
                print("Socket UDP fechado.")       

    def obter_valores(self):
        """
            Retorna os últimos valores de aceleração lidos do sensor e o tempo
            desde a última atualização válida.

            Este método é seguro para uso em threads diferentes, pois acessa as
            variáveis compartilhadas dentro de um bloco protegido pelo lock da classe.
            Isso evita condições de corrida entre a thread de recebimento UDP e a
            thread principal do jogo.

            Returns:
                tuple: uma tupla no formato (x, y, idade), onde:
                    - x: último valor em X recebido;
                    - y: último valor em Y recebido;
                    - idade: tempo em segundos desde a última atualização válida.
        """
        with self._lock:
            x = self._save_x
            y = self._save_y
            idade = time.time() - self._ultima_atualizacao
        return (x, y, idade)

    
    def iniciar_atentimento(self):
        """
            Inicia a conexão com ESP32 e a recepção das informações

            Returns:
                bool: True se a conexão for bem sucedida; False caso contrário, o código se encerra

        """
        # Verificação da conexão
        conectar = self._conectar()
        if not conectar:
            print("Serviço encerrado por falhar ao abrir o socket UDP")
            return False 

        return True

        
        
        
            
            




