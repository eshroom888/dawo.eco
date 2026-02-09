/**
 * CaptionEditor component.
 *
 * Inline caption editor with character/word count and editing controls.
 *
 * Features:
 * - Textarea with character count
 * - Word count display with target range (180-220)
 * - Rich text formatting toolbar (bold, italic, emoji)
 * - Hashtag editing with autocomplete suggestions
 * - Save, Cancel, and Revert to Original buttons
 * - Loading states during save
 */

import React, { useState, useCallback, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Loader2,
  Save,
  X,
  RotateCcw,
  AlertTriangle,
  Bold,
  Italic,
  Smile,
} from "lucide-react";

// Common DAWO hashtag suggestions
const HASHTAG_SUGGESTIONS = [
  "DAWO",
  "DAWOmushrooms",
  "DAWOwellness",
  "lionsmane",
  "reishi",
  "chaga",
  "cordyceps",
  "functionalfoods",
  "adaptogens",
  "wellness",
  "naturalhealth",
  "plantbased",
  "superfood",
  "brainhealth",
  "immunesupport",
  "energy",
  "focus",
  "Norway",
  "Nordic",
];

// Common emojis for social media posts
const EMOJI_PALETTE = [
  "🍄", "✨", "🌿", "💚", "🌱", "🧠", "💪", "🔥",
  "⚡", "🌟", "🙌", "❤️", "🌈", "🍃", "🌲", "🏔️",
];

export interface CaptionEditorProps {
  caption: string;
  originalCaption?: string | null;
  hashtags: string[];
  onSave: (caption: string, hashtags: string[]) => Promise<void>;
  onCancel: () => void;
  onRevert?: () => Promise<void>;
  isLoading?: boolean;
  maxCharacters?: number;
  targetWordMin?: number;
  targetWordMax?: number;
}

/**
 * Count words in text.
 */
