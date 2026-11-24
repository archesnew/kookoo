import { useEffect, useState } from "react";
import { useGame } from "./store";
import {
  ECONOMY,
  feedCost,
  canCollectCrumbs,
  minFeedCost,
  formatBirdNumber,
} from "./economy";

const rarity = [
  "Обычный",
  "Необычный",
  "Редкий",
  "Эпический",
  "Легендарный",
  "Мифический",
];
const colors = [
  "#aeb5c2",
  "#63dd9c",
  "#58a7ff",
  "#bd67fa",
  "#ffc629",
  "#ff82df",
];

function SeedIcon() {
  return (
    <svg
      className="seed-icon"
      viewBox="0 0 32 32"
      role="img"
      aria-label="Семечки"
    >
      <path
        d="M3.5 18.8C5.9 10.6 14.8 4.1 26.7 3.1c.1 11.9-5.4 21.2-13.5 24.3-6.2 2.4-11.7-2.4-9.7-8.6Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.2"
      />
      <path
        d="M6.1 25.2 25 7.3"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

function Egg({ level }: { level: number }) {
  return (
    <div className={`egg egg-${level}`}>
      <i />
      <b>{level}</b>
    </div>
  );
}

const RARITY_SLUGS = [
  "common",
  "uncommon",
  "rare",
  "epic",
  "legendary",
  "mythic",
] as const;

const EYE_TRAIT_MAP: Record<string, string> = {
  grumpy: "grumpy",
  sparkle: "sparkle",
  crazy: "crazy",
  cyber: "cyber",
  boss: "boss",
  sleepy: "sleepy",
  anime: "anime",
  berserk: "berserk",
  rich: "rich",
  reaper: "reaper",
  "01": "grumpy",
  "02": "boss",
  "03": "sparkle",
  "04": "sleepy",
  "05": "rich",
  "06": "anime",
  "07": "cyber",
  "08": "berserk",
  "09": "reaper",
  "10": "crazy",
};

const DEV_EYE_OPTIONS = [
  { id: "grumpy", label: "Базовый (grumpy)" },
  { id: "sparkle", label: "Сияющий (sparkle)" },
  { id: "crazy", label: "Безумный (crazy)" },
  { id: "cyber", label: "Кибер (cyber)" },
  { id: "boss", label: "Босс (boss)" },
  { id: "sleepy", label: "Сонный (sleepy)" },
  { id: "anime", label: "Аниме (anime)" },
  { id: "berserk", label: "Берсерк (berserk)" },
  { id: "rich", label: "Богатый (rich)" },
  { id: "reaper", label: "Жнец (reaper)" },
] as const;

function Pigeon({
  rarityIndex,
  feedEffect,
  eyeTrait = "grumpy",
  onFeed,
  cost,
  canFeed = true,
}: {
  rarityIndex: number;
  feedEffect: number;
  eyeTrait?: string;
  onFeed?: () => void;
  cost?: number;
  canFeed?: boolean;
}) {
  const [imgError, setImgError] = useState(false);
  const raritySlug = RARITY_SLUGS[rarityIndex] || "common";
  const resolvedEye = EYE_TRAIT_MAP[eyeTrait] || eyeTrait || "grumpy";

  useEffect(() => {
    setImgError(false);
  }, [rarityIndex, eyeTrait]);

  return (
    <button
      type="button"
      className={`pigeon-stage rarity-${rarityIndex} ${
        feedEffect ? "fed" : ""
      } ${!canFeed ? "cant-feed" : ""}`}
      key={feedEffect}
      onClick={onFeed}
      aria-label={
        canFeed
          ? `Покормить голубя (стоимость: ${cost ?? 1} семечек)`
          : `Недостаточно семечек для кормления (${cost ?? 1} семечек)`
      }
    >
      <div className="pigeon-halo" />
      <div className="pigeon-orbit orbit-one" />
      <div className="pigeon-orbit orbit-two" />

      {!imgError ? (
        <div
          className="pigeon-layers"
          role="img"
          aria-label={`Голубь KOO KOO, редкость: ${rarity[rarityIndex]}`}
        >
          {/* Базовое тело (z-index: 10) */}
          <img
            src="/assets/pigeon/body-base.webp"
            alt="Базовое тело голубя"
            className="pigeon-layer layer-base"
            onError={() => setImgError(true)}
          />

          {/* Слой шеи (z-index: 20, для common не выводится) */}
          {raritySlug !== "common" && (
            <img
              src={`/assets/pigeon/neck-${raritySlug}.webp`}
              alt={`Шея: ${rarity[rarityIndex]}`}
              className="pigeon-layer layer-neck"
              onError={() => setImgError(true)}
            />
          )}

          {/* Слой глаз (z-index: 30, для grumpy не выводится) */}
          {resolvedEye !== "grumpy" && (
            <img
              src={`/assets/pigeon/eyes-${resolvedEye}.webp`}
              alt={`Взгляд: ${resolvedEye}`}
              className="pigeon-layer layer-eyes"
              onError={() => setImgError(true)}
            />
          )}

          {/* Анимация крошек/семян при кормлении */}
          <svg
            className="pigeon-layer layer-burst"
            viewBox="0 0 360 440"
            aria-hidden="true"
          >
            <g className="seed-burst" fill="#FFC629">
              <path d="M74 173q5-8 10 0-5 12-10 0Z" />
              <path d="M280 209q5-8 10 0-5 12-10 0Z" />
              <path d="M89 281q5-8 10 0-5 12-10 0Z" />
              <path d="M271 300q5-8 10 0-5 12-10 0Z" />
            </g>
          </svg>
        </div>
      ) : (
        <>
          <svg
            className="pigeon-art"
            viewBox="0 0 360 440"
            role="img"
            aria-label="Временный концепт голубя KOO KOO: панама, жёлтая куртка и наушники"
          >
        <defs>
          <linearGradient id="body" x1="0" x2="1" y1="0" y2="1">
            <stop stopColor="#f3effa" />
            <stop offset=".56" stopColor="#a8a0b7" />
            <stop offset="1" stopColor="#51495f" />
          </linearGradient>
          <linearGradient id="neck" x1="0" x2="1" y1="0" y2="1">
            <stop stopColor={colors[rarityIndex]} />
            <stop offset=".48" stopColor="#e478ff" />
            <stop offset="1" stopColor="#463252" />
          </linearGradient>
          <linearGradient id="hoodie" x1="0" x2="1" y1="0" y2="1">
            <stop stopColor="#ffdf53" />
            <stop offset=".55" stopColor="#ffb51e" />
            <stop offset="1" stopColor="#d87912" />
          </linearGradient>
          <linearGradient id="hat" x1="0" x2="1" y1="0" y2="1">
            <stop stopColor="#403449" />
            <stop offset=".5" stopColor="#17111f" />
            <stop offset="1" stopColor="#55405e" />
          </linearGradient>
          <radialGradient id="eye">
            <stop offset=".45" stopColor="#16111a" />
            <stop offset=".48" stopColor="#eea83e" />
            <stop offset=".8" stopColor="#9b5422" />
            <stop offset="1" stopColor="#34221d" />
          </radialGradient>
          <filter id="shadow">
            <feDropShadow
              dx="0"
              dy="12"
              stdDeviation="8"
              floodColor="#08040c"
              floodOpacity=".6"
            />
          </filter>
        </defs>
        <g filter="url(#shadow)">
          <path
            d="M112 276Q37 252 28 196q44 9 86 61-28-67-9-106 45 39 53 91"
            fill="#80798b"
            stroke="#d6cfdf"
            strokeWidth="8"
            strokeLinejoin="round"
          />
          <path
            d="m47 218 40-52m-24 69 54-70m-23 90 56-63"
            stroke="#d8cfe2"
            strokeOpacity=".5"
            strokeWidth="5"
            strokeLinecap="round"
          />
          <path
            d="M100 271q14-88 90-97 98-13 132 94l-4 78q-77 56-191 4-26-33-27-79Z"
            fill="url(#body)"
            stroke="#ddd7e6"
            strokeWidth="5"
          />
          <path
            d="M131 231q-21-48 13-103 23-38 72-37 67 1 77 58 2 48-45 85-45 26-91 3Z"
            fill="url(#body)"
            stroke="#e5dfeb"
            strokeWidth="5"
          />
          <path
            d="M139 167q18 57 56 70 37 12 70-23-10 66-59 91-57-15-76-73-9-31 9-65Z"
            fill="url(#neck)"
          />
          <path
            d="M146 191q9 22 22 27m-11-50q13 25 27 36m-3-50q8 24 23 37m0-42q6 22 23 33m-1-15q7 13 18 19"
            fill="none"
            stroke="#ffe2ff"
            strokeOpacity=".42"
            strokeWidth="6"
            strokeLinecap="round"
          />
          <path
            d="M95 273q49-45 103-7 24 17 38 57l-9 62q-89 14-145-35-14-44 13-77Z"
            fill="url(#hoodie)"
            stroke="#ffe58a"
            strokeWidth="5"
          />
          <path
            d="M205 323q53-25 101-1l20 51q-58 29-116 11Z"
            fill="#f2eef4"
            stroke="#fff"
            strokeWidth="4"
          />
          <path
            d="M119 356v36m75-19v23"
            stroke="#e8a829"
            strokeWidth="13"
            strokeLinecap="round"
          />
          <path
            d="M110 394h34m39 0h34"
            stroke="#ffbd42"
            strokeWidth="15"
            strokeLinecap="round"
          />
          <path
            d="M110 283q43 30 92 1l8 20q-41 35-105 5Z"
            fill="#33243d"
            stroke="#8d718f"
            strokeWidth="4"
          />
          <path
            d="m183 290 24 17-9 47-25 17-18-18 12-44Z"
            fill="#211827"
            stroke="#a893b0"
            strokeWidth="4"
          />
          <path
            d="M180 339q16-22 34-2l-15 13Z"
            fill="none"
            stroke="#f2e8f8"
            strokeWidth="4"
          />
          <path
            d="M119 304q43 38 77 3"
            fill="none"
            stroke="#b77319"
            strokeWidth="7"
            strokeLinecap="round"
          />
          <path
            d="M173 275q-17 15-31 3"
            fill="none"
            stroke="#f8f2fd"
            strokeWidth="5"
            strokeLinecap="round"
          />
          <path
            d="M208 135q20-21 39 0"
            fill="none"
            stroke="#403747"
            strokeWidth="9"
            strokeLinecap="round"
          />
          <ellipse cx="218" cy="159" rx="19" ry="22" fill="#f9f5fc" />
          <ellipse cx="221" cy="160" rx="13" ry="16" fill="url(#eye)" />
          <circle cx="226" cy="153" r="4" fill="white" />
          <path
            d="M250 162q27-19 50 1l-22 22-32-9Z"
            fill="#f5a33f"
            stroke="#d56f2d"
            strokeWidth="4"
            strokeLinejoin="round"
          />
          <path
            d="M203 111q12-44 69-38 27 4 37 27-49-10-106 11Z"
            fill="url(#hat)"
            stroke="#82718b"
            strokeWidth="3"
          />
          <path
            d="M195 104q47-23 111-11 23 6 37 22-74-15-153 9Z"
            fill="url(#hat)"
            stroke="#a18baa"
            strokeWidth="4"
          />
          <path d="m269 85-12 22 12-4 7 5 2-23Z" fill="#f3eaf8" />
          <path
            d="M141 239q-3-36 31-40 33-2 41 31-32 30-72 9Z"
            fill="#25202d"
            stroke="#74617d"
            strokeWidth="7"
          />
          <circle
            cx="177"
            cy="225"
            r="20"
            fill="#170f1f"
            stroke="#d35bff"
            strokeWidth="6"
          />
          <circle
            cx="177"
            cy="225"
            r="12"
            fill="none"
            stroke="#8d49a9"
            strokeWidth="2"
          />
          <path
            d="M143 225q-23 21-21 51m92-52q26 14 26 39"
            fill="none"
            stroke="#4b4354"
            strokeWidth="12"
            strokeLinecap="round"
          />
          <path
            d="M193 188q-7 10-16 3"
            fill="none"
            stroke="#f5dce9"
            strokeWidth="5"
            strokeLinecap="round"
          />
        </g>
        <g className="seed-burst" fill="#FFC629">
          <path d="M74 173q5-8 10 0-5 12-10 0Z" />
          <path d="M280 209q5-8 10 0-5 12-10 0Z" />
          <path d="M89 281q5-8 10 0-5 12-10 0Z" />
          <path d="M271 300q5-8 10 0-5 12-10 0Z" />
        </g>
      </svg>
      <span className="temp-art-label">ВРЕМЕННЫЙ КОНЦЕПТ</span>
    </>
  )}
  <span className="pigeon-tap-hint" aria-hidden="true">
    Тапни, чтобы покормить
  </span>
</button>
);
}

export default function App() {
  const s = useGame();
  const [counter, setCounter] = useState(Date.now());
  const [confirm, setConfirm] = useState<number | null>(null);
  const [splash, setSplash] = useState(true);
  const [splashFading, setSplashFading] = useState(false);
  const [previewRarity, setPreviewRarity] = useState<number | null>(null);
  const [previewEyes, setPreviewEyes] = useState<string | null>(null);

  useEffect(() => {
    const t = setInterval(() => setCounter(Date.now()), 1000);

    const prefersReducedMotion =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (prefersReducedMotion) {
      setSplash(false);
      return () => clearInterval(t);
    }

    const fadeTimer = setTimeout(() => setSplashFading(true), 1300);
    const closeTimer = setTimeout(() => setSplash(false), 1750);

    return () => {
      clearInterval(t);
      clearTimeout(fadeTimer);
      clearTimeout(closeTimer);
    };
  }, []);

  useEffect(() => {
    if (!s.notice) return;
    const t = setTimeout(s.dismissNotice, 2400);
    return () => clearTimeout(t);
  }, [s.notice, s.dismissNotice]);

  const bird =
    s.birds.find((b) => b.id === s.activeBirdId) ?? s.birds[s.birdIndex];
  const rarityIndex = bird?.rarity ?? s.rarity;
  const eyeTrait = bird?.traits?.eyes || "grumpy";
  const activeRarity = previewRarity ?? rarityIndex;
  const activeEyes = previewEyes ?? eyeTrait;
  const feeds = bird?.cycleFeeds ?? s.cycleFeeds;
  const startedAt = bird?.cycleStartedAt ?? s.cycleStartedAt;
  const expired =
    startedAt !== null && counter - startedAt >= ECONOMY.feedCycleMs;
  const cost = feedCost(rarityIndex, expired ? 0 : feeds);
  const remaining =
    startedAt && !expired
      ? Math.max(0, ECONOMY.feedCycleMs - (counter - startedAt))
      : 0;

  const timer = remaining
    ? `${String(Math.floor(remaining / 3600000)).padStart(2, "0")}:${String(
        Math.floor((remaining % 3600000) / 60000)
      ).padStart(2, "0")}:${String(Math.floor((remaining % 60000) / 1000)).padStart(
        2,
        "0"
      )}`
    : "08:00:00";

  const progress = s.totalFeeds % ECONOMY.eggEveryFeeds;

  const handleFeed = () => {
    if (s.seeds < cost) {
      s.select(null);
      useGame.setState({ notice: "Недостаточно семечек для кормления!" });
      return;
    }
    s.feed();
    navigator.vibrate?.(18);
  };

  // Проверка страховки от нуля («Собрать крошки»)
  const canCrumbs = canCollectCrumbs(s, counter);
  const isOutOfSeeds = s.seeds < minFeedCost(s) && !s.board.some((e) => e !== null) && s.queue.length === 0;
  const crumbsRemainingMs = s.lastCrumbsAt ? Math.max(0, ECONOMY.crumbsCooldownMs - (counter - s.lastCrumbsAt)) : 0;
  const crumbsCooldownTimer = crumbsRemainingMs
    ? `${String(Math.floor(crumbsRemainingMs / 60000)).padStart(2, "0")}:${String(Math.floor((crumbsRemainingMs % 60000) / 1000)).padStart(2, "0")}`
    : null;

  const tap = (i: number) => {
    const egg = s.board[i];
    if (!egg) {
      if (s.selected) s.place(s.selected, i);
      return;
    }
    if (confirm !== null) return;
    if (s.selected) {
      const other = s.board.findIndex((e) => e?.id === s.selected);
      if (other >= 0 && other !== i) {
        s.merge(other, i);
        s.select(null);
        return;
      }
    }
    s.select(egg.id);
  };

  return (
    <main className="app">
      {splash && (
        <aside
          className={`splash-overlay ${splashFading ? "fade-out" : ""}`}
          role="status"
          aria-live="polite"
          aria-label="Загрузка KOO KOO"
          onClick={() => setSplash(false)}
        >
          <div className="splash-backdrop">
            <img
              src="/assets/brand/splash-poster.webp"
              alt="KOO KOO Загрузка"
              className="splash-poster-img"
            />
            <div className="splash-gradient-vignette" />
          </div>

          <div className="splash-content">
            <div className="splash-loading-group">
              <div className="splash-spinner-ring">
                <svg className="spinner-svg" viewBox="0 0 80 80" aria-hidden="true">
                  <defs>
                    <linearGradient id="spinner-grad" x1="0" y1="0" x2="1" y2="1">
                      <stop offset="0%" stopColor="#d693ff" />
                      <stop offset="50%" stopColor="#9b36f5" />
                      <stop offset="100%" stopColor="#ffc629" />
                    </linearGradient>
                  </defs>
                  <circle
                    className="spinner-track"
                    cx="40"
                    cy="40"
                    r="34"
                    fill="none"
                    strokeWidth="4"
                  />
                  <circle
                    className="spinner-arc"
                    cx="40"
                    cy="40"
                    r="34"
                    fill="none"
                    strokeWidth="4"
                    stroke="url(#spinner-grad)"
                  />
                </svg>
                <img
                  src="/assets/brand/seed-icon.webp"
                  alt=""
                  className="spinner-center-seed"
                  aria-hidden="true"
                />
              </div>
              <span className="splash-status-text">Загрузка стаи...</span>
            </div>
          </div>
        </aside>
      )}

      <header className="topbar">
        <div className="brand">
          <img
            src="/assets/brand/logo-koo-koo.webp"
            alt="KOO KOO"
            className="brand-logo-img"
          />
        </div>
        <div className="balance">
          <img
            src="/assets/brand/seed-icon.webp"
            alt=""
            className="balance-seed-icon"
            aria-hidden="true"
          />
          <b>{s.seeds.toLocaleString("ru-RU")}</b>
        </div>
      </header>

      {s.screen === "home" ? (
        <section className="home-screen">
          <div className="bird-heading">
            <div className="rank">
              <span
                style={
                  { "--rarity": colors[activeRarity] } as React.CSSProperties
                }
              />
              {rarity[activeRarity]}
            </div>
            <div className="bird-title">
              <div>
                <h1>{formatBirdNumber(bird, s.birdIndex)}</h1>
                <small>
                  {rarity[activeRarity]} · Ур. {s.level}
                </small>
              </div>
              <div className="switch">
                <button
                  aria-label="Предыдущий голубь"
                  disabled={s.birdIndex === 0}
                  onClick={() => s.cycleBird(-1)}
                >
                  ‹
                </button>
                <button
                  aria-label="Следующий голубь"
                  disabled={s.birdIndex >= s.birds.length - 1}
                  onClick={() => s.cycleBird(1)}
                >
                  ›
                </button>
              </div>
            </div>
          </div>

          <Pigeon
            rarityIndex={activeRarity}
            feedEffect={s.feedEffect}
            eyeTrait={activeEyes}
            onFeed={handleFeed}
            cost={cost}
            canFeed={s.seeds >= cost}
          />

          <div className="unified-progress-card">
            <div className="progress-card-header">
              <div className="progress-metric">
                <span className="metric-label">ОПЫТ</span>
                <span className="metric-value">
                  <b>{s.xp % 100}</b> <i>/ 100 XP</i>
                </span>
              </div>
              <div className="progress-metric right">
                <span className="metric-label">ДО ЯЙЦА</span>
                <span className="metric-value">
                  <b>{progress}</b> <i>/ {ECONOMY.eggEveryFeeds}</i>
                </span>
              </div>
            </div>

            <div
              className="unified-xp-bar"
              role="progressbar"
              aria-valuenow={s.xp % 100}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Опыт текущего уровня"
            >
              <i style={{ width: `${s.xp % 100}%` }} />
            </div>

            <div
              className="egg-steps-track"
              role="group"
              aria-label={`Шагов до яйца: ${progress} из ${ECONOMY.eggEveryFeeds}`}
            >
              {Array.from({ length: ECONOMY.eggEveryFeeds }).map((_, idx) => (
                <div
                  key={idx}
                  className={`egg-step-segment ${idx < progress ? "active" : ""}`}
                >
                  <span className="step-glow" />
                </div>
              ))}
            </div>
          </div>

          {import.meta.env.DEV && (
            <div className="dev-preview-panel">
              <div className="dev-preview-header">
                <small>🛠 DEV ПРЕВЬЮ СЛОЁВ ГОЛУБЯ</small>
                {(previewRarity !== null || previewEyes !== null) && (
                  <button
                    type="button"
                    className="dev-preview-reset"
                    onClick={() => {
                      setPreviewRarity(null);
                      setPreviewEyes(null);
                    }}
                  >
                    ↺ Сброс
                  </button>
                )}
              </div>
              <div className="dev-preview-controls">
                <label>
                  <span>Шея:</span>
                  <select
                    value={activeRarity}
                    onChange={(e) => setPreviewRarity(Number(e.target.value))}
                  >
                    {RARITY_SLUGS.map((slug, idx) => (
                      <option key={slug} value={idx}>
                        {rarity[idx]} ({slug})
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>Взгляд:</span>
                  <select
                    value={activeEyes}
                    onChange={(e) => setPreviewEyes(e.target.value)}
                  >
                    {DEV_EYE_OPTIONS.map((opt) => (
                      <option key={opt.id} value={opt.id}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </div>
          )}

          <section className="feed-status-card">
            <div className="feed-status-summary">
              <div className="cost-box">
                <small>СТОИМОСТЬ КОРМЛЕНИЯ</small>
                <strong>
                  <SeedIcon />
                  <span>{cost}</span>
                  <i>семечек</i>
                </strong>
              </div>
              <div className="reset-box">
                <small>СБРОС ЦЕНЫ (8 Ч)</small>
                <strong>{timer}</strong>
              </div>
            </div>

            {isOutOfSeeds && (
              <div className="crumbs-wrapper">
                {canCrumbs ? (
                  <button
                    type="button"
                    className="crumbs-btn"
                    onClick={() => {
                      s.collectCrumbs();
                      navigator.vibrate?.(25);
                    }}
                  >
                    🥖 Собрать крошки (+25 семечек)
                  </button>
                ) : crumbsCooldownTimer ? (
                  <div className="crumbs-cooldown">
                    <span>Крошки доступны через {crumbsCooldownTimer}</span>
                  </div>
                ) : null}
              </div>
            )}
          </section>
        </section>
      ) : (
        <section className="egg-screen">
          <div className="screen-title">
            <button className="back" onClick={() => s.setScreen("home")}>
              ‹
            </button>
            <div>
              <h1>Яйца</h1>
              <small>СОБИРАЙ · ОБЪЕДИНЯЙ · ОТКРЫВАЙ</small>
            </div>
            <span className="egg-count">
              {s.eggs.length + s.queue.length} яиц
            </span>
          </div>

          <div className="board">
            {s.board.map((egg, i) => (
              <button
                key={i}
                className={`cell ${s.selected === egg?.id ? "selected" : ""}`}
                onClick={() => tap(i)}
                aria-label={`Ячейка ${i + 1}${
                  egg ? `, яйцо уровня ${egg.level}` : ", пустая"
                }`}
              >
                {egg ? <Egg level={egg.level} /> : <span>＋</span>}
              </button>
            ))}
          </div>

          <div className="board-actions">
            <button
              disabled={!s.selected}
              onClick={() => {
                const i = s.board.findIndex((e) => e?.id === s.selected);
                if (i >= 0) {
                  if ((s.board[i]?.level ?? 1) >= 8) setConfirm(i);
                  else s.hatch(i);
                }
              }}
            >
              Разбить выбранное
            </button>
            <small>
              Базовая награда по уровню · шанс джекпота и редкого голубя
            </small>
          </div>

          <div className="queue-head">
            <h2>Очередь яиц</h2>
            <span>{s.queue.length}</span>
          </div>

          {s.queue.length ? (
            <div className="queue">
              {s.queue.map((e) => (
                <button
                  key={e.id}
                  onClick={() => s.select(e.id)}
                  className={s.selected === e.id ? "selected" : ""}
                >
                  <Egg level={e.level} />
                  <small>Ур. {e.level}</small>
                </button>
              ))}
            </div>
          ) : (
            <div className="empty">Здесь будут яйца за кормление</div>
          )}

          {s.lastReward !== null && (
            <div className="toast">
              <SeedIcon /> +{s.lastReward.toLocaleString("ru-RU")} семечек
              <button onClick={() => useGame.setState({ lastReward: null })}>
                ×
              </button>
            </div>
          )}
        </section>
      )}

      <nav className="bottom-nav">
        <NavItem id="birds" label="Голуби" icon="bird" />
        <NavItem id="eggs" label="Яйца" icon="egg" />
        <NavItem id="breed" label="Разведение" icon="breed" />
        <NavItem id="market" label="Маркет" icon="market" />
        <NavItem id="tasks" label="Задания" icon="tasks" />
      </nav>

      {s.notice && (
        <div className="notice" role="status">
          <span>{s.notice.includes("яйцо") ? "🥚" : "✦"}</span>
          {s.notice}
          <button aria-label="Закрыть уведомление" onClick={s.dismissNotice}>
            ×
          </button>
        </div>
      )}

      {confirm !== null && (
        <div className="modal">
          <div className="dialog">
            <Egg level={s.board[confirm]?.level ?? 1} />
            <h2>Разбить яйцо?</h2>
            <p>
              Яйцо исчезнет. Вы получите гарантированные семечки и шанс на
              бонус.
            </p>
            <button
              onClick={() => {
                s.hatch(confirm);
                setConfirm(null);
              }}
            >
              Разбить яйцо
            </button>
            <button className="cancel" onClick={() => setConfirm(null)}>
              Оставить
            </button>
          </div>
        </div>
      )}
    </main>
  );
}

function NavItem({
  id,
  label,
  icon,
}: {
  id: string;
  label: string;
  icon: string;
}) {
  const s = useGame();
  const selected = s.activeTab === id;
  return (
    <button
      className={`nav-item ${selected ? "active" : ""}`}
      onClick={() => {
        s.setTab(id);
        if (id === "eggs") s.setScreen("eggs");
        else if (id === "birds") s.setScreen("home");
        else s.notice = "Раздел скоро появится";
      }}
    >
      <div className="nav-icon-wrap">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          {icon === "bird" ? (
            <>
              <path d="M4 15c3-7 8-9 15-7-2 7-7 11-13 10" />
              <path d="m5 18 8-8m2 0 3-2-1 4" />
            </>
          ) : icon === "egg" ? (
            <>
              <path d="M12 3c-4 0-7 7-7 12a7 7 0 0 0 14 0c0-5-3-12-7-12Z" />
              <path d="M9 17c1 2 3 2 5 1" />
            </>
          ) : icon === "breed" ? (
            <>
              <circle cx="8" cy="9" r="3" />
              <circle cx="16" cy="9" r="3" />
              <path d="M3 20c0-4 2-6 5-6m13 6c0-4-2-6-5-6m-4 6c0-3 1-5 3-6" />
            </>
          ) : icon === "market" ? (
            <>
              <path d="M4 9h16l-1 11H5L4 9Z" />
              <path d="m3 9 2-5h14l2 5M9 20v-6h6v6" />
            </>
          ) : (
            <path d="m12 3 2.7 5.5 6.1.9-4.4 4.3 1 6.1-5.4-2.9-5.4 2.9 1-6.1-4.4-4.3 6.1-.9L12 3Z" />
          )}
        </svg>
        {id !== "birds" && id !== "eggs" && <i className="soon-dot" />}
      </div>
      <span>{label}</span>
    </button>
  );
}
