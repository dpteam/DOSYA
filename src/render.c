/* ===========================================================================
   DOSYA -- render.c
   =========================================================================== */
#include <string.h>

#include "render.h"
#include "pal.h"

void r_clear(unsigned char c)
{
  memset(g_backbuf, c, SCREEN_W * SCREEN_H);
}

void r_pixel(int x, int y, unsigned char c)
{
  if ((unsigned)x < (unsigned)SCREEN_W && (unsigned)y < (unsigned)SCREEN_H)
    g_backbuf[y * SCREEN_W + x] = c;
}

void r_hline(int x0, int x1, int y, unsigned char c)
{
  unsigned char *p;
  if ((unsigned)y < 0 || y >= SCREEN_H)
    return;
  if (x0 < 0) x0 = 0;
  if (x1 >= SCREEN_W) x1 = SCREEN_W - 1;
  if (x0 > x1)
    return;
  p = g_backbuf + y * SCREEN_W + x0;
  memset(p, c, (size_t)(x1 - x0 + 1));
}

void r_vline(int x, int y0, int y1, unsigned char c)
{
  unsigned char *p;
  if ((unsigned)x < 0 || x >= SCREEN_W)
    return;
  if (y0 < 0) y0 = 0;
  if (y1 >= SCREEN_H) y1 = SCREEN_H - 1;
  if (y0 > y1)
    return;
  p = g_backbuf + y0 * SCREEN_W + x;
  while (y0++ <= y1) {
    *p = c;
    p += SCREEN_W;
  }
}

void r_rect(int x0, int y0, int x1, int y1, unsigned char c)
{
  int y;
  if (y0 < 0) y0 = 0;
  if (y1 >= SCREEN_H) y1 = SCREEN_H - 1;
  for (y = y0; y <= y1; y++)
    r_hline(x0, x1, y, c);
}

void r_frame(int x0, int y0, int x1, int y1, unsigned char c)
{
  r_hline(x0, x1, y0, c);
  r_hline(x0, x1, y1, c);
  r_vline(x0, y0, y1, c);
  r_vline(x1, y0, y1, c);
}

/* --- sprites ------------------------------------------------------------- */

static void blit(const unsigned char *px, int w, int h, int x, int y,
                 int clipy0, int clipy1, int flip)
{
  int sy0 = 0, sy1 = h - 1;
  int dy, dx;
  if (y < clipy0) { sy0 = clipy0 - y; }
  if (y + h - 1 > clipy1) { sy1 = clipy1 - y; }
  if (sy0 > sy1)
    return;

  for (dy = sy0; dy <= sy1; dy++) {
    int py = y + dy;
    unsigned char *dst;
    const unsigned char *src;
    if ((unsigned)py >= SCREEN_H)
      continue;
    dst = g_backbuf + py * SCREEN_W;
    src = px + dy * w;
    if (!flip) {
      for (dx = 0; dx < w; dx++) {
        unsigned char c = src[dx];
        int px_ = x + dx;
        if (c && (unsigned)px_ < SCREEN_W)
          dst[px_] = c;
      }
    } else {
      for (dx = 0; dx < w; dx++) {
        unsigned char c = src[w - 1 - dx];
        int px_ = x + dx;
        if (c && (unsigned)px_ < SCREEN_W)
          dst[px_] = c;
      }
    }
  }
}

void r_sprite(int idx, int x, int y)
{
  const Sprite *s = &g_sprites[idx];
  blit(s->px, s->w, s->h, x, y, 0, SCREEN_H - 1, 0);
}

void r_sprite_flip(int idx, int x, int y)
{
  const Sprite *s = &g_sprites[idx];
  blit(s->px, s->w, s->h, x, y, 0, SCREEN_H - 1, 1);
}

void r_sprite_clip(int idx, int x, int y, int clipy0, int clipy1)
{
  const Sprite *s = &g_sprites[idx];
  blit(s->px, s->w, s->h, x, y, clipy0, clipy1, 0);
}

