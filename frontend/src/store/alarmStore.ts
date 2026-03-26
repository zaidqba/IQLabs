import { create } from 'zustand';
import { Alarm } from '../types/alarms';

interface AlarmState {
  activeAlarms: Alarm[];
  setActiveAlarms: (alarms: Alarm[]) => void;
  addAlarm: (alarm: Alarm) => void;
  updateAlarm: (alarmId: number, update: Partial<Alarm>) => void;
  removeAlarm: (alarmId: number) => void;
}

export const useAlarmStore = create<AlarmState>((set) => ({
  activeAlarms: [],
  setActiveAlarms: (alarms) => set({ activeAlarms: alarms }),
  addAlarm: (alarm) =>
    set((state) => ({ activeAlarms: [alarm, ...state.activeAlarms] })),
  updateAlarm: (alarmId, update) =>
    set((state) => ({
      activeAlarms: state.activeAlarms.map((a) =>
        a.alarm_id === alarmId ? { ...a, ...update } : a
      ),
    })),
  removeAlarm: (alarmId) =>
    set((state) => ({
      activeAlarms: state.activeAlarms.filter((a) => a.alarm_id !== alarmId),
    })),
}));
