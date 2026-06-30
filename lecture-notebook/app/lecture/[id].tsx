import React, { useEffect, useState, useRef, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  TextInput, Alert, ActivityIndicator, Platform, Pressable, Modal,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { Audio } from 'expo-av';
import { useColors } from '@/hooks/useColors';
import { Lecture, updateLecture, getLecture } from '@/lib/storage';
import { summarizeLecture, extractKeyPoints, generateQuestions, suggestTags, aiChat } from '@/lib/ai';

type Tab = 'notes' | 'transcript' | 'ai';

export default function LectureScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const colors = useColors();
  const insets = useSafeAreaInsets();
  const [lecture, setLecture] = useState<Lecture | null>(null);
  const [tab, setTab] = useState<Tab>('notes');
  const [loading, setLoading] = useState(true);

  // Recording
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordDuration, setRecordDuration] = useState(0);
  const durationTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const [sound, setSound] = useState<Audio.Sound | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  // AI
  const [aiLoading, setAiLoading] = useState(false);
  const [aiAction, setAiAction] = useState('');
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState<{ role: 'user' | 'ai'; text: string }[]>([]);
  const [chatLoading, setChatLoading] = useState(false);

  useEffect(() => {
    if (id) getLecture(id).then(l => { setLecture(l); setLoading(false); });
    return () => {
      if (durationTimer.current) clearInterval(durationTimer.current);
      sound?.unloadAsync();
    };
  }, [id]);

  const save = useCallback(async (updates: Partial<Lecture>) => {
    if (!lecture) return;
    const updated = { ...lecture, ...updates, updatedAt: Date.now() };
    setLecture(updated);
    await updateLecture(lecture.id, updates);
  }, [lecture]);

  // ── Recording ──────────────────────────────────────────────────────
  const startRecording = async () => {
    try {
      const { status } = await Audio.requestPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('إذن الميكروفون', 'نحتاج إذن الميكروفون لتسجيل المحاضرة');
        return;
      }
      await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
      const rec = new Audio.Recording();
      await rec.prepareToRecordAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);
      await rec.startAsync();
      setRecording(rec);
      setIsRecording(true);
      setRecordDuration(0);
      await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      durationTimer.current = setInterval(() => setRecordDuration(d => d + 1), 1000);
    } catch (e) {
      Alert.alert('خطأ', 'تعذّر بدء التسجيل');
    }
  };

  const stopRecording = async () => {
    if (!recording) return;
    if (durationTimer.current) clearInterval(durationTimer.current);
    try {
      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      const status = await recording.getStatusAsync();
      setRecording(null);
      setIsRecording(false);
      await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      if (uri) {
        await save({ audioUri: uri, audioDuration: Math.round(recordDuration) });
        setTab('transcript');
      }
    } catch (e) {
      setIsRecording(false);
    }
  };

  const playAudio = async () => {
    if (!lecture?.audioUri) return;
    if (sound) {
      if (isPlaying) { await sound.pauseAsync(); setIsPlaying(false); }
      else { await sound.playAsync(); setIsPlaying(true); }
      return;
    }
    const { sound: s } = await Audio.Sound.createAsync({ uri: lecture.audioUri }, { shouldPlay: true });
    s.setOnPlaybackStatusUpdate(status => {
      if (status.isLoaded && status.didJustFinish) { setIsPlaying(false); setSound(null); }
    });
    setSound(s);
    setIsPlaying(true);
  };

  // ── AI Actions ─────────────────────────────────────────────────────
  const runAI = async (action: 'summarize' | 'keypoints' | 'questions' | 'tags') => {
    const text = lecture?.transcript || '';
    if (!text.trim()) {
      Alert.alert('لا يوجد نص', 'أضف نصاً أو سجّل محاضرة أولاً');
      return;
    }
    setAiLoading(true);
    setAiAction(action);
    try {
      if (action === 'summarize') {
        const summary = await summarizeLecture(text);
        await save({ summary });
      } else if (action === 'keypoints') {
        const keyPoints = await extractKeyPoints(text);
        await save({ keyPoints });
      } else if (action === 'questions') {
        const questions = await generateQuestions(text);
        await save({ tags: questions });
      } else if (action === 'tags') {
        const tags = await suggestTags(text);
        await save({ tags });
      }
      await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    } catch (e) {
      Alert.alert('خطأ', 'تعذّر الاتصال بالذكاء الاصطناعي');
    } finally {
      setAiLoading(false);
      setAiAction('');
    }
  };

  const sendChat = async () => {
    if (!chatInput.trim() || !lecture?.transcript) return;
    const userMsg = chatInput.trim();
    setChatInput('');
    setChatMessages(prev => [...prev, { role: 'user', text: userMsg }]);
    setChatLoading(true);
    try {
      const reply = await aiChat(userMsg, lecture.transcript);
      setChatMessages(prev => [...prev, { role: 'ai', text: reply }]);
    } catch {
      setChatMessages(prev => [...prev, { role: 'ai', text: 'تعذّر الرد. تحقق من الاتصال.' }]);
    } finally {
      setChatLoading(false);
    }
  };

  const fmtDuration = (sec: number) => `${Math.floor(sec / 60).toString().padStart(2, '0')}:${(sec % 60).toString().padStart(2, '0')}`;

  if (loading) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.background, alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator color={colors.primary} size="large" />
      </View>
    );
  }

  if (!lecture) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.background, alignItems: 'center', justifyContent: 'center' }}>
        <Text style={{ fontFamily: 'Tajawal_400Regular', color: colors.muted }}>المحاضرة غير موجودة</Text>
      </View>
    );
  }

  const s = styles(colors);

  return (
    <View style={[s.container, { paddingTop: insets.top }]}>
      {/* Header */}
      <View style={s.header}>
        <TouchableOpacity onPress={() => router.back()} style={s.backBtn}>
          <Ionicons name="chevron-back" size={22} color={colors.foreground} />
        </TouchableOpacity>
        <Text style={s.headerTitle} numberOfLines={1}>{lecture.title}</Text>
        <TouchableOpacity onPress={() => router.push(`/lecture/canvas/${lecture.id}`)} style={s.canvasBtn}>
          <Ionicons name="pencil" size={20} color={colors.accent} />
        </TouchableOpacity>
      </View>

      {/* Recording Bar */}
      <View style={s.recordBar}>
        {isRecording ? (
          <>
            <View style={s.recDot} />
            <Text style={s.recTime}>{fmtDuration(recordDuration)}</Text>
            <Text style={s.recLabel}>جاري التسجيل...</Text>
            <TouchableOpacity style={s.recStopBtn} onPress={stopRecording}>
              <Ionicons name="stop" size={18} color="#fff" />
            </TouchableOpacity>
          </>
        ) : lecture.audioUri ? (
          <>
            <TouchableOpacity style={s.playBtn} onPress={playAudio}>
              <Ionicons name={isPlaying ? 'pause' : 'play'} size={18} color="#fff" />
            </TouchableOpacity>
            <View style={s.waveform}>
              {Array.from({ length: 20 }).map((_, i) => (
                <View key={i} style={[s.waveBar, { height: 4 + Math.random() * 20, opacity: isPlaying ? 1 : 0.4 }]} />
              ))}
            </View>
            <Text style={s.recTime}>{fmtDuration(lecture.audioDuration ?? 0)}</Text>
          </>
        ) : (
          <>
            <TouchableOpacity style={s.recStartBtn} onPress={startRecording}>
              <Ionicons name="mic" size={18} color="#fff" />
              <Text style={s.recStartText}>بدء التسجيل</Text>
            </TouchableOpacity>
          </>
        )}
      </View>

      {/* Tabs */}
      <View style={s.tabBar}>
        {(['notes', 'transcript', 'ai'] as Tab[]).map(t => (
          <TouchableOpacity key={t} style={[s.tabBtn, tab === t && s.tabActive]} onPress={() => setTab(t)}>
            <Text style={[s.tabText, tab === t && s.tabTextActive]}>
              {t === 'notes' ? 'ملاحظات' : t === 'transcript' ? 'النص' : 'الذكاء الاصطناعي'}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Content */}
      {tab === 'notes' && (
        <ScrollView style={s.content} contentContainerStyle={{ padding: 16 }}>
          <TextInput
            style={s.notesInput}
            multiline
            placeholder="اكتب ملاحظاتك هنا..."
            placeholderTextColor={colors.mutedForeground}
            value={lecture.pages[0]?.textBoxes[0]?.text ?? ''}
            onChangeText={text => {
              const pages = [...lecture.pages];
              if (pages[0]) {
                if (pages[0].textBoxes.length === 0) {
                  pages[0].textBoxes = [{ id: 'tb1', text, x: 0, y: 0, width: 300, fontSize: 15, color: colors.foreground }];
                } else {
                  pages[0].textBoxes[0] = { ...pages[0].textBoxes[0], text };
                }
              }
              save({ pages });
            }}
            textAlignVertical="top"
            textAlign="right"
          />
        </ScrollView>
      )}

      {tab === 'transcript' && (
        <ScrollView style={s.content} contentContainerStyle={{ padding: 16, gap: 12 }}>
          <Text style={s.sectionLabel}>نص المحاضرة</Text>
          <TextInput
            style={s.transcriptInput}
            multiline
            placeholder="أضف نص المحاضرة يدوياً أو عبر تسجيل الصوت..."
            placeholderTextColor={colors.mutedForeground}
            value={lecture.transcript ?? ''}
            onChangeText={text => save({ transcript: text })}
            textAlignVertical="top"
            textAlign="right"
          />
        </ScrollView>
      )}

      {tab === 'ai' && (
        <View style={s.aiContainer}>
          {/* AI Action Buttons */}
          <View style={s.aiActions}>
            {[
              { key: 'summarize', icon: 'document-text', label: 'ملخص' },
              { key: 'keypoints', icon: 'list', label: 'نقاط رئيسية' },
              { key: 'questions', icon: 'help-circle', label: 'أسئلة متوقعة' },
              { key: 'tags', icon: 'pricetag', label: 'كلمات مفتاحية' },
            ].map(a => (
              <TouchableOpacity
                key={a.key}
                style={[s.aiActionBtn, aiLoading && aiAction === a.key && { opacity: 0.5 }]}
                onPress={() => runAI(a.key as any)}
                disabled={aiLoading}
              >
                {aiLoading && aiAction === a.key
                  ? <ActivityIndicator size={14} color={colors.primary} />
                  : <Ionicons name={a.icon as any} size={14} color={colors.primary} />
                }
                <Text style={s.aiActionText}>{a.label}</Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* AI Results */}
          <ScrollView style={s.aiResults} contentContainerStyle={{ padding: 14, gap: 12 }}>
            {lecture.summary && (
              <View style={s.aiCard}>
                <Text style={s.aiCardTitle}>الملخص</Text>
                <Text style={s.aiCardText}>{lecture.summary}</Text>
              </View>
            )}
            {lecture.keyPoints && lecture.keyPoints.length > 0 && (
              <View style={s.aiCard}>
                <Text style={s.aiCardTitle}>النقاط الرئيسية</Text>
                {lecture.keyPoints.map((kp, i) => (
                  <Text key={i} style={s.aiPoint}>• {kp}</Text>
                ))}
              </View>
            )}
            {lecture.tags && lecture.tags.length > 0 && (
              <View style={s.aiCard}>
                <Text style={s.aiCardTitle}>كلمات مفتاحية</Text>
                <View style={{ flexDirection: 'row', gap: 6, flexWrap: 'wrap', marginTop: 6 }}>
                  {lecture.tags.map(t => (
                    <View key={t} style={s.tag}><Text style={s.tagText}>{t}</Text></View>
                  ))}
                </View>
              </View>
            )}

            {/* Chat */}
            <View style={s.aiCard}>
              <Text style={s.aiCardTitle}>اسأل عن المحاضرة</Text>
              {chatMessages.map((m, i) => (
                <View key={i} style={[s.chatBubble, m.role === 'user' ? s.chatUser : s.chatAI]}>
                  <Text style={[s.chatText, m.role === 'user' ? s.chatTextUser : s.chatTextAI]}>{m.text}</Text>
                </View>
              ))}
              {chatLoading && <ActivityIndicator size="small" color={colors.primary} style={{ marginTop: 8 }} />}
              <View style={s.chatInputRow}>
                <TextInput
                  style={s.chatInput}
                  placeholder="اسأل سؤالاً..."
                  placeholderTextColor={colors.mutedForeground}
                  value={chatInput}
                  onChangeText={setChatInput}
                  textAlign="right"
                />
                <TouchableOpacity style={s.chatSendBtn} onPress={sendChat} disabled={chatLoading}>
                  <Ionicons name="send" size={16} color="#fff" />
                </TouchableOpacity>
              </View>
            </View>
          </ScrollView>
        </View>
      )}

      <View style={{ height: insets.bottom + (Platform.OS === 'web' ? 34 : 0) }} />
    </View>
  );
}

const styles = (c: ReturnType<typeof useColors>) => StyleSheet.create({
  container: { flex: 1, backgroundColor: c.background },
  header: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 14, paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: c.border },
  backBtn: { padding: 4, marginRight: 6 },
  headerTitle: { flex: 1, fontFamily: 'Tajawal_700Bold', fontSize: 18, color: c.foreground },
  canvasBtn: { padding: 4, backgroundColor: c.accent + '15', borderRadius: 8, borderWidth: 1, borderColor: c.accent + '30' },
  recordBar: { flexDirection: 'row', alignItems: 'center', gap: 10, padding: 12, backgroundColor: c.surface, borderBottomWidth: 1, borderBottomColor: c.border },
  recDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: c.recordingRed },
  recTime: { fontFamily: 'Tajawal_700Bold', fontSize: 14, color: c.foreground, minWidth: 40 },
  recLabel: { flex: 1, fontFamily: 'Tajawal_400Regular', fontSize: 13, color: c.muted },
  recStopBtn: { backgroundColor: c.recordingRed, borderRadius: 8, padding: 8 },
  recStartBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: c.recordingRed, borderRadius: 10, paddingHorizontal: 14, paddingVertical: 8 },
  recStartText: { fontFamily: 'Tajawal_500Medium', fontSize: 13, color: '#fff' },
  playBtn: { backgroundColor: c.primary, borderRadius: 8, padding: 8 },
  waveform: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 2, height: 28 },
  waveBar: { width: 3, backgroundColor: c.waveform, borderRadius: 2 },
  tabBar: { flexDirection: 'row', backgroundColor: c.surface, borderBottomWidth: 1, borderBottomColor: c.border },
  tabBtn: { flex: 1, paddingVertical: 12, alignItems: 'center', borderBottomWidth: 2, borderBottomColor: 'transparent' },
  tabActive: { borderBottomColor: c.primary },
  tabText: { fontFamily: 'Tajawal_500Medium', fontSize: 13, color: c.muted },
  tabTextActive: { color: c.primary },
  content: { flex: 1 },
  notesInput: { fontFamily: 'Tajawal_400Regular', fontSize: 15, color: c.foreground, lineHeight: 26, minHeight: 300 },
  sectionLabel: { fontFamily: 'Tajawal_700Bold', fontSize: 14, color: c.muted },
  transcriptInput: { fontFamily: 'Tajawal_400Regular', fontSize: 15, color: c.foreground, lineHeight: 26, backgroundColor: c.card, borderRadius: 12, padding: 14, minHeight: 200, borderWidth: 1, borderColor: c.border },
  aiContainer: { flex: 1 },
  aiActions: { flexDirection: 'row', gap: 8, padding: 12, flexWrap: 'wrap', backgroundColor: c.surface, borderBottomWidth: 1, borderBottomColor: c.border },
  aiActionBtn: { flexDirection: 'row', alignItems: 'center', gap: 5, backgroundColor: c.primary + '15', borderRadius: 10, paddingHorizontal: 10, paddingVertical: 7, borderWidth: 1, borderColor: c.primary + '30' },
  aiActionText: { fontFamily: 'Tajawal_500Medium', fontSize: 12, color: c.primary },
  aiResults: { flex: 1 },
  aiCard: { backgroundColor: c.card, borderRadius: 14, padding: 14, gap: 8, borderWidth: 1, borderColor: c.border },
  aiCardTitle: { fontFamily: 'Tajawal_700Bold', fontSize: 14, color: c.primary },
  aiCardText: { fontFamily: 'Tajawal_400Regular', fontSize: 14, color: c.foreground, lineHeight: 22 },
  aiPoint: { fontFamily: 'Tajawal_400Regular', fontSize: 14, color: c.foreground, lineHeight: 24 },
  tag: { backgroundColor: c.primary + '20', borderRadius: 7, paddingHorizontal: 9, paddingVertical: 3 },
  tagText: { fontFamily: 'Tajawal_400Regular', fontSize: 12, color: c.primary },
  chatBubble: { borderRadius: 12, padding: 10, maxWidth: '85%' },
  chatUser: { alignSelf: 'flex-end', backgroundColor: c.primary },
  chatAI: { alignSelf: 'flex-start', backgroundColor: c.surfaceElevated },
  chatText: { fontFamily: 'Tajawal_400Regular', fontSize: 13, lineHeight: 20 },
  chatTextUser: { color: '#fff' },
  chatTextAI: { color: c.foreground },
  chatInputRow: { flexDirection: 'row', gap: 8, marginTop: 6 },
  chatInput: { flex: 1, backgroundColor: c.surface, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 8, fontFamily: 'Tajawal_400Regular', fontSize: 13, color: c.foreground, borderWidth: 1, borderColor: c.border },
  chatSendBtn: { backgroundColor: c.primary, borderRadius: 10, padding: 10, alignItems: 'center', justifyContent: 'center' },
});
