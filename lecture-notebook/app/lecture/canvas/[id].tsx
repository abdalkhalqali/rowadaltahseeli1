import React, { useEffect, useRef, useState, useCallback } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, PanResponder,
  Dimensions, Alert, Platform,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Svg, { Path, G } from 'react-native-svg';
import { Ionicons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { useColors } from '@/hooks/useColors';
import { getLecture, updateLecture, Stroke, LecturePage } from '@/lib/storage';

const { width: SCREEN_W, height: SCREEN_H } = Dimensions.get('window');

type Tool = 'pen' | 'pencil' | 'highlighter' | 'eraser';

const TOOL_COLORS = ['#F1F5F9', '#4F8EF7', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6'];
const TOOL_WIDTHS: Record<Tool, number> = { pen: 2, pencil: 1.5, highlighter: 12, eraser: 20 };

function uid() { return Date.now().toString() + Math.random().toString(36).substr(2, 9); }

function pointsToPath(points: number[]): string {
  if (points.length < 4) return '';
  let d = `M ${points[0]} ${points[1]}`;
  for (let i = 2; i < points.length - 2; i += 2) {
    const mx = (points[i] + points[i + 2]) / 2;
    const my = (points[i + 1] + points[i + 3]) / 2;
    d += ` Q ${points[i]} ${points[i + 1]} ${mx} ${my}`;
  }
  return d;
}

export default function CanvasScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const colors = useColors();
  const insets = useSafeAreaInsets();

  const [strokes, setStrokes] = useState<Stroke[]>([]);
  const [currentPoints, setCurrentPoints] = useState<number[]>([]);
  const [tool, setTool] = useState<Tool>('pen');
  const [penColor, setPenColor] = useState(TOOL_COLORS[0]);
  const [pageId, setPageId] = useState('');
  const [saved, setSaved] = useState(true);
  const [showColors, setShowColors] = useState(false);
  const strokesRef = useRef<Stroke[]>([]);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!id) return;
    getLecture(id).then(l => {
      if (!l) return;
      const page = l.pages[0];
      if (page) { setStrokes(page.strokes); strokesRef.current = page.strokes; setPageId(page.id); }
    });
  }, [id]);

  const scheduleAutoSave = useCallback(() => {
    setSaved(false);
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(async () => {
      if (!id || !pageId) return;
      const l = await getLecture(id);
      if (!l) return;
      const pages = l.pages.map(p =>
        p.id === pageId ? { ...p, strokes: strokesRef.current } : p
      );
      await updateLecture(id, { pages });
      setSaved(true);
    }, 1500);
  }, [id, pageId]);

  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      onPanResponderGrant: (e) => {
        const { locationX, locationY } = e.nativeEvent;
        setCurrentPoints([locationX, locationY]);
      },
      onPanResponderMove: (e) => {
        const { locationX, locationY } = e.nativeEvent;
        setCurrentPoints(prev => [...prev, locationX, locationY]);
      },
      onPanResponderRelease: () => {
        setCurrentPoints(prev => {
          if (prev.length < 4) return [];
          const toolRef = toolRef_current;
          const colorRef = colorRef_current;
          const widthRef = TOOL_WIDTHS[toolRef];
          if (toolRef === 'eraser') {
            // Simplified eraser: remove last stroke
            strokesRef.current = strokesRef.current.slice(0, -1);
            setStrokes([...strokesRef.current]);
          } else {
            const newStroke: Stroke = {
              id: uid(),
              points: prev,
              color: toolRef === 'highlighter' ? colorRef + '60' : colorRef,
              width: widthRef,
              tool: toolRef,
            };
            strokesRef.current = [...strokesRef.current, newStroke];
            setStrokes([...strokesRef.current]);
          }
          scheduleAutoSave();
          return [];
        });
      },
    })
  ).current;

  // Refs to capture latest state in panResponder closure
  const toolRef_current = tool;
  const colorRef_current = penColor;

  const undo = async () => {
    if (strokesRef.current.length === 0) return;
    await Haptics.selectionAsync();
    strokesRef.current = strokesRef.current.slice(0, -1);
    setStrokes([...strokesRef.current]);
    scheduleAutoSave();
  };

  const clearAll = () => {
    Alert.alert('مسح الكل', 'هل تريد مسح جميع الرسومات؟', [
      { text: 'إلغاء', style: 'cancel' },
      {
        text: 'مسح', style: 'destructive', onPress: async () => {
          strokesRef.current = [];
          setStrokes([]);
          scheduleAutoSave();
          await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
        },
      },
    ]);
  };

  const canvasH = SCREEN_H - insets.top - 110;
  const s = styles(colors);

  return (
    <View style={[s.container, { paddingTop: insets.top }]}>
      {/* Header */}
      <View style={s.header}>
        <TouchableOpacity onPress={() => router.back()} style={s.backBtn}>
          <Ionicons name="chevron-back" size={22} color={colors.foreground} />
        </TouchableOpacity>
        <Text style={s.headerTitle}>لوحة الكتابة</Text>
        <View style={s.headerRight}>
          {!saved && <Text style={s.savingText}>حفظ...</Text>}
          {saved && <Ionicons name="checkmark-circle" size={18} color={colors.accent} />}
        </View>
      </View>

      {/* Toolbar */}
      <View style={s.toolbar}>
        {/* Tools */}
        <View style={s.toolGroup}>
          {(['pen', 'pencil', 'highlighter', 'eraser'] as Tool[]).map(t => (
            <TouchableOpacity key={t} style={[s.toolBtn, tool === t && s.toolActive]}
              onPress={() => { setTool(t); Haptics.selectionAsync(); }}>
              <Ionicons
                name={t === 'pen' ? 'create' : t === 'pencil' ? 'pencil' : t === 'highlighter' ? 'brush' : 'square'}
                size={18}
                color={tool === t ? colors.primary : colors.mutedForeground}
              />
            </TouchableOpacity>
          ))}
        </View>

        {/* Color picker */}
        <TouchableOpacity
          style={[s.colorPickerBtn, { backgroundColor: penColor }]}
          onPress={() => setShowColors(!showColors)}
        />

        {/* Undo / Clear */}
        <TouchableOpacity style={s.toolBtn} onPress={undo}>
          <Ionicons name="arrow-undo" size={18} color={colors.mutedForeground} />
        </TouchableOpacity>
        <TouchableOpacity style={s.toolBtn} onPress={clearAll}>
          <Ionicons name="trash" size={18} color={colors.accentDanger} />
        </TouchableOpacity>
      </View>

      {/* Color palette */}
      {showColors && (
        <View style={s.palette}>
          {TOOL_COLORS.map(c => (
            <TouchableOpacity key={c} onPress={() => { setPenColor(c); setShowColors(false); }}
              style={[s.paletteDot, { backgroundColor: c }, penColor === c && s.paletteDotActive]} />
          ))}
        </View>
      )}

      {/* Canvas */}
      <View style={[s.canvas, { height: canvasH }]} {...panResponder.panHandlers}>
        {/* Grid background */}
        <Svg style={StyleSheet.absoluteFill} width={SCREEN_W} height={canvasH}>
          <G opacity={0.08}>
            {Array.from({ length: Math.ceil(canvasH / 30) }).map((_, i) => (
              <Path key={`h${i}`} d={`M 0 ${i * 30} L ${SCREEN_W} ${i * 30}`} stroke={colors.foreground} strokeWidth={0.5} />
            ))}
            {Array.from({ length: Math.ceil(SCREEN_W / 30) }).map((_, i) => (
              <Path key={`v${i}`} d={`M ${i * 30} 0 L ${i * 30} ${canvasH}`} stroke={colors.foreground} strokeWidth={0.5} />
            ))}
          </G>
          {/* Saved strokes */}
          {strokes.map(stroke => (
            <Path
              key={stroke.id}
              d={pointsToPath(stroke.points)}
              stroke={stroke.color}
              strokeWidth={stroke.width}
              strokeLinecap="round"
              strokeLinejoin="round"
              fill="none"
            />
          ))}
          {/* Current stroke */}
          {currentPoints.length >= 4 && (
            <Path
              d={pointsToPath(currentPoints)}
              stroke={tool === 'highlighter' ? penColor + '60' : penColor}
              strokeWidth={TOOL_WIDTHS[tool]}
              strokeLinecap="round"
              strokeLinejoin="round"
              fill="none"
            />
          )}
        </Svg>
      </View>
    </View>
  );
}

