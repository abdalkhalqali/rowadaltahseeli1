import React, { useState, useCallback } from 'react';
import { View, Text, StyleSheet, TextInput, FlatList, TouchableOpacity, Platform } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { useColors } from '@/hooks/useColors';
import { searchLectures, Lecture } from '@/lib/storage';

export default function SearchScreen() {
  const colors = useColors();
  const insets = useSafeAreaInsets();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Lecture[]>([]);
  const [searching, setSearching] = useState(false);

  const handleSearch = useCallback(async (text: string) => {
    setQuery(text);
    if (!text.trim()) { setResults([]); return; }
    setSearching(true);
    try { setResults(await searchLectures(text)); }
    finally { setSearching(false); }
  }, []);

  const s = styles(colors);

  return (
    <View style={[s.container, { paddingTop: insets.top + (Platform.OS === 'web' ? 67 : 0) }]}>
      <View style={s.header}>
        <Text style={s.title}>البحث</Text>
      </View>
      <View style={s.searchBox}>
        <Ionicons name="search-outline" size={18} color={colors.mutedForeground} />
        <TextInput
          style={s.input}
          placeholder="ابحث في المحاضرات..."
          placeholderTextColor={colors.mutedForeground}
          value={query}
          onChangeText={handleSearch}
          textAlign="right"
        />
        {query.length > 0 && (
          <TouchableOpacity onPress={() => handleSearch('')}>
            <Ionicons name="close-circle" size={18} color={colors.mutedForeground} />
          </TouchableOpacity>
        )}
      </View>

      <FlatList
        data={results}
        keyExtractor={i => i.id}
        contentContainerStyle={s.list}
        ListEmptyComponent={
          <View style={s.empty}>
            <Ionicons name={query ? 'search-outline' : 'document-text-outline'} size={52} color={colors.border} />
            <Text style={s.emptyText}>{query ? 'لا توجد نتائج' : 'ابحث في محاضراتك'}</Text>
          </View>
        }
        renderItem={({ item }) => (
          <TouchableOpacity style={s.card} onPress={async () => {
            await Haptics.selectionAsync();
            router.push(`/lecture/${item.id}`);
          }}>
            <View style={s.cardIcon}>
              <Ionicons name="document-text" size={18} color={colors.primary} />
            </View>
            <View style={s.cardInfo}>
              <Text style={s.cardTitle}>{item.title}</Text>
              {item.summary && (
                <Text style={s.cardSummary} numberOfLines={2}>{item.summary}</Text>
              )}
              <View style={s.tagRow}>
                {item.tags?.slice(0, 3).map(t => (
                  <View key={t} style={s.tag}><Text style={s.tagText}>{t}</Text></View>
                ))}
              </View>
            </View>
          </TouchableOpacity>
        )}
      />
    </View>
  );
}

const styles = (c: ReturnType<typeof useColors>) => StyleSheet.create({
  container: { flex: 1, backgroundColor: c.background },
  header: { paddingHorizontal: 16, paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: c.border },
  title: { fontFamily: 'Tajawal_700Bold', fontSize: 20, color: c.foreground },
  searchBox: { flexDirection: 'row', alignItems: 'center', margin: 14, backgroundColor: c.card, borderRadius: 14, paddingHorizontal: 14, paddingVertical: 10, gap: 10, borderWidth: 1, borderColor: c.border },
  input: { flex: 1, fontFamily: 'Tajawal_400Regular', fontSize: 15, color: c.foreground },
  list: { padding: 14, gap: 10 },
  empty: { alignItems: 'center', paddingTop: 80, gap: 12 },
  emptyText: { fontFamily: 'Tajawal_400Regular', fontSize: 15, color: c.muted },
  card: { flexDirection: 'row', backgroundColor: c.card, borderRadius: 14, padding: 14, gap: 12, borderWidth: 1, borderColor: c.border },
  cardIcon: { width: 36, height: 36, borderRadius: 9, backgroundColor: c.primary + '15', alignItems: 'center', justifyContent: 'center' },
  cardInfo: { flex: 1, gap: 4 },
  cardTitle: { fontFamily: 'Tajawal_700Bold', fontSize: 15, color: c.foreground },
  cardSummary: { fontFamily: 'Tajawal_400Regular', fontSize: 13, color: c.muted, lineHeight: 20 },
  tagRow: { flexDirection: 'row', gap: 6, flexWrap: 'wrap', marginTop: 4 },
  tag: { backgroundColor: c.primary + '20', borderRadius: 6, paddingHorizontal: 8, paddingVertical: 2 },
  tagText: { fontFamily: 'Tajawal_400Regular', fontSize: 11, color: c.primary },
});
