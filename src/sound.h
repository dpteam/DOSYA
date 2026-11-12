/* ===========================================================================
   DOSYA -- sound.h
   PC speaker. Not a Sound Blaster. A 1981 buzzer with one bit of output.
   =========================================================================== */
#ifndef DOSYA_SOUND_H
#define DOSYA_SOUND_H

enum {
  SFX_NONE = 0,
  SFX_JUMP,
  SFX_PICKUP,
  SFX_STOMP,
  SFX_HURT,
  SFX_THROW,
  SFX_DIE,
  SFX_WIN,
  SFX_SELECT,
  SFX_COUNT
};

void snd_init(void);
void snd_done(void);
void snd_play(int id);
void snd_tick(unsigned long now_ms);   /* call every frame */
void snd_off(void);

#endif
