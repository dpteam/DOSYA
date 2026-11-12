/* ===========================================================================
   DOSYA -- game.c

   A 320x200 platformer. Everything is fixed point, everything is integers,
   nothing allocates after startup. The whole game state is about 40 KB,
   which is what we have instead of a design document.

   Units: positions and velocities are 8.8 fixed point (256 = 1 pixel),
   so `x >> 8` is the pixel coordinate.
   =========================================================================== */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "game.h"
#include "video.h"
#include "render.h"
#include "sound.h"
#include "pal.h"
#include "strings.h"
#include "levels.h"

#define FX 256
#define TOFX(px)     ((px) * FX)
#define TOPX(v)      ((v) >> 8)

/* ---- physics ------------------------------------------------------------
   Tuned so a jump clears three tiles and a full run jumps about four and a
   half. Numbers are 8.8 fixed point; 256 = one pixel. */
#define GRAV        118       /* px/frame^2 while falling */
#define GRAV_HOLD    92       /* ...while rising with the button held */
#define JUMP_V     (-1700)
#define RUN_ACC     130
#define RUN_MAX     700
#define AIR_ACC     110
#define FRICTION    160
#define MAX_FALL    1150
#define RUN_MAX_DRUNK 880

/* ---- tile flags ---------------------------------------------------------
   Fence and hay are scenery: they are drawn but you walk in front of them.
   Making them solid turns a pretty village into a maze of invisible walls,
   which is a mistake I already made once today. */
static const unsigned char tile_flags[NTILES] = {
  0,                                          /* empty   */
  TILE_SOLID,                                 /* dirt    */
  TILE_SOLID,                                 /* grass   */
  TILE_SOLID,                                 /* grass2  */
  TILE_SOLID,                                 /* brick   */
  TILE_SOLID,                                 /* wood    */
  0,                                          /* fence   */
  TILE_WATER,                                 /* water   */
  TILE_SPIKE,                                 /* spikes  */
  0,                                          /* hay     */
  TILE_SOLID,                                 /* roof    */
  TILE_SOLID,                                 /* stone   */
  TILE_ONEWAY,                                /* platform*/
  TILE_SOLID,                                 /* log_end */
  TILE_SOLID,                                 /* plaster */
  TILE_SOLID,                                 /* window  */
  TILE_SOLID                                  /* door    */
};

/* ---- entity types ------------------------------------------------------- */
enum {
  E_NONE = 0, E_CHICKEN, E_ROOSTER, E_GOAT, E_DED, E_TRACTOR,
  E_MILK, E_EGG, E_MANURE, E_SAMOGON, E_BUS, E_THROWN, E_POOF
};

#define MAX_ENT 96

typedef struct {
  int type;
  int x, y, vx, vy;
  int w, h;
  int alive;
  int face;
  int t;            /* generic timer / animation phase */
  int hp;
  int home_x, home_y;
  int anim;
} Ent;

/* ---- globals ------------------------------------------------------------ */
static State g_state;
static int g_state_t;                 /* frames spent in current state */
static unsigned char *g_map;          /* w*h foreground tiles (collide) */
static unsigned char *g_bg;           /* w*h background tiles (decor only) */
static int g_w, g_h;
static int g_level;                   /* 0-based */
static int g_lives, g_hearts, g_score, g_milk, g_ammo;
static int g_invuln;                  /* frames of invulnerability left */
static int g_drunk;                   /* frames of samogon left */
static int g_paused;
static int g_death_msg;
static int g_death_cause;

static Ent g_ent[MAX_ENT];
static int g_nent;

typedef struct {
  int x, y, vx, vy;
  int on_ground;
  int face;
  int anim;
  int coyote;
  int jump_held;
} Player;

static Player g_pl;

static int g_cam_x, g_cam_y;
static int g_shake;
static unsigned long g_rng = 12345;

/* input, pushed in once per frame by main() */
static int g_left, g_right, g_jump_pressed, g_jump_held;

static int rnd(void)
{
  g_rng = g_rng * 1103515245UL + 12345UL;
  return (int)((g_rng >> 16) & 0x7FFF);
}

/* =========================================================================
   map helpers
   ========================================================================= */
static int tile_at(int tx, int ty)
{
  if (tx < 0 || tx >= g_w || ty < 0 || ty >= g_h)
    return T_EMPTY;
  return g_map[ty * g_w + tx];
}

static int char_to_tile(char c)
{
  switch (c) {
    case '#': return T_DIRT;
    case '=': return T_GRASS_TOP;
    case '%': return T_GRASS;
    case 'B': return T_BRICK;
    case 'W': return T_WOOD;
    case 'F': return T_FENCE;
    case '~': return T_WATER;
    case '^': return T_SPIKES;
    case 'H': return T_HAY;
    case 'R': return T_ROOF;
    case 'S': return T_STONE;
    case '-': return T_PLATFORM;
    default:  return T_EMPTY;
  }
}

static int char_to_ent(char c)
{
  switch (c) {
    case 'c': return E_CHICKEN;
    case 'r': return E_ROOSTER;
    case 'o': return E_GOAT;
    case 'd': return E_DED;
    case 't': return E_TRACTOR;
    case 'm': return E_MILK;
    case 'e': return E_EGG;
    case 'n': return E_MANURE;
    case 'v': return E_SAMOGON;
    case 'X': return E_BUS;
    default:  return E_NONE;
  }
}

/* Digits are background decoration: drawn behind everything, never collided
   with. This is how the village gets houses without becoming a maze. */
static int char_to_bg(char c)
{
  switch (c) {
    case '1': return T_WOOD;      /* log wall */
    case '2': return T_ROOF;      /* thatch */
    case '3': return T_FENCE;
    case '4': return T_HAY;
    case '5': return T_PLASTER;   /* whitewashed wall */
    case '6': return T_STONE;
    case '7': return T_WINDOW;
    case '8': return T_DOOR;
    case '9': return T_LOG_END;
    default:  return T_EMPTY;
  }
}

/* pixel box vs solid tiles */
static int box_hard(int x, int y, int w, int h)
{
  int tx0 = x >> 4, tx1 = (x + w - 1) >> 4;
  int ty0 = y >> 4, ty1 = (y + h - 1) >> 4;
  int tx, ty;
  for (ty = ty0; ty <= ty1; ty++)
    for (tx = tx0; tx <= tx1; tx++)
      if (tile_flags[tile_at(tx, ty)] & TILE_SOLID)
        return 1;
  return 0;
}