const styles = (c: ReturnType<typeof useColors>) => StyleSheet.create({
  container: { flex: 1, backgroundColor: c.background },
  header: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 14, paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: c.border },
  backBtn: { padding: 4, marginRight: 6 },
  headerTitle: { flex: 1, fontFamily: 'Tajawal_700Bold', fontSize: 18, color: c.foreground },
  headerRight: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  savingText: { fontFamily: 'Tajawal_400Regular', fontSize: 12, color: c.muted },
  toolbar: { flexDirection: 'row', alignItems: 'center', gap: 6, padding: 10, backgroundColor: c.surface, borderBottomWidth: 1, borderBottomColor: c.border },
  toolGroup: { flexDirection: 'row', gap: 4 },
  toolBtn: { width: 36, height: 36, borderRadius: 9, alignItems: 'center', justifyContent: 'center', backgroundColor: c.card, borderWidth: 1, borderColor: c.border },
  toolActive: { borderColor: c.primary, backgroundColor: c.primary + '15' },
  colorPickerBtn: { width: 28, height: 28, borderRadius: 14, borderWidth: 2, borderColor: '#fff', marginLeft: 4 },
  palette: { flexDirection: 'row', gap: 10, padding: 10, backgroundColor: c.surfaceElevated, borderBottomWidth: 1, borderBottomColor: c.border, justifyContent: 'center' },
  paletteDot: { width: 30, height: 30, borderRadius: 15 },
  paletteDotActive: { borderWidth: 3, borderColor: '#fff' },
  canvas: { flex: 1, backgroundColor: '#0D1321' },
});
