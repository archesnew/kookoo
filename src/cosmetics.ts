/**
 * Модуль каталога черт и косметики KOO KOO (только данные и типы).
 * Синхронизирован с реальными ассетами в public/assets/pigeon/.
 */

export type CosmeticSlot = "eyes" | "shoes" | "clothing" | "hat";

export type CosmeticRarity =
  | "common"
  | "uncommon"
  | "rare"
  | "epic"
  | "legendary"
  | "mythic";

export interface CosmeticItem {
  id: string;
  slot: CosmeticSlot;
  name: string;
  rarity: CosmeticRarity;
  assetPath: string;
  zIndex: number;
}

export interface ClothingItem extends CosmeticItem {
  slot: "clothing";
  hidesNeck: boolean;
}

/**
 * Порядок слоёв косметики по z-index (снизу вверх):
 * 1. shoes (20) — обувь на лапках
 * 2. clothing (30) — одежда
 * 3. eyes (50) — глаза/взгляд
 * 4. hat (60) — головные уборы
 */
export const LAYER_ORDER: readonly CosmeticSlot[] = [
  "shoes",
  "clothing",
  "eyes",
  "hat",
] as const;

export const SLOT_Z_INDEX: Record<CosmeticSlot, number> = {
  shoes: 20,
  clothing: 30,
  eyes: 50,
  hat: 60,
};

export interface PigeonTraits {
  eyes: string;
  skin?: string | null;
  shoes?: string | null;
  clothing?: string | null;
  hat?: string | null;
  // Опциональные legacy-поля для обратной совместимости старых сохранений koo-koo-v01
  beak?: string | null;
  tattoo?: string | null;
}