/* pixel box vs solid tiles + one-way platforms whose top is at or below
   prev_bottom (so we only land on them from above) */
static int box_down(int x, int y, int w, int h, int prev_bottom)
{
  int tx0 = x >> 4, tx1 = (x + w - 1) >> 4;
  int ty0 = y >> 4, ty1 = (y + h - 1) >> 4;
  int tx, ty;
  for (ty = ty0; ty <= ty1; ty++)
    for (tx = tx0; tx <= tx1; tx++) {
      int f = tile_flags[tile_at(tx, ty)];
      if (f & TILE_SOLID)
        return 1;
      if ((f & TILE_ONEWAY) && prev_bottom <= (ty << 4))
        return 1;
    }
  return 0;
}

static int box_tile_flag(int x, int y, int w, int h, int flag)
{
  int tx0 = x >> 4, tx1 = (x + w - 1) >> 4;
  int ty0 = y >> 4, ty1 = (y + h - 1) >> 4;
  int tx, ty;
  for (ty = ty0; ty <= ty1; ty++)
    for (tx = tx0; tx <= tx1; tx++)
      if (tile_flags[tile_at(tx, ty)] & flag)
        return 1;
  return 0;
}

/* =========================================================================
   entity helpers
   ========================================================================= */
static void ent_clear(void)
{
  memset(g_ent, 0, sizeof(g_ent));
  g_nent = 0;
}

static Ent *ent_new(int type, int x, int y)
{
  Ent *e;
  if (g_nent >= MAX_ENT)
    return 0;
  e = &g_ent[g_nent++];
  memset(e, 0, sizeof(*e));
  e->type = type;
  e->x = TOFX(x);
  e->y = TOFX(y);
  e->alive = 1;
  e->face = -1;
  e->hp = 1;
  e->home_x = e->x;
  e->home_y = e->y;
  switch (type) {
    case E_CHICKEN:  e->w = 12; e->h = 12; break;
    case E_ROOSTER:  e->w = 14; e->h = 14; break;
    case E_GOAT:     e->w = 20; e->h = 12; break;
    case E_DED:      e->w = 12; e->h = 19; e->hp = 2; break;
    case E_TRACTOR:  e->w = 30; e->h = 14; break;
    case E_MILK:     e->w = 8;  e->h = 10; break;
    case E_EGG:      e->w = 8;  e->h = 9;  break;
    case E_MANURE:   e->w = 10; e->h = 8;  break;
    case E_SAMOGON:  e->w = 8;  e->h = 10; break;
    case E_BUS:      e->w = 28; e->h = 40; break;
    case E_THROWN:   e->w = 6;  e->h = 6;  break;
    case E_POOF:     e->w = 6;  e->h = 6;  break;
  }
  /* centre the hitbox on the cell */
  e->x = TOFX(x + 8 - e->w / 2);
  e->y = TOFX(y + 16 - e->h);
  e->home_x = e->x;
  e->home_y = e->y;
  return e;
}

static int is_enemy(const Ent *e)
{
  return e->type == E_CHICKEN || e->type == E_ROOSTER || e->type == E_GOAT ||
         e->type == E_DED || e->type == E_TRACTOR;
}

static int is_item(const Ent *e)
{
  return e->type == E_MILK || e->type == E_EGG || e->type == E_MANURE ||
         e->type == E_SAMOGON;
}

static int boxes_overlap(int ax, int ay, int aw, int ah,
                         int bx, int by, int bw, int bh)
{
  return ax < bx + bw && ax + aw > bx && ay < by + bh && ay + ah > by;
}

/* =========================================================================
   level loading
   ========================================================================= */
static void load_level(int idx)
{
  const LevelDef *ld = &g_levels[idx];
  int y, x;
  char c;

  g_level = idx;
  g_w = ld->w;
  g_h = ld->h;
  if (g_map)
    free(g_map);
  if (g_bg)
    free(g_bg);
  g_map = (unsigned char *)malloc((size_t)(g_w * g_h));
  g_bg = (unsigned char *)malloc((size_t)(g_w * g_h));
  memset(g_map, 0, (size_t)(g_w * g_h));
  memset(g_bg, 0, (size_t)(g_w * g_h));

  ent_clear();
  g_pl.x = TOFX(32);
  g_pl.y = TOFX(32);
  g_pl.vx = g_pl.vy = 0;
  g_pl.face = 1;
  g_pl.anim = 0;
  g_pl.on_ground = 0;
  g_pl.coyote = 0;
  g_pl.jump_held = 0;

  for (y = 0; y < g_h; y++) {
    const char *row = ld->rows[y];
    for (x = 0; x < g_w; x++) {
      int e;
      c = row[x];
      if (!c)
        break;
      {
        int bg = char_to_bg(c);
        if (bg != T_EMPTY) {
          g_bg[y * g_w + x] = (unsigned char)bg;
          continue;
        }
      }
      g_map[y * g_w + x] = (unsigned char)char_to_tile(c);
      if (c == 'P') {
        g_map[y * g_w + x] = T_EMPTY;
        g_pl.x = TOFX(x * 16 + 3);
        g_pl.y = TOFX(y * 16 + 16 - 22);
        continue;
      }
      e = char_to_ent(c);
      if (e == E_NONE)
        continue;
      g_map[y * g_w + x] = T_EMPTY;
      ent_new(e, x * 16, y * 16);
    }
  }
  g_cam_x = 0;
  g_cam_y = 0;
  /* Snap the camera to where it belongs on frame one. Without this the level
     starts with the ground below the screen and Dosya runs on air for a
     second, which looks like a bug because it is one. */
  {
    int max_y = g_h * 16 - PLAY_H;
    int max_x = g_w * 16 - SCREEN_W;
    if (max_y < 0) max_y = 0;
    if (max_x < 0) max_x = 0;
    g_cam_x = TOPX(g_pl.x) + 5 - SCREEN_W / 2;
    g_cam_y = TOPX(g_pl.y) + 11 - PLAY_H / 2;
    if (g_cam_x < 0) g_cam_x = 0;
    if (g_cam_x > max_x) g_cam_x = max_x;
    if (g_cam_y < 0) g_cam_y = 0;
    if (g_cam_y > max_y) g_cam_y = max_y;
  }
  g_invuln = 60;
  g_drunk = 0;
}

/* =========================================================================
   player
   ========================================================================= */
static void player_die(int cause)
{
  int n = 0;
  const char **list = g_die_lists[cause & 3];
  while (list[n])
    n++;
  g_death_msg = rnd() % (n ? n : 1);
  g_death_cause = cause & 3;
  g_state = ST_DEAD;
  g_state_t = 0;
  snd_play(SFX_DIE);
  g_hearts = 0;
}

