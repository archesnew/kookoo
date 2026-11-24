/**
 * Модуль каталога черт и косметики KOO KOO (только данные и типы).
 * Описывает слои с порядком z-index, предметы гардероба и генерацию черт голубя.
 */

export type CosmeticSlot =
  | "eyes"
  | "shoes"
  | "clothing"
  | "hat"
  | "tattoo"
  | "beak";

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
  assetPath: string; // pigeon/{slot}-{id}.webp
  zIndex: number;
}

export interface ClothingItem extends CosmeticItem {
  slot: "clothing";
  hidesNeck: boolean; // скрывает ли шею (требует доступного индикатора редкости)
}

/**
 * Порядок слоёв персонажа по z-index (снизу вверх):
 * 1. tattoo (10) — татуировки/метки на теле
 * 2. shoes (20) — обувь на лапках
 * 3. clothing (30) — худи/куртки/одежда
 * 4. beak (40) — клюв
 * 5. eyes (50) — глаза/взгляд
 * 6. hat (60) — головные уборы/панамы
 */
export const LAYER_ORDER: readonly CosmeticSlot[] = [
  "tattoo",
  "shoes",
  "clothing",
  "beak",
  "eyes",
  "hat",
] as const;

export const SLOT_Z_INDEX: Record<CosmeticSlot, number> = {
  tattoo: 10,
  shoes: 20,
  clothing: 30,
  beak: 40,
  eyes: 50,
  hat: 60,
};

