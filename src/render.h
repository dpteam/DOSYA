/* ===========================================================================
   DOSYA -- render.h
   Software renderer for an indexed 320x200 buffer. No clipping rectangle
   stack, no blitter state, no 4 MB of code: just pixels.
   =========================================================================== */
#ifndef DOSYA_RENDER_H
#define DOSYA_RENDER_H

#include "video.h"

extern const unsigned char g_font[256 * 16];

void r_clear(unsigned char c);
void r_pixel(int x, int y, unsigned char c);
void r_rect(int x0, int y0, int x1, int y1, unsigned char c);
void r_frame(int x0, int y0, int x1, int y1, unsigned char c);
void r_hline(int x0, int x1, int y, unsigned char c);
void r_vline(int x, int y0, int y1, unsigned char c);

void r_sprite(int idx, int x, int y);
void r_sprite_flip(int idx, int x, int y);
void r_sprite_clip(int idx, int x, int y, int clipy0, int clipy1);
void r_tile(int tile, int x, int y);
void r_tile_dim(int tile, int x, int y);

int  r_text(int x, int y, const char *s, unsigned char c);
int  r_text_shadow(int x, int y, const char *s, unsigned char c);
int  r_text_center(int y, const char *s, unsigned char c);
int  r_text_width(const char *s);
void r_text_wrap(int x, int y, int maxw, const char *s, unsigned char c, int lh);

void r_gradient_v(int y0, int y1, int base, int n, int from, int to);
void r_vignette(void);

#endif