static void hurt_player(void)
{
  if (g_invuln > 0 || g_drunk > 0)
    return;
  g_hearts--;
  g_invuln = 90;
  g_shake = 8;
  /* Knock her back and up. Without this she just stands inside whatever is
     killing her, losing every heart in three seconds. */
  g_pl.vy = -900;
  g_pl.vx = -g_pl.face * 420;
  g_pl.on_ground = 0;
  snd_play(SFX_HURT);
  if (g_hearts <= 0)
    player_die(DIE_ENEMY);
}

static void move_x(Ent *e, int dx, int hard_only)
{
  int sign = dx > 0 ? 1 : -1;
  int rem = dx * sign;
  while (rem > 0) {
    int s = rem > FX ? FX : rem;
    int nx = e->x + sign * s;
    if ((hard_only ? box_hard(TOPX(nx), TOPX(e->y), e->w, e->h)
                   : box_down(TOPX(nx), TOPX(e->y), e->w, e->h, 1 << 20))) {
      e->vx = 0;
      return;
    }
    e->x = nx;
    rem -= s;
  }
}

/* returns 1 if it landed */
static int move_y(Ent *e)
{
  int sign = e->vy > 0 ? 1 : -1;
  int rem = e->vy * sign;
  while (rem > 0) {
    int s = rem > FX ? FX : rem;
    int ny = e->y + sign * s;
    int prev_bottom = TOPX(e->y) + e->h;
    int blocked;
    if (sign > 0)
      blocked = box_down(TOPX(e->x), TOPX(ny), e->w, e->h, prev_bottom);
    else
      blocked = box_hard(TOPX(e->x), TOPX(ny), e->w, e->h);
    if (blocked) {
      e->vy = 0;
      return sign > 0;
    }
    e->y = ny;
    rem -= s;
  }
  return 0;
}

static void update_player(void)
{
  Player *p = &g_pl;
  int maxrun = (g_drunk > 0) ? RUN_MAX_DRUNK : RUN_MAX;

  /* horizontal input */
  if (g_left) {
    p->vx -= RUN_ACC;
    if (p->vx < -maxrun) p->vx = -maxrun;
    p->face = -1;
  } else if (g_right) {
    p->vx += RUN_ACC;
    if (p->vx > maxrun) p->vx = maxrun;
    p->face = 1;
  } else {
    if (p->vx > FRICTION) p->vx -= FRICTION;
    else if (p->vx < -FRICTION) p->vx += FRICTION;
    else p->vx = 0;
  }

  /* jump: buffered by coyote time, cut short on release */
  if (p->on_ground)
    p->coyote = 6;
  else if (p->coyote > 0)
    p->coyote--;

  if (g_jump_pressed && p->coyote > 0) {
    p->vy = JUMP_V;
    p->on_ground = 0;
    p->coyote = 0;
    snd_play(SFX_JUMP);
  }
  g_jump_pressed = 0;

  p->vy += (g_jump_held && p->vy < 0) ? GRAV_HOLD : GRAV;
  if (p->vy > MAX_FALL)
    p->vy = MAX_FALL;

  /* move */
  {
    Ent tmp;
    memset(&tmp, 0, sizeof(tmp));
    tmp.x = p->x; tmp.y = p->y; tmp.w = 10; tmp.h = 22;
    tmp.vx = p->vx; tmp.vy = p->vy;
    move_x(&tmp, tmp.vx, 0);
    p->x = tmp.x;
    p->vx = tmp.vx;
    tmp.vy = p->vy;
    p->on_ground = move_y(&tmp);
    p->y = tmp.y;
    p->vy = tmp.vy;
  }

  /* animation */
  if (!p->on_ground)
    p->anim = 0;
  else if (p->vx != 0)
    p->anim++;
  else
    p->anim = 0;

  /* hazards */
  {
    int px = TOPX(p->x), py = TOPX(p->y);
    if (box_tile_flag(px + 2, py + 4, 6, 18, TILE_WATER))
      player_die(DIE_WATER);
    else if (box_tile_flag(px + 1, py + 16, 8, 6, TILE_SPIKE))
      player_die(DIE_SPIKE);
    if (py > g_h * 16 + 40)
      player_die(DIE_FALL);
  }
}

/* =========================================================================
   entities
   ========================================================================= */
static void enemy_walk(Ent *e, int speed, int can_fall)
{
  int ny;
  e->vx = e->face * speed;
  {
    Ent tmp = *e;
    move_x(&tmp, tmp.vx, 0);
    if (tmp.vx == 0)
      e->face = -e->face;
    else
      e->x = tmp.x;
  }
  e->vy += GRAV;
  if (e->vy > MAX_FALL) e->vy = MAX_FALL;
  ny = e->y;
  {
    Ent tmp = *e;
    tmp.vy = e->vy;
    move_y(&tmp);
    e->y = tmp.y;
    e->vy = tmp.vy;
  }
  if (!can_fall) {
    /* turn around at ledges: probe one pixel ahead and below */
    int probe_x = TOPX(e->x) + (e->face > 0 ? e->w + 1 : -2);
    int probe_y = TOPX(e->y) + e->h + 2;
    int t = tile_at(probe_x >> 4, probe_y >> 4);
    if (!(tile_flags[t] & (TILE_SOLID | TILE_ONEWAY)))
      e->face = -e->face;
  }
  (void)ny;
}

static void spawn_poof(int x, int y)
{
  Ent *e = ent_new(E_POOF, 0, 0);
  if (!e) return;
  e->x = TOFX(x);
  e->y = TOFX(y);
  e->t = 12;
}

static void kill_enemy(Ent *e)
{
  e->alive = 0;
  spawn_poof(TOPX(e->x) + e->w / 2, TOPX(e->y) + e->h / 2);
}

