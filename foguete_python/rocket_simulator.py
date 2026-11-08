"""Código de aprendizagem de um foguete"""

from direct.showbase.ShowBase import ShowBase
from panda3d.core import (NodePath, AmbientLight, 
                          Vec4, GeomVertexFormat, 
                          GeomVertexData, GeomVertexWriter,
                          Geom, GeomTriangles, 
                          GeomNode)
from direct.task import Task
import math
import random
from esp32_comunication import UDPManager
import sys

class FogueteApp(ShowBase):
    """Classe que herda ShowBase e cria um foguete em 3D."""

    def __init__(self):
        """Construtor da classe FogueteApp que inicializa toda infraestrutura do Panda3D
            com janela, câmera, motor de renderização"""
        ShowBase.__init__(self)

        self.sensor_mpu = UDPManager(porta_serial="COM3",
                                     baud_rate=115200,
                                     timeout=1.0,
                                     ip="0.0.0.0",
                                     porta=4210,
                                     buffer_size=1024,)
        
        if not self.sensor_mpu.iniciar_atentimento():
            print("Aviso: não foi possível iniciar o UDPManager. Encerrando.")
            sys.exit(1)

        # Calibração do sensor
        self.SENSIBILIDADE = 90.0
        # Fator de suavização (0 a 1).
        self.ALPHA_SUAVIZACAO = 0.15

        # Valores suavizados, mantidos entre frames.
        self.pitch_suavizado = 0.0
        self.roll_suavizado = 0.0

        # Tempo (segundos) sem dados novos até considerarmos o
        # sensor "desconectado" e voltarmos à posição neutra.
        self.TIMEOUT_SENSOR = 1.0
        

        # --- Variáveis de estado da rotação ---
        # Guardamos os ângulos atuais como variáveis PRÓPRIAS (não
        # perguntamos ao Panda3D "qual é o ângulo agora" toda vez),
        # porque vamos incrementá-los manualmente a cada frame.
        self.angulo_pitch = 0.0
        self.angulo_roll = 0.0

        # Velocidade de rotação em GRAUS POR SEGUNDO (não por frame!)
        # — lembra do conceito de delta time? É por isso que definimos
        # a velocidade nessa unidade, e não "graus por frame".
        self.VELOCIDADE_ROTACAO = 60.0

        # Registra nossa função de atualização no Task Manager.
        # A partir daqui, self.update() será chamada automaticamente
        # UMA VEZ POR FRAME, para sempre, até o programa fechar.
        self.taskMgr.add(self.update, "tarefa_atualizacao")

        # ---------Configuração da cor de fundo ---------
        # Cor de fundo da cena (RGB normalizado de 0 a 1, não 0-255).
        hex_cor_ceu =  "#183A7A"
        hex_cor_ceu = hex_cor_ceu.lstrip("#")
        r = int(hex_cor_ceu[0:2], 16) / 255
        g = int(hex_cor_ceu[2:4], 16) / 255
        b = int(hex_cor_ceu[4:6], 16) / 255        
        self.setBackgroundColor(r, g, b)

        # ---------Configuração da câmera---------
        # Posicionamento da câmera padrão do Panda3D, setPos(x, y z):
        # Foi colocado atrás do eixo y = -14 e um pouco acima z = 1.8 para visualização
        # completa do objeto
        self.cam.setPos(0, -14, 10)
        # Direcionamento da câmera
        self.cam.lookAt(0, 0, 2.5)

        # ---------Configuração da luz ambiente---------
        # Sem nenhuma luz na cena, para garantir que o objeto apareça em todas as direções
        # e sem sombra para não atrapalhar a visualização (forma simples)
        luz_ambiente = AmbientLight("luz_ambiente")
        luz_ambiente.setColor(Vec4(0.6, 0.6, 0.6, 1))
        # attachNewNode() cria um NodePath para essa luz e já coloca no scene graph, 
        # como filha de "render".
        no_luz = self.render.attachNewNode(luz_ambiente)
        # setLight() ativa essa luz para iluminar TUDO que está
        # "abaixo" de render na hierarquia (ou seja, a cena inteira).
        self.render.setLight(no_luz)

        # ---------Configuração do eixo---------
        # Este é um NodePath VAZIO, sem geometria própria — ele serve
        # só como um "ponto de pivô": ao rotacionar ESTE nó, todos os
        # filhos dele (corpo) giram juntos, mantendo a posição
        # relativa entre eles. É exatamente o conceito de hierarquia
        # do scene graph que expliquei na teoria.
        self.foguete = self.render.attachNewNode("foguete")

        # ---------Construção do corpo do foguete (tamanho, forma, cor e posição)---------
        raio = 0.28
        altura_corpo = 4.5
        corpo = self._criar_cilindro(raio, altura_corpo, segmentos=24)
        hex_cor_corpo = "#E08C3E"
        hex_cor_corpo = hex_cor_corpo.lstrip("#")
        r1 = int(hex_cor_corpo[0:2], 16) / 255
        g1= int(hex_cor_corpo[2:4], 16) / 255
        b1 = int(hex_cor_corpo[4:6], 16) / 255
        corpo.setColor(r1, g1, b1)
        # Posiciona o corpo DENTRO do referencial do foguete (não do
        # mundo inteiro) — por isso os valores são relativos à origem
        # do próprio "self.foguete", não à câmera ou ao chão.
        corpo.setPos(0, 0, altura_corpo / 2)
        corpo.reparentTo(self.foguete)

        # ---Construção da coifa -----
        altura_coifa = 1.4
        bico = self._criar_cone(raio, altura_coifa, segmentos=24)
        hex_cor_coifa = "#E08C3E"
        hex_cor_coifa = hex_cor_coifa.lstrip("#")
        r2 = int(hex_cor_coifa[0:2], 16) / 255
        g2= int(hex_cor_coifa[2:4], 16) / 255
        b2 = int(hex_cor_coifa[4:6], 16) / 255
        bico.setColor(r2, g2, b2)       
        bico.setPos(0, 0, altura_corpo + altura_coifa / 2)
        bico.reparentTo(self.foguete)

        # ---Construção da tubeira -----
        tubeira = self._criar_cilindro(raio* 0.85, 0.4, 24)
        hex_cor_tubeira = "#8B8886"
        hex_cor_tubeira = hex_cor_tubeira.lstrip("#")
        r3 = int(hex_cor_tubeira[0:2], 16) / 255
        g3 = int(hex_cor_tubeira[2:4], 16) / 255
        b3 = int(hex_cor_tubeira[4:6], 16) / 255
        tubeira.setColor(r3, g3, b3)
        tubeira.setPos(0,0,-0.2)
        tubeira.reparentTo(self.foguete)
        tubeira.setLightOff()

        # ---Construção das aletas -----
        for i in range(4):
            ang = i * (math.pi / 2)
            aleta = self._criar_aleta()
            hex_cor_aleta = "#26140A"
            hex_cor_aleta = hex_cor_aleta.lstrip("#")
            r4 = int(hex_cor_aleta[0:2], 16) / 255
            g4 = int(hex_cor_aleta[2:4], 16) / 255
            b4 = int(hex_cor_aleta[4:6], 16) / 255
            aleta.setColor(r4,g4,b4)            
            aleta.setPos(raio * math.cos(ang), raio * math.sin(ang), 0.1)
            aleta.setH(math.degrees(ang))
            aleta.reparentTo(self.foguete)
            aleta.setLightOff()
            aleta.setTwoSided(True)

        # ---Construção do propulsor -----
        self.chama = self._criar_cone(raio * 0.65, 1.6, 16)
        hex_cor_chama = "#4C7A59"
        hex_cor_chama = hex_cor_chama.lstrip("#")
        r5 = int(hex_cor_chama[0:2], 16) / 255
        g5 = int(hex_cor_chama[2:4], 16) / 255
        b5 = int(hex_cor_chama[4:6], 16) / 255
        self.chama.setColor(r5,g5,b5)
        self.chama.setPos(0, 0, -1.2)
        self.chama.setP(180)
        self.chama.reparentTo(self.foguete)
        self.chama.setLightOff()

        


    def _criar_aleta(self):
        format = GeomVertexFormat.getV3()
        vdata = GeomVertexData("aleta_losangular", format, Geom.UHStatic)
        vertex = GeomVertexWriter(vdata, "vertex")

        vertex.addData3(0.0, 0, 1.4)
        vertex.addData3(0.8, 0, 0.4)
        vertex.addData3(0.8, 0, -0.3)
        vertex.addData3(0.0, 0, -0.1)

        prim = GeomTriangles(Geom.UHStatic)
        prim.addVertices(0, 1, 2)
        prim.addVertices(0, 2, 3)

        geom = Geom(vdata)
        geom.addPrimitive(prim)
        node = GeomNode("aleta")
        node.addGeom(geom)
        return NodePath(node)


    def _criar_cilindro(self,raio, altura,segmentos):
        """
        Gera a geometria de um cilindro manualmente, vértice por
        vértice. Isso é 'geometria procedural' — construir formas
        3D através de matemática, em vez de carregar um arquivo de
        modelo pronto (.obj, .gltf, etc.).
        """

        formato = GeomVertexFormat.getV3()  # Formato: só posição (x,y,z), sem cor/textura por vértice
        dados_vertices = GeomVertexData("cilindro", formato, Geom.UHStatic)
        escritor = GeomVertexWriter(dados_vertices, "vertex")

        # Para cada "fatia" ao redor do círculo, criamos 2 vértices:
        # um na base (Z negativo) e um no topo (Z positivo).
        for i in range(segmentos + 1):
            angulo = 2 * math.pi * i / segmentos
            x = raio * math.cos(angulo)
            y = raio * math.sin(angulo)
            escritor.addData3(x, y, -altura / 2)  # vértice de baixo
            escritor.addData3(x, y, altura / 2)   # vértice de cima

        # Triângulos conectam os vértices em pares, formando a
        # superfície lateral do cilindro (2 triângulos por "fatia").
        triangulos = GeomTriangles(Geom.UHStatic)
        for i in range(segmentos):
            i1, i2 = i * 2, i * 2 + 1
            i3, i4 = (i + 1) * 2, (i + 1) * 2 + 1
            triangulos.addVertices(i1, i3, i2)
            triangulos.addVertices(i2, i3, i4)

        geometria = Geom(dados_vertices)
        geometria.addPrimitive(triangulos)
        no = GeomNode("cilindro")
        no.addGeom(geometria)
        return NodePath(no)

    def _criar_cone(self, raio, altura, segmentos):
        """Mesma lógica do cilindro, mas convergindo para um único
        ponto no topo (o ápice do cone)."""
        formato = GeomVertexFormat.getV3()
        dados_vertices = GeomVertexData("cone", formato, Geom.UHStatic)
        escritor = GeomVertexWriter(dados_vertices, "vertex")

        for i in range(segmentos):
            angulo = 2 * math.pi * i / segmentos
            x = raio * math.cos(angulo)
            y = raio * math.sin(angulo)
            escritor.addData3(x, y, -altura / 2)

        escritor.addData3(0, 0, altura / 2)  # O ápice (ponta do cone)
        indice_apice = segmentos

        triangulos = GeomTriangles(Geom.UHStatic)
        for i in range(segmentos):
            proximo = (i + 1) % segmentos
            triangulos.addVertices(i, proximo, indice_apice)

        geometria = Geom(dados_vertices)
        geometria.addPrimitive(triangulos)
        no = GeomNode("cone")
        no.addGeom(geometria)
        return NodePath(no)

    def update(self, task):
        """
        Executada automaticamente uma vez por frame pelo Task Manager.
        Aqui vive a lógica de "o que muda a cada instante".
        """
        #Mudança de cor da chama da propulsão
        escala = 1.4 + random.uniform(-0.25, 0.35)
        self.chama.setScale(1, 1, escala)
        self.chama.setColor(1.0, random.uniform(0.4, 0.8), 0.0, 1)
        # globalClock.getDt() retorna quantos SEGUNDOS se passaram
        # desde o último frame (geralmente uma fração pequena, tipo
        # 0.016 para 60 FPS). É a peça-chave do movimento consistente
        # que explicamos na teoria.
        dt = globalClock.getDt() # type: ignore

        x,y,idade_dados = self.sensor_mpu.obter_valores()

        if idade_dados > self.TIMEOUT_SENSOR:
            # Watchdog: sensor "sumiu" — trata como posição neutra.
            x, y = 0.0, 0.0

        # --- Mapeamento: g -> graus ---
        pitch_bruto = x * self.SENSIBILIDADE
        roll_bruto = y * self.SENSIBILIDADE

        # --- Suavização (média móvel exponencial) ---
        self.pitch_suavizado = (
            self.ALPHA_SUAVIZACAO * pitch_bruto
            + (1 - self.ALPHA_SUAVIZACAO) * self.pitch_suavizado
        )
        self.roll_suavizado = (
            self.ALPHA_SUAVIZACAO * roll_bruto
            + (1 - self.ALPHA_SUAVIZACAO) * self.roll_suavizado
        )

        #Desafio de código: Adicionando um "limite" (clamp) na rotação
        self.angulo_pitch = max(-45.0, min(45.0, self.pitch_suavizado))
        self.angulo_roll = max(-45.0, min(45.0, self.roll_suavizado))

        # Aplicamos os ângulos acumulados ao NÓ PAI do foguete.
        # Como corpo e bico são FILHOS desse nó, os dois giram juntos.
        self.foguete.setP(self.angulo_pitch)
        self.foguete.setR(self.angulo_roll)

        # OBRIGATÓRIO: retornar Task.cont diz ao Panda3D "continue
        # me chamando no próximo frame". Esquecer isso é um erro
        # comum que faz a tarefa parar de rodar após o 1º frame.
        return Task.cont




