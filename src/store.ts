import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import {
  feed as doFeed,
  initialGame,
  merge as doMerge,
  hatch as doHatch,
  placeFromQueue,
  collectCrumbs as doCollectCrumbs,
  migrateGameState,
  type Game,
} from "./economy";

export type Store = Game & {
  screen: "home" | "eggs";
  setScreen: (s: "home" | "eggs") => void;
  feed: () => void;
  merge: (a: number, b: number) => void;
  hatch: (i: number) => void;
  place: (id: string, i: number) => void;
  collectCrumbs: () => void;
  selected: string | null;
  select: (id: string | null) => void;
  lastReward: number | null;
  notice: string | null;
  dismissNotice: () => void;
  feedEffect: number;
  activeTab: string;
  setTab: (s: string) => void;
  birdIndex: number;
  cycleBird: (direction: number) => void;
};

export const useGame = create<Store>()(
  persist(
    (set, get) => ({
      ...initialGame(),
      screen: "home",
      selected: null,
      lastReward: null,
      notice: null,
      feedEffect: 0,
      activeTab: "birds",
      birdIndex: 0,
      setScreen: (screen) => set({ screen }),
      setTab: (activeTab) => set({ activeTab }),
      cycleBird: (direction) =>
        set((s) => ({
          birdIndex: Math.max(
            0,
            Math.min(s.birds.length - 1, s.birdIndex + direction)
          ),
        })),
      dismissNotice: () => set({ notice: null }),
      feed: () =>
        set((s) => {
          const next = doFeed(s, Date.now());
          if (next === s) return s;
          const eggNotice = next.eggs.length > s.eggs.length;
          return {
            ...next,
            feedEffect: s.feedEffect + 1,
            notice: eggNotice ? "Получено яйцо в очередь!" : "+10 XP",
          };
        }),
      merge: (a, b) => set((s) => doMerge(s, a, b)),
      hatch: (i) => {
        const result = doHatch(get(), i);
        if (result) {
          set({
            ...result.game,
            lastReward: result.reward,
            selected: null,
            notice: `+${result.reward.toLocaleString("ru-RU")} семечек${
              result.jackpot ? " · джекпот!" : ""
            }${result.bird ? " · новый голубь!" : ""}${
              result.achievementBird ? " · голубь за достижение!" : ""
            }`,
          });
        }
      },
      place: (id, i) =>
        set((s) => ({ ...placeFromQueue(s, id, i), selected: null })),
      collectCrumbs: () =>
        set((s) => {
          const next = doCollectCrumbs(s, Date.now());
          if (next === s) return s;
          return {
            ...next,
            notice: "+25 семечек собрано!",
          };
        }),
      select: (selected) => set({ selected }),
    }),
    {
      name: "koo-koo-v01",
      storage: createJSONStorage(() => localStorage),
      migrate: (persistedState) => migrateGameState(persistedState),
      merge: (persistedState, currentState) => ({
        ...currentState,
        ...migrateGameState(persistedState),
      }),
      partialize: (s) => ({
        seeds: s.seeds,
        xp: s.xp,
        level: s.level,
        rarity: s.rarity,
        cycleFeeds: s.cycleFeeds,
        cycleStartedAt: s.cycleStartedAt,
        birds: s.birds,
        activeBirdId: s.activeBirdId,
        totalFeeds: s.totalFeeds,
        eggs: s.eggs,
        queue: s.queue,
        board: s.board,
        hatched: s.hatched,
        lastCrumbsAt: s.lastCrumbsAt,
        lvl4BirdAwarded: s.lvl4BirdAwarded,
      }),
    }
  )
);