static void update_ents(void)
{
  int i;
  int px = TOPX(g_pl.x), py = TOPX(g_pl.y);

  for (i = 0; i < g_nent; i++) {
    Ent *e = &g_ent[i];
    int ex;
    if (!e->alive)
      continue;
    ex = TOPX(e->x);

    switch (e->type) {
      case E_CHICKEN:
        enemy_walk(e, 60, 0);
        e->t++;
        break;
      case E_ROOSTER:
        enemy_walk(e, 120, 0);
        e->t++;
        if (e->t % 70 == 0 && e->vy == 0) {
          e->vy = -1500;
          snd_play(SFX_JUMP);
        }
        break;
      case E_GOAT:
        enemy_walk(e, (e->t > 0 && abs(ex - px) < 90) ? 170 : 70, 0);
        e->t = 1;
        break;
      case E_DED:
        enemy_walk(e, 40, 0);
        e->t++;
        break;
      case E_TRACTOR:
        e->vx = e->face * 230;
        {
          Ent tmp = *e;
          move_x(&tmp, tmp.vx, 1);
          if (tmp.vx == 0) e->face = -e->face;
          else e->x = tmp.x;
        }
        e->vy += GRAV;
        if (e->vy > MAX_FALL) e->vy = MAX_FALL;
        {
          Ent tmp = *e;
          tmp.vy = e->vy;
          move_y(&tmp);
          e->y = tmp.y;
          e->vy = tmp.vy;
        }
        e->t++;
        break;
      case E_THROWN:
        e->vy += GRAV;
        move_x(e, e->vx, 1);
        {
          Ent tmp = *e;
          tmp.vy = e->vy;
          if (move_y(&tmp)) { e->alive = 0; break; }
          e->y = tmp.y;
        }
        if (e->x < 0 || TOPX(e->x) > g_w * 16)
          e->alive = 0;
        e->t++;
        break;
      case E_POOF:
        if (--e->t <= 0)
          e->alive = 0;
        break;
      case E_BUS:
        break;
      default:
        break;
    }

    /* ---- collision with the player ---- */
    if (is_item(e)) {
      if (boxes_overlap(px, py, 10, 22, TOPX(e->x), TOPX(e->y), e->w, e->h)) {
        e->alive = 0;
        snd_play(SFX_PICKUP);
        switch (e->type) {
          case E_MILK:    g_milk++;  g_score += 100; break;
          case E_EGG:     g_score += 250; break;
          case E_MANURE:  g_ammo += 3; break;
          case E_SAMOGON: g_drunk = 420; g_score += 50; break;
        }
      }
      continue;
    }

    if (e->type == E_BUS) {
      if (boxes_overlap(px, py, 10, 22, TOPX(e->x), TOPX(e->y), e->w, e->h)) {
        if (g_level + 1 >= g_num_levels) {
          g_state = ST_WIN;
          g_state_t = 0;
          snd_play(SFX_WIN);
        } else {
          g_state = ST_LEVEL_DONE;
          g_state_t = 0;
          snd_play(SFX_WIN);
        }
      }
      continue;
    }

    if (is_enemy(e)) {
      int ox = TOPX(e->x), oy = TOPX(e->y);
      if (boxes_overlap(px, py, 10, 22, ox, oy, e->w, e->h)) {
        int stomped = (g_pl.vy > 0) && (py + 22 - g_pl.vy / FX <= oy + 6);
        if (stomped && e->type != E_TRACTOR) {
          e->hp--;
          if (e->hp <= 0) {
            kill_enemy(e);
            g_score += (e->type == E_DED) ? 300 : 150;
          } else {
            e->face = (px < ox) ? 1 : -1;
          }
          g_pl.vy = -1500;
          g_pl.on_ground = 0;
          snd_play(SFX_STOMP);
          g_shake = 3;
        } else if (e->type == E_TRACTOR) {
          hurt_player();
        } else {
          hurt_player();
        }
      }
    }

    /* thrown manure vs enemies */
    if (e->type == E_THROWN) {
      int j;
      for (j = 0; j < g_nent; j++) {
        Ent *o = &g_ent[j];
        if (!o->alive || !is_enemy(o) || o->type == E_TRACTOR)
          continue;
        if (boxes_overlap(TOPX(e->x), TOPX(e->y), e->w, e->h,
                          TOPX(o->x), TOPX(o->y), o->w, o->h)) {
          kill_enemy(o);
          e->alive = 0;
          g_score += 100;
          snd_play(SFX_STOMP);
          break;
        }
      }
    }
  }
}

/* =========================================================================
   autopilot
   -------------------------------------------------------------------------
   A tiny "does the floor continue?" bot. It is used by the host build to
   smoke-test every level without a human, and by the title screen as an
   attract mode. It is deliberately stupid: look one tile ahead, jump if the
   ground ends or if something hostile is in the way.
   ========================================================================= */
static int g_autopilot;

#ifdef DOSYA_HOST
/* 0 = silent, 1 = state transitions, 2 = per-frame trace of the autopilot.
   Set from the environment so the smoke test can read the game's mind
   without a debugger. */
int g_dbg;
#endif

void game_set_autopilot(int on)
{
  g_autopilot = on;
}

static void autopilot_input(void)
{
  int px = TOPX(g_pl.x);
  int py = TOPX(g_pl.y);
  int probe_x = px + (g_pl.face > 0 ? 10 : -6);
  int foot_row = (py + 21) >> 4;
  int gap = 0;
  int danger = 0;
  int i;
  static int hold;

  if (g_pl.on_ground) {
    /* Is there floor one step ahead, looking a few rows down so a one-way
       platform counts as floor? */
    int dy, found = 0;
    for (dy = 0; dy < 3 && !found; dy++)
      if (tile_flags[tile_at(probe_x >> 4, foot_row + dy)] & (TILE_SOLID | TILE_ONEWAY))
        found = 1;
    if (!found)
      gap = 1;
    /* Hazards get a longer look-ahead than holes: jumping at the last pixel
       means clipping the first spike with your ankle. */
    if (tile_flags[tile_at((px + 26) >> 4, foot_row)] & (TILE_WATER | TILE_SPIKE))
      gap = 1;
    /* a wall right in front? */
    if (tile_flags[tile_at((px + 12) >> 4, (py + 10) >> 4)] & TILE_SOLID)
      gap = 1;
    hold = gap || danger;
  }

  /* something to stomp or avoid within 40 px? */
  for (i = 0; i < g_nent; i++) {
    const Ent *e = &g_ent[i];
    int ex;
    if (!e->alive || !is_enemy(e))
      continue;
    ex = TOPX(e->x);
    if (ex > px && ex - px < 44 && abs(TOPX(e->y) - py) < 28)
      danger = 1;
  }
  if (danger && g_pl.on_ground) {
    /* Only hop over an enemy if there is somewhere to land. Hopping into a
       pit to dodge a chicken is how the bot kept dying at the same pixel. */
    int landing = (px + 88) >> 4;
    int dy, ok = 0;
    for (dy = 0; dy < 3 && !ok; dy++)
      if (tile_flags[tile_at(landing, foot_row + dy)] & (TILE_SOLID | TILE_ONEWAY))
        ok = 1;
    if (ok)
      hold = 1;
  }

  g_left = 0;
  g_right = 1;
  g_pl.face = 1;
  if (hold && g_pl.on_ground)
    g_jump_pressed = 1;
  g_jump_held = hold;

#ifdef DOSYA_HOST
  if (g_dbg >= 2)
    fprintf(stderr, "ap lvl=%d px=%d py=%d gnd=%d gap=%d danger=%d hold=%d\n",
            g_level, px, py, g_pl.on_ground, gap, danger, hold);
#endif
}

