import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import {
  University, Year, Subject, Lecture,
  getUniversities, createUniversity, deleteUniversity,
  getYears, createYear, deleteYear,
  getSubjects, createSubject, deleteSubject,
  getLectures, createLecture, updateLecture, deleteLecture, getLecture,
} from '@/lib/storage';

interface AppState {
  universities: University[];
  years: Year[];
  subjects: Subject[];
  lectures: Lecture[];
  loading: boolean;
  selectedUniversityId: string | null;
  selectedYearId: string | null;
  selectedSubjectId: string | null;
}

interface AppActions {
  loadUniversities: () => Promise<void>;
  loadYears: (uniId: string) => Promise<void>;
  loadSubjects: (yearId: string) => Promise<void>;
  loadLectures: (subjectId: string) => Promise<void>;
  addUniversity: (name: string) => Promise<University>;
  removeUniversity: (id: string) => Promise<void>;
  addYear: (uniId: string, name: string) => Promise<Year>;
  removeYear: (id: string) => Promise<void>;
  addSubject: (yearId: string, name: string, color: string, icon: string) => Promise<Subject>;
  removeSubject: (id: string) => Promise<void>;
  addLecture: (subjectId: string, title: string) => Promise<Lecture>;
  saveLecture: (id: string, updates: Partial<Lecture>) => Promise<void>;
  removeLecture: (id: string) => Promise<void>;
  refreshLecture: (id: string) => Promise<Lecture | null>;
  setSelectedUniversity: (id: string | null) => void;
  setSelectedYear: (id: string | null) => void;
  setSelectedSubject: (id: string | null) => void;
}

const AppContext = createContext<(AppState & AppActions) | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [universities, setUniversities] = useState<University[]>([]);
  const [years, setYears] = useState<Year[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [lectures, setLectures] = useState<Lecture[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedUniversityId, setSelectedUniversityId] = useState<string | null>(null);
  const [selectedYearId, setSelectedYearId] = useState<string | null>(null);
  const [selectedSubjectId, setSelectedSubjectId] = useState<string | null>(null);

  const loadUniversities = useCallback(async () => {
    setLoading(true);
    try { setUniversities(await getUniversities()); }
    finally { setLoading(false); }
  }, []);

  const loadYears = useCallback(async (uniId: string) => {
    setYears(await getYears(uniId));
  }, []);

  const loadSubjects = useCallback(async (yearId: string) => {
    setSubjects(await getSubjects(yearId));
  }, []);

  const loadLectures = useCallback(async (subjectId: string) => {
    setLectures(await getLectures(subjectId));
  }, []);

  const addUniversity = useCallback(async (name: string) => {
    const u = await createUniversity(name);
    setUniversities(prev => [...prev, u]);
    return u;
  }, []);

  const removeUniversity = useCallback(async (id: string) => {
    await deleteUniversity(id);
    setUniversities(prev => prev.filter(u => u.id !== id));
  }, []);

  const addYear = useCallback(async (uniId: string, name: string) => {
    const y = await createYear(uniId, name);
    setYears(prev => [...prev, y]);
    return y;
  }, []);

  const removeYear = useCallback(async (id: string) => {
    await deleteYear(id);
    setYears(prev => prev.filter(y => y.id !== id));
  }, []);

  const addSubject = useCallback(async (yearId: string, name: string, color: string, icon: string) => {
    const s = await createSubject(yearId, name, color, icon);
    setSubjects(prev => [...prev, s]);
    return s;
  }, []);

  const removeSubject = useCallback(async (id: string) => {
    await deleteSubject(id);
    setSubjects(prev => prev.filter(s => s.id !== id));
  }, []);

  const addLecture = useCallback(async (subjectId: string, title: string) => {
    const l = await createLecture(subjectId, title);
    setLectures(prev => [l, ...prev]);
    return l;
  }, []);

  const saveLecture = useCallback(async (id: string, updates: Partial<Lecture>) => {
    await updateLecture(id, updates);
    setLectures(prev => prev.map(l => l.id === id ? { ...l, ...updates, updatedAt: Date.now() } : l));
  }, []);

  const removeLecture = useCallback(async (id: string) => {
    await deleteLecture(id);
    setLectures(prev => prev.filter(l => l.id !== id));
  }, []);

  const refreshLecture = useCallback(async (id: string) => {
    const l = await getLecture(id);
    if (l) setLectures(prev => prev.map(x => x.id === id ? l : x));
    return l;
  }, []);

  const setSelectedUniversity = useCallback((id: string | null) => setSelectedUniversityId(id), []);
  const setSelectedYear = useCallback((id: string | null) => setSelectedYearId(id), []);
  const setSelectedSubject = useCallback((id: string | null) => setSelectedSubjectId(id), []);

  return (
    <AppContext.Provider value={{
      universities, years, subjects, lectures, loading,
      selectedUniversityId, selectedYearId, selectedSubjectId,
      loadUniversities, loadYears, loadSubjects, loadLectures,
      addUniversity, removeUniversity,
      addYear, removeYear,
      addSubject, removeSubject,
      addLecture, saveLecture, removeLecture, refreshLecture,
      setSelectedUniversity, setSelectedYear, setSelectedSubject,
    }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
}
