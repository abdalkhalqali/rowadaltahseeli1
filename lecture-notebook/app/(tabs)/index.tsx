import React, { useEffect, useState } from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity,
  Pressable, Platform, Modal, TextInput, Alert,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { useColors } from '@/hooks/useColors';
import { useApp } from '@/context/AppContext';
import { University, Year, Subject } from '@/lib/storage';

const SUBJECT_COLORS = ['#4F8EF7','#10B981','#F59E0B','#EF4444','#8B5CF6','#06B6D4','#F97316','#EC4899'];
const SUBJECT_ICONS = ['book','flask','calculator','globe','musical-notes','leaf','rocket','heart'];

type ViewMode = 'universities' | 'years' | 'subjects' | 'lectures';

export default function HomeScreen() {
  const colors = useColors();
  const insets = useSafeAreaInsets();
  const {
    universities, years, subjects, lectures,
    loadUniversities, loadYears, loadSubjects, loadLectures,
    addUniversity, addYear, addSubject, addLecture,
    selectedUniversityId, selectedYearId, selectedSubjectId,
    setSelectedUniversity, setSelectedYear, setSelectedSubject,
  } = useApp();

  const [viewMode, setViewMode] = useState<ViewMode>('universities');
  const [modalVisible, setModalVisible] = useState(false);
  const [inputText, setInputText] = useState('');
  const [selectedColor, setSelectedColor] = useState(SUBJECT_COLORS[0]);
  const [selectedIconIdx, setSelectedIconIdx] = useState(0);
  const [creating, setCreating] = useState(false);

  useEffect(() => { loadUniversities(); }, []);

  const handleUniversityPress = async (u: University) => {
    await Haptics.selectionAsync();
    setSelectedUniversity(u.id);
    setViewMode('years');
    loadYears(u.id);
  };

  const handleYearPress = async (y: Year) => {
    await Haptics.selectionAsync();
    setSelectedYear(y.id);
    setViewMode('subjects');
    loadSubjects(y.id);
  };

  const handleSubjectPress = async (s: Subject) => {
    await Haptics.selectionAsync();
    setSelectedSubject(s.id);
    setViewMode('lectures');
    loadLectures(s.id);
  };

  const handleLecturePress = async (lectureId: string) => {
    await Haptics.selectionAsync();
    router.push(`/lecture/${lectureId}`);
  };

  const handleBack = async () => {
    await Haptics.selectionAsync();
    if (viewMode === 'lectures') { setViewMode('subjects'); setSelectedSubject(null); }
    else if (viewMode === 'subjects') { setViewMode('years'); setSelectedYear(null); }
    else if (viewMode === 'years') { setViewMode('universities'); setSelectedUniversity(null); }
  };

  const handleAdd = async () => {
    if (!inputText.trim()) return;
    setCreating(true);
    try {
      if (viewMode === 'universities') {
        await addUniversity(inputText.trim());
      } else if (viewMode === 'years' && selectedUniversityId) {
        await addYear(selectedUniversityId, inputText.trim());
      } else if (viewMode === 'subjects' && selectedYearId) {
        await addSubject(selectedYearId, inputText.trim(), selectedColor, SUBJECT_ICONS[selectedIconIdx]);
      } else if (viewMode === 'lectures' && selectedSubjectId) {
        const l = await addLecture(selectedSubjectId, inputText.trim());
        setModalVisible(false);
        setInputText('');
        router.push(`/lecture/${l.id}`);
        return;
      }
      setModalVisible(false);
      setInputText('');
      await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    } finally {
      setCreating(false);
    }
  };

  const getTitle = () => {
    if (viewMode === 'universities') return 'جامعاتي';
    if (viewMode === 'years') return universities.find(u => u.id === selectedUniversityId)?.name ?? 'السنوات';
    if (viewMode === 'subjects') return years.find(y => y.id === selectedYearId)?.name ?? 'المواد';
    return subjects.find(s => s.id === selectedSubjectId)?.name ?? 'المحاضرات';
  };

  const getEmptyText = () => {
    if (viewMode === 'universities') return 'أضف جامعتك الأولى';
    if (viewMode === 'years') return 'أضف السنة الدراسية';
    if (viewMode === 'subjects') return 'أضف مادة دراسية';
    return 'لا توجد محاضرات بعد';
  };

  const getAddLabel = () => {
    if (viewMode === 'universities') return 'اسم الجامعة';
    if (viewMode === 'years') return 'السنة (مثال: السنة الأولى)';
    if (viewMode === 'subjects') return 'اسم المادة';
    return 'عنوان المحاضرة';
  };

  const data = viewMode === 'universities' ? universities
    : viewMode === 'years' ? years
    : viewMode === 'subjects' ? subjects
    : lectures;

  const s = styles(colors);

  return (
    <View style={[s.container, { paddingTop: insets.top + (Platform.OS === 'web' ? 67 : 0) }]}>
      {/* Header */}
      <View style={s.header}>
        {viewMode !== 'universities' && (
          <TouchableOpacity onPress={handleBack} style={s.backBtn}>
            <Ionicons name="chevron-back" size={22} color={colors.foreground} />
          </TouchableOpacity>
        )}
        <Text style={s.headerTitle}>{getTitle()}</Text>
        <TouchableOpacity onPress={() => setModalVisible(true)} style={s.addBtn}>
          <Ionicons name="add" size={24} color={colors.primary} />
        </TouchableOpacity>
      </View>

      {/* Breadcrumb */}
      {viewMode !== 'universities' && (
        <View style={s.breadcrumb}>
          <Text style={s.breadcrumbText}>
            {viewMode === 'years' ? '🏛️ ' + (universities.find(u => u.id === selectedUniversityId)?.name ?? '')
              : viewMode === 'subjects' ? '📅 ' + (years.find(y => y.id === selectedYearId)?.name ?? '')
              : '📚 ' + (subjects.find(s => s.id === selectedSubjectId)?.name ?? '')}
          </Text>
        </View>
      )}

      <FlatList
        data={data as any[]}
        keyExtractor={item => item.id}
        contentContainerStyle={s.list}
        ListEmptyComponent={
          <View style={s.empty}>
            <Ionicons name="folder-open-outline" size={56} color={colors.border} />
            <Text style={s.emptyText}>{getEmptyText()}</Text>
            <TouchableOpacity style={s.emptyBtn} onPress={() => setModalVisible(true)}>
              <Text style={s.emptyBtnText}>إضافة الآن</Text>
            </TouchableOpacity>
          </View>
        }
        renderItem={({ item }) => {
          if (viewMode === 'lectures') {
            return (
              <TouchableOpacity style={s.lectureCard} onPress={() => handleLecturePress(item.id)}>
                <View style={s.lectureIcon}>
                  <Ionicons name="document-text" size={20} color={colors.primary} />
                </View>
                <View style={s.lectureInfo}>
                  <Text style={s.lectureName}>{item.title}</Text>
                  <Text style={s.lectureMeta}>
                    {new Date(item.date).toLocaleDateString('ar-SA')}
                    {item.audioUri ? '  •  🎙️ تسجيل' : ''}
                    {item.summary ? '  •  🤖 ملخص' : ''}
                  </Text>
                </View>
                <Ionicons name="chevron-forward" size={16} color={colors.mutedForeground} />
              </TouchableOpacity>
            );
          }
          if (viewMode === 'subjects') {
            return (
              <TouchableOpacity style={[s.subjectCard, { borderLeftColor: item.color }]} onPress={() => handleSubjectPress(item)}>
                <View style={[s.subjectIcon, { backgroundColor: item.color + '20' }]}>
                  <Ionicons name={item.icon as any} size={22} color={item.color} />
                </View>
                <Text style={s.subjectName}>{item.name}</Text>
                <Ionicons name="chevron-forward" size={16} color={colors.mutedForeground} />
              </TouchableOpacity>
            );
          }
          return (
            <TouchableOpacity
              style={s.card}
              onPress={() => viewMode === 'universities' ? handleUniversityPress(item) : handleYearPress(item)}
            >
              <Ionicons
                name={viewMode === 'universities' ? 'school-outline' : 'calendar-outline'}
                size={20} color={colors.primary}
              />
              <Text style={s.cardText}>{item.name}</Text>
              <Ionicons name="chevron-forward" size={16} color={colors.mutedForeground} />
            </TouchableOpacity>
          );
        }}
      />

      {/* Add Modal */}
      <Modal visible={modalVisible} transparent animationType="slide" onRequestClose={() => setModalVisible(false)}>
        <Pressable style={s.modalOverlay} onPress={() => setModalVisible(false)}>
          <Pressable style={s.modalBox} onPress={e => e.stopPropagation()}>
            <Text style={s.modalTitle}>{getAddLabel()}</Text>
            <TextInput
              style={s.modalInput}
              placeholder={getAddLabel()}
              placeholderTextColor={colors.mutedForeground}
              value={inputText}
              onChangeText={setInputText}
              autoFocus
              textAlign="right"
            />
            {viewMode === 'subjects' && (
              <>
                <Text style={s.modalLabel}>اللون</Text>
                <View style={s.colorRow}>
                  {SUBJECT_COLORS.map(c => (
                    <TouchableOpacity key={c} onPress={() => setSelectedColor(c)}
                      style={[s.colorDot, { backgroundColor: c }, selectedColor === c && s.colorDotSelected]} />
                  ))}
                </View>
                <Text style={s.modalLabel}>الأيقونة</Text>
                <View style={s.iconRow}>
                  {SUBJECT_ICONS.map((ic, idx) => (
                    <TouchableOpacity key={ic} onPress={() => setSelectedIconIdx(idx)}
                      style={[s.iconBtn, selectedIconIdx === idx && { backgroundColor: selectedColor + '30', borderColor: selectedColor }]}>
                      <Ionicons name={ic as any} size={20} color={selectedIconIdx === idx ? selectedColor : colors.muted} />
                    </TouchableOpacity>
                  ))}
                </View>
              </>
            )}
            <TouchableOpacity style={[s.modalBtn, creating && { opacity: 0.6 }]} onPress={handleAdd} disabled={creating}>
              <Text style={s.modalBtnText}>{creating ? 'جاري الإضافة...' : 'إضافة'}</Text>
            </TouchableOpacity>
          </Pressable>
        </Pressable>
      </Modal>
    </View>
  );
}