static void update_camera(void)
{
  int max_x = g_w * 16 - SCREEN_W;
  int max_y = g_h * 16 - PLAY_H;
  int px = TOPX(g_pl.x), py = TOPX(g_pl.y);

  if (max_x < 0) max_x = 0;
  if (max_y < 0) max_y = 0;

  /* Horizontal: follow with a dead zone so the camera does not twitch every
     time she turns around. */
  {
    int screen_x = px - g_cam_x;
    int target = g_cam_x;
    if (screen_x < 100)
      target = px - 100;
    else if (screen_x > 190)
      target = px - 190;
    target += (px + 5 - SCREEN_W / 2 - target) / 8;
    g_cam_x += (target - g_cam_x) / 2;
    if (g_cam_x < 0) g_cam_x = 0;
    if (g_cam_x > max_x) g_cam_x = max_x;
  }

  /* Vertical: stay put until she climbs into the top third or drops into the
     bottom quarter, then follow. This kills the seasick bobbing. */
  {
    int screen_y = py - g_cam_y;
    if (screen_y < 56)
      g_cam_y = py - 56;
    else if (screen_y > 150)
      g_cam_y = py - 150;
    if (g_cam_y < 0) g_cam_y = 0;
    if (g_cam_y > max_y) g_cam_y = max_y;
  }

  /* Never let her leave the screen, whatever the maths above says. */
  if (px - g_cam_x < 6) g_cam_x = px - 6;
  if (px - g_cam_x > SCREEN_W - 22) g_cam_x = px - (SCREEN_W - 22);
  if (g_cam_x < 0) g_cam_x = 0;
  if (g_cam_x > max_x) g_cam_x = max_x;
}

/* =========================================================================
   rendering -- background
   ========================================================================= */
static void draw_sky(void)
{
  int i;
  r_gradient_v(0, PLAY_H - 1, PAL_SKY_BASE, PAL_SKY_N, PAL_SKY_N - 1, 3);

  /* A band of haze where the sky meets the hills. Without it the horizon is
     a hard seam and the whole backdrop looks like two posters glued together. */
  {
    int y;
    for (y = 88; y < 106; y++) {
      int t = (y - 88) * 6 / 18;
      r_hline(0, SCREEN_W - 1, y, (unsigned char)(PAL_SKY2 + (5 - t)));
    }
  }

  /* Sun: a disc with a soft edge, drawn scanline by scanline. */
  {
    int cx = 266, cy = 30, r = 12;
    for (i = -r; i <= r; i++) {
      int span = 0;
      while ((i * i + span * span) <= r * r)
        span++;
      span--;
      if (span < 0)
        continue;
      r_hline(cx - span, cx + span, cy + i,
              (span > r - 4) ? PAL_YELLOW2 : PAL_YELLOW3);
    }
  }
}

static void draw_clouds(void)
{
  int i;
  for (i = 0; i < 9; i++) {
    int span = g_w * 16 / 3 + 400;
    int cx = (i * 190 - g_cam_x / 3) % span;
    int cy = 10 + (i % 4) * 15;
    if (cx < 0) cx += span;
    cx -= 40;
    if (cx > SCREEN_W || cx < -80)
      continue;
    r_sprite(SPR_CLOUD, cx, cy);
  }
}

/* Deterministic 2D value noise, 0..255. Cheap, integer-only, and stable
   across frames, which is all a parallax backdrop needs. */
static int noise2(int x, int y, int seed)
{
  unsigned n = (unsigned)(x * 374761393 + y * 668265263 + seed * 1442695040);
  n = (n ^ (n >> 13)) * 1274126177u;
  return (int)((n ^ (n >> 16)) & 0xFF);
}

/* Smooth 1D noise: sample noise2 at integer steps and lerp between them.
   Using raw noise gives spiky grass; using (x*3)%47 gives diagonal stripes
   (I know, I tried). This gives rolling hills. */
static int wave(int x, int period, int seed)
{
  int i0 = x / period;
  int f = x % period;
  int a = noise2(i0, 0, seed);
  int b = noise2(i0 + 1, 0, seed);
  return a + (b - a) * f / period;
}

static void draw_hills(void)
{
  /* Four silhouette layers, far to near. Brightness rises with distance so the
     layers separate instead of turning into one green soup. */
  int layer;
  for (layer = 0; layer < 4; layer++) {
    int par = 9 - layer * 2;
    int base = 100 + layer * 12;
    int amp = 10 + layer * 4;
    int seed = layer * 911;
    unsigned char col = (unsigned char)(PAL_DARKGREEN_BASE + layer);
    int x;
    if (par < 1) par = 1;
    for (x = 0; x < SCREEN_W; x++) {
      int wx = g_cam_x / par + x;
      int h = wave(wx, 37, seed) * 2 + wave(wx, 13, seed + 5);
      h = base - (h * amp) / 600;
      r_vline(x, h, PLAY_H - 1, col);
      /* A single soft highlight on the ridge. Full-brightness rim lines made
         the hills look like a heart monitor, so it is one pixel of +2. */
      r_pixel(x, h, (unsigned char)(col + 2));
    }
  }
}

static void draw_world(void)
{
  int tx0 = g_cam_x >> 4;
  int ty0 = g_cam_y >> 4;
  int tx1 = (g_cam_x + SCREEN_W) >> 4;
  int ty1 = (g_cam_y + PLAY_H) >> 4;
  int tx, ty;

  /* background decor first, dimmed so it reads as "behind" */
  for (ty = ty0; ty <= ty1; ty++)
    for (tx = tx0; tx <= tx1; tx++) {
      int t = g_bg[ty * g_w + tx];
      if (t != T_EMPTY)
        r_tile_dim(t, (tx << 4) - g_cam_x, (ty << 4) - g_cam_y);
    }

  for (ty = ty0; ty <= ty1; ty++) {
    for (tx = tx0; tx <= tx1; tx++) {
      int t = g_map[ty * g_w + tx];
      int sx, sy;
      if (t == T_EMPTY)
        continue;
      sx = (tx << 4) - g_cam_x;
      sy = (ty << 4) - g_cam_y;
      r_tile(t, sx, sy);
    }
  }
}

