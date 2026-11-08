#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <WiFiUdp.h>

const int MPU_ADDR = 0x68;
const int REG_PWR_MGMT_1 = 0x6B;
const int REG_ACCEL_XOUT_H = 0x3B;
const float FATOR_ESCALA_2G = 16384.0;

// Wi‑Fi
const char* WIFI_SSID = "TP-LINK_51AE";
const char* WIFI_SENHA = "65784150";

// PC que vai receber
const char* IP_DESTINO = "192.168.1.101";
const int PORTA_UDP = 4210;

// I2C
const int PINO_SDA = 21;
const int PINO_SCL = 22;

// UDP
WiFiUDP udp;

void conectarWiFi() {
  Serial.println("Conectando ao Wi Fi...");
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_SENHA);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWi Fi conectado!");
  Serial.print("IP do ESP32: ");
  Serial.println(WiFi.localIP());
}

void recuperarBarramentoI2C() {
  Serial.println("[AVISO] Barramento I2C travado. Tentando recuperar...");
  delay(500);

  Wire.end();

  pinMode(PINO_SDA, OUTPUT);
  pinMode(PINO_SCL, OUTPUT);
  digitalWrite(PINO_SDA, HIGH);

  for (int i = 0; i < 9; i++) {
    digitalWrite(PINO_SCL, HIGH);
    delayMicroseconds(5);
    digitalWrite(PINO_SCL, LOW);
    delayMicroseconds(5);
  }

  digitalWrite(PINO_SDA, LOW);
  delayMicroseconds(5);
  digitalWrite(PINO_SCL, HIGH);
  delayMicroseconds(5);
  digitalWrite(PINO_SDA, HIGH);

  delay(10);

  Wire.begin(PINO_SDA, PINO_SCL);
  Wire.setClock(100000);
  Serial.println("[AVISO] Barramento reiniciado.");
}

bool lerAcelerometro(float &ax, float &ay, float &az) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(REG_ACCEL_XOUT_H);
  Wire.endTransmission(false);

  uint8_t bytesRecebidos = Wire.requestFrom(MPU_ADDR, 6, true);

  if (bytesRecebidos != 6) {
    return false;
  }

  int16_t bruto_x = (Wire.read() << 8) | Wire.read();
  int16_t bruto_y = (Wire.read() << 8) | Wire.read();
  int16_t bruto_z = (Wire.read() << 8) | Wire.read();

  ax = bruto_x / 16384.0;
  ay = bruto_y / 16384.0;
  az = bruto_z / 16384.0;

  return true;
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  conectarWiFi();

  Wire.begin(PINO_SDA, PINO_SCL);
  Wire.setClock(100000);

  Wire.beginTransmission(MPU_ADDR);
  Wire.write(REG_PWR_MGMT_1);
  Wire.write(0);
  Wire.endTransmission(true);

  Serial.println("ESP32 pronto. Enviando dados via UDP...");
  delay(100);
}

void loop() {
  float ax, ay, az;

  if (!lerAcelerometro(ax, ay, az)) {
    recuperarBarramentoI2C();
    delay(50);
    return;
  }

  
  char mensagem[32];
  snprintf(mensagem, sizeof(mensagem), "X:%.3f,Y:%.3f", ax, ay);

  // Envia via UDP
  udp.beginPacket(IP_DESTINO, PORTA_UDP);
  udp.print(mensagem);
  udp.endPacket();

  Serial.println(mensagem);
  delay(20); // ~50 Hz
}