/* ───────── Генератор детерминированного RNG ───────── */
export function createDeterministicRng(seed: string | number): () => number {
  let h = typeof seed === "number" ? seed : 0;
  if (typeof seed === "string") {
    for (let i = 0; i < seed.length; i++) {
      h = (Math.imul(31, h) + seed.charCodeAt(i)) | 0;
    }
  }
  let s = (h ^ 0xdeadbeef) >>> 0;
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

export const SKIN_SLUGS = [
  "wedding-white",
  "sandy-cappuccino",
  "obsidian-black",
  "peacock-emerald",
  "golden-gilded",
  "cosmic-holographic",
  "zebra-sketch",
  "firework-neon-splash",
  "pumpkin-orange",
  "shimmering-ruby-quartz",
  "patchwork-plush",
  "cherry-blossom",
  "fire-lava",
  "pink-flamingo",
  "cyberpunk-neon",
  "blue-frost-ice",
  "spotted-leopard",
  "iridescent-oil-slick",
] as const;

/* ───────── 1. EYES (10 вариантов) ───────── */
export const EYES_CATALOG: CosmeticItem[] = [
  { id: "01", slot: "eyes", name: "Базовый (grumpy)", rarity: "common", assetPath: "pigeon/eyes-01.webp", zIndex: SLOT_Z_INDEX.eyes },
  { id: "02", slot: "eyes", name: "Сияющий (sparkle)", rarity: "common", assetPath: "pigeon/eyes-sparkle.webp", zIndex: SLOT_Z_INDEX.eyes },
  { id: "03", slot: "eyes", name: "Сонный (sleepy)", rarity: "uncommon", assetPath: "pigeon/eyes-sleepy.webp", zIndex: SLOT_Z_INDEX.eyes },
  { id: "04", slot: "eyes", name: "Аниме (anime)", rarity: "uncommon", assetPath: "pigeon/eyes-anime.webp", zIndex: SLOT_Z_INDEX.eyes },
  { id: "05", slot: "eyes", name: "Босс (boss)", rarity: "rare", assetPath: "pigeon/eyes-boss.webp", zIndex: SLOT_Z_INDEX.eyes },
  { id: "06", slot: "eyes", name: "Кибер (cyber)", rarity: "rare", assetPath: "pigeon/eyes-cyber.webp", zIndex: SLOT_Z_INDEX.eyes },
  { id: "07", slot: "eyes", name: "Берсерк (berserk)", rarity: "epic", assetPath: "pigeon/eyes-berserk.webp", zIndex: SLOT_Z_INDEX.eyes },
  { id: "08", slot: "eyes", name: "Богатый (rich)", rarity: "epic", assetPath: "pigeon/eyes-rich.webp", zIndex: SLOT_Z_INDEX.eyes },
  { id: "09", slot: "eyes", name: "Жнец (reaper)", rarity: "legendary", assetPath: "pigeon/eyes-reaper.webp", zIndex: SLOT_Z_INDEX.eyes },
  { id: "10", slot: "eyes", name: "Безумный (crazy)", rarity: "mythic", assetPath: "pigeon/eyes-crazy.webp", zIndex: SLOT_Z_INDEX.eyes },
];

/* ───────── 2. SHOES (18 вариантов) ───────── */
export const SHOES_CATALOG: CosmeticItem[] = Array.from({ length: 18 }, (_, i) => {
  const id = String(i + 1).padStart(2, "0");
  const rarities: CosmeticRarity[] = ["common", "uncommon", "rare", "epic", "legendary", "mythic"];
  return {
    id,
    slot: "shoes",
    name: `Обувь #${id}`,
    rarity: rarities[Math.min(5, Math.floor(i / 3))],
    assetPath: `pigeon/shoes/shoes-${id}.webp`,
    zIndex: SLOT_Z_INDEX.shoes,
  };
});

/* ───────── 3. CLOTHING (18 вариантов) ───────── */
export const CLOTHING_CATALOG: ClothingItem[] = Array.from({ length: 18 }, (_, i) => {
  const id = String(i + 1).padStart(2, "0");
  const rarities: CosmeticRarity[] = ["common", "uncommon", "rare", "epic", "legendary", "mythic"];
  return {
    id,
    slot: "clothing",
    name: `Одежда #${id}`,
    rarity: rarities[Math.min(5, Math.floor(i / 3))],
    assetPath: `pigeon/clothes/clothes-${id}.webp`,
    zIndex: SLOT_Z_INDEX.clothing,
    hidesNeck: false,
  };
});

/* ───────── 4. HAT (18 вариантов) ───────── */
export const HAT_CATALOG: CosmeticItem[] = Array.from({ length: 18 }, (_, i) => {
  const id = String(i + 1).padStart(2, "0");
  const rarities: CosmeticRarity[] = ["common", "uncommon", "rare", "epic", "legendary", "mythic"];
  return {
    id,
    slot: "hat",
    name: `Шапка #${id}`,
    rarity: rarities[Math.min(5, Math.floor(i / 3))],
    assetPath: `pigeon/hats/hats-${id}.webp`,
    zIndex: SLOT_Z_INDEX.hat,
  };
});

/**
 * Детерминированная генерация черт голубя на основе его редкости и сида/RNG.
 */
export function generatePigeonTraits(
  rarity: number,
  rngOrSeed: number | string | (() => number) = Math.random
): PigeonTraits {
  const rng =
    typeof rngOrSeed === "function"
      ? rngOrSeed
      : createDeterministicRng(rngOrSeed);

  const pickIndex = (max: number) => Math.floor(rng() * max);

  const eyes = EYES_CATALOG[pickIndex(EYES_CATALOG.length)].id;
  const skin =
    rarity >= 1 && rng() < 0.35 + Math.min(rarity * 0.1, 0.5)
      ? SKIN_SLUGS[pickIndex(SKIN_SLUGS.length)]
      : null;

  const accessoryChance = 0.5 + Math.min(rarity * 0.09, 0.45);

  const clothing =
    rng() < accessoryChance
      ? CLOTHING_CATALOG[pickIndex(CLOTHING_CATALOG.length)].id
      : null;

  const hat =
    rng() < accessoryChance
      ? HAT_CATALOG[pickIndex(HAT_CATALOG.length)].id
      : null;

  const shoes =
    rng() < accessoryChance * 0.8
      ? SHOES_CATALOG[pickIndex(SHOES_CATALOG.length)].id
      : null;

  return {
    eyes,
    skin,
    shoes,
    clothing,
    hat,
  };
}