/* =========================================================================
   rendering -- entities
   ========================================================================= */
static int sprite_for_ent(const Ent *e)
{
  int f = e->face;
  switch (e->type) {
    case E_CHICKEN:  return (e->t >> 3) & 1 ? SPR_CHICKEN1 : SPR_CHICKEN0;
    case E_ROOSTER:  return (e->t >> 3) & 1 ? SPR_ROOSTER1 : SPR_ROOSTER0;
    case E_GOAT:     return (e->t >> 3) & 1 ? SPR_GOAT1 : SPR_GOAT0;
    case E_DED:      return (e->t >> 4) & 1 ? SPR_DED1 : SPR_DED0;
    case E_TRACTOR:  return (e->t >> 2) & 1 ? SPR_TRACTOR1 : SPR_TRACTOR0;
    case E_MILK:     return SPR_MILK;
    case E_EGG:      return SPR_EGG;
    case E_MANURE:   return SPR_MANURE;
    case E_SAMOGON:  return SPR_SAMOGON;
    case E_BUS:      return SPR_BUS;
    case E_THROWN:   return SPR_MANURE;
    default:         return -1;
  }
  (void)f;
}

static void draw_ent(const Ent *e)
{
  int spr, sx, sy, sw, sh;
  spr = sprite_for_ent(e);
  if (spr < 0)
    return;
  sw = g_sprites[spr].w;
  sh = g_sprites[spr].h;
  sx = TOPX(e->x) + e->w / 2 - sw / 2 - g_cam_x;
  sy = TOPX(e->y) + e->h - sh + 1 - g_cam_y;
  if (sx < -sw || sx > SCREEN_W || sy < -sh || sy > PLAY_H)
    return;
  if (e->face > 0)
    r_sprite_flip(spr, sx, sy);
  else
    r_sprite(spr, sx, sy);
}

static void draw_poof(const Ent *e)
{
  int cx = TOPX(e->x) - g_cam_x;
  int cy = TOPX(e->y) - g_cam_y;
  int rad = (12 - e->t) / 2 + 2;
  int i;
  for (i = 0; i < 6; i++) {
    int a = i * 60;
    int dx = (a % 100) - 50;
    r_pixel(cx + dx / 6 * rad, cy + (i - 3) * 2, PAL_HAY4);
  }
}

/* =========================================================================
   rendering -- player
   ========================================================================= */
static void draw_player(void)
{
  int spr;
  int px, py, sx, sy;
  const Sprite *sp;

  if (g_state == ST_DEAD && g_state_t > 20)
    spr = SPR_DOSYA_DEAD;
  else if (g_drunk > 0)
    spr = (g_pl.anim >> 2) & 1 ? SPR_DOSYA_WALK2 : SPR_DOSYA_WIN;
  else if (!g_pl.on_ground)
    spr = (g_pl.vy < 0) ? SPR_DOSYA_JUMP : SPR_DOSYA_FALL;
  else if (g_pl.vx != 0) {
    int f = (g_pl.anim >> 3) & 3;
    spr = SPR_DOSYA_WALK1 + f;
  } else
    spr = SPR_DOSYA_STAND;

  px = TOPX(g_pl.x);
  py = TOPX(g_pl.y);
  sp = &g_sprites[spr];
  sx = px + 5 - sp->w / 2 - g_cam_x;
  sy = py + 22 - sp->h + 2 - g_cam_y;

  if (g_invuln > 0 && (g_invuln >> 2) & 1)
    return;                     /* blink */

  if (g_pl.face > 0)
    r_sprite_flip(spr, sx, sy);
  else
    r_sprite(spr, sx, sy);
}

/* =========================================================================
   rendering -- HUD
   ========================================================================= */
static void draw_face(void)
{
  int spr;
  if (g_state == ST_DEAD) spr = SPR_FACE_DEAD;
  else if (g_hearts >= 3) spr = SPR_FACE_OK;
  else if (g_hearts == 2) spr = SPR_FACE_HURT;
  else spr = SPR_FACE_BAD;
  r_sprite(spr, 4, PLAY_H + 3);
}

static void draw_hud(void)
{
  char buf[32];
  int y = PLAY_H + 5;
  r_rect(0, PLAY_H, SCREEN_W - 1, SCREEN_H - 1, PAL_GREY1);
  r_hline(0, SCREEN_W - 1, PLAY_H, PAL_GREY5);
  r_hline(0, SCREEN_W - 1, PLAY_H + 1, PAL_GREY3);
  r_hline(0, SCREEN_W - 1, SCREEN_H - 1, PAL_GREY0);

  draw_face();

  /* lives */
  sprintf(buf, "x%d", g_lives);
  r_text(26, y, buf, PAL_WHITE8);

  /* milk */
  r_text(50, y, S_HUD_MILK, PAL_GREY7);
  sprintf(buf, "%d", g_milk);
  r_text(98, y, buf, PAL_WHITE9);

  /* manure ammo */
  r_text(130, y, S_HUD_AMMO, PAL_GREY7);
  sprintf(buf, "%d", g_ammo);
  r_text(178, y, buf, PAL_HAY5);

  /* score */
  r_text(214, y, S_SCORE, PAL_GREY7);
  sprintf(buf, "%d", g_score);
  r_text(254, y, buf, PAL_YELLOW5);
}

/* =========================================================================
   screens
   ========================================================================= */
