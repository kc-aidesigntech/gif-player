/*
 * SD-only probe for QT Py ESP32-S3 + EYESPI BFF + 6178 round TFT
 *
 * Upload this sketch (not the GIF player) to test ONLY the microSD slot
 * on the TFT module. Open Serial Monitor @ 115200.
 *
 * Per Adafruit 6178 pinouts, SD needs MISO on the EYESPI ribbon (pin 6).
 * The TFT does not use MISO — so this test isolates SD wiring.
 *
 * https://learn.adafruit.com/adafruit-1-28-240x240-round-tft-lcd/pinouts
 */

#include <SPI.h>
#include <SD.h>

#define SD_CS A3

static void printPins() {
  Serial.printf("SD_CS (A3) GPIO %d\n", digitalPinToGPIONumber(SD_CS));
  Serial.printf("SCK GPIO %d  MISO GPIO %d  MOSI GPIO %d\n",
                digitalPinToGPIONumber(SCK), digitalPinToGPIONumber(MISO),
                digitalPinToGPIONumber(MOSI));
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n--- SD card probe (TFT slot, EYESPI ribbon) ---");
  printPins();

  pinMode(SD_CS, OUTPUT);
  digitalWrite(SD_CS, HIGH);

#if defined(ARDUINO_ADAFRUIT_QTPY_ESP32S3) || defined(ARDUINO_ADAFRUIT_QTPY_ESP32S3_NOPSRAM)
  SPI.begin(SCK, MISO, MOSI);
#else
  SPI.begin();
#endif

  delay(200);

  const uint32_t speeds[] = {400000, 1000000, 4000000, 8000000};
  bool ok = false;
  for (uint32_t hz : speeds) {
    SD.end();
    delay(50);
    Serial.printf("Trying SD.begin @ %lu Hz ... ", hz);
    if (SD.begin(SD_CS, SPI, hz)) {
      Serial.println("OK");
      ok = true;
      break;
    }
    Serial.println("fail");
  }

  if (!ok) {
    Serial.println("\nSD mount FAILED.");
    Serial.println("Check: card in TFT back slot, FAT32, ribbon fully seated.");
    Serial.println("Display can work while SD fails if MISO (EYESPI pin 6) is bad.");
    return;
  }

  uint8_t t = SD.cardType();
  Serial.printf("cardType=%u  size=%llu MB\n", t, SD.cardSize() / (1024 * 1024));

  File root = SD.open("/");
  if (!root) {
    Serial.println("SD.open(/) failed");
    return;
  }
  Serial.println("Root listing:");
  while (true) {
    File e = root.openNextFile();
    if (!e) break;
    Serial.print("  ");
    Serial.println(e.name());
    e.close();
  }
  root.close();
  Serial.println("Done — SD hardware looks OK. Re-upload the GIF player sketch.");
}

void loop() {}
