import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Platform } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useColors } from '@/hooks/useColors';
import { getLectures, Lecture } from '@/lib/storage';

export default function StatsScreen() {
  const colors = useColors();
  const insets = useSafeAreaInsets();
  const [lectures, setLectures] = useState<Lecture[]>([]);

  useEffect(() => {
    getLectures().then(setLectures);
  }, []);

  const totalLectures = lectures.length;
  const withAudio = lectures.filter(l => l.audioUri).length;
  const withSummary = lectures.filter(l => l.summary).length;
  const totalPages = lectures.reduce((acc, l) => acc + l.pages.length, 0);

  const recentLectures = [...lectures]
    .sort((a, b) => b.updatedAt - a.updatedAt)
    .slice(0, 5);

  const s = styles(colors);

  return (
    <ScrollView style={[s.container, { paddingTop: insets.top + (Platform.OS === 'web' ? 67 : 0) }]}>
      <View style={s.header}>
        <Text style={s.title}>الإحصاءات</Text>
      </View>

      <View style={s.grid}>
        {[
          { icon: 'document-text', label: 'المحاضرات', value: totalLectures, color: colors.primary },
          { icon: 'mic', label: 'مُسجَّلة', value: withAudio, color: colors.accentAudio },
          { icon: 'sparkles', label: 'مُلخَّصة', value: withSummary, color: colors.accent },
          { icon: 'layers', label: 'الصفحات', value: totalPages, color: '#8B5CF6' },
        ].map(stat => (
          <View key={stat.label} style={[s.statCard, { borderColor: stat.color + '30' }]}>
            <View style={[s.statIcon, { backgroundColor: stat.color + '20' }]}>
              <Ionicons name={stat.icon as any} size={22} color={stat.color} />
            </View>
            <Text style={[s.statValue, { color: stat.color }]}>{stat.value}</Text>
            <Text style={s.statLabel}>{stat.label}</Text>
          </View>
        ))}
      </View>

      {recentLectures.length > 0 && (
        <View style={s.section}>
          <Text style={s.sectionTitle}>آخر المحاضرات</Text>
          {recentLectures.map(l => (
            <View key={l.id} style={s.recentCard}>
              <Ionicons name="time-outline" size={16} color={colors.mutedForeground} />
              <View style={{ flex: 1 }}>
                <Text style={s.recentTitle}>{l.title}</Text>
                <Text style={s.recentDate}>{new Date(l.updatedAt).toLocaleDateString('ar-SA')}</Text>
              </View>
              {l.audioUri && <Ionicons name="mic" size={14} color={colors.accentAudio} />}
              {l.summary && <Ionicons name="sparkles" size={14} color={colors.accent} />}
            </View>
          ))}
        </View>
      )}

      {totalLectures === 0 && (
        <View style={s.empty}>
          <Ionicons name="bar-chart-outline" size={56} color={colors.border} />
          <Text style={s.emptyText}>ابدأ بإضافة محاضراتك لعرض الإحصاءات</Text>
        </View>
      )}
    </ScrollView>
  );
}

const styles = (c: ReturnType<typeof useColors>) => StyleSheet.create({
  container: { flex: 1, backgroundColor: c.background },
  header: { paddingHorizontal: 16, paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: c.border },
  title: { fontFamily: 'Tajawal_700Bold', fontSize: 20, color: c.foreground },
  grid: { flexDirection: 'row', flexWrap: 'wrap', padding: 14, gap: 12 },
  statCard: { flex: 1, minWidth: '44%', backgroundColor: c.card, borderRadius: 16, padding: 16, alignItems: 'center', gap: 8, borderWidth: 1 },
  statIcon: { width: 44, height: 44, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  statValue: { fontFamily: 'Tajawal_700Bold', fontSize: 28 },
  statLabel: { fontFamily: 'Tajawal_400Regular', fontSize: 13, color: c.muted },
  section: { paddingHorizontal: 14, marginTop: 8 },
  sectionTitle: { fontFamily: 'Tajawal_700Bold', fontSize: 16, color: c.foreground, marginBottom: 10 },
  recentCard: { flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: c.card, borderRadius: 12, padding: 12, marginBottom: 8, borderWidth: 1, borderColor: c.border },
  recentTitle: { fontFamily: 'Tajawal_500Medium', fontSize: 14, color: c.foreground },
  recentDate: { fontFamily: 'Tajawal_400Regular', fontSize: 12, color: c.muted, marginTop: 2 },
  empty: { alignItems: 'center', paddingTop: 80, gap: 12, paddingHorizontal: 32 },
  emptyText: { fontFamily: 'Tajawal_400Regular', fontSize: 15, color: c.muted, textAlign: 'center' },
});
