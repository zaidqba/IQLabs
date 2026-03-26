import { create } from 'zustand';
import { LatestReading } from '../types/readings';

interface ReadingsState {
  latestReadings: Map<string, LatestReading>;
  ntpValid: boolean;
  ntpOffsetMs: number | null;
  updateReading: (reading: LatestReading) => void;
  setNtpStatus: (valid: boolean, offset: number | null) => void;
}

export const useReadingsStore = create<ReadingsState>((set) => ({
  latestReadings: new Map(),
  ntpValid: true,
  ntpOffsetMs: null,
  updateReading: (reading) =>
    set((state) => {
      const next = new Map(state.latestReadings);
      next.set(reading.channel_code, reading);
      return { latestReadings: next };
    }),
  setNtpStatus: (valid, offset) => set({ ntpValid: valid, ntpOffsetMs: offset }),
}));
