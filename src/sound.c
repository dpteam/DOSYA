/* ===========================================================================
   DOSYA -- sound.c
   Square waves through the PC speaker, driven by PIT channel 2. It sounds
   like a fridge with opinions, which is exactly the era we are imitating.
   =========================================================================== */
#include "sound.h"
#include "video.h"

#ifdef DOSYA_HOST
/* No hardware, no sound. The host build exists to test logic, not to buzz. */
void snd_init(void) {}
void snd_done(void) {}
void snd_play(int id) { (void)id; }
void snd_tick(unsigned long now_ms) { (void)now_ms; }
void snd_off(void) {}
#else

/* <dos.h> lives here, not at the top of the file: MinGW quietly provides a
   stub header so an unconditional include builds on Windows, but a Linux
   host has no <dos.h> at all and the host build dies. Ask me how I know. */
#include <dos.h>

#define SPK_PORT  0x61
#define PIT2_CMD  0x43
#define PIT2_CH2  0x42
#define PIT_HZ    1193182UL

typedef struct {
  unsigned int freq;
  unsigned int dur;      /* ms */
} Note;

/* Each effect is a tiny note list. Kept short: a beep is a beep. */
static const Note fx_jump[]  = { {520, 40}, {700, 30}, {0, 0} };
static const Note fx_pick[]  = { {880, 35}, {1180, 55}, {0, 0} };
static const Note fx_stomp[] = { {300, 30}, {180, 60}, {0, 0} };
static const Note fx_hurt[]  = { {220, 60}, {160, 80}, {0, 0} };
static const Note fx_throw[] = { {420, 25}, {300, 25}, {0, 0} };
static const Note fx_die[]   = { {400, 70}, {320, 70}, {240, 70}, {160, 140}, {0, 0} };
static const Note fx_win[]   = { {523, 90}, {659, 90}, {784, 90}, {1046, 180}, {0, 0} };
static const Note fx_sel[]   = { {660, 30}, {0, 0} };

static const Note *cur;
static int cur_i;
static unsigned long next_at;

static void spk_on(void)
{
  outportb(SPK_PORT, inportb(SPK_PORT) | 3);
}

static void spk_gate(int on)
{
  unsigned char v = inportb(SPK_PORT);
  if (on)
    v |= 3;
  else
    v &= (unsigned char)~3;
  outportb(SPK_PORT, v);
}

static void tone(unsigned int hz)
{
  unsigned long div;
  if (!hz) {
    spk_gate(0);
    return;
  }
  div = PIT_HZ / hz;
  outportb(PIT2_CMD, 0xB6);
  outportb(PIT2_CH2, (unsigned char)(div & 0xFF));
  outportb(PIT2_CH2, (unsigned char)((div >> 8) & 0xFF));
  spk_on();
}

void snd_init(void)
{
  spk_gate(0);
  cur = 0;
}

void snd_done(void)
{
  spk_gate(0);
}

void snd_off(void)
{
  spk_gate(0);
  cur = 0;
}

void snd_play(int id)
{
  switch (id) {
    case SFX_JUMP:   cur = fx_jump;  break;
    case SFX_PICKUP: cur = fx_pick;  break;
    case SFX_STOMP:  cur = fx_stomp; break;
    case SFX_HURT:   cur = fx_hurt;  break;
    case SFX_THROW:  cur = fx_throw; break;
    case SFX_DIE:    cur = fx_die;   break;
    case SFX_WIN:    cur = fx_win;   break;
    case SFX_SELECT: cur = fx_sel;   break;
    default: return;
  }
  cur_i = 0;
  next_at = 0;                     /* fire on the next tick */
}

void snd_tick(unsigned long now_ms)
{
  if (!cur)
    return;
  if (now_ms < next_at)
    return;
  if (cur[cur_i].freq == 0) {
    spk_gate(0);
    cur = 0;
    return;
  }
  tone(cur[cur_i].freq);
  next_at = now_ms + cur[cur_i].dur;
  cur_i++;
}

#endif