function countWords(text: string): number {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

/**
 * Parse hashtags from text.
 */
function parseHashtags(text: string): string[] {
  const matches = text.match(/#[\w\u00C0-\u024F]+/g) || [];
  return matches.map((tag) => tag.slice(1)); // Remove # prefix
}

/**
 * Inline caption editor.
 */
export function CaptionEditor({
  caption,
  originalCaption,
  hashtags,
  onSave,
  onCancel,
  onRevert,
  isLoading = false,
  maxCharacters = 2200,
  targetWordMin = 180,
  targetWordMax = 220,
}: CaptionEditorProps): React.ReactElement {
  const [editedCaption, setEditedCaption] = useState(caption);
  const [editedHashtags, setEditedHashtags] = useState(hashtags.join(" #"));
  const [error, setError] = useState<string | null>(null);
  const [saveAction, setSaveAction] = useState<"save" | "revert" | null>(null);
  const [showHashtagSuggestions, setShowHashtagSuggestions] = useState(false);
  const [hashtagFilter, setHashtagFilter] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const hashtagInputRef = useRef<HTMLTextAreaElement>(null);

  // Update local state when props change
  useEffect(() => {
    setEditedCaption(caption);
    setEditedHashtags(hashtags.join(" #"));
  }, [caption, hashtags]);

  // Filter hashtag suggestions based on input
  const filteredHashtags = HASHTAG_SUGGESTIONS.filter(
    (tag) =>
      tag.toLowerCase().includes(hashtagFilter.toLowerCase()) &&
      !editedHashtags.toLowerCase().includes(tag.toLowerCase())
  );

  // Insert text at cursor position in caption
  const insertTextAtCursor = useCallback((text: string) => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const newCaption =
      editedCaption.slice(0, start) + text + editedCaption.slice(end);
    setEditedCaption(newCaption);

    // Restore cursor position after insertion
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(start + text.length, start + text.length);
    }, 0);
  }, [editedCaption]);

  // Wrap selected text with formatting markers
  const wrapSelection = useCallback((prefix: string, suffix: string) => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selectedText = editedCaption.slice(start, end);

    if (selectedText) {
      const newCaption =
        editedCaption.slice(0, start) +
        prefix +
        selectedText +
        suffix +
        editedCaption.slice(end);
      setEditedCaption(newCaption);

      // Restore selection with formatting
      setTimeout(() => {
        textarea.focus();
        textarea.setSelectionRange(
          start + prefix.length,
          end + prefix.length
        );
      }, 0);
    }
  }, [editedCaption]);

  // Format handlers
  const handleBold = useCallback(() => {
    wrapSelection("**", "**");
  }, [wrapSelection]);

  const handleItalic = useCallback(() => {
    wrapSelection("_", "_");
  }, [wrapSelection]);

  const handleEmojiInsert = useCallback((emoji: string) => {
    insertTextAtCursor(emoji);
  }, [insertTextAtCursor]);

  // Add hashtag from suggestions
  const handleAddHashtag = useCallback((tag: string) => {
    const separator = editedHashtags.trim() ? " " : "";
    setEditedHashtags((prev) => prev.trim() + separator + tag);
    setHashtagFilter("");
    setShowHashtagSuggestions(false);
  }, [editedHashtags]);

  // Handle hashtag input changes for autocomplete
  const handleHashtagInputChange = useCallback((value: string) => {
    setEditedHashtags(value);
    // Extract last word for filtering
    const words = value.split(/[\s,]+/);
    const lastWord = words[words.length - 1] || "";
    setHashtagFilter(lastWord);
    setShowHashtagSuggestions(lastWord.length > 0 && filteredHashtags.length > 0);
  }, [filteredHashtags.length]);

  // Calculate counts
  const charCount = editedCaption.length;
  const wordCount = countWords(editedCaption);
  const hashtagList = editedHashtags
    ? editedHashtags
        .split(/[\s,]+/)
        .filter(Boolean)
        .map((tag) => (tag.startsWith("#") ? tag.slice(1) : tag))
    : [];
  const hashtagCount = hashtagList.length;

  // Validation
  const isValidLength = charCount <= maxCharacters && charCount > 0;
  const isWordCountInTarget = wordCount >= targetWordMin && wordCount <= targetWordMax;
  const hasChanges = editedCaption !== caption || editedHashtags !== hashtags.join(" #");
  const canSave = isValidLength && hasChanges && !isLoading;
  const canRevert = !!originalCaption && originalCaption !== caption && !isLoading;

  // Handle save
  const handleSave = useCallback(async () => {
    if (!canSave) return;

    setError(null);
    setSaveAction("save");

    try {
      await onSave(editedCaption, hashtagList);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save changes");
    } finally {
      setSaveAction(null);
    }
  }, [canSave, editedCaption, hashtagList, onSave]);

  // Handle revert
  const handleRevert = useCallback(async () => {
    if (!canRevert || !onRevert) return;

    setError(null);
    setSaveAction("revert");

    try {
      await onRevert();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to revert");
    } finally {
      setSaveAction(null);
    }
  }, [canRevert, onRevert]);

  // Keyboard shortcuts
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && canSave) {
        e.preventDefault();
        handleSave();
      }
      if (e.key === "Escape") {
        e.preventDefault();
        onCancel();
      }
    },
    [canSave, handleSave, onCancel]
  );

  return (
    <div className="space-y-4" onKeyDown={handleKeyDown}>
      {/* Caption textarea */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label htmlFor="caption-editor">Caption</Label>
          <div className="flex items-center gap-2 text-sm">
            <span
              className={
                isWordCountInTarget ? "text-green-600" : "text-yellow-600"
              }
            >
              {wordCount} words
              {!isWordCountInTarget && (
                <span className="text-gray-500 ml-1">
                  (target: {targetWordMin}-{targetWordMax})
                </span>
              )}
            </span>
            <span className="text-gray-400">|</span>
            <span
              className={
                charCount > maxCharacters ? "text-red-600" : "text-gray-600"
              }
            >
              {charCount}/{maxCharacters}
            </span>
          </div>
        </div>

        {/* Formatting Toolbar */}
        <div className="flex items-center gap-1 p-1 border rounded-t-md bg-gray-50">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleBold}
            disabled={isLoading}
            className="h-8 w-8 p-0"
            aria-label="Bold"
            title="Bold (select text first)"
          >
            <Bold className="h-4 w-4" />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleItalic}
            disabled={isLoading}
            className="h-8 w-8 p-0"
            aria-label="Italic"
            title="Italic (select text first)"
          >
            <Italic className="h-4 w-4" />
          </Button>
          <div className="w-px h-6 bg-gray-300 mx-1" />
          <Popover>
            <PopoverTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                disabled={isLoading}
                className="h-8 w-8 p-0"
                aria-label="Insert emoji"
                title="Insert emoji"
              >
                <Smile className="h-4 w-4" />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-2" align="start">
              <div className="grid grid-cols-8 gap-1">
                {EMOJI_PALETTE.map((emoji) => (
                  <Button
                    key={emoji}
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => handleEmojiInsert(emoji)}
                    className="h-8 w-8 p-0 text-lg hover:bg-gray-100"
                  >
                    {emoji}
                  </Button>
                ))}
              </div>
            </PopoverContent>
          </Popover>
        </div>

        <Textarea
          ref={textareaRef}
          id="caption-editor"
          value={editedCaption}
          onChange={(e) => setEditedCaption(e.target.value)}
          disabled={isLoading}
          placeholder="Enter caption text..."
          className="min-h-[200px] font-normal rounded-t-none border-t-0"
          aria-describedby="caption-help"
        />

        {charCount > maxCharacters && (
          <p className="text-sm text-red-600 flex items-center gap-1">
            <AlertTriangle className="h-4 w-4" />
            Caption exceeds maximum character limit
          </p>
        )}
      </div>

      {/* Hashtags editor */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label htmlFor="hashtags-editor">Hashtags</Label>
          <span
            className={
              hashtagCount > 30
                ? "text-red-600 text-sm"
                : "text-gray-600 text-sm"
            }
          >
            {hashtagCount}/30 max
          </span>
        </div>

        <div className="relative">
          <Textarea
            ref={hashtagInputRef}
            id="hashtags-editor"
            value={editedHashtags}
            onChange={(e) => handleHashtagInputChange(e.target.value)}
            onFocus={() => setShowHashtagSuggestions(hashtagFilter.length > 0)}
            onBlur={() => setTimeout(() => setShowHashtagSuggestions(false), 150)}
            disabled={isLoading}
            placeholder="Enter hashtags (e.g., DAWO DAWOmushrooms wellness)"
            className="min-h-[60px] font-normal"
            aria-describedby="hashtags-help"
          />

          {/* Hashtag Autocomplete Suggestions */}
          {showHashtagSuggestions && filteredHashtags.length > 0 && (
            <div className="absolute z-10 w-full mt-1 bg-white border rounded-md shadow-lg max-h-32 overflow-y-auto">
              {filteredHashtags.slice(0, 6).map((tag) => (
                <button
                  key={tag}
                  type="button"
                  onClick={() => handleAddHashtag(tag)}
                  className="w-full px-3 py-2 text-left text-sm hover:bg-gray-100 focus:bg-gray-100 focus:outline-none"
                >
                  #{tag}
                </button>
              ))}
            </div>
          )}
        </div>

        <p id="hashtags-help" className="text-xs text-gray-500">
          Enter hashtags separated by spaces. The # symbol is optional. Start typing for suggestions.
        </p>

        {/* Preview hashtags */}
        {hashtagList.length > 0 && (
          <div className="flex flex-wrap gap-1 pt-2">
            {hashtagList.slice(0, 10).map((tag, i) => (
              <Badge key={i} variant="secondary" className="text-xs">
                #{tag}
              </Badge>
            ))}
            {hashtagList.length > 10 && (
              <Badge variant="outline" className="text-xs">
                +{hashtagList.length - 10} more
              </Badge>
            )}
          </div>
        )}
      </div>

      {/* Error message */}
      {error && (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      {/* Action buttons */}
      <div className="flex items-center justify-between pt-2 border-t">
        <div className="flex gap-2">
          {/* Revert to Original */}
          {canRevert && onRevert && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleRevert}
              disabled={isLoading}
            >
              {saveAction === "revert" ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <RotateCcw className="h-4 w-4 mr-2" />
              )}
              Revert to Original
            </Button>
          )}
        </div>

        <div className="flex gap-2">
          {/* Cancel */}
          <Button
            variant="outline"
            size="sm"
            onClick={onCancel}
            disabled={isLoading}
          >
            <X className="h-4 w-4 mr-2" />
            Cancel
          </Button>

          {/* Save */}
          <Button
            size="sm"
            onClick={handleSave}
            disabled={!canSave}
            className="bg-blue-600 hover:bg-blue-700"
          >
            {saveAction === "save" ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Save className="h-4 w-4 mr-2" />
            )}
            Save Changes
          </Button>
        </div>
      </div>

      {/* Keyboard hint */}
      <p className="text-xs text-gray-500 text-center">
        Press Ctrl+Enter to save, Esc to cancel
      </p>
    </div>
  );
}

export default CaptionEditor;
