import { generatePigeonTraits, type PigeonTraits } from "./cosmetics";

export const ECONOMY = {
  startSeeds: 1000,
  feedCycleMs: 8 * 60 * 60 * 1000, // 8 часов
  eggEveryFeeds: 5,
  maxEggLevel: 12,
  baseCostByRarity: [1, 5, 15, 30, 60, 100],
  steps: [
    { through: 20, multiplier: 1 },
    { through: 40, multiplier: 2 },
    { through: 55, multiplier: 3 },
    { through: 70, multiplier: 4 },
    { through: 80, multiplier: 5 },
    { through: 90, multiplier: 6 },
    { through: 95, multiplier: 8 },
    { through: 100, multiplier: 10 },
  ],
  beyondStep: 5,
  beyondIncrement: 2,
  crumbsReward: 25,
  crumbsCooldownMs: 60 * 60 * 1000, // 1 час
  eggDropChances: [
    { chance: 0.75, offset: 1 },
    { chance: 0.20, offset: 2 },
    { chance: 0.05, offset: 3 },
  ],
  eggs: [
    { base: 10, jackpot: 100, jackpotPct: 0.01, birdPct: 0.00001, maxRarity: 0 },
    { base: 22, jackpot: 250, jackpotPct: 0.009, birdPct: 0.00002, maxRarity: 0 },
    { base: 48, jackpot: 600, jackpotPct: 0.008, birdPct: 0.00005, maxRarity: 1 },
    { base: 105, jackpot: 1500, jackpotPct: 0.007, birdPct: 0.0001, maxRarity: 1 },
    { base: 230, jackpot: 3500, jackpotPct: 0.006, birdPct: 0.0002, maxRarity: 2 },
    { base: 500, jackpot: 8000, jackpotPct: 0.005, birdPct: 0.0004, maxRarity: 2 },
    { base: 1100, jackpot: 20000, jackpotPct: 0.004, birdPct: 0.0008, maxRarity: 3 },
    { base: 2400, jackpot: 50000, jackpotPct: 0.003, birdPct: 0.0015, maxRarity: 3 },
    { base: 5200, jackpot: 125000, jackpotPct: 0.002, birdPct: 0.0035, maxRarity: 4 }, // LVL 9: 0.35%
    { base: 11500, jackpot: 300000, jackpotPct: 0.0015, birdPct: 0.0075, maxRarity: 4 }, // LVL 10: 0.75%
    { base: 25000, jackpot: 750000, jackpotPct: 0.001, birdPct: 0.016, maxRarity: 5 }, // LVL 11: 1.6%
    { base: 55000, jackpot: 2000000, jackpotPct: 0.0005, birdPct: 0.035, maxRarity: 5 }, // LVL 12: 3.5%
  ],
} as const;

export function feedCost(rarity: number, cycleFeeds: number) {
  const base = ECONOMY.baseCostByRarity[rarity] ?? 1;
  const nextFeed = cycleFeeds + 1;
  let mult =
    ECONOMY.steps.find((s) => nextFeed <= s.through)?.multiplier ??
    (ECONOMY.steps.at(-1)?.multiplier ?? 1);
  if (nextFeed > 100)
    mult +=
      Math.ceil((nextFeed - 100) / ECONOMY.beyondStep) *
      ECONOMY.beyondIncrement;
  return base * mult;
}

export type Egg = { id: string; level: number };
export type Bird = {
  id: string;
  rarity: number;
  cycleFeeds: number;
  cycleStartedAt: number | null;
  traits?: PigeonTraits;
};

/**
 * Форматирует отображаемый личный номер голубя (например, "#0001").
 * Извлекает числовой идентификатор из id (например, "bird-001" -> "#0001")
 * или использует порядковый индекс + 1 как надёжный fallback.
 */
export function formatBirdNumber(
  bird?: { id?: string } | null,
  fallbackIndex = 0
): string {
  if (!bird?.id) return `#${String(fallbackIndex + 1).padStart(4, "0")}`;
  const match = bird.id.match(/\d+/);
  const num = match ? parseInt(match[0], 10) : fallbackIndex + 1;
  return `#${String(num).padStart(4, "0")}`;
}

export type Game = {
  seeds: number;
  xp: number;
  level: number;
  rarity: number;
  cycleFeeds: number;
  cycleStartedAt: number | null;
  birds: Bird[];
  activeBirdId: string;
  totalFeeds: number;
  eggs: Egg[];
  queue: Egg[];
  board: (Egg | null)[];
  hatched: number;
  lastCrumbsAt: number | null;
  lvl4BirdAwarded: boolean;
};

