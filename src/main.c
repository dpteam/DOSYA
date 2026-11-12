/* ===========================================================================
   DOSYA -- main.c

   Boot, the frame loop, and the two lines of glue between the platform layer
   and the game.

   The loop runs a fixed 60 Hz logic step driven by the PIT, so a 486 and a
   modern PC play at the same speed. If the machine cannot keep up, the
   accumulator is capped: a stall must not turn into a 40-frame teleport.

   Command line:
     DOSYA.EXE            play
     DOSYA.EXE -test [n]  render n frames with the autopilot and dump PPMs
   =========================================================================== */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "video.h"
#include "render.h"
#include "sound.h"
#include "game.h"

#define STEP_MS 16            /* ~60 Hz */

#ifdef DOSYA_HOST
extern int g_dbg;
#endif

static int g_selftest;
static int g_selftest_frames;

#ifndef DOSYA_HOST
/* Screenshot in PPM, used by -test. PPM because it needs no library at all. */
static void selftest_dump(const char *path)
{
  FILE *f = fopen(path, "wb");
  int i;
  if (!f)
    return;
  fprintf(f, "P6\n%d %d\n255\n", SCREEN_W, SCREEN_H);
  for (i = 0; i < SCREEN_W * SCREEN_H; i++) {
    unsigned char c = g_backbuf[i];
    unsigned char rgb[3];
    rgb[0] = (unsigned char)(g_pal[c * 3 + 0] << 2);
    rgb[1] = (unsigned char)(g_pal[c * 3 + 1] << 2);
    rgb[2] = (unsigned char)(g_pal[c * 3 + 2] << 2);
    fwrite(rgb, 1, 3, f);
  }
  fclose(f);
}
#endif

#ifdef DOSYA_HOST
int main(void)
#else
int main(int argc, char **argv)
#endif
{
  unsigned long last, now;
  unsigned long acc = 0;
  int running = 1;
  int sc;

  vid_init();
  timer_init();
  kbd_init();
  snd_init();

  game_init();

#ifdef DOSYA_HOST
  {
    const char *ap = getenv("DOSYA_AUTOPILOT");
    const char *dbg = getenv("DOSYA_DBG");
    if (ap && *ap == '1')
      game_set_autopilot(1);
    if (dbg)
      g_dbg = atoi(dbg);
  }
#else
  if (argc > 1 && argv[1][0] == '-' && argv[1][1] == 't') {
    g_selftest = 1;
    g_selftest_frames = (argc > 2) ? atoi(argv[2]) : 240;
    game_set_autopilot(1);
    game_key(K_SPACE);
    game_key(K_SPACE);
  }
#endif

  last = timer_ticks();
  acc = 0;

  while (running) {
    now = timer_ticks();
    acc += now - last;
    last = now;

    if (acc > 120)
      acc = 120;

    while (acc >= STEP_MS) {
      acc -= STEP_MS;

      while ((sc = kbd_pop()) != 0) {
        if (sc == K_ESC) {
          running = 0;
        } else {
          game_key(sc);
        }
      }
      if (game_state() == ST_PLAY) {
        int jump_now = kbd_held(K_SPACE);
        static int jump_prev;
        game_set_input(kbd_held(K_LEFT) || kbd_held(K_A),
                       kbd_held(K_RIGHT) || kbd_held(K_D),
                       jump_now && !jump_prev,
                       jump_now);
        jump_prev = jump_now;
      }

      game_tick();
      snd_tick(timer_ticks());

      if (g_selftest && --g_selftest_frames <= 0)
        running = 0;
    }

    game_render();
    vid_present();

#ifndef DOSYA_HOST
    if (g_selftest) {
      static int n;
      if ((n++ % 20) == 0) {
        char path[32];
        sprintf(path, "SHOT%03d.PPM", n / 20);
        selftest_dump(path);
      }
    }
#endif
  }

  snd_off();
  snd_done();
  kbd_done();
  timer_done();
  vid_shutdown();
  return 0;
}
