import { Check, ChevronDown } from 'lucide-react'
import {
  useEffect,
  useId,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from 'react'

export interface SelectOption {
  value: string
  label: string
  description?: string
}

interface CustomSelectProps {
  ariaLabel: string
  disabled?: boolean
  icon?: ReactNode
  onChange: (value: string) => void
  options: SelectOption[]
  placeholder?: string
  value: string
  variant?: 'toolbar' | 'field'
}

export function CustomSelect({
  ariaLabel,
  disabled = false,
  icon,
  onChange,
  options,
  placeholder = 'Select an option',
  value,
  variant = 'toolbar',
}: CustomSelectProps) {
  const [open, setOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(0)
  const rootRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const optionRefs = useRef<Array<HTMLButtonElement | null>>([])
  const listboxId = useId()
  const selectedIndex = Math.max(0, options.findIndex((option) => option.value === value))
  const selected = options.find((option) => option.value === value)
  const unavailable = disabled || options.length === 0

  useEffect(() => {
    const closeOnOutsideClick = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('pointerdown', closeOnOutsideClick)
    return () => document.removeEventListener('pointerdown', closeOnOutsideClick)
  }, [])

  useEffect(() => {
    if (!open) return
    window.requestAnimationFrame(() => optionRefs.current[selectedIndex]?.focus())
  }, [open, selectedIndex])

  const closeAndFocus = () => {
    setOpen(false)
    window.requestAnimationFrame(() => triggerRef.current?.focus())
  }

  const moveFocus = (index: number) => {
    const nextIndex = (index + options.length) % options.length
    setActiveIndex(nextIndex)
    optionRefs.current[nextIndex]?.focus()
  }

  const handleTriggerKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      setActiveIndex(selectedIndex)
      setOpen(true)
    }
    if (event.key === 'Escape') setOpen(false)
  }

  const handleOptionKeyDown = (
    event: KeyboardEvent<HTMLButtonElement>,
    index: number,
  ) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      moveFocus(index + 1)
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      moveFocus(index - 1)
    } else if (event.key === 'Home') {
      event.preventDefault()
      moveFocus(0)
    } else if (event.key === 'End') {
      event.preventDefault()
      moveFocus(options.length - 1)
    } else if (event.key === 'Escape') {
      event.preventDefault()
      closeAndFocus()
    } else if (event.key === 'Tab') {
      setOpen(false)
    }
  }

  return (
    <div
      className={`custom-select custom-select--${variant}${open ? ' custom-select--open' : ''}`}
      ref={rootRef}
    >
      <button
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-label={ariaLabel}
        aria-controls={open ? listboxId : undefined}
        className="custom-select__trigger"
        disabled={unavailable}
        onClick={() => {
          if (!open) setActiveIndex(selectedIndex)
          setOpen((current) => !current)
        }}
        onKeyDown={handleTriggerKeyDown}
        ref={triggerRef}
        type="button"
      >
        {icon && <span className="custom-select__icon">{icon}</span>}
        <span className="custom-select__value">{selected?.label ?? placeholder}</span>
        <ChevronDown aria-hidden="true" className="custom-select__chevron" size={15} />
      </button>
      {open && (
        <div aria-label={ariaLabel} className="custom-select__menu" id={listboxId} role="listbox">
          {options.map((option, index) => (
            <button
              aria-selected={option.value === value}
              className={
                option.value === value
                  ? 'custom-select__option custom-select__option--selected'
                  : 'custom-select__option'
              }
              key={option.value}
              onClick={() => {
                onChange(option.value)
                closeAndFocus()
              }}
              onFocus={() => setActiveIndex(index)}
              onKeyDown={(event) => handleOptionKeyDown(event, index)}
              ref={(element) => { optionRefs.current[index] = element }}
              role="option"
              tabIndex={index === activeIndex ? 0 : -1}
              type="button"
            >
              <span>
                <strong>{option.label}</strong>
                {option.description && <small>{option.description}</small>}
              </span>
              {option.value === value && <Check aria-hidden="true" size={14} />}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
