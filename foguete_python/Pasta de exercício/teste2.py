import math
import random
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import (
    AmbientLight,
    CardMaker,
    Geom,
    GeomNode,
    GeomTriangles,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
    MouseButton,
    NodePath,
    TextNode,
    Vec4,
)


class FogueteApp(ShowBase):

    def __init__(self):
        ShowBase.__init__(self)

        self.setBackgroundColor(40 / 255, 40 / 255, 45 / 255)

        self.cam.setPos(0, -14, 1.8)
        self.cam.lookAt(0, 0, 1.5)

        alight = AmbientLight("alight")
        alight.setColor(Vec4(0.55, 0.55, 0.55, 1))
        alnp = self.render.attachNewNode(alight)
        self.render.setLight(alnp)

        self.foguete = self.render.attachNewNode("foguete")
        self.foguete.setPos(0, 0, 0)

        RAIO = 0.28
        ALTURA_CORPO = 4.5
        ALTURA_BICO = 1.4

        corpo = self._criar_cilindro(RAIO, ALTURA_CORPO, 32)
        corpo.setColor(0.72, 0.45, 0.2, 1)
        corpo.setPos(0, 0, ALTURA_CORPO / 2)
        corpo.reparentTo(self.foguete)
        corpo.setLightOff()

        bico = self._criar_cone(RAIO, ALTURA_BICO, 32)
        bico.setColor(0.72, 0.45, 0.2, 1)
        bico.setPos(0, 0, ALTURA_CORPO + ALTURA_BICO / 2)
        bico.reparentTo(self.foguete)
        bico.setLightOff()

        bocal = self._criar_cilindro(RAIO * 0.85, 0.4, 24)
        bocal.setColor(0.8, 0.8, 0.85, 1)
        bocal.setPos(0, 0, -0.2)
        bocal.reparentTo(self.foguete)
        bocal.setLightOff()

        # --- TEXTO SUPERNOVA ---
        text_node = TextNode("texto_supernova")
        text_node.setText("SUPERNOVA")
        text_node.setAlign(TextNode.ACenter)

        texto_frente = self.foguete.attachNewNode(text_node)
        texto_frente.setColor(1.0, 1.0, 1.0, 1)
        texto_frente.setScale(0.35)
        texto_frente.setPos(0, -(RAIO + 0.01), ALTURA_CORPO * 0.45)
        texto_frente.setR(90)
        texto_frente.setLightOff()

        texto_costas = self.foguete.attachNewNode(text_node)
        texto_costas.setColor(1.0, 1.0, 1.0, 1)
        texto_costas.setScale(0.35)
        texto_costas.setPos(0, (RAIO + 0.01), ALTURA_CORPO * 0.45)
        texto_costas.setH(180)
        texto_costas.setR(-90)
        texto_costas.setLightOff()

        # -------------------------------------------------------------
        # BANDEIRA DO BRASIL VIA IMAGEM (.PNG / .JPG)
        # -------------------------------------------------------------
        try:
            tex_bandeira = self.loader.loadTexture("image.png")

            # Frente
            #bandeira_frente = self._criar_adesivo_imagem(tex_bandeira)
            #bandeira_frente.reparentTo(self.foguete)
            #bandeira_frente.setPos(0, -(RAIO + 0.012), ALTURA_CORPO * 0.72)
            #bandeira_frente.setR(90)
            #bandeira_frente.setLightOff()

            # Costas
            #bandeira_costas = self._criar_adesivo_imagem(tex_bandeira)
            #bandeira_costas.reparentTo(self.foguete)
            #bandeira_costas.setPos(0, (RAIO + 0.012), ALTURA_CORPO * 0.72)
            #bandeira_costas.setH(180)
            #bandeira_costas.setR(-90)
            #bandeira_costas.setLightOff()

        except Exception as e:
            print(
                f"Aviso: Não foi possível carregar 'bandeira_brasil.png'. {e}"
            )
        # -------------------------------------------------------------

        # Aletas
        for i in range(4):
            ang = i * (math.pi / 2)
            aleta = self._criar_aleta()
            aleta.setColor(0.15, 0.08, 0.04, 1)
            aleta.setPos(RAIO * math.cos(ang), RAIO * math.sin(ang), 0.1)
            aleta.setH(math.degrees(ang))
            aleta.reparentTo(self.foguete)
            aleta.setLightOff()
            aleta.setTwoSided(True)

        self.chama = self._criar_cone(RAIO * 0.65, 1.6, 16)
        self.chama.setColor(0.3, 0.48, 0.35, 1)
        self.chama.setPos(0, 0, -1.2)
        self.chama.setP(180)
        self.chama.reparentTo(self.foguete)
        self.chama.setLightOff()

        self.last_mouse = None
        self.accept("wheel_up", self.rotacionar, [1])
        self.accept("wheel_down", self.rotacionar, [-1])

        self.taskMgr.add(self.update, "update")

    # Função que cria o plano e aplica a imagem
    def _criar_adesivo_imagem(self, textura):
        cm = CardMaker("adesivo_bandeira")
        # Proporção da bandeira (largura x altura)
        cm.setFrame(-0.25, 0.25, -0.175, 0.175)
        np = NodePath(cm.generate())
        np.setTexture(textura)
        return np

    def _criar_cilindro(self, radius, height, segments):
        format = GeomVertexFormat.getV3()
        vdata = GeomVertexData("cylinder", format, Geom.UHStatic)
        vertex = GeomVertexWriter(vdata, "vertex")

        for i in range(segments + 1):
            angle = 2 * math.pi * i / segments
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            vertex.addData3(x, y, -height / 2)
            vertex.addData3(x, y, height / 2)

        prim = GeomTriangles(Geom.UHStatic)
        for i in range(segments):
            i1 = i * 2
            i2 = i1 + 1
            i3 = (i + 1) * 2
            i4 = i3 + 1
            prim.addVertices(i1, i3, i2)
            prim.addVertices(i2, i3, i4)

        geom = Geom(vdata)
        geom.addPrimitive(prim)
        node = GeomNode("cylinder")
        node.addGeom(geom)
        return NodePath(node)

    def _criar_cone(self, radius, height, segments):
        format = GeomVertexFormat.getV3()
        vdata = GeomVertexData("cone", format, Geom.UHStatic)
        vertex = GeomVertexWriter(vdata, "vertex")

        for i in range(segments):
            angle = 2 * math.pi * i / segments
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            vertex.addData3(x, y, -height / 2)

        vertex.addData3(0, 0, height / 2)
        apex = segments

        prim = GeomTriangles(Geom.UHStatic)
        for i in range(segments):
            next_i = (i + 1) % segments
            prim.addVertices(i, next_i, apex)

        geom = Geom(vdata)
        geom.addPrimitive(prim)
        node = GeomNode("cone")
        node.addGeom(geom)
        return NodePath(node)

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

    def rotacionar(self, direcao):
        self.foguete.setH(self.foguete.getH() + direcao * 12)
        self.foguete.setP(self.foguete.getP() + direcao * 8)
        self.foguete.setR(self.foguete.getR() + direcao * 6)

    def update(self, task):
        escala = 1.4 + random.uniform(-0.25, 0.35)
        self.chama.setScale(1, 1, escala)
        self.chama.setColor(1.0, random.uniform(0.4, 0.8), 0.0, 1)

        if self.mouseWatcherNode.hasMouse():
            mpos = self.mouseWatcherNode.getMouse()

            if self.mouseWatcherNode.is_button_down(MouseButton.one()):
                if self.last_mouse is not None:
                    dx = mpos.getX() - self.last_mouse.getX()
                    dy = mpos.getY() - self.last_mouse.getY()
                    self.foguete.setX(self.foguete.getX() + dx * 10)
                    self.foguete.setZ(self.foguete.getZ() + dy * 10)
                self.last_mouse = mpos

            elif self.mouseWatcherNode.is_button_down(MouseButton.three()):
                if self.last_mouse is not None:
                    dy = mpos.getY() - self.last_mouse.getY()
                    nova_dist = self.cam.getY() + dy * 18
                    nova_dist = max(-35, min(-5, nova_dist))
                    self.cam.setY(nova_dist)
                    self.cam.lookAt(0, 0, 1.5)
                self.last_mouse = mpos
            else:
                self.last_mouse = None
        else:
            self.last_mouse = None

        return Task.cont


app = FogueteApp()
app.run()