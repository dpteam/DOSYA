/* ===========================================================================
   DOSYA -- video.h
   Platform layer: 320x200x256 framebuffer, 1 kHz timer, raw scancodes.
   =========================================================================== */
#ifndef DOSYA_VIDEO_H
#define DOSYA_VIDEO_H

#include "assets.h"

#define SCREEN_W 320
#define SCREEN_H 200
#define PLAY_H   176          /* playfield height; the rest is the status bar */
#define TICK_HZ  1000

extern unsigned char *g_backbuf;

void vid_init(void);
void vid_shutdown(void);
void vid_setpal(const unsigned char *rgb6);
void vid_present(void);
void vid_waitvsync(void);
void vid_fade(int level);          /* 0 = black, 16 = full */

void timer_init(void);
void timer_done(void);
unsigned long timer_ticks(void);

void kbd_init(void);
void kbd_done(void);
int  kbd_pop(void);                /* scancode of the next press, or 0 */
int  kbd_held(int sc);             /* is that key currently down? */
void kbd_flush(void);

/* set 1 scancodes we actually use */
#define K_ESC    0x01
#define K_1      0x02
#define K_2      0x03
#define K_3      0x04
#define K_TAB    0x0F
#define K_Q      0x10
#define K_W      0x11
#define K_E      0x12
#define K_R      0x13
#define K_ENTER  0x1C
#define K_CTRL   0x1D
#define K_A      0x1E
#define K_S      0x1F
#define K_D      0x20
#define K_F      0x21
#define K_P      0x19
#define K_Z      0x2C
#define K_SPACE  0x39
#define K_F1     0x3B
#define K_F2     0x3C
#define K_F10    0x44
#define K_UP     0x48
#define K_LEFT   0x4B
#define K_RIGHT  0x4D
#define K_DOWN   0x50
#define K_X      0x2D

#endif
