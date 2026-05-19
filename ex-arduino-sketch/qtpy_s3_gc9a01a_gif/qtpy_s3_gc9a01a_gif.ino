/*
 * QT Py ESP32-S3 + EYESPI BFF + GC9A01A round TFT (ribbon / FPC cable)
 *
 * The display talks over SPI on the ribbon — not serial UART.
 * With the EYESPI BFF stacked on the QT Py, the BFF routes:
 *   TFT CS  -> pin labeled TX  (GPIO, not "use UART")
 *   TFT DC  -> pin labeled RX
 *   SD CS   -> A3
 *   SCK/MOSI/MISO -> QT Py default SPI (also on the ribbon)
 *
 * Gift setup:
 *   1. Copy assets/sample.gif to the microSD as /gifs/sample.gif
 *   2. Insert SD into the display breakout, power on — it loops forever.
 */

#include <SPI.h>
#include <SD.h>
#include <Adafruit_GFX.h>
#include <Adafruit_GC9A01A.h>
#include <AnimatedGIF.h>

// --- pins (EYESPI BFF defaults) ---
#define TFT_CS TX
#define TFT_DC RX
#define TFT_RST -1
#define SD_CS A3

// --- tuning ---
// Start slow while bringing up hardware; raise to 30000000 once colors work.
static const uint32_t TFT_SPI_HZ = 8000000;
static const uint32_t SD_SPI_HZ = 20000000;

// Full-screen red/green/blue/white at boot. Set false after display works.
#define BOOT_COLOR_TEST true

// Tried in order until one opens.
static const char *GIF_PATHS[] = {
    "/gifs/sample.gif",
    "/sample.gif",
};
static const size_t GIF_PATH_COUNT = sizeof(GIF_PATHS) / sizeof(GIF_PATHS[0]);

Adafruit_GC9A01A tft(TFT_CS, TFT_DC, TFT_RST);
AnimatedGIF gif;
File gifFile;
static uint16_t lineBuf[GC9A01A_TFTWIDTH];

static void displaySelfTest() {
  const uint16_t colors[] = {GC9A01A_RED, GC9A01A_GREEN, GC9A01A_BLUE, GC9A01A_WHITE};
  for (uint16_t c : colors) {
    tft.fillScreen(c);
    delay(700);
  }
}

static void splash(const char *msg, uint16_t color) {
  tft.fillScreen(GC9A01A_BLACK);
  tft.setTextColor(color);
  tft.setTextSize(2);
  tft.setCursor(12, 108);
  tft.print(msg);
}

static void *GIFOpenFile(const char *fname, int32_t *pSize) {
  gifFile = SD.open(fname);
  if (!gifFile) return nullptr;
  *pSize = (int32_t)gifFile.size();
  return (void *)&gifFile;
}

static void GIFCloseFile(void *pHandle) {
  File *f = static_cast<File *>(pHandle);
  if (f) f->close();
}

static int32_t GIFReadFile(GIFFILE *pFile, uint8_t *pBuf, int32_t iLen) {
  File *f = static_cast<File *>(pFile->fHandle);
  if (!f) return 0;
  int32_t remain = pFile->iSize - pFile->iPos;
  if (remain <= 0) return 0;
  if (iLen > remain) iLen = remain;
  int32_t n = (int32_t)f->read(pBuf, iLen);
  if (n < 0) n = 0;
  pFile->iPos += n;
  return n;
}

static int32_t GIFSeekFile(GIFFILE *pFile, int32_t iPosition) {
  File *f = static_cast<File *>(pFile->fHandle);
  if (!f) return pFile->iPos;
  if (!f->seek(iPosition)) return pFile->iPos;
  pFile->iPos = (int32_t)f->position();
  return pFile->iPos;
}

static void GIFDraw(GIFDRAW *pDraw) {
  int y = pDraw->iY + pDraw->y;
  if (y < 0 || y >= GC9A01A_TFTHEIGHT) return;

  int x = pDraw->iX;
  int w = pDraw->iWidth;
  if (x >= GC9A01A_TFTWIDTH || w <= 0) return;

  if (x < 0) {
    w += x;
    x = 0;
  }
  if (x + w > GC9A01A_TFTWIDTH) w = GC9A01A_TFTWIDTH - x;
  if (w <= 0) return;

  uint8_t *s = pDraw->pPixels;
  uint16_t *pal = (uint16_t *)pDraw->pPalette;

  if (pDraw->ucHasTransparency) {
    const uint8_t transparent = pDraw->ucTransparent;
    int i = 0;
    while (i < w) {
      while (i < w && s[i] == transparent) i++;
      int start = i;
      while (i < w && s[i] != transparent) {
        lineBuf[i - start] = pal[s[i]];
        i++;
      }
      int run = i - start;
      if (run > 0) {
        tft.setAddrWindow(x + start, y, run, 1);
        tft.writePixels(lineBuf, run, true, false);
      }
    }
  } else {
    for (int i = 0; i < w; i++) lineBuf[i] = pal[s[i]];
    tft.setAddrWindow(x, y, w, 1);
    tft.writePixels(lineBuf, w, true, false);
  }
}

static bool mountSD() {
  pinMode(SD_CS, OUTPUT);
  digitalWrite(SD_CS, HIGH);
  return SD.begin(SD_CS, SPI, SD_SPI_HZ);
}

static const char *openAnyGif() {
  for (size_t i = 0; i < GIF_PATH_COUNT; i++) {
    if (gif.open(GIF_PATHS[i], GIFOpenFile, GIFCloseFile, GIFReadFile, GIFSeekFile, GIFDraw)) {
      return GIF_PATHS[i];
    }
    gif.close();
  }
  return nullptr;
}

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("gif-player boot");

  pinMode(TFT_CS, OUTPUT);
  digitalWrite(TFT_CS, HIGH);

#if defined(ARDUINO_ADAFRUIT_QTPY_ESP32S3) || defined(ARDUINO_ADAFRUIT_QTPY_ESP32S3_NOPSRAM)
  SPI.begin(SCK, MISO, MOSI);
#else
  SPI.begin();
#endif

  tft.begin(TFT_SPI_HZ);
  tft.setRotation(0);

#if BOOT_COLOR_TEST
  Serial.println("display self-test (expect red/green/blue/white)");
  displaySelfTest();
#endif

  splash("GIF", GC9A01A_GREEN);
  delay(400);

  if (!mountSD()) {
    splash("SD?", GC9A01A_RED);
    while (true) {
      delay(1000);
      if (mountSD()) break;
    }
  }

  gif.begin(LITTLE_ENDIAN_PIXELS);
}

void loop() {
  const char *path = openAnyGif();
  if (!path) {
    splash("No GIF", GC9A01A_YELLOW);
    delay(2000);
    return;
  }

  tft.startWrite();
  while (gif.playFrame(true, nullptr)) {
    // playFrame(true) honors frame delays in the GIF
  }
  tft.endWrite();
  gif.close();
}
