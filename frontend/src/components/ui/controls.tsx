import React from 'react';
import * as Select from '@radix-ui/react-select';
import * as Slider from '@radix-ui/react-slider';
import * as Tooltip from '@radix-ui/react-tooltip';
import TextareaAutosize from 'react-textarea-autosize';
import clsx from 'clsx';
import { Check, ChevronDown, Minus, Plus } from 'lucide-react';

export type SelectOption = {
  label: string;
  value: string;
};

export function FieldLabel({
  label,
  value,
  icon,
}: {
  label: string;
  value?: React.ReactNode;
  icon?: React.ReactNode;
}) {
  return (
    <div className="control-label">
      <span className="flex items-center gap-2">
        {icon}
        {label}
      </span>
      {value !== undefined && <span className="control-value">{value}</span>}
    </div>
  );
}

export function TextField({
  label,
  value,
  onChange,
  placeholder,
  icon,
  className,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  icon?: React.ReactNode;
  className?: string;
}) {
  return (
    <label className={clsx('block space-y-2', className)}>
      <FieldLabel label={label} icon={icon} />
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="arpo-text-field"
      />
    </label>
  );
}

export function NumberField({
  label,
  value,
  onChange,
  min,
  max,
  icon,
  className,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  icon?: React.ReactNode;
  className?: string;
}) {
  return (
    <label className={clsx('block space-y-2', className)}>
      <FieldLabel label={label} icon={icon} />
      <input
        type="number"
        min={min}
        max={max}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="arpo-text-field arpo-number-field"
      />
    </label>
  );
}

export function StepperField({
  label,
  value,
  onChange,
  min = 0,
  max = Number.MAX_SAFE_INTEGER,
  step = 1,
  icon,
  accent = 'var(--color-accent-cyan)',
  className,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  icon?: React.ReactNode;
  accent?: string;
  className?: string;
}) {
  const clamp = (nextValue: number) => Math.min(max, Math.max(min, nextValue));
  const update = (nextValue: number) => onChange(clamp(nextValue));

  return (
    <label className={clsx('block space-y-2', className)}>
      <FieldLabel label={label} icon={icon} />
      <div className="arpo-stepper" style={{ '--stepper-accent': accent } as React.CSSProperties}>
        <button
          type="button"
          onClick={() => update(value - step)}
          disabled={value <= min}
          className="arpo-stepper-button"
          aria-label={`Decrease ${label}`}
        >
          <Minus size={13} strokeWidth={2.6} />
        </button>
        <input
          value={value}
          inputMode="numeric"
          aria-label={label}
          onChange={(event) => {
            const numeric = Number(event.target.value.replace(/[^\d.-]/g, ''));
            if (Number.isFinite(numeric)) update(numeric);
          }}
          onBlur={() => update(value)}
          className="arpo-stepper-input"
        />
        <button
          type="button"
          onClick={() => update(value + step)}
          disabled={value >= max}
          className="arpo-stepper-button"
          aria-label={`Increase ${label}`}
        >
          <Plus size={13} strokeWidth={2.6} />
        </button>
      </div>
    </label>
  );
}

export function TextAreaField({
  label,
  value,
  onChange,
  placeholder,
  valueLabel,
  icon,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  valueLabel?: React.ReactNode;
  icon?: React.ReactNode;
}) {
  return (
    <label className="block space-y-2">
      <FieldLabel label={label} value={valueLabel} icon={icon} />
      <TextareaAutosize
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        minRows={5}
        maxRows={9}
        className="arpo-input"
      />
    </label>
  );
}

export function SelectField({
  label,
  icon,
  value,
  onChange,
  options,
  accent = 'text-[var(--color-accent-cyan)]',
}: {
  label: string;
  icon?: React.ReactNode;
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  accent?: string;
}) {
  return (
    <div className="space-y-2">
      <FieldLabel label={label} />
      <Select.Root value={value} onValueChange={onChange}>
        <Select.Trigger className="arpo-select-trigger" aria-label={label}>
          <span className={clsx('flex items-center gap-2', accent)}>
            {icon}
          </span>
          <Select.Value />
          <Select.Icon asChild>
            <ChevronDown size={15} className="ml-auto text-[var(--color-text-muted)]" />
          </Select.Icon>
        </Select.Trigger>
        <Select.Portal>
          <Select.Content className="arpo-select-content" position="popper" sideOffset={7}>
            <Select.Viewport className="p-1">
              {options.map((option) => (
                <Select.Item key={option.value} value={option.value} className="arpo-select-item">
                  <Select.ItemText>{option.label}</Select.ItemText>
                  <Select.ItemIndicator className="ml-auto">
                    <Check size={13} />
                  </Select.ItemIndicator>
                </Select.Item>
              ))}
            </Select.Viewport>
          </Select.Content>
        </Select.Portal>
      </Select.Root>
    </div>
  );
}

export function SliderField({
  label,
  value,
  min,
  max,
  step,
  color = 'var(--color-accent-cyan)',
  formatter = (nextValue) => String(nextValue),
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  color?: string;
  formatter?: (value: number) => string;
  onChange: (value: number) => void;
}) {
  return (
    <div className="rounded-lg border border-[var(--color-border-subtle)] bg-[rgba(7,11,23,0.62)] p-3">
      <FieldLabel label={label} value={formatter(value)} />
      <Slider.Root
        value={[value]}
        min={min}
        max={max}
        step={step}
        onValueChange={([next]) => onChange(next)}
        className="arpo-slider-root"
        style={{ '--slider-color': color } as React.CSSProperties}
      >
        <Slider.Track className="arpo-slider-track">
          <Slider.Range className="arpo-slider-range" />
        </Slider.Track>
        <Slider.Thumb className="arpo-slider-thumb" aria-label={label} />
      </Slider.Root>
    </div>
  );
}

export function TooltipProvider({ children }: { children: React.ReactNode }) {
  return <Tooltip.Provider delayDuration={220}>{children}</Tooltip.Provider>;
}

export function AppTooltip({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <Tooltip.Root>
      <Tooltip.Trigger asChild>{children}</Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content className="arpo-tooltip" sideOffset={8}>
          {label}
          <Tooltip.Arrow className="fill-[var(--color-bg-panel)]" />
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}