export interface PigeonTraits {
  eyes: string;
  beak: string;
  shoes?: string | null;
  clothing?: string | null;
  hat?: string | null;
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

/* ───────── 1. EYES (10 вариантов) ───────── */
export const EYES_CATALOG: CosmeticItem[] = [
  { id: "01", slot: "eyes", name: "Классический взгляд", rarity: "common", assetPath: "pigeon/eyes-01.webp", zIndex: SLOT_Z_INDEX.eyes },
  { id: "02", slot: "eyes", name: "Хитрый прищур", rarity: "common", assetPath: "pigeon/eyes-02.webp", zIndex: SLOT_Z_INDEX.eyes },
  { id: "03", slot: "eyes", name: "Удивлённые бусины", rarity: "uncommon", assetPath: "pigeon/eyes-03.webp", zIndex: SLOT_Z_INDEX.eyes },
  { id: "04", slot: "eyes", name: "Сонные зенки", rarity: "uncommon", assetPath: "pigeon/eyes-04.webp", zIndex: SLOT_Z_INDEX.eyes },
  { id: "05", slot: "eyes", name: "Янтарный фокус", rarity: "rare", assetPath: "pigeon/eyes-05.webp", zIndex: SLOT_Z_INDEX.eyes },
  { id: "06", slot: "eyes", name: "Неоновый глянец", rarity: "rare", assetPath: "pigeon/eyes-06.webp", zIndex: SLOT_Z_INDEX.eyes },
  { id: "07", slot: "eyes", name: "Кибер-визор", rarity: "epic", assetPath: "pigeon/eyes-07.webp", zIndex: SLOT_Z_INDEX.eyes },
  { id: "08", slot: "eyes", name: "Аметистовый блеск", rarity: "epic", assetPath: "pigeon/eyes-08.webp", zIndex: SLOT_Z_INDEX.eyes },
  { id: "09", slot: "eyes", name: "Золотое пламя", rarity: "legendary", assetPath: "pigeon/eyes-09.webp", zIndex: SLOT_Z_INDEX.eyes },
  { id: "10", slot: "eyes", name: "Радужная сингулярность", rarity: "mythic", assetPath: "pigeon/eyes-10.webp", zIndex: SLOT_Z_INDEX.eyes },
];

/* ───────── 2. SHOES (20 вариантов) ───────── */
export const SHOES_CATALOG: CosmeticItem[] = [
  { id: "01", slot: "shoes", name: "Босые лапки", rarity: "common", assetPath: "pigeon/shoes-01.webp", zIndex: SLOT_Z_INDEX.shoes },
  { id: "02", slot: "shoes", name: "Вязаные носочки", rarity: "common", assetPath: "pigeon/shoes-02.webp", zIndex: SLOT_Z_INDEX.shoes },
  { id: "03", slot: "shoes", name: "Уличные кеды", rarity: "common", assetPath: "pigeon/shoes-03.webp", zIndex: SLOT_Z_INDEX.shoes },
  { id: "04", slot: "shoes", name: "Резиновые галоши", rarity: "common", assetPath: "pigeon/shoes-04.webp", zIndex: SLOT_Z_INDEX.shoes },
  { id: "05", slot: "shoes", name: "Спортивные кроссы", rarity: "uncommon", assetPath: "pigeon/shoes-05.webp", zIndex: SLOT_Z_INDEX.shoes },
  { id: "06", slot: "shoes", name: "Жёлтые тимберы", rarity: "uncommon", assetPath: "pigeon/shoes-06.webp", zIndex: SLOT_Z_INDEX.shoes },
  { id: "07", slot: "shoes", name: "Шлёпанцы с носками", rarity: "uncommon", assetPath: "pigeon/shoes-07.webp", zIndex: SLOT_Z_INDEX.shoes },
  { id: "08", slot: "shoes", name: "Армейские берцы", rarity: "uncommon", assetPath: "pigeon/shoes-08.webp", zIndex: SLOT_Z_INDEX.shoes },
  { id: "09", slot: "shoes", name: "Скейтерские вансы", rarity: "rare", assetPath: "pigeon/shoes-09.webp", zIndex: SLOT_Z_INDEX.shoes },
  { id: "10", slot: "shoes", name: "Неоновые раннеры", rarity: "rare", assetPath: "pigeon/shoes-10.webp", zIndex: SLOT_Z_INDEX.shoes },
  { id: "11", slot: "shoes", name: "Ретро-хайтопы", rarity: "rare", assetPath: "pigeon/shoes-11.webp", zIndex: SLOT_Z_INDEX.shoes },
  { id: "12", slot: "shoes", name: "Лакированные туфли", rarity: "rare", assetPath: "pigeon/shoes-12.webp", zIndex: SLOT_Z_INDEX.shoes },
  { id: "13", slot: "shoes", name: "Тактические сапоги", rarity: "epic", assetPath: "pigeon/shoes-13.webp", zIndex: SLOT_Z_INDEX.shoes },
  { id: "14", slot: "shoes", name: "Светящиеся платформы", rarity: "epic", assetPath: "pigeon/shoes-14.webp", zIndex: SLOT_Z_INDEX.shoes },
  { id: "15", slot: "shoes", name: "Гравитационные боты", rarity: "epic", assetPath: "pigeon/shoes-15.webp", zIndex: SLOT_Z_INDEX.shoes },
  { id: "16", slot: "shoes", name: "Кибер-протекторы", rarity: "epic", assetPath: "pigeon/shoes-16.webp", zIndex: SLOT_Z_INDEX.shoes },
  { id: "17", slot: "shoes", name: "Золотые сникерсы", rarity: "legendary", assetPath: "pigeon/shoes-17.webp", zIndex: SLOT_Z_INDEX.shoes },
  { id: "18", slot: "shoes", name: "Алмазные когти", rarity: "legendary", assetPath: "pigeon/shoes-18.webp", zIndex: SLOT_Z_INDEX.shoes },
  { id: "19", slot: "shoes", name: "Эфирные сандалии Гермеса", rarity: "mythic", assetPath: "pigeon/shoes-19.webp", zIndex: SLOT_Z_INDEX.shoes },
  { id: "20", slot: "shoes", name: "Космические антигравы", rarity: "mythic", assetPath: "pigeon/shoes-20.webp", zIndex: SLOT_Z_INDEX.shoes },
];

/* ───────── 3. CLOTHING (20 вариантов, с флагом hidesNeck) ───────── */
export const CLOTHING_CATALOG: ClothingItem[] = [
  { id: "01", slot: "clothing", name: "Жёлтое худи оверсайз", rarity: "common", assetPath: "pigeon/clothing-01.webp", zIndex: SLOT_Z_INDEX.clothing, hidesNeck: false },
  { id: "02", slot: "clothing", name: "Серая базовая толстовка", rarity: "common", assetPath: "pigeon/clothing-02.webp", zIndex: SLOT_Z_INDEX.clothing, hidesNeck: false },
  { id: "03", slot: "clothing", name: "Джинсовая жилетка", rarity: "common", assetPath: "pigeon/clothing-03.webp", zIndex: SLOT_Z_INDEX.clothing, hidesNeck: false },
  { id: "04", slot: "clothing", name: "Вязаный шарф с бахромой", rarity: "common", assetPath: "pigeon/clothing-04.webp", zIndex: SLOT_Z_INDEX.clothing, hidesNeck: true },
  { id: "05", slot: "clothing", name: "Спортивная ветровка 90-х", rarity: "uncommon", assetPath: "pigeon/clothing-05.webp", zIndex: SLOT_Z_INDEX.clothing, hidesNeck: false },
  { id: "06", slot: "clothing", name: "Кожаный бомбер пилота", rarity: "uncommon", assetPath: "pigeon/clothing-06.webp", zIndex: SLOT_Z_INDEX.clothing, hidesNeck: false },
  { id: "07", slot: "clothing", name: "Тельняшка моряка", rarity: "uncommon", assetPath: "pigeon/clothing-07.webp", zIndex: SLOT_Z_INDEX.clothing, hidesNeck: false },
  { id: "08", slot: "clothing", name: "Зимний пуховик-дутыш", rarity: "uncommon", assetPath: "pigeon/clothing-08.webp", zIndex: SLOT_Z_INDEX.clothing, hidesNeck: true },
  { id: "09", slot: "clothing", name: "Флисовый анорак", rarity: "rare", assetPath: "pigeon/clothing-09.webp", zIndex: SLOT_Z_INDEX.clothing, hidesNeck: false },
  { id: "10", slot: "clothing", name: "Худи с принтом граффити", rarity: "rare", assetPath: "pigeon/clothing-10.webp", zIndex: SLOT_Z_INDEX.clothing, hidesNeck: false },
  { id: "11", slot: "clothing", name: "Косуха с заклёпками", rarity: "rare", assetPath: "pigeon/clothing-11.webp", zIndex: SLOT_Z_INDEX.clothing, hidesNeck: false },
  { id: "12", slot: "clothing", name: "Свитер с высоким воротом", rarity: "rare", assetPath: "pigeon/clothing-12.webp", zIndex: SLOT_Z_INDEX.clothing, hidesNeck: true },
  { id: "13", slot: "clothing", name: "Строгий смокинг джентльмена", rarity: "epic", assetPath: "pigeon/clothing-13.webp", zIndex: SLOT_Z_INDEX.clothing, hidesNeck: false },
  { id: "14", slot: "clothing", name: "Кибер-куртка с LED-подсветкой", rarity: "epic", assetPath: "pigeon/clothing-14.webp", zIndex: SLOT_Z_INDEX.clothing, hidesNeck: false },
  { id: "15", slot: "clothing", name: "Водолазка с золотой цепью", rarity: "epic", assetPath: "pigeon/clothing-15.webp", zIndex: SLOT_Z_INDEX.clothing, hidesNeck: true },
  { id: "16", slot: "clothing", name: "Тактический бронежилет", rarity: "epic", assetPath: "pigeon/clothing-16.webp", zIndex: SLOT_Z_INDEX.clothing, hidesNeck: false },
  { id: "17", slot: "clothing", name: "Королевская горностаевая мантия", rarity: "legendary", assetPath: "pigeon/clothing-17.webp", zIndex: SLOT_Z_INDEX.clothing, hidesNeck: true },
  { id: "18", slot: "clothing", name: "Золотой скафандр космонавта", rarity: "legendary", assetPath: "pigeon/clothing-18.webp", zIndex: SLOT_Z_INDEX.clothing, hidesNeck: true },
  { id: "19", slot: "clothing", name: "Плащ звёздного повелителя", rarity: "mythic", assetPath: "pigeon/clothing-19.webp", zIndex: SLOT_Z_INDEX.clothing, hidesNeck: false },
  { id: "20", slot: "clothing", name: "Светотканая мантия Феникса", rarity: "mythic", assetPath: "pigeon/clothing-20.webp", zIndex: SLOT_Z_INDEX.clothing, hidesNeck: true },
];

/* ───────── 4. HAT (20 вариантов) ───────── */
export const HAT_CATALOG: CosmeticItem[] = [
  { id: "01", slot: "hat", name: "Тёмная панама", rarity: "common", assetPath: "pigeon/hat-01.webp", zIndex: SLOT_Z_INDEX.hat },
  { id: "02", slot: "hat", name: "Вязаная шапка-бини", rarity: "common", assetPath: "pigeon/hat-02.webp", zIndex: SLOT_Z_INDEX.hat },
  { id: "03", slot: "hat", name: "Бейсболка козырьком назад", rarity: "common", assetPath: "pigeon/hat-03.webp", zIndex: SLOT_Z_INDEX.hat },
  { id: "04", slot: "hat", name: "Газетная треуголка", rarity: "common", assetPath: "pigeon/hat-04.webp", zIndex: SLOT_Z_INDEX.hat },
  { id: "05", slot: "hat", name: "Наушники студийные", rarity: "uncommon", assetPath: "pigeon/hat-05.webp", zIndex: SLOT_Z_INDEX.hat },
  { id: "06", slot: "hat", name: "Кепка разносчика пиццы", rarity: "uncommon", assetPath: "pigeon/hat-06.webp", zIndex: SLOT_Z_INDEX.hat },
  { id: "07", slot: "hat", name: "Рыболовная панама с крючками", rarity: "uncommon", assetPath: "pigeon/hat-07.webp", zIndex: SLOT_Z_INDEX.hat },
  { id: "08", slot: "hat", name: "Поварской колпак", rarity: "uncommon", assetPath: "pigeon/hat-08.webp", zIndex: SLOT_Z_INDEX.hat },
  { id: "09", slot: "hat", name: "Фетровая шляпа гангстера", rarity: "rare", assetPath: "pigeon/hat-09.webp", zIndex: SLOT_Z_INDEX.hat },
  { id: "10", slot: "hat", name: "Берет уличного художника", rarity: "rare", assetPath: "pigeon/hat-10.webp", zIndex: SLOT_Z_INDEX.hat },
  { id: "11", slot: "hat", name: "Шлем пилота с очками", rarity: "rare", assetPath: "pigeon/hat-11.webp", zIndex: SLOT_Z_INDEX.hat },
  { id: "12", slot: "hat", name: "Ковбойская стетсон-шляпа", rarity: "rare", assetPath: "pigeon/hat-12.webp", zIndex: SLOT_Z_INDEX.hat },
  { id: "13", slot: "hat", name: "Неоновый козырёк киберпанк", rarity: "epic", assetPath: "pigeon/hat-13.webp", zIndex: SLOT_Z_INDEX.hat },
  { id: "14", slot: "hat", name: "Цилиндр иллюзиониста", rarity: "epic", assetPath: "pigeon/hat-14.webp", zIndex: SLOT_Z_INDEX.hat },
  { id: "15", slot: "hat", name: "Шлем космодесантника", rarity: "epic", assetPath: "pigeon/hat-15.webp", zIndex: SLOT_Z_INDEX.hat },
  { id: "16", slot: "hat", name: "Шапка-ушанка с кокардой", rarity: "epic", assetPath: "pigeon/hat-16.webp", zIndex: SLOT_Z_INDEX.hat },
  { id: "17", slot: "hat", name: "Золотая корона монарха", rarity: "legendary", assetPath: "pigeon/hat-17.webp", zIndex: SLOT_Z_INDEX.hat },
  { id: "18", slot: "hat", name: "Лавровый венок Цезаря", rarity: "legendary", assetPath: "pigeon/hat-18.webp", zIndex: SLOT_Z_INDEX.hat },
  { id: "19", slot: "hat", name: "Нимб святого голубя", rarity: "mythic", assetPath: "pigeon/hat-19.webp", zIndex: SLOT_Z_INDEX.hat },
  { id: "20", slot: "hat", name: "Шлем повелителя галактики", rarity: "mythic", assetPath: "pigeon/hat-20.webp", zIndex: SLOT_Z_INDEX.hat },
];

/* ───────── 5. TATTOO (20 вариантов) ───────── */
export const TATTOO_CATALOG: CosmeticItem[] = [
  { id: "01", slot: "tattoo", name: "Семечка на крыле", rarity: "common", assetPath: "pigeon/tattoo-01.webp", zIndex: SLOT_Z_INDEX.tattoo },
  { id: "02", slot: "tattoo", name: "Царапина с района", rarity: "common", assetPath: "pigeon/tattoo-02.webp", zIndex: SLOT_Z_INDEX.tattoo },
  { id: "03", slot: "tattoo", name: "Точечный орнамент", rarity: "common", assetPath: "pigeon/tattoo-03.webp", zIndex: SLOT_Z_INDEX.tattoo },
  { id: "04", slot: "tattoo", name: "Штрих-код на лапе", rarity: "common", assetPath: "pigeon/tattoo-04.webp", zIndex: SLOT_Z_INDEX.tattoo },
  { id: "05", slot: "tattoo", name: "Граффити KOO", rarity: "uncommon", assetPath: "pigeon/tattoo-05.webp", zIndex: SLOT_Z_INDEX.tattoo },
  { id: "06", slot: "tattoo", name: "Перо свободы", rarity: "uncommon", assetPath: "pigeon/tattoo-06.webp", zIndex: SLOT_Z_INDEX.tattoo },
  { id: "07", slot: "tattoo", name: "Ласточка на груди", rarity: "uncommon", assetPath: "pigeon/tattoo-07.webp", zIndex: SLOT_Z_INDEX.tattoo },
  { id: "08", slot: "tattoo", name: "Следы лапок", rarity: "uncommon", assetPath: "pigeon/tattoo-08.webp", zIndex: SLOT_Z_INDEX.tattoo },
  { id: "09", slot: "tattoo", name: "Якорь моряка", rarity: "rare", assetPath: "pigeon/tattoo-09.webp", zIndex: SLOT_Z_INDEX.tattoo },
  { id: "10", slot: "tattoo", name: "Племенной узор крыла", rarity: "rare", assetPath: "pigeon/tattoo-10.webp", zIndex: SLOT_Z_INDEX.tattoo },
  { id: "11", slot: "tattoo", name: "Огненные языки", rarity: "rare", assetPath: "pigeon/tattoo-11.webp", zIndex: SLOT_Z_INDEX.tattoo },
  { id: "12", slot: "tattoo", name: "Молния скорости", rarity: "rare", assetPath: "pigeon/tattoo-12.webp", zIndex: SLOT_Z_INDEX.tattoo },
  { id: "13", slot: "tattoo", name: "Кибернетическая печатная плата", rarity: "epic", assetPath: "pigeon/tattoo-13.webp", zIndex: SLOT_Z_INDEX.tattoo },
  { id: "14", slot: "tattoo", name: "Дракон вокруг шеи", rarity: "epic", assetPath: "pigeon/tattoo-14.webp", zIndex: SLOT_Z_INDEX.tattoo },
  { id: "15", slot: "tattoo", name: "Руны предков", rarity: "epic", assetPath: "pigeon/tattoo-15.webp", zIndex: SLOT_Z_INDEX.tattoo },
  { id: "16", slot: "tattoo", name: "Биомеханический экзоскелет", rarity: "epic", assetPath: "pigeon/tattoo-16.webp", zIndex: SLOT_Z_INDEX.tattoo },
  { id: "17", slot: "tattoo", name: "Золотая вязь султана", rarity: "legendary", assetPath: "pigeon/tattoo-17.webp", zIndex: SLOT_Z_INDEX.tattoo },
  { id: "18", slot: "tattoo", name: "Зодиакальное созвездие", rarity: "legendary", assetPath: "pigeon/tattoo-18.webp", zIndex: SLOT_Z_INDEX.tattoo },
  { id: "19", slot: "tattoo", name: "Космическая туманность", rarity: "mythic", assetPath: "pigeon/tattoo-19.webp", zIndex: SLOT_Z_INDEX.tattoo },
  { id: "20", slot: "tattoo", name: "Герб Первого Голубя", rarity: "mythic", assetPath: "pigeon/tattoo-20.webp", zIndex: SLOT_Z_INDEX.tattoo },
];

/* ───────── 6. BEAK (20 вариантов) ───────── */
export const BEAK_CATALOG: CosmeticItem[] = [
  { id: "01", slot: "beak", name: "Городской серый клюв", rarity: "common", assetPath: "pigeon/beak-01.webp", zIndex: SLOT_Z_INDEX.beak },
  { id: "02", slot: "beak", name: "Песочно-жёлтый клюв", rarity: "common", assetPath: "pigeon/beak-02.webp", zIndex: SLOT_Z_INDEX.beak },
  { id: "03", slot: "beak", name: "Клюв с крошкой батона", rarity: "common", assetPath: "pigeon/beak-03.webp", zIndex: SLOT_Z_INDEX.beak },
  { id: "04", slot: "beak", name: "Оливковый матовый клюв", rarity: "common", assetPath: "pigeon/beak-04.webp", zIndex: SLOT_Z_INDEX.beak },
  { id: "05", slot: "beak", name: "Оранжевый морковный клюв", rarity: "uncommon", assetPath: "pigeon/beak-05.webp", zIndex: SLOT_Z_INDEX.beak },
  { id: "06", slot: "beak", name: "Коралловый глянец", rarity: "uncommon", assetPath: "pigeon/beak-06.webp", zIndex: SLOT_Z_INDEX.beak },
  { id: "07", slot: "beak", name: "Клюв с золотым пирсингом", rarity: "uncommon", assetPath: "pigeon/beak-07.webp", zIndex: SLOT_Z_INDEX.beak },
  { id: "08", slot: "beak", name: "Двухцветный клюв сапфир", rarity: "uncommon", assetPath: "pigeon/beak-08.webp", zIndex: SLOT_Z_INDEX.beak },
  { id: "09", slot: "beak", name: "Хищный крючковатый клюв", rarity: "rare", assetPath: "pigeon/beak-09.webp", zIndex: SLOT_Z_INDEX.beak },
  { id: "10", slot: "beak", name: "Бирюзовый неоновый клюв", rarity: "rare", assetPath: "pigeon/beak-10.webp", zIndex: SLOT_Z_INDEX.beak },
  { id: "11", slot: "beak", name: "Клюв с травинкой победы", rarity: "rare", assetPath: "pigeon/beak-11.webp", zIndex: SLOT_Z_INDEX.beak },
  { id: "12", slot: "beak", name: "Стальной полированный клюв", rarity: "rare", assetPath: "pigeon/beak-12.webp", zIndex: SLOT_Z_INDEX.beak },
  { id: "13", slot: "beak", name: "Титановый кибер-клюв", rarity: "epic", assetPath: "pigeon/beak-13.webp", zIndex: SLOT_Z_INDEX.beak },
  { id: "14", slot: "beak", name: "Обсидиановый монолит", rarity: "epic", assetPath: "pigeon/beak-14.webp", zIndex: SLOT_Z_INDEX.beak },
  { id: "15", slot: "beak", name: "Фиолетовый кристаллический клюв", rarity: "epic", assetPath: "pigeon/beak-15.webp", zIndex: SLOT_Z_INDEX.beak },
  { id: "16", slot: "beak", name: "Лавовый пылающий клюв", rarity: "epic", assetPath: "pigeon/beak-16.webp", zIndex: SLOT_Z_INDEX.beak },
  { id: "17", slot: "beak", name: "Золотой клюв 999 пробы", rarity: "legendary", assetPath: "pigeon/beak-17.webp", zIndex: SLOT_Z_INDEX.beak },
  { id: "18", slot: "beak", name: "Алмазный гранёный клюв", rarity: "legendary", assetPath: "pigeon/beak-18.webp", zIndex: SLOT_Z_INDEX.beak },
  { id: "19", slot: "beak", name: "Плазменный клюв гиперпространства", rarity: "mythic", assetPath: "pigeon/beak-19.webp", zIndex: SLOT_Z_INDEX.beak },
  { id: "20", slot: "beak", name: "Радужный призматический клюв", rarity: "mythic", assetPath: "pigeon/beak-20.webp", zIndex: SLOT_Z_INDEX.beak },
];

/* ───────── Полный каталог косметики ───────── */
export const COSMETICS_CATALOG = {
  eyes: EYES_CATALOG,
  shoes: SHOES_CATALOG,
  clothing: CLOTHING_CATALOG,
  hat: HAT_CATALOG,
  tattoo: TATTOO_CATALOG,
  beak: BEAK_CATALOG,
} as const;

/**
 * Детерминированная генерация черт голубя на основе его редкости и сида/RNG.
 * Обеспечивает воспроизводимость генерации для существующих и новых голубей.
 */
export function generatePigeonTraits(
  rarity: number,
  rngOrSeed: number | string | (() => number) = Math.random
): PigeonTraits {
  const rng =
    typeof rngOrSeed === "function"
      ? rngOrSeed
      : createDeterministicRng(rngOrSeed);

  // Выбираем обязательные базовые черты: глаза и клюв
  const pickIndex = (max: number) => Math.floor(rng() * max);

  const eyes = EYES_CATALOG[pickIndex(EYES_CATALOG.length)].id;
  const beak = BEAK_CATALOG[pickIndex(BEAK_CATALOG.length)].id;

  // Шанс наличия дополнительных предметов растёт с редкостью (от 50% до 95%)
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

  const tattoo =
    rng() < accessoryChance * 0.7
      ? TATTOO_CATALOG[pickIndex(TATTOO_CATALOG.length)].id
      : null;

  return {
    eyes,
    beak,
    shoes,
    clothing,
    hat,
    tattoo,
  };
}
