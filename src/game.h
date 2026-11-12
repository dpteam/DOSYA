/* ===========================================================================
   DOSYA -- game.h
   =========================================================================== */
#ifndef DOSYA_GAME_H
#define DOSYA_GAME_H

#define TILE_SOLID 1
#define TILE_ONEWAY 2
#define TILE_WATER 4
#define TILE_SPIKE 8

/* tile indices, matching tools/gen_tiles.py order */
enum {
  T_EMPTY = 0, T_DIRT, T_GRASS_TOP, T_GRASS, T_BRICK, T_WOOD, T_FENCE,
  T_WATER, T_SPIKES, T_HAY, T_ROOF, T_STONE, T_PLATFORM,
  T_LOG_END, T_PLASTER, T_WINDOW, T_DOOR
};

typedef struct {
  int x, y;            /* top-left, in pixels */
  int w, h;
} Rect;

typedef enum {
  ST_TITLE, ST_INTRO, ST_PLAY, ST_DEAD, ST_LEVEL_DONE, ST_WIN, ST_GAMEOVER
} State;

/* why Dosya died, so the obituary matches the accident */
enum { DIE_WATER = 0, DIE_FALL, DIE_SPIKE, DIE_ENEMY };

void game_init(void);
void game_tick(void);
void game_render(void);
int  game_state(void);
void game_key(int sc);
void game_set_input(int left, int right, int jump_pressed, int jump_held);
void game_set_autopilot(int on);

#endif