const styles = (c: ReturnType<typeof useColors>) => StyleSheet.create({
  container: { flex: 1, backgroundColor: c.background },
  header: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: c.border },
  backBtn: { marginRight: 8, padding: 4 },
  headerTitle: { flex: 1, fontFamily: 'Tajawal_700Bold', fontSize: 20, color: c.foreground },
  addBtn: { padding: 4 },
  breadcrumb: { paddingHorizontal: 16, paddingVertical: 6, backgroundColor: c.surface },
  breadcrumbText: { fontFamily: 'Tajawal_400Regular', fontSize: 13, color: c.muted },
  list: { padding: 16, gap: 10, paddingBottom: 32 },
  card: { flexDirection: 'row', alignItems: 'center', backgroundColor: c.card, borderRadius: 14, padding: 16, gap: 12, borderWidth: 1, borderColor: c.border },
  cardText: { flex: 1, fontFamily: 'Tajawal_500Medium', fontSize: 16, color: c.foreground },
  subjectCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: c.card, borderRadius: 14, padding: 14, gap: 12, borderWidth: 1, borderColor: c.border, borderLeftWidth: 3 },
  subjectIcon: { width: 40, height: 40, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
  subjectName: { flex: 1, fontFamily: 'Tajawal_500Medium', fontSize: 16, color: c.foreground },
  lectureCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: c.card, borderRadius: 14, padding: 14, gap: 12, borderWidth: 1, borderColor: c.border },
  lectureIcon: { width: 38, height: 38, borderRadius: 10, backgroundColor: c.primary + '15', alignItems: 'center', justifyContent: 'center' },
  lectureInfo: { flex: 1 },
  lectureName: { fontFamily: 'Tajawal_500Medium', fontSize: 15, color: c.foreground },
  lectureMeta: { fontFamily: 'Tajawal_400Regular', fontSize: 12, color: c.muted, marginTop: 2 },
  empty: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingTop: 80, gap: 12 },
  emptyText: { fontFamily: 'Tajawal_400Regular', fontSize: 16, color: c.muted },
  emptyBtn: { backgroundColor: c.primary + '20', borderRadius: 10, paddingHorizontal: 20, paddingVertical: 10, borderWidth: 1, borderColor: c.primary + '40' },
  emptyBtnText: { fontFamily: 'Tajawal_500Medium', fontSize: 14, color: c.primary },
  modalOverlay: { flex: 1, backgroundColor: c.overlay, justifyContent: 'flex-end' },
  modalBox: { backgroundColor: c.surface, borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 24, gap: 14 },
  modalTitle: { fontFamily: 'Tajawal_700Bold', fontSize: 18, color: c.foreground, textAlign: 'center' },
  modalLabel: { fontFamily: 'Tajawal_500Medium', fontSize: 13, color: c.muted },
  modalInput: { backgroundColor: c.card, borderRadius: 12, padding: 14, fontFamily: 'Tajawal_400Regular', fontSize: 16, color: c.foreground, borderWidth: 1, borderColor: c.border },
  colorRow: { flexDirection: 'row', gap: 10, flexWrap: 'wrap' },
  colorDot: { width: 28, height: 28, borderRadius: 14 },
  colorDotSelected: { borderWidth: 3, borderColor: '#fff' },
  iconRow: { flexDirection: 'row', gap: 8, flexWrap: 'wrap' },
  iconBtn: { width: 42, height: 42, borderRadius: 10, alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: 'transparent', backgroundColor: 'transparent' },
  modalBtn: { backgroundColor: c.primary, borderRadius: 14, padding: 16, alignItems: 'center', marginTop: 4 },
  modalBtnText: { fontFamily: 'Tajawal_700Bold', fontSize: 16, color: '#fff' },
});
