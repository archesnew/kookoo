import { describe, it, expect } from "vitest";
import {
  ECONOMY,
  feedCost,
  feed,
  initialGame,
  merge,
  hatch,
  placeFromQueue,
  rollEggLevel,
  minFeedCost,
  canCollectCrumbs,
  collectCrumbs,
  migrateGameState,
  type Game,
} from "./economy";
import {
  COSMETICS_CATALOG,
  LAYER_ORDER,
  SLOT_Z_INDEX,
  generatePigeonTraits,
} from "./cosmetics";

describe("KOO KOO Economy v0.2", () => {
  /* ───────── 1. Граничные ступени цены ───────── */
  describe("Ступени стоимости кормления и границы", () => {
    it("проверяет точные множители на границах 20→21, 40→41, 100→101 для всех редкостей", () => {
      // Граница 20 → 21 (переход ×1 → ×2)
      expect(feedCost(0, 19)).toBe(1); // 20-е кормление, Обычный
      expect(feedCost(0, 20)).toBe(2); // 21-е кормление, Обычный
      expect(feedCost(1, 19)).toBe(5); // 20-е кормление, Необычный (5 × 1)
      expect(feedCost(1, 20)).toBe(10); // 21-е кормление, Необычный (5 × 2)
      expect(feedCost(5, 19)).toBe(100); // 20-е кормление, Мифический (100 × 1)
      expect(feedCost(5, 20)).toBe(200); // 21-е кормление, Мифический (100 × 2)

      // Граница 40 → 41 (переход ×2 → ×3)
      expect(feedCost(0, 39)).toBe(2); // 40-е кормление
      expect(feedCost(0, 40)).toBe(3); // 41-е кормление
      expect(feedCost(2, 39)).toBe(30); // 40-е кормление, Редкий (15 × 2)
      expect(feedCost(2, 40)).toBe(45); // 41-е кормление, Редкий (15 × 3)

      // Граница 55 → 56 (переход ×3 → ×4)
      expect(feedCost(0, 54)).toBe(3);
      expect(feedCost(0, 55)).toBe(4);

      // Граница 70 → 71 (переход ×4 → ×5)
      expect(feedCost(0, 69)).toBe(4);
      expect(feedCost(0, 70)).toBe(5);

      // Граница 80 → 81 (переход ×5 → ×6)
      expect(feedCost(0, 79)).toBe(5);
      expect(feedCost(0, 80)).toBe(6);

      // Граница 90 → 91 (переход ×6 → ×8)
      expect(feedCost(0, 89)).toBe(6);
      expect(feedCost(0, 90)).toBe(8);

      // Граница 95 → 96 (переход ×8 → ×10)
      expect(feedCost(0, 94)).toBe(8);
      expect(feedCost(0, 95)).toBe(10);

      // Граница 100 → 101 (переход ×10 → ×12, далее +2 каждые 5 кормлений)
      expect(feedCost(0, 99)).toBe(10); // 100-е кормление
      expect(feedCost(0, 100)).toBe(12); // 101-е кормление
      expect(feedCost(0, 104)).toBe(12); // 105-е кормление
      expect(feedCost(0, 105)).toBe(14); // 106-е кормление
      expect(feedCost(3, 99)).toBe(300); // 100-е кормление, Эпический (30 × 10)
      expect(feedCost(3, 100)).toBe(360); // 101-е кормление, Эпический (30 × 12)
    });
  });

  /* ───────── 2. Сброс 8-часового цикла без потери опыта ───────── */
  describe("Сброс 8-часового цикла кормления", () => {
    it("сбрасывает стоимость до базовой ровно через 8 часов, сохраняя весь накопленный опыт", () => {
      let g = initialGame();
      const t0 = 1000000;

      // Кормим 25 раз в первом цикле (затраты: 20 по 1 + 5 по 2 = 30 семечек, опыт: 250)
      for (let i = 0; i < 25; i++) {
        g = feed(g, t0 + i * 1000);
      }
      expect(g.cycleFeeds).toBe(25);
      expect(g.xp).toBe(250);
      expect(g.seeds).toBe(1000 - 30);
      expect(feedCost(0, g.cycleFeeds)).toBe(2); // следующая цена до сброса = 2

      // Кормим до истечения 8 часов (через 7.5 часов) — цикл НЕ сбрасывается
      const tMid = t0 + 7.5 * 3600 * 1000;
      g = feed(g, tMid);
      expect(g.cycleFeeds).toBe(26);
      expect(g.xp).toBe(260);

      // Прошло 8 часов с момента первого кормления — следующий корм сбрасывает счётчик цикла
      const tAfter8h = t0 + ECONOMY.feedCycleMs + 10;
      g = feed(g, tAfter8h);

      // cycleFeeds стал 1 (новый цикл начался)
      expect(g.cycleFeeds).toBe(1);
      // Списалась базовая цена (1 семечка для обычного голубя)
      expect(g.seeds).toBe(1000 - 30 - 2 - 1);
      // Опыт НЕ сбросился и увеличился на +10 (было 260 -> стало 270)
      expect(g.xp).toBe(270);
      // Новый таймер цикла зафиксирован на tAfter8h
      expect(g.cycleStartedAt).toBe(tAfter8h);
    });

    it("сохраняет независимые таймеры циклов для каждого голубя", () => {
      let g = initialGame();
      g = feed(g, 100);
      g = {
        ...g,
        birds: [
          ...g.birds,
          { id: "bird-002", rarity: 1, cycleFeeds: 0, cycleStartedAt: null },
        ],
        activeBirdId: "bird-002",
      };
      g = feed(g, 500);

      const b1 = g.birds.find((b) => b.id === "bird-001");
      const b2 = g.birds.find((b) => b.id === "bird-002");
      expect(b1?.cycleStartedAt).toBe(100);
      expect(b2?.cycleStartedAt).toBe(500);
    });
  });

  /* ───────── 3. Окно дропа уровня яйца по редкости (v0.2) ───────── */
  describe("Окно дропа уровня яйца по редкости голубя (v0.2)", () => {
    it("выдаёт правильные уровни яиц (75% / 20% / 5%) для Обычного голубя (rarity 0)", () => {
      // 75% -> LVL 1 (r < 0.75)
      expect(rollEggLevel(0, () => 0.0)).toBe(1);
      expect(rollEggLevel(0, () => 0.74)).toBe(1);
      // 20% -> LVL 2 (0.75 <= r < 0.95)
      expect(rollEggLevel(0, () => 0.75)).toBe(2);
      expect(rollEggLevel(0, () => 0.94)).toBe(2);
      // 5% -> LVL 3 (r >= 0.95)
      expect(rollEggLevel(0, () => 0.95)).toBe(3);
      expect(rollEggLevel(0, () => 0.999)).toBe(3);
    });

    it("выдаёт правильные уровни яиц для всех градаций редкости голубей", () => {
      // Необычный (1): LVL 2 (75%), LVL 3 (20%), LVL 4 (5%)
      expect(rollEggLevel(1, () => 0.5)).toBe(2);
      expect(rollEggLevel(1, () => 0.8)).toBe(3);
      expect(rollEggLevel(1, () => 0.96)).toBe(4);

      // Редкий (2): LVL 3 (75%), LVL 4 (20%), LVL 5 (5%)
      expect(rollEggLevel(2, () => 0.5)).toBe(3);
      expect(rollEggLevel(2, () => 0.8)).toBe(4);
      expect(rollEggLevel(2, () => 0.96)).toBe(5);

      // Эпический (3): LVL 4 (75%), LVL 5 (20%), LVL 6 (5%)
      expect(rollEggLevel(3, () => 0.5)).toBe(4);
      expect(rollEggLevel(3, () => 0.8)).toBe(5);
      expect(rollEggLevel(3, () => 0.96)).toBe(6);

      // Легендарный (4): LVL 5 (75%), LVL 6 (20%), LVL 7 (5%)
      expect(rollEggLevel(4, () => 0.5)).toBe(5);
      expect(rollEggLevel(4, () => 0.8)).toBe(6);
      expect(rollEggLevel(4, () => 0.96)).toBe(7);

      // Мифический (5): LVL 6 (75%), LVL 7 (20%), LVL 8 (5%)
      expect(rollEggLevel(5, () => 0.5)).toBe(6);
      expect(rollEggLevel(5, () => 0.8)).toBe(7);
      expect(rollEggLevel(5, () => 0.96)).toBe(8);
    });

    it("добавляет полученное яйцо соответствующего уровня в eggs и queue каждые 5 кормлений", () => {
      let g = initialGame();
      // Эпический голубь (rarity 3)
      g = {
        ...g,
        birds: [
          { id: "bird-epic", rarity: 3, cycleFeeds: 0, cycleStartedAt: null },
        ],
        activeBirdId: "bird-epic",
      };

      // Первые 4 кормления яйцо не дают
      for (let n = 1; n <= 4; n++) g = feed(g, n * 100);
      expect(g.eggs).toHaveLength(0);
      expect(g.queue).toHaveLength(0);

      // 5-е кормление с RNG = 0.8 (должно дать яйцо LVL 5: rarity 3 + offset 2)
      g = feed(g, 500, () => 0.8);
      expect(g.eggs).toHaveLength(1);
      expect(g.queue).toHaveLength(1);
      expect(g.eggs[0].level).toBe(5);
      expect(g.queue[0].level).toBe(5);
    });
  });

  /* ───────── 4. Скорректированные шансы голубя на старших яйцах ───────── */
  describe("Шансы выпадения голубя на старших яйцах (v0.2)", () => {
    it("соответствует обновлённой спецификации v0.2 для LVL 9-12", () => {
      expect(ECONOMY.eggs[8].birdPct).toBe(0.0035); // LVL 9: 0.35%
      expect(ECONOMY.eggs[9].birdPct).toBe(0.0075); // LVL 10: 0.75%
      expect(ECONOMY.eggs[10].birdPct).toBe(0.016); // LVL 11: 1.6%
      expect(ECONOMY.eggs[11].birdPct).toBe(0.035); // LVL 12: 3.5%
    });
  });

  /* ───────── 5. Страховка от нулевого баланса («Собрать крошки») ───────── */
  describe("Страховка от нулевого баланса («Собрать крошки»)", () => {
    it("разрешает сбор крошек только когда seeds < minCost и нет яиц на поле и в очереди", () => {
      let g: Game = { ...initialGame(), seeds: 0, board: Array(25).fill(null), queue: [] };
      const now = 1000000;

      // Все условия выполнены: seeds=0, board пуст, queue пуста
      expect(minFeedCost(g)).toBe(1);
      expect(canCollectCrumbs(g, now)).toBe(true);

      // Собираем крошки
      g = collectCrumbs(g, now);
      expect(g.seeds).toBe(25);
      expect(g.lastCrumbsAt).toBe(now);

      // Теперь seeds=25 >= minFeedCost(1) -> нельзя собирать
      expect(canCollectCrumbs(g, now + 1000)).toBe(false);
    });

    it("запрещает сбор крошек, если на поле есть яйцо (его можно разбить)", () => {
      const g: Game = {
        ...initialGame(),
        seeds: 0,
        board: Array(25).fill(null).map((_, i) => (i === 3 ? { id: "egg-1", level: 1 } : null)),
        queue: [],
      };
      expect(canCollectCrumbs(g, 1000)).toBe(false);
    });

    it("запрещает сбор крошек, если в очереди есть яйцо", () => {
      const g: Game = {
        ...initialGame(),
        seeds: 0,
        board: Array(25).fill(null),
        queue: [{ id: "q-1", level: 1 }],
      };
      expect(canCollectCrumbs(g, 1000)).toBe(false);
    });

    it("соблюдает кулдаун в 1 час между сборами крошек", () => {
      let g: Game = { ...initialGame(), seeds: 0, board: Array(25).fill(null), queue: [] };
      const t0 = 1000000;
      g = collectCrumbs(g, t0);
      g = { ...g, seeds: 0 }; // потратил крошки

      // Через 30 минут — кулдаун ещё действует
      expect(canCollectCrumbs(g, t0 + 30 * 60 * 1000)).toBe(false);
      expect(collectCrumbs(g, t0 + 30 * 60 * 1000).seeds).toBe(0);

      // Ровно через 1 час (3600000 мс) — можно собирать снова
      expect(canCollectCrumbs(g, t0 + ECONOMY.crumbsCooldownMs)).toBe(true);
      const g2 = collectCrumbs(g, t0 + ECONOMY.crumbsCooldownMs);
      expect(g2.seeds).toBe(25);
    });
  });

  /* ───────── 6. Стартовая цель-достижение: голубь за яйцо LVL 4 ───────── */
  describe("Стартовая цель-достижение (яйцо LVL 4)", () => {
    it("выдаёт гарантированного второго обычного голубя за первое разбитие яйца уровня 4", () => {
      let g: Game = {
        ...initialGame(),
        board: Array(25).fill(null).map((_, i) => (i === 0 ? { id: "egg-lvl4", level: 4 } : null)),
        birds: [{ id: "bird-001", rarity: 0, cycleFeeds: 0, cycleStartedAt: null }],
        lvl4BirdAwarded: false,
      };

      const result = hatch(g, 0, () => 0.5)!;
      expect(result).not.toBeNull();
      expect(result.achievementBird).toBe(true);
      expect(result.game.lvl4BirdAwarded).toBe(true);
      expect(result.game.birds).toHaveLength(2);
      expect(result.game.birds[1].id).toBe("bird-002");
      expect(result.game.birds[1].rarity).toBe(0); // Обычный
    });

    it("НЕ выдаёт голубя повторно при втором разбитии яйца LVL 4 или LVL 5", () => {
      let g: Game = {
        ...initialGame(),
        board: Array(25).fill(null).map((_, i) => (i === 0 ? { id: "egg-lvl4-second", level: 4 } : null)),
        birds: [
          { id: "bird-001", rarity: 0, cycleFeeds: 0, cycleStartedAt: null },
          { id: "bird-002", rarity: 0, cycleFeeds: 0, cycleStartedAt: null },
        ],
        lvl4BirdAwarded: true, // уже получено ранее
      };

      const result = hatch(g, 0, () => 0.5)!;
      expect(result.achievementBird).toBe(false);
      expect(result.game.birds).toHaveLength(2); // количество птиц не изменилось
    });

    it("НЕ выдаёт голубя за достижение при разбитии яиц уровней 1–3", () => {
      for (const level of [1, 2, 3]) {
        const g: Game = {
          ...initialGame(),
          board: Array(25).fill(null).map((_, i) => (i === 0 ? { id: `egg-lvl${level}`, level } : null)),
          lvl4BirdAwarded: false,
        };
        const result = hatch(g, 0, () => 0.5)!;
        expect(result.achievementBird).toBe(false);
        expect(result.game.birds).toHaveLength(1);
        expect(result.game.lvl4BirdAwarded).toBe(false);
      }
    });
  });

  /* ───────── 7. Воспроизводимость RNG ───────── */
  describe("Воспроизводимость RNG", () => {
    it("гарантирует 100% идентичные результаты при фиксированном или сидированном RNG", () => {
      const createLcg = (seed: number) => {
        let s = seed;
        return () => {
          s = (s * 1664525 + 1013904223) % 4294967296;
          return s / 4294967296;
        };
      };

      const baseState: Game = {
        ...initialGame(),
        seeds: 100,
        board: Array(25).fill(null).map((_, i) => (i === 0 ? { id: "egg-test", level: 6 } : null)),
      };

      const run1 = hatch(baseState, 0, createLcg(42));
      const run2 = hatch(baseState, 0, createLcg(42));

      expect(run1).toEqual(run2);
      expect(run1?.reward).toBe(run2?.reward);
      expect(run1?.jackpot).toBe(run2?.jackpot);
      expect(run1?.bird).toBe(run2?.bird);
    });

    it("выдаёт джекпот и голубя при малом RNG ниже порогов", () => {
      const g: Game = {
        ...initialGame(),
        board: Array(25).fill(null).map((_, i) => (i === 0 ? { id: "egg-jackpot", level: 1 } : null)),
      };
      // LVL 1: jackpotPct = 0.01, birdPct = 0.00001
      const res = hatch(g, 0, () => 0.000001)!;
      expect(res.jackpot).toBe(true);
      expect(res.bird).toBe(true);
      expect(res.reward).toBe(10 + 100); // base + jackpot
    });
  });

  /* ───────── 8. Миграция сохранённого состояния `koo-koo-v01` ───────── */
  describe("Миграция сохранённого состояния koo-koo-v01", () => {
    it("корректно восстанавливает дефолтные значения из пустых/невалидных данных", () => {
      const empty = migrateGameState(null);
      expect(empty.seeds).toBe(1000);
      expect(empty.birds).toHaveLength(1);
      expect(empty.board).toHaveLength(25);
      expect(empty.lastCrumbsAt).toBeNull();
      expect(empty.lvl4BirdAwarded).toBe(false);
    });

    it("мигрирует ранний v0 стейт без birds, queue и board, сохраняя семечки и опыт", () => {
      const legacy = {
        seeds: 840,
        xp: 160,
        level: 2,
        rarity: 1,
        cycleFeeds: 8,
        cycleStartedAt: 1700000000,
        totalFeeds: 30,
      };

      const migrated = migrateGameState(legacy);
      expect(migrated.seeds).toBe(840);
      expect(migrated.xp).toBe(160);
      expect(migrated.level).toBe(2);
      expect(migrated.rarity).toBe(1);
      expect(migrated.birds).toHaveLength(1);
      expect(migrated.birds[0].id).toBe("bird-001");
      expect(migrated.birds[0].rarity).toBe(1);
      expect(migrated.birds[0].cycleFeeds).toBe(8);
      expect(migrated.board).toHaveLength(25);
      expect(migrated.queue).toHaveLength(0);
      expect(migrated.lastCrumbsAt).toBeNull();
      expect(migrated.lvl4BirdAwarded).toBe(false);
    });

    it("сохраняет существующие яйца на поле и в очереди при валидации", () => {
      const stateWithEggs = {
        seeds: 500,
        xp: 90,
        board: [
          { id: "e1", level: 3 },
          null,
          { id: "e2", level: 7 },
        ],
        queue: [{ id: "q1", level: 2 }],
        lvl4BirdAwarded: true,
        lastCrumbsAt: 1234567,
      };

      const migrated = migrateGameState(stateWithEggs);
      expect(migrated.board).toHaveLength(25);
      expect(migrated.board[0]?.level).toBe(3);
      expect(migrated.board[1]).toBeNull();
      expect(migrated.board[2]?.level).toBe(7);
      expect(migrated.queue).toHaveLength(1);
      expect(migrated.queue[0].level).toBe(2);
      expect(migrated.lvl4BirdAwarded).toBe(true);
      expect(migrated.lastCrumbsAt).toBe(1234567);
    });
  });

  /* ───────── 9. Базовые правила игры ───────── */
  describe("Базовые правила игры (merge, placement, zero guards)", () => {
    it("объединяет одинаковые яйца до 12 уровня, отклоняет 12 и невалидные индексы", () => {
      let g = initialGame();
      g.board[0] = { id: "a", level: 11 };
      g.board[1] = { id: "b", level: 11 };
      g = merge(g, 0, 1);
      expect(g.board[0]?.level).toBe(12);
      expect(g.board[1]).toBeNull();

      g.board[0] = { id: "c", level: 12 };
      g.board[1] = { id: "d", level: 12 };
      expect(merge(g, 0, 1).board[0]?.level).toBe(12);
      expect(merge(g, -1, 1)).toBe(g);
    });

    it("не делает баланс семечек отрицательным при недостатке средств", () => {
      const g = { ...initialGame(), seeds: 0 };
      expect(feed(g, 10)).toBe(g);
      expect(g.seeds).toBe(0);
    });

    it("сохраняет яйца в очереди пока они не размещены в пустую ячейку", () => {
      const g: Game = { ...initialGame(), queue: [{ id: "q", level: 2 }] };
      expect(placeFromQueue(g, "q", 0).queue).toHaveLength(0);
      expect(
        placeFromQueue(
          { ...g, board: g.board.map((_, i) => (i === 0 ? { id: "x", level: 1 } : null)) },
          "q",
          0
        ).queue
      ).toHaveLength(1);
    });
  });

  /* ───────── 10. Каталог черт и косметики (cosmetics.ts) ───────── */
  describe("Каталог черт и косметики (cosmetics.ts)", () => {
    it("содержит требуемое количество предметов по слотам (eyes:10, shoes:20, clothing:20, hat:20, tattoo:20, beak:20)", () => {
      expect(COSMETICS_CATALOG.eyes).toHaveLength(10);
      expect(COSMETICS_CATALOG.shoes).toHaveLength(20);
      expect(COSMETICS_CATALOG.clothing).toHaveLength(20);
      expect(COSMETICS_CATALOG.hat).toHaveLength(20);
      expect(COSMETICS_CATALOG.tattoo).toHaveLength(20);
      expect(COSMETICS_CATALOG.beak).toHaveLength(20);

      const totalItems =
        COSMETICS_CATALOG.eyes.length +
        COSMETICS_CATALOG.shoes.length +
        COSMETICS_CATALOG.clothing.length +
        COSMETICS_CATALOG.hat.length +
        COSMETICS_CATALOG.tattoo.length +
        COSMETICS_CATALOG.beak.length;
      expect(totalItems).toBe(110);
    });

    it("проверяет корректность путей ассетов (pigeon/{slot}-{id}.webp) и zIndex", () => {
      for (const item of COSMETICS_CATALOG.eyes) {
        expect(item.assetPath).toBe(`pigeon/eyes-${item.id}.webp`);
        expect(item.zIndex).toBe(SLOT_Z_INDEX.eyes);
      }
      for (const item of COSMETICS_CATALOG.clothing) {
        expect(item.assetPath).toBe(`pigeon/clothing-${item.id}.webp`);
        expect(typeof item.hidesNeck).toBe("boolean");
        expect(item.zIndex).toBe(SLOT_Z_INDEX.clothing);
      }
      for (const item of COSMETICS_CATALOG.shoes) {
        expect(item.assetPath).toBe(`pigeon/shoes-${item.id}.webp`);
      }
      for (const item of COSMETICS_CATALOG.hat) {
        expect(item.assetPath).toBe(`pigeon/hat-${item.id}.webp`);
      }
      for (const item of COSMETICS_CATALOG.tattoo) {
        expect(item.assetPath).toBe(`pigeon/tattoo-${item.id}.webp`);
      }
      for (const item of COSMETICS_CATALOG.beak) {
        expect(item.assetPath).toBe(`pigeon/beak-${item.id}.webp`);
      }
    });

    it("соблюдает порядок слоёв LAYER_ORDER (tattoo -> shoes -> clothing -> beak -> eyes -> hat)", () => {
      expect(LAYER_ORDER).toEqual([
        "tattoo",
        "shoes",
        "clothing",
        "beak",
        "eyes",
        "hat",
      ]);
      expect(SLOT_Z_INDEX.tattoo).toBeLessThan(SLOT_Z_INDEX.shoes);
      expect(SLOT_Z_INDEX.shoes).toBeLessThan(SLOT_Z_INDEX.clothing);
      expect(SLOT_Z_INDEX.clothing).toBeLessThan(SLOT_Z_INDEX.beak);
      expect(SLOT_Z_INDEX.beak).toBeLessThan(SLOT_Z_INDEX.eyes);
      expect(SLOT_Z_INDEX.eyes).toBeLessThan(SLOT_Z_INDEX.hat);
    });

    it("генерирует детерминированные черты голубя при фиксированном сиде/id", () => {
      const traits1 = generatePigeonTraits(0, "bird-001");
      const traits2 = generatePigeonTraits(0, "bird-001");
      expect(traits1).toEqual(traits2);
      expect(traits1.eyes).toBeTruthy();
      expect(traits1.beak).toBeTruthy();

      const traitsDiff = generatePigeonTraits(0, "bird-diff-seed-999");
      // Разные сиды дают валидные черты
      expect(traitsDiff.eyes).toBeTruthy();
      expect(traitsDiff.beak).toBeTruthy();
    });

    it("при миграции старого сохранения koo-koo-v01 детерминированно дозаполняет traits без потери данных", () => {
      const legacyState = {
        seeds: 777,
        xp: 120,
        level: 2,
        rarity: 0,
        cycleFeeds: 3,
        cycleStartedAt: 1000,
        birds: [
          { id: "bird-001", rarity: 0, cycleFeeds: 3, cycleStartedAt: 1000 },
          { id: "bird-002", rarity: 1, cycleFeeds: 0, cycleStartedAt: null },
        ],
        activeBirdId: "bird-001",
        totalFeeds: 10,
        eggs: [],
        queue: [],
        board: Array(25).fill(null),
        hatched: 1,
      };

      const migrated = migrateGameState(legacyState);
      expect(migrated.seeds).toBe(777);
      expect(migrated.xp).toBe(120);
      expect(migrated.birds).toHaveLength(2);

      // Проверяем детерминированность traits у обоих голубей
      const b1 = migrated.birds[0];
      const b2 = migrated.birds[1];
      expect(b1.traits).toBeDefined();
      expect(b2.traits).toBeDefined();
      expect(b1.traits?.eyes).toBeTruthy();
      expect(b1.traits?.beak).toBeTruthy();
      expect(b2.traits?.eyes).toBeTruthy();

      // Повторная миграция того же объекта даёт точно такие же traits
      const migratedAgain = migrateGameState(legacyState);
      expect(migratedAgain.birds[0].traits).toEqual(b1.traits);
      expect(migratedAgain.birds[1].traits).toEqual(b2.traits);
    });
  });
});
