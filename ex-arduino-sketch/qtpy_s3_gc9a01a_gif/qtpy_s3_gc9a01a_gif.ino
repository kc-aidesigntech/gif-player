/*
 * QT Py ESP32-S3 + EYESPI BFF + GC9A01A round TFT (ribbon / FPC cable)
 *
 * microSD slot is on the 1.28" TFT PCB (FAT32, e.g. /gifs/sample.gif).
 */

#include <SPI.h>
#include <SD.h>
#include <Adafruit_GFX.h>
#include <Adafruit_GC9A01A.h>
#include <AnimatedGIF.h>

#define TFT_CS TX
#define TFT_DC RX
#define TFT_RST -1
#define SD_CS A3

static const uint32_t TFT_SPI_HZ = 8000000;
static const uint32_t SD_SPI_HZ = 4000000;

#define BOOT_COLOR_TEST true

Adafruit_GC9A01A tft(TFT_CS, TFT_DC, TFT_RST);
AnimatedGIF gif;
File gifFile;
static uint16_t lineBuf[GC9A01A_TFTWIDTH];
static char activeGifPath[64];

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
  busIdle();
  gifFile = SD.open(fname);
  if (!gifFile) {
    Serial.printf("SD.open failed: %s\n", fname);
    return nullptr;
  }
  *pSize = (int32_t)gifFile.size();
  Serial.printf("Opened %s (%ld bytes)\n", fname, (long)*pSize);
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
        tft.writePixels(lineBuf, run, false, false);
      }
    }
  } else {
    for (int i = 0; i < w; i++) lineBuf[i] = pal[s[i]];
    tft.setAddrWindow(x, y, w, 1);
    tft.writePixels(lineBuf, w, false, false);
  }
}

static void busIdle() {
  digitalWrite(TFT_CS, HIGH);
  digitalWrite(SD_CS, HIGH);
}

static bool mountSD() {
  busIdle();
  SD.end();
  delay(20);
  if (SD.begin(SD_CS, SPI, SD_SPI_HZ)) {
    Serial.printf("SD ok, type=%u\n", SD.cardType());
    return true;
  }
  Serial.println("SD.begin failed");
  return false;
}

static bool endsWithGif(const char *name) {
  size_t n = strlen(name);
  if (n < 4) return false;
  const char *ext = name + n - 4;
  return (ext[0] == '.' || ext[0] == '.') &&
         (ext[1] == 'g' || ext[1] == 'G') &&
         (ext[2] == 'i' || ext[2] == 'I') &&
         (ext[3] == 'f' || ext[3] == 'F');
}

static bool isMacJunk(const char *name) {
  return name[0] == '.' || (name[0] == '_' && name[1] == '.');
}

static bool scanDirForGif(const char *dirPath, char *out, size_t outLen) {
  File dir = SD.open(dirPath);
  if (!dir || !dir.isDirectory()) {
    if (dir) dir.close();
    return false;
  }
  while (true) {
    File entry = dir.openNextFile();
    if (!entry) break;
    const char *name = entry.name();
    if (!isMacJunk(name) && !entry.isDirectory() && endsWithGif(name)) {
      if (strcmp(dirPath, "/") == 0) {
        snprintf(out, outLen, "/%s", name);
      } else {
        snprintf(out, outLen, "%s/%s", dirPath, name);
      }
      entry.close();
      dir.close();
      return true;
    }
    entry.close();
  }
  dir.close();
  return false;
}

static bool findGifOnCard(char *out, size_t outLen) {
  static const char *candidates[] = {"/gifs/sample.gif", "/sample.gif",
                                     "/gifs/SAMPLE.GIF"};
  for (const char *p : candidates) {
    if (SD.exists(p)) {
      strncpy(out, p, outLen - 1);
      out[outLen - 1] = '\0';
      return true;
    }
  }
  if (scanDirForGif("/gifs", out, outLen)) return true;
  if (scanDirForGif("/", out, outLen)) return true;
  return false;
}

static bool playActiveGif() {
  if (!gif.open(activeGifPath, GIFOpenFile, GIFCloseFile, GIFReadFile, GIFSeekFile,
               GIFDraw)) {
    Serial.printf("gif.open failed: %s\n", activeGifPath);
    return false;
  }

  tft.fillScreen(GC9A01A_BLACK);
  tft.startWrite();
  while (gif.playFrame(true, nullptr)) {
    // frame delay handled by playFrame(true, ...)
  }
  tft.endWrite();
  gif.close();
  busIdle();
  return true;
}

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("gif-player boot");

  pinMode(TFT_CS, OUTPUT);
  pinMode(SD_CS, OUTPUT);
  busIdle();

#if defined(ARDUINO_ADAFRUIT_QTPY_ESP32S3) || defined(ARDUINO_ADAFRUIT_QTPY_ESP32S3_NOPSRAM)
  SPI.begin(SCK, MISO, MOSI);
#else
  SPI.begin();
#endif

  delay(150);

  // SD before display — avoids SPI.end() breaking the TFT after mount.
  if (!mountSD()) {
    tft.begin(TFT_SPI_HZ);
    tft.setRotation(0);
    splash("SD?", GC9A01A_RED);
    while (!mountSD()) delay(1500);
  }

  tft.begin(TFT_SPI_HZ);
  tft.setRotation(0);

#if BOOT_COLOR_TEST
  displaySelfTest();
#endif

  gif.begin(LITTLE_ENDIAN_PIXELS);

  if (!findGifOnCard(activeGifPath, sizeof(activeGifPath))) {
    splash("No GIF", GC9A01A_YELLOW);
    Serial.println("Put a .gif in /gifs/ on the FAT32 card");
  } else {
    Serial.printf("Using %s\n", activeGifPath);
  }
}

void loop() {
  if (activeGifPath[0] == '\0') {
    if (!findGifOnCard(activeGifPath, sizeof(activeGifPath))) {
      splash("No GIF", GC9A01A_YELLOW);
      delay(2000);
      return;
    }
  }

  if (!playActiveGif()) {
    splash("Bad GIF", GC9A01A_MAGENTA);
    delay(2000);
    activeGifPath[0] = '\0';
  }
}