void r_tile(int tile, int x, int y)
{
  const unsigned char *px;
  int dy, dx;
  if ((unsigned)tile >= NTILES)
    return;
  px = g_tiles + (unsigned)tile * TILE_W * TILE_H;
  for (dy = 0; dy < TILE_H; dy++) {
    int py = y + dy;
    unsigned char *dst;
    const unsigned char *src;
    if ((unsigned)py >= SCREEN_H)
      continue;
    dst = g_backbuf + py * SCREEN_W;
    src = px + dy * TILE_W;
    for (dx = 0; dx < TILE_W; dx++) {
      unsigned char c = src[dx];
      int pxx = x + dx;
      if (c && (unsigned)pxx < SCREEN_W)
        dst[pxx] = c;
    }
  }
}

/* Same tile, one ramp darker: used for the background decor layer so houses
   read as "behind" without needing a second art set. */
void r_tile_dim(int tile, int x, int y)
{
  const unsigned char *px;
  int dy, dx;
  if ((unsigned)tile >= NTILES)
    return;
  px = g_tiles_dim + (unsigned)tile * TILE_W * TILE_H;
  for (dy = 0; dy < TILE_H; dy++) {
    int py = y + dy;
    unsigned char *dst;
    const unsigned char *src;
    if ((unsigned)py >= SCREEN_H)
      continue;
    dst = g_backbuf + py * SCREEN_W;
    src = px + dy * TILE_W;
    for (dx = 0; dx < TILE_W; dx++) {
      unsigned char c = src[dx];
      int pxx = x + dx;
      if (c && (unsigned)pxx < SCREEN_W)
        dst[pxx] = c;
    }
  }
}

/* --- text ---------------------------------------------------------------- */

int r_text_width(const char *s)
{
  return (int)strlen(s) * 8;
}

int r_text(int x, int y, const char *s, unsigned char c)
{
  int cx = x;
  while (*s) {
    const unsigned char *g = g_font + (unsigned char)*s * 16;
    int gy;
    for (gy = 0; gy < 16; gy++) {
      unsigned char bits = g[gy];
      int gx;
      if (!bits)
        continue;
      for (gx = 0; gx < 8; gx++)
        if (bits & (0x80 >> gx))
          r_pixel(cx + gx, y + gy, c);
    }
    cx += 8;
    s++;
  }
  return cx;
}

int r_text_shadow(int x, int y, const char *s, unsigned char c)
{
  r_text(x + 1, y + 1, s, PAL_SHADOW);
  return r_text(x, y, s, c);
}

int r_text_center(int y, const char *s, unsigned char c)
{
  int x = (SCREEN_W - r_text_width(s)) / 2;
  if (x < 0)
    x = 0;
  return r_text(x, y, s, c);
}

void r_text_wrap(int x, int y, int maxw, const char *s, unsigned char c, int lh)
{
  char line[128];
  int n = 0;
  int cx = 0;
  const char *p = s;
  while (*p) {
    const char *word = p;
    int wlen = 0;
    while (*p && *p != ' ') { p++; wlen++; }
    if (cx && (cx + 1 + wlen) * 8 > maxw) {
      line[n] = 0;
      r_text(x, y, line, c);
      y += lh;
      n = 0;
      cx = 0;
    }
    if (n && cx) {
      line[n++] = ' ';
      cx++;
    }
    memcpy(line + n, word, (size_t)wlen);
    n += wlen;
    cx += wlen;
    if (*p == ' ')
      p++;
  }
  line[n] = 0;
  r_text(x, y, line, c);
}

/* --- background helpers -------------------------------------------------- */

/* Vertical gradient inside one palette ramp.

   Interpolating palette *indices* across ramps is a trap: index 120 -> 40
   walks through every ramp in between and paints a rainbow. So a gradient
   always names a ramp and two steps inside it. */
void r_gradient_v(int y0, int y1, int base, int n, int from, int to)
{
  int y;
  if (y1 <= y0)
    return;
  for (y = y0; y <= y1; y++) {
    int step = from + (to - from) * (y - y0) / (y1 - y0);
    if (step < 0) step = 0;
    if (step >= n) step = n - 1;
    r_hline(0, SCREEN_W - 1, y, (unsigned char)(base + step));
  }
}

void r_vignette(void)
{
  int y;
  for (y = 0; y < SCREEN_H; y++) {
    int d = (y < SCREEN_H / 2) ? y : (SCREEN_H - 1 - y);
    if (d < 3) {
      unsigned char c = PAL_VOID1;
      r_hline(0, SCREEN_W - 1, y, c);
    }
  }
}