export const initialGame = (): Game => ({
  seeds: ECONOMY.startSeeds,
  xp: 0,
  level: 1,
  rarity: 0,
  cycleFeeds: 0,
  cycleStartedAt: null,
  birds: [
    {
      id: "bird-001",
      rarity: 0,
      cycleFeeds: 0,
      cycleStartedAt: null,
      traits: generatePigeonTraits(0, "bird-001"),
    },
  ],
  activeBirdId: "bird-001",
  totalFeeds: 0,
  eggs: [],
  queue: [],
  board: Array(25).fill(null),
  hatched: 0,
  lastCrumbsAt: null,
  lvl4BirdAwarded: false,
});

/**
 * Окно дропа уровня яйца по редкости кормимого голубя (v0.2):
 * 75% — rarity + 1
 * 20% — rarity + 2
 *  5% — rarity + 3
 */
export function rollEggLevel(rarity: number, rng = Math.random): number {
  const r = rng();
  let offset = 1;
  if (r < 0.75) offset = 1;
  else if (r < 0.95) offset = 2;
  else offset = 3;
  return Math.min(ECONOMY.maxEggLevel, Math.max(1, rarity + offset));
}

export function feed(g: Game, now: number, rng = Math.random): Game {
  const bird =
    g.birds.find((b) => b.id === g.activeBirdId) ?? {
      id: g.activeBirdId,
      rarity: g.rarity,
      cycleFeeds: g.cycleFeeds,
      cycleStartedAt: g.cycleStartedAt,
    };
  let cycleFeeds = bird.cycleFeeds;
  if (
    bird.cycleStartedAt !== null &&
    now - bird.cycleStartedAt >= ECONOMY.feedCycleMs
  )
    cycleFeeds = 0;
  const cost = feedCost(bird.rarity, cycleFeeds);
  if (g.seeds < cost) return g;
  cycleFeeds++;
  const cycleStartedAt = cycleFeeds === 1 ? now : bird.cycleStartedAt;
  const egg = g.totalFeeds + 1;
  const isEggFeed = egg % ECONOMY.eggEveryFeeds === 0;
  const eggLevel = isEggFeed ? rollEggLevel(bird.rarity, rng) : 1;
  const newEgg: Egg | null = isEggFeed
    ? { id: `egg-${now}-${g.totalFeeds}`, level: eggLevel }
    : null;
  const updatedBird = { ...bird, cycleFeeds, cycleStartedAt };
  return {
    ...g,
    seeds: g.seeds - cost,
    xp: g.xp + 10,
    cycleFeeds,
    cycleStartedAt,
    birds: g.birds.some((b) => b.id === bird.id)
      ? g.birds.map((b) => (b.id === bird.id ? updatedBird : b))
      : [...g.birds, updatedBird],
    totalFeeds: egg,
    eggs: newEgg ? [...g.eggs, newEgg] : g.eggs,
    queue: newEgg ? [...g.queue, newEgg] : g.queue,
  };
}

export function merge(g: Game, a: number, b: number) {
  if (
    a === b ||
    !Number.isInteger(a) ||
    !Number.isInteger(b) ||
    a < 0 ||
    b < 0 ||
    a >= 25 ||
    b >= 25
  )
    return g;
  const x = g.board[a],
    y = g.board[b];
  if (!x || !y || x.level !== y.level || x.level >= ECONOMY.maxEggLevel)
    return g;
  const board = [...g.board];
  board[a] = { id: `${x.id}+${y.id}`, level: x.level + 1 };
  board[b] = null;
  return { ...g, board };
}