static void draw_title(void)
{
  int i;
  r_clear(PAL_NAVY1);
  r_gradient_v(0, PLAY_H, PAL_NAVY_BASE, PAL_NAVY_N, 3, 0);

  /* stars, because every 1993 title screen had stars */
  for (i = 0; i < 46; i++) {
    int x = (i * 97 + 13) % SCREEN_W;
    int y = (i * 53 + 7) % 120;
    r_pixel(x, y, (i & 1) ? PAL_GREY6 : PAL_GREY4);
  }

  /* The village, seen from the road she is about to walk down. */
  {
    int layer;
    for (layer = 0; layer < 3; layer++) {
      int base = 108 + layer * 14;
      unsigned char col = (unsigned char)(PAL_DARKGREEN_BASE + 1 + layer);
      int x;
      for (x = 0; x < SCREEN_W; x++) {
        int h = wave(x * (1 + layer), 41 + layer * 9, 17 + layer * 101);
        h = base - h / 14;
        r_vline(x, h, PLAY_H - 1, col);
      }
    }
    /* a couple of houses on the ridge */
    r_sprite(SPR_SIGN, 42, 118);
    r_sprite(SPR_BUSH, 250, 126);
    r_sprite(SPR_SUNFLOWER, 286, 108);
  }

  /* the title, doubled in size out of the 8x16 font */
  {
    const char *t = S_TITLE_1;
    int w = r_text_width(t) * 2;
    int cx = (SCREEN_W - w) / 2;
    while (*t) {
      const unsigned char *g = g_font + (unsigned char)*t * 16;
      int gy, gx;
      for (gy = 0; gy < 16; gy++)
        for (gx = 0; gx < 8; gx++)
          if (g[gy] & (0x80 >> gx)) {
            r_rect(cx + gx * 2 + 2, 22 + gy * 2 + 2, cx + gx * 2 + 3, 22 + gy * 2 + 3, PAL_VOID1);
            r_rect(cx + gx * 2, 22 + gy * 2, cx + gx * 2 + 1, 22 + gy * 2 + 1, PAL_RED9);
          }
      cx += 16;
      t++;
    }
  }

  r_text_center(58, S_TITLE_2, PAL_YELLOW5);
  r_text_center(78, S_TITLE_LINE, PAL_GREY7);
  r_sprite(SPR_DOSYA_STAND, SCREEN_W / 2 - 9, 96);

  /* blinking prompt */
  if ((g_state_t >> 4) & 1)
    r_text_center(126, S_TITLE_HINT, PAL_WHITE9);

  /* Controls live in the playfield, not the status bar: the bar is 24 px tall
     and a 16 px font only fits one line in it. */
  r_text(6, 142, S_CTRL_1, PAL_GREY6);
  r_text(6, 158, S_CTRL_3, PAL_GREY6);
  r_text(174, 142, S_CTRL_2, PAL_GREY6);
  r_text(174, 158, S_CTRL_4, PAL_GREY6);

  r_rect(0, PLAY_H, SCREEN_W - 1, SCREEN_H - 1, PAL_NAVY0);
  r_hline(0, SCREEN_W - 1, PLAY_H, PAL_NAVY2);
  r_text(6, PLAY_H + 4, S_TITLE_FOOT, PAL_GREY5);
}

static void draw_intro(void)
{
  int i;
  static const char *lines[] = {
    S_INTRO_1, S_INTRO_2, S_INTRO_3, S_INTRO_4, S_INTRO_5,
    S_INTRO_6, S_INTRO_7, S_INTRO_8, S_INTRO_9, S_INTRO_10
  };
  r_clear(PAL_VOID0);
  r_gradient_v(0, SCREEN_H - 1, PAL_VOID_BASE, PAL_VOID_N, 1, 0);
  for (i = 0; i < 10; i++) {
    int y = 16 + i * 17;
    if (g_state_t > i * 8)
      r_text_center(y, lines[i], (i >= 8) ? PAL_RED7 : PAL_GREY7);
  }
  if (g_state_t > 120)
    r_text_center(180, S_PRESS, (g_state_t >> 3) & 1 ? PAL_WHITE8 : PAL_GREY4);
}

static void draw_dead(void)
{
  r_clear(PAL_BLOOD0);
  r_rect(0, 0, SCREEN_W - 1, SCREEN_H - 1, PAL_BLOOD0);

  /* A pool of something, spreading outward. */
  {
    int i;
    for (i = 0; i < 10; i++) {
      int r = 10 + i * 6;
      int y;
      for (y = -r; y <= r; y++) {
        int span = 0;
        while ((y * y + span * span) <= r * r)
          span++;
        span--;
        if (span < 0)
          continue;
        r_hline(SCREEN_W / 2 - span, SCREEN_W / 2 + span,
                132 + y / 4, (i & 1) ? PAL_BLOOD1 : PAL_BLOOD2);
      }
    }
  }

  r_text_center(18, S_DEAD_TITLE, PAL_RED9);
  r_text_wrap(26, 42, 268, g_die_lists[g_death_cause][g_death_msg], PAL_GREY8, 17);
  r_sprite(SPR_DOSYA_DEAD, SCREEN_W / 2 - 9, 84);

  if (g_state_t > 24) {
    r_text_center(142, S_DEAD_HINT, PAL_WHITE9);
    r_text_center(160, S_DEAD_HINT2, PAL_GREY7);
  }
}

static void draw_done(void)
{
  r_clear(PAL_NAVY1);
  r_gradient_v(0, SCREEN_H - 1, PAL_NAVY_BASE, PAL_NAVY_N, 2, 0);
  r_text_center(50, S_DONE_1, PAL_YELLOW4);
  r_text_center(78, S_DONE_2, PAL_GREY7);
  r_sprite(SPR_DOSYA_WIN, SCREEN_W / 2 - 9, 100);
  if (g_state_t > 30)
    r_text_center(170, S_DONE_HINT, PAL_WHITE7);
}

static void draw_win(void)
{
  r_clear(PAL_NAVY1);
  r_gradient_v(0, SCREEN_H - 1, PAL_PURPLE_BASE, PAL_PURPLE_N, 2, 0);
  r_text_center(20, S_WIN_1, PAL_YELLOW4);
  r_text_center(48, S_WIN_2, PAL_GREY7);
  r_sprite(SPR_BUS, SCREEN_W / 2 - 15, 70);
  if (g_state_t > 40) {
    r_text_center(104, S_WIN_3, PAL_RED6);
    r_text_center(122, S_WIN_4, PAL_GREY6);
  }
  if (g_state_t > 90) {
    r_text_center(148, S_WIN_5, PAL_WHITE8);
    r_text_center(176, S_WIN_HINT, PAL_GREY5);
  }
}

/* =========================================================================
   public API
   ========================================================================= */
void game_init(void)
{
  g_lives = 3;
  g_hearts = 3;
  g_score = 0;
  g_milk = 0;
  g_ammo = 2;
  g_level = 0;
  g_paused = 0;
  g_state = ST_TITLE;
  g_state_t = 0;
  g_invuln = 0;
  g_drunk = 0;
  g_shake = 0;
  load_level(0);
}

