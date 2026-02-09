/**
 * ScheduleTimeSelector component.
 *
 * Allows modification of scheduled publish time during approval.
 *
 * Features:
 * - Date/time picker with relative time options
 * - Shows suggested time as default
 * - Validates time is in the future
 * - Confirmation before saving
 */

import React, { useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Calendar } from "@/components/ui/calendar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { CalendarIcon, Clock, Check, X } from "lucide-react";
import { format, addHours, addDays, setHours, setMinutes, isBefore } from "date-fns";

export interface ScheduleTimeSelectorProps {
  suggestedTime?: Date | string | null;
  onConfirm: (time: Date | null) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

/**
 * Quick schedule options for common use cases.
 */
const QUICK_OPTIONS = [
  { label: "In 1 hour", getTime: () => addHours(new Date(), 1) },
  { label: "In 3 hours", getTime: () => addHours(new Date(), 3) },
  { label: "Tomorrow 9 AM", getTime: () => setMinutes(setHours(addDays(new Date(), 1), 9), 0) },
  { label: "Tomorrow 6 PM", getTime: () => setMinutes(setHours(addDays(new Date(), 1), 18), 0) },
] as const;

/**
 * Hour options for the time picker.
 */
const HOURS = Array.from({ length: 24 }, (_, i) => ({
  value: i.toString(),
  label: i.toString().padStart(2, "0"),
}));

/**
 * Minute options for the time picker (15-minute intervals).
 */
const MINUTES = [0, 15, 30, 45].map((m) => ({
  value: m.toString(),
  label: m.toString().padStart(2, "0"),
}));

/**
 * Parse date from string or Date.
 */
function parseDate(value: Date | string | null | undefined): Date | null {
  if (!value) return null;
  if (value instanceof Date) return value;
  const parsed = new Date(value);
  return isNaN(parsed.getTime()) ? null : parsed;
}

/**
 * Schedule time selector for approval workflow.
 */
export function ScheduleTimeSelector({
  suggestedTime,
  onConfirm,
  onCancel,
  isLoading = false,
}: ScheduleTimeSelectorProps): React.ReactElement {
  const suggested = parseDate(suggestedTime);
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(
    suggested || undefined
  );
  const [selectedHour, setSelectedHour] = useState<string>(
    suggested ? suggested.getHours().toString() : "12"
  );
  const [selectedMinute, setSelectedMinute] = useState<string>(
    suggested ? (Math.floor(suggested.getMinutes() / 15) * 15).toString() : "0"
  );
  const [error, setError] = useState<string | null>(null);

  // Calculate the full datetime
  const getScheduledTime = useCallback((): Date | null => {
    if (!selectedDate) return null;
    const time = new Date(selectedDate);
    time.setHours(parseInt(selectedHour, 10));
    time.setMinutes(parseInt(selectedMinute, 10));
    time.setSeconds(0);
    time.setMilliseconds(0);
    return time;
  }, [selectedDate, selectedHour, selectedMinute]);

  // Handle quick option selection
  const handleQuickOption = useCallback((getTime: () => Date) => {
    const time = getTime();
    setSelectedDate(time);
    setSelectedHour(time.getHours().toString());
    setSelectedMinute((Math.floor(time.getMinutes() / 15) * 15).toString());
    setError(null);
  }, []);

  // Handle confirm
  const handleConfirm = useCallback(() => {
    const time = getScheduledTime();

    if (time && isBefore(time, new Date())) {
      setError("Schedule time must be in the future");
      return;
    }

    setError(null);
    onConfirm(time);
  }, [getScheduledTime, onConfirm]);

  // Handle use suggested time
  const handleUseSuggested = useCallback(() => {
    if (suggested) {
      setSelectedDate(suggested);
      setSelectedHour(suggested.getHours().toString());
      setSelectedMinute((Math.floor(suggested.getMinutes() / 15) * 15).toString());
      setError(null);
    }
  }, [suggested]);

  const scheduledTime = getScheduledTime();
  const isModified = suggested && scheduledTime
    ? scheduledTime.getTime() !== suggested.getTime()
    : !!scheduledTime;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Label className="text-base font-medium">Schedule Publish Time</Label>
        {isModified && (
          <Badge variant="outline" className="text-yellow-600 border-yellow-500">
            Modified
          </Badge>
        )}
      </div>

      {/* Suggested time display */}
      {suggested && (
        <div className="flex items-center gap-2 p-3 bg-blue-50 rounded-lg">
          <Clock className="h-4 w-4 text-blue-600" />
          <span className="text-sm text-blue-700">
            Suggested: {format(suggested, "PPpp")}
          </span>
          {isModified && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleUseSuggested}
              className="ml-auto text-blue-600 hover:text-blue-800"
            >
              Use Suggested
            </Button>
          )}
        </div>
      )}

      {/* Quick options */}
      <div>
        <Label className="text-sm text-gray-500 mb-2 block">Quick Options</Label>
        <div className="flex flex-wrap gap-2">
          {QUICK_OPTIONS.map((option) => (
            <Button
              key={option.label}
              variant="outline"
              size="sm"
              onClick={() => handleQuickOption(option.getTime)}
              disabled={isLoading}
            >
              {option.label}
            </Button>
          ))}
        </div>
      </div>

      {/* Date picker */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label className="text-sm text-gray-500 mb-2 block">Date</Label>
          <Popover>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                className="w-full justify-start text-left font-normal"
                disabled={isLoading}
              >
                <CalendarIcon className="mr-2 h-4 w-4" />
                {selectedDate ? format(selectedDate, "PP") : "Select date"}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="start">
              <Calendar
                mode="single"
                selected={selectedDate}
                onSelect={setSelectedDate}
                disabled={(date) => isBefore(date, new Date())}
                initialFocus
              />
            </PopoverContent>
          </Popover>
        </div>

        {/* Time picker */}
        <div>
          <Label className="text-sm text-gray-500 mb-2 block">Time</Label>
          <div className="flex gap-2">
            <Select
              value={selectedHour}
              onValueChange={setSelectedHour}
              disabled={isLoading}
            >
              <SelectTrigger className="w-[70px]">
                <SelectValue placeholder="HH" />
              </SelectTrigger>
              <SelectContent>
                {HOURS.map((h) => (
                  <SelectItem key={h.value} value={h.value}>
                    {h.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <span className="flex items-center text-gray-500">:</span>
            <Select
              value={selectedMinute}
              onValueChange={setSelectedMinute}
              disabled={isLoading}
            >
              <SelectTrigger className="w-[70px]">
                <SelectValue placeholder="MM" />
              </SelectTrigger>
              <SelectContent>
                {MINUTES.map((m) => (
                  <SelectItem key={m.value} value={m.value}>
                    {m.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      {/* Selected time preview */}
      {scheduledTime && (
        <div className="p-3 bg-gray-50 rounded-lg">
          <span className="text-sm text-gray-600">
            Will publish: <strong>{format(scheduledTime, "PPpp")}</strong>
          </span>
        </div>
      )}

      {/* Error message */}
      {error && (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      {/* Action buttons */}
      <div className="flex justify-end gap-2 pt-2 border-t">
        <Button
          variant="outline"
          size="sm"
          onClick={onCancel}
          disabled={isLoading}
        >
          <X className="h-4 w-4 mr-2" />
          Cancel
        </Button>
        <Button
          size="sm"
          onClick={handleConfirm}
          disabled={isLoading}
          className="bg-green-600 hover:bg-green-700"
        >
          <Check className="h-4 w-4 mr-2" />
          Confirm Time
        </Button>
      </div>
    </div>
  );
}

export default ScheduleTimeSelector;