export function hatch(
  g: Game,
  index: number,
  rng = Math.random
): {
  game: Game;
  reward: number;
  jackpot: boolean;
  bird: boolean;
  achievementBird: boolean;
} | null {
  if (!Number.isInteger(index) || index < 0 || index >= 25) return null;
  const egg = g.board[index];
  if (!egg) return null;
  const row = ECONOMY.eggs[egg.level - 1];
  if (!row) return null;

  const jackpot = rng() < row.jackpotPct;
  const bird = rng() < row.birdPct;
  const reward = row.base + (jackpot ? row.jackpot : 0);
  const board = [...g.board];
  board[index] = null;

  let achievementBird = false;
  let lvl4BirdAwarded = g.lvl4BirdAwarded ?? false;
  let birds = [...g.birds];

  // Стартовая цель-достижение: гарантированный второй обычный голубь за первое разбитие яйца LVL 4
  if (egg.level >= 4 && !lvl4BirdAwarded) {
    achievementBird = true;
    lvl4BirdAwarded = true;
    const newBirdId = `bird-${String(birds.length + 1).padStart(3, "0")}`;
    birds.push({
      id: newBirdId,
      rarity: 0, // Обычный
      cycleFeeds: 0,
      cycleStartedAt: null,
      traits: generatePigeonTraits(0, newBirdId),
    });
  }

  // Если выпал редкий голубь по вероятности из яйца
  if (bird) {
    const droppedBirdRarity = row.maxRarity;
    const newBirdId = `bird-${String(birds.length + 1).padStart(3, "0")}`;
    birds.push({
      id: newBirdId,
      rarity: droppedBirdRarity,
      cycleFeeds: 0,
      cycleStartedAt: null,
      traits: generatePigeonTraits(droppedBirdRarity, newBirdId),
    });
  }

  const newRarity = bird ? Math.max(g.rarity, row.maxRarity) : g.rarity;

  return {
    game: {
      ...g,
      seeds: g.seeds + reward,
      board,
      hatched: g.hatched + 1,
      rarity: newRarity,
      birds,
      lvl4BirdAwarded,
    },
    reward,
    jackpot,
    bird,
    achievementBird,
  };
}

export function placeFromQueue(g: Game, id: string, index: number): Game {
  if (g.board[index] || index < 0 || index >= 25) return g;
  const egg = g.queue.find((e) => e.id === id);
  if (!egg) return g;
  return {
    ...g,
    queue: g.queue.filter((e) => e.id !== id),
    board: g.board.map((e, i) => (i === index ? egg : e)),
  };
}

/**
 * Минимальная стоимость кормления среди голубей игрока в текущем цикле.
 */
export function minFeedCost(g: Game): number {
  if (!g.birds || g.birds.length === 0) return 1;
  return Math.min(...g.birds.map((b) => feedCost(b.rarity, b.cycleFeeds)));
}

/**
 * Проверка условий страховки от нуля («Собрать крошки»):
 * 1. seeds < минимальной цены кормления
 * 2. Нет яиц на поле (board)
 * 3. Нет яиц в очереди (queue)
 * 4. Истёк кулдаун 1 час
 */
export function canCollectCrumbs(g: Game, now: number): boolean {
  if (g.seeds >= minFeedCost(g)) return false;
  if (g.board.some((e) => e !== null)) return false;
  if (g.queue.length > 0) return false;
  if (
    g.lastCrumbsAt !== null &&
    now - g.lastCrumbsAt < ECONOMY.crumbsCooldownMs
  ) {
    return false;
  }
  return true;
}

/**
 * Сбор крошек: +25 семечек, обновление таймера кулдауна.
 */
export function collectCrumbs(g: Game, now: number): Game {
  if (!canCollectCrumbs(g, now)) return g;
  return {
    ...g,
    seeds: g.seeds + ECONOMY.crumbsReward,
    lastCrumbsAt: now,
  };
}

/**
 * Безопасная миграция и санитизация сохранённого состояния `koo-koo-v01`.
 * Поддерживает ранние версии без `birds`/`board`/`crumbs`/`traits`, сохраняя накопленный прогресс игрока.
 */