void game_tick(void)
{
  State prev = g_state;
  (void)prev;
  g_state_t++;
  if (g_shake > 0)
    g_shake--;

  switch (g_state) {
    case ST_TITLE:
      break;

    case ST_INTRO:
      break;

    case ST_PLAY:
      if (g_paused)
        break;
      if (g_autopilot)
        autopilot_input();
      update_player();
      update_ents();
      update_camera();
      if (g_invuln > 0) g_invuln--;
      if (g_drunk > 0) {
        g_drunk--;
        if (g_drunk == 0)
          g_drunk = 0;
      }
      break;

    case ST_DEAD:
      /* Show the obituary for a couple of seconds, then respawn or give up.
         Automatic, because nobody wants to press a key to be told they died. */
      if (g_state_t > 150) {
        g_lives--;
        if (g_lives <= 0) {
          g_state = ST_GAMEOVER;
          g_state_t = 0;
        } else {
          g_hearts = 3;
          g_drunk = 0;
          load_level(g_level);
          g_state = ST_PLAY;
          g_state_t = 0;
        }
      }
      break;

    case ST_LEVEL_DONE:
      if (g_autopilot && g_state_t > 60) {
        load_level(g_level + 1);
        g_hearts = 3;
        g_state = ST_PLAY;
        g_state_t = 0;
      }
      break;

    case ST_WIN:
      break;

    default:
      break;
  }

#ifdef DOSYA_HOST
  if (g_dbg >= 1 && g_state != prev)
    fprintf(stderr, "[tick] state %d -> %d lvl=%d x=%d y=%d lives=%d hearts=%d cause=%d\n",
            prev, g_state, g_level, TOPX(g_pl.x), TOPX(g_pl.y),
            g_lives, g_hearts, g_death_cause);
#endif
}

void game_render(void)
{
  int sx = 0, sy = 0;

#ifdef DOSYA_HOST
  if (g_dbg >= 2)
    fprintf(stderr, "st=%d t=%d pl=(%d,%d) v=(%d,%d) cam=(%d,%d) gnd=%d\n",
            g_state, g_state_t, TOPX(g_pl.x), TOPX(g_pl.y),
            g_pl.vx, g_pl.vy, g_cam_x, g_cam_y, g_pl.on_ground);
#endif

  if (g_shake) {
    sx = (rnd() % 5) - 2;
    sy = (rnd() % 5) - 2;
  }

  switch (g_state) {
    case ST_TITLE:
      draw_title();
      break;
    case ST_INTRO:
      draw_intro();
      break;
    case ST_PLAY:
      r_clear(PAL_SKY4);
      draw_sky();
      draw_clouds();
      draw_hills();
      g_cam_x += sx;
      g_cam_y += sy;
      draw_world();
      {
        int i;
        for (i = 0; i < g_nent; i++)
          if (g_ent[i].alive && g_ent[i].type != E_POOF)
            draw_ent(&g_ent[i]);
        for (i = 0; i < g_nent; i++)
          if (g_ent[i].alive && g_ent[i].type == E_POOF)
            draw_poof(&g_ent[i]);
      }
      draw_player();
      g_cam_x -= sx;
      g_cam_y -= sy;
      draw_hud();
      if (g_paused) {
        r_rect(80, 68, 240, 106, PAL_VOID1);
        r_frame(80, 68, 240, 106, PAL_GREY5);
        r_text_center(76, S_PAUSE, PAL_WHITE9);
        r_text_center(96, S_PAUSE_HINT, PAL_GREY6);
      }
      break;
    case ST_DEAD:
      draw_dead();
      break;
    case ST_LEVEL_DONE:
      draw_done();
      break;
    case ST_WIN:
      draw_win();
      break;
    case ST_GAMEOVER:
      r_clear(PAL_VOID0);
      r_text_center(70, S_GAMEOVER, PAL_RED7);
      r_text_center(110, S_GAMEOVER_HINT, PAL_GREY6);
      break;
  }
}

int game_state(void)
{
  return g_state;
}

void game_set_input(int left, int right, int jump_pressed, int jump_held)
{
  g_left = left;
  g_right = right;
  if (jump_pressed)
    g_jump_pressed = 1;
  g_jump_held = jump_held;
}

/* Called once per key press. Handles state transitions and the throw. */
void game_key(int sc)
{
  switch (g_state) {
    case ST_TITLE:
      if (sc == K_SPACE || sc == K_ENTER) {
        g_state = ST_INTRO;
        g_state_t = 0;
        snd_play(SFX_SELECT);
      }
      break;

    case ST_INTRO:
      if (sc == K_SPACE || sc == K_ENTER) {
        g_state = ST_PLAY;
        g_state_t = 0;
      }
      break;

    case ST_PLAY:
      if (sc == K_P) {
        g_paused = !g_paused;
        snd_play(SFX_SELECT);
      }
      if (sc == K_X || sc == K_CTRL || sc == K_Z) {
        if (g_ammo > 0 && !g_paused) {
          Ent *e = ent_new(E_THROWN, 0, 0);
          g_ammo--;
          snd_play(SFX_THROW);
          if (e) {
            e->x = g_pl.x + (g_pl.face > 0 ? TOFX(10) : -TOFX(6));
            e->y = g_pl.y + TOFX(6);
            e->vx = g_pl.face * 620 + g_pl.vx / 2;
            e->vy = -420;
            e->face = g_pl.face;
            e->t = 0;
          }
        }
      }
      break;

    case ST_DEAD:
      if (g_state_t > 30 && (sc == K_SPACE || sc == K_ENTER))
        g_state_t = 150;             /* skip the wait */
      break;

    case ST_LEVEL_DONE:
      if (g_autopilot) {
        if (g_state_t > 60) {
          load_level(g_level + 1);
          g_hearts = 3;
          g_state = ST_PLAY;
          g_state_t = 0;
        }
        break;
      }
      if (sc == K_SPACE || sc == K_ENTER) {
        load_level(g_level + 1);
        g_hearts = 3;
        g_state = ST_PLAY;
        g_state_t = 0;
      }
      break;

    case ST_WIN:
      if (g_autopilot) {
        if (g_state_t > 120)
          g_state_t = 0;      /* just sit on the win screen */
        break;
      }
      if (sc == K_SPACE || sc == K_ENTER) {
        g_score = 0;
        g_milk = 0;
        g_ammo = 2;
        g_lives = 3;
        g_hearts = 3;
        load_level(0);
        g_state = ST_TITLE;
        g_state_t = 0;
      }
      break;

    case ST_GAMEOVER:
      if (sc == K_SPACE || sc == K_ENTER) {
        g_score = 0;
        g_milk = 0;
        g_ammo = 2;
        g_lives = 3;
        g_hearts = 3;
        load_level(0);
        g_state = ST_PLAY;
        g_state_t = 0;
      }
      break;

    default:
      break;
  }
}