export function migrateGameState(raw: unknown): Game {
  const base = initialGame();
  if (!raw || typeof raw !== "object") return base;
  const p = raw as Record<string, unknown>;

  const seeds =
    typeof p.seeds === "number" && Number.isFinite(p.seeds) && p.seeds >= 0
      ? Math.floor(p.seeds)
      : base.seeds;
  const xp =
    typeof p.xp === "number" && Number.isFinite(p.xp) && p.xp >= 0
      ? Math.floor(p.xp)
      : base.xp;
  const level =
    typeof p.level === "number" && Number.isFinite(p.level) && p.level >= 1
      ? Math.floor(p.level)
      : base.level;
  const rarity =
    typeof p.rarity === "number" &&
    Number.isFinite(p.rarity) &&
    p.rarity >= 0 &&
    p.rarity <= 5
      ? Math.floor(p.rarity)
      : base.rarity;
  const cycleFeeds =
    typeof p.cycleFeeds === "number" &&
    Number.isFinite(p.cycleFeeds) &&
    p.cycleFeeds >= 0
      ? Math.floor(p.cycleFeeds)
      : base.cycleFeeds;
  const cycleStartedAt =
    typeof p.cycleStartedAt === "number" && Number.isFinite(p.cycleStartedAt)
      ? p.cycleStartedAt
      : null;
  const totalFeeds =
    typeof p.totalFeeds === "number" &&
    Number.isFinite(p.totalFeeds) &&
    p.totalFeeds >= 0
      ? Math.floor(p.totalFeeds)
      : base.totalFeeds;
  const hatched =
    typeof p.hatched === "number" &&
    Number.isFinite(p.hatched) &&
    p.hatched >= 0
      ? Math.floor(p.hatched)
      : base.hatched;
  const lastCrumbsAt =
    typeof p.lastCrumbsAt === "number" && Number.isFinite(p.lastCrumbsAt)
      ? p.lastCrumbsAt
      : null;
  const lvl4BirdAwarded = Boolean(p.lvl4BirdAwarded);

  // Восстановление списка голубей с детерминированным заполнением traits
  let birds: Bird[] = [];
  if (Array.isArray(p.birds) && p.birds.length > 0) {
    birds = p.birds
      .filter((b) => b && typeof b === "object")
      .map((b: any, idx: number) => {
        const birdId =
          typeof b.id === "string" && b.id
            ? b.id
            : `bird-${String(idx + 1).padStart(3, "0")}`;
        const birdRarity =
          typeof b.rarity === "number" && b.rarity >= 0 && b.rarity <= 5
            ? Math.floor(b.rarity)
            : 0;
        return {
          id: birdId,
          rarity: birdRarity,
          cycleFeeds:
            typeof b.cycleFeeds === "number" && b.cycleFeeds >= 0
              ? Math.floor(b.cycleFeeds)
              : 0,
          cycleStartedAt:
            typeof b.cycleStartedAt === "number" ? b.cycleStartedAt : null,
          traits:
            b.traits && typeof b.traits === "object"
              ? b.traits
              : generatePigeonTraits(birdRarity, birdId),
        };
      });
  }
  if (birds.length === 0) {
    const defaultId =
      typeof p.activeBirdId === "string" && p.activeBirdId
        ? p.activeBirdId
        : "bird-001";
    birds = [
      {
        id: defaultId,
        rarity,
        cycleFeeds,
        cycleStartedAt,
        traits: generatePigeonTraits(rarity, defaultId),
      },
    ];
  }

  const activeBirdId =
    typeof p.activeBirdId === "string" &&
    birds.some((b) => b.id === p.activeBirdId)
      ? p.activeBirdId
      : birds[0].id;

  // Валидация игрового поля 5x5 (25 ячеек)
  const board: (Egg | null)[] = Array(25).fill(null);
  if (Array.isArray(p.board)) {
    for (let i = 0; i < 25; i++) {
      const cell = p.board[i];
      if (
        cell &&
        typeof cell === "object" &&
        typeof (cell as any).level === "number" &&
        (cell as any).level >= 1 &&
        (cell as any).level <= ECONOMY.maxEggLevel
      ) {
        board[i] = {
          id:
            typeof (cell as any).id === "string" && (cell as any).id
              ? (cell as any).id
              : `egg-restored-${i}`,
          level: Math.floor((cell as any).level),
        };
      }
    }
  }

  // Очередь яиц
  const queue: Egg[] = [];
  if (Array.isArray(p.queue)) {
    for (const q of p.queue) {
      if (
        q &&
        typeof q === "object" &&
        typeof (q as any).level === "number" &&
        (q as any).level >= 1 &&
        (q as any).level <= ECONOMY.maxEggLevel
      ) {
        queue.push({
          id:
            typeof (q as any).id === "string" && (q as any).id
              ? (q as any).id
              : `egg-queue-${queue.length}`,
          level: Math.floor((q as any).level),
        });
      }
    }
  }

  // Каталог яиц
  const eggs: Egg[] = [];
  if (Array.isArray(p.eggs)) {
    for (const e of p.eggs) {
      if (
        e &&
        typeof e === "object" &&
        typeof (e as any).level === "number" &&
        (e as any).level >= 1 &&
        (e as any).level <= ECONOMY.maxEggLevel
      ) {
        eggs.push({
          id:
            typeof (e as any).id === "string" && (e as any).id
              ? (e as any).id
              : `egg-${eggs.length}`,
          level: Math.floor((e as any).level),
        });
      }
    }
  }

  return {
    seeds,
    xp,
    level,
    rarity,
    cycleFeeds,
    cycleStartedAt,
    birds,
    activeBirdId,
    totalFeeds,
    eggs,
    queue,
    board,
    hatched,
    lastCrumbsAt,
    lvl4BirdAwarded,
  };
}